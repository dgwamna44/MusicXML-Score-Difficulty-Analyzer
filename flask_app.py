import json
import os
import tempfile
import uuid
import time
import threading

from flask import Flask, Response, jsonify, request, stream_with_context, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from app_data import FULL_GRADES, GRADES
from models import AnalysisOptions
from run_analysis import run_analysis_engine
from progress_tracker import progress_tracker

app = Flask(__name__, static_folder="html")
CORS(app, resources={r"/api/*": {"origins": "*"}})

UPLOAD_DIR = tempfile.mkdtemp(prefix="score_uploads_")

_INLINE_CANCEL_LOCK = threading.Lock()
_INLINE_CANCEL_FLAGS: dict[str, threading.Event] = {}


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


MAX_UPLOAD_BYTES = _env_int("MAX_UPLOAD_BYTES", 50_000_000)
MAX_QUEUE_SIZE = _env_int("MAX_QUEUE_SIZE", 8)
JOB_TIMEOUT_BASE = _env_int("JOB_TIMEOUT_BASE", 120)
JOB_TIMEOUT_PER_MB = _env_float("JOB_TIMEOUT_PER_MB", 8.0)
JOB_TIMEOUT_MIN = _env_int("JOB_TIMEOUT_MIN", 60)
JOB_TIMEOUT_MAX = _env_int("JOB_TIMEOUT_MAX", 900)

ANALYZER_NAMES = [
    "range",
    "articulation",
    "rhythm",
    "dynamics",
    "availability",
    "key",
    "tempo",
    "meter",
    "duration",
    "scoring",
]


def make_json_safe(value):
    if isinstance(value, dict):
        return {str(key): make_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return make_json_safe(vars(value))
    return str(value)


def _register_inline_cancel(cancel_id: str | None) -> threading.Event | None:
    if not cancel_id:
        return None
    with _INLINE_CANCEL_LOCK:
        event = _INLINE_CANCEL_FLAGS.get(cancel_id)
        if event is None:
            event = threading.Event()
            _INLINE_CANCEL_FLAGS[cancel_id] = event
        return event


def _pop_inline_cancel(cancel_id: str | None) -> None:
    if not cancel_id:
        return
    with _INLINE_CANCEL_LOCK:
        _INLINE_CANCEL_FLAGS.pop(cancel_id, None)


def _cancel_inline(cancel_id: str) -> bool:
    with _INLINE_CANCEL_LOCK:
        event = _INLINE_CANCEL_FLAGS.get(cancel_id)
        if event is None:
            return False
        event.set()
        return True


def parse_bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def estimate_timeout(file_size_bytes: int | None) -> int:
    if not file_size_bytes or file_size_bytes <= 0:
        return JOB_TIMEOUT_BASE
    size_mb = file_size_bytes / (1024 * 1024)
    timeout = JOB_TIMEOUT_BASE + size_mb * JOB_TIMEOUT_PER_MB
    timeout = max(JOB_TIMEOUT_MIN, timeout)
    timeout = min(JOB_TIMEOUT_MAX, timeout)
    return int(timeout)




def ensure_score_path(payload):
    return payload.get("score_path")


@app.get("/")
def index():
    return send_from_directory("html", "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory("html", filename)

@app.get("/verovio/dist/<path:filename>")
def verovio_dist(filename):
    return send_from_directory("verovio/dist", filename)


def _tracker_names(name: str) -> tuple[str, ...]:
    if name == "key_range":
        return ("key", "range")
    if name == "tempo_duration":
        return ("tempo", "duration")
    return (name,)


def _track_progress_event(job_id: str, event: dict) -> None:
    event_type = event.get("type")
    analyzer = event.get("analyzer")
    if not analyzer:
        return
    names = _tracker_names(str(analyzer))
    if event_type == "analyzer_start":
        for name in names:
            progress_tracker.start_analyzer(job_id, name)
    elif event_type == "analyzer_done":
        duration = event.get("duration")
        for name in names:
            progress_tracker.complete_analyzer(job_id, name, duration=duration)
    elif event_type == "observed":
        idx = event.get("idx") or 0
        total = event.get("total") or 0
        for name in names:
            progress_tracker.update_analyzer_progress(
                job_id,
                name,
                items_processed=int(idx),
                total_items=int(total) if total else None,
            )


def _run_job(job_id, payload):
    progress_tracker.start_job(job_id)
    score_path = payload.get("score_path")

    def progress_cb(event):
        safe_event = make_json_safe(event)
        progress_tracker.push_event(job_id, safe_event)
        _track_progress_event(job_id, safe_event)

    try:
        target_only = parse_bool(payload.get("target_only"))
        strings_only = parse_bool(payload.get("strings_only"))
        full_grade = parse_bool(payload.get("full_grade_analysis"))
        target_grade = float(payload.get("target_grade", 2))
        observed_grades = None

        if target_only is False:
            observed_grades = FULL_GRADES if full_grade else GRADES
        options = AnalysisOptions(
            run_observed=not target_only,
            string_only=strings_only,
            observed_grades=observed_grades,
        )

        if not score_path:
            raise RuntimeError("Missing score file for analysis.")

        timeout_seconds = payload.get("timeout_seconds")
        deadline = (
            time.monotonic() + float(timeout_seconds)
            if timeout_seconds
            else None
        )
        result = run_analysis_engine(
            score_path,
            target_grade,
            analysis_options=options,
            progress_cb=progress_cb,
            deadline=deadline,
        )
        safe_result = make_json_safe(result)
        progress_tracker.set_result(job_id, safe_result)
        progress_tracker.finalize_analyzers(job_id)
        progress_tracker.push_event(job_id, {"type": "result", "data": safe_result})
    except Exception as exc:
        progress_tracker.set_error(job_id, str(exc))
        progress_tracker.push_event(job_id, {"type": "error", "message": str(exc)})
    finally:
        if score_path and os.path.exists(score_path):
            try:
                os.remove(score_path)
            except Exception:
                pass
        progress_tracker.mark_done(job_id)
        progress_tracker.push_event(job_id, {"type": "done"})


def _handle_analyze(*, force_inline: bool = False):
    payload = {}
    pending_upload = None
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        form = request.form
        uploaded = request.files.get("score_file")
        if uploaded:
            filename = secure_filename(uploaded.filename or "score.musicxml")
            ext = os.path.splitext(filename)[1] or ".musicxml"
            data = uploaded.read()
            if len(data) > MAX_UPLOAD_BYTES:
                return jsonify({"error": "Score too large"}), 413
            pending_upload = {
                "data": data,
                "ext": ext,
                "file_size": len(data),
            }
        payload["target_only"] = form.get("target_only") == "true"
        payload["strings_only"] = form.get("strings_only") == "true"
        payload["full_grade_analysis"] = form.get("full_grade_analysis") == "true"
        if form.get("debug_inline") is not None:
            payload["debug_inline"] = form.get("debug_inline")
        if form.get("target_grade"):
            payload["target_grade"] = float(form.get("target_grade"))
    else:
        payload = request.get_json(force=True, silent=True) or {}

    if not payload.get("score_path") and not pending_upload:
        return jsonify({"error": "Missing score or target grade."}), 400
    if "target_grade" not in payload:
        return jsonify({"error": "Missing score or target grade."}), 400
    if pending_upload:
        payload["file_size"] = pending_upload["file_size"]
    if payload.get("score_path") and not payload.get("file_size"):
        try:
            payload["file_size"] = os.path.getsize(payload["score_path"])
        except OSError:
            payload["file_size"] = None
    if payload.get("file_size") and payload["file_size"] > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Score too large"}), 413

    timeout_seconds = estimate_timeout(payload.get("file_size"))
    payload["timeout_seconds"] = timeout_seconds

    inline_requested = (
        force_inline
        or parse_bool(request.args.get("debug_inline"))
        or parse_bool(payload.get("debug_inline"))
        or os.environ.get("ANALYZE_INLINE") == "1"
    )
    host = request.host or ""
    is_local_request = host.startswith("127.0.0.1") or host.startswith("localhost")
    inline_allowed = inline_requested and (
        app.debug or os.environ.get("ALLOW_INLINE_ANALYSIS") == "1" or is_local_request
    )

    if inline_allowed:
        cancel_id = payload.get("cancel_id") or request.args.get("cancel_id")
        cancel_event = _register_inline_cancel(str(cancel_id) if cancel_id else None)

        if pending_upload and not payload.get("score_path"):
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=pending_upload["ext"], dir=UPLOAD_DIR
            )
            tmp.write(pending_upload["data"])
            tmp.flush()
            tmp.close()
            payload["score_path"] = tmp.name
        score_path = ensure_score_path(payload)
        if not score_path:
            return jsonify({"error": "Missing score file for analysis."}), 400
        target_only = parse_bool(payload.get("target_only"))
        strings_only = parse_bool(payload.get("strings_only"))
        full_grade = parse_bool(payload.get("full_grade_analysis"))
        target_grade = float(payload.get("target_grade", 2))
        observed_grades = None
        if target_only is False:
            observed_grades = FULL_GRADES if full_grade else GRADES
        options = AnalysisOptions(
            run_observed=not target_only,
            string_only=strings_only,
            observed_grades=observed_grades,
        )
        deadline = time.monotonic() + float(timeout_seconds)
        def _inline_progress(_event):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Analysis cancelled.")

        try:
            result = run_analysis_engine(
                score_path,
                target_grade,
                analysis_options=options,
                progress_cb=_inline_progress,
                deadline=deadline,
            )
            return jsonify(make_json_safe(result))
        except RuntimeError as exc:
            if cancel_event and cancel_event.is_set():
                return jsonify({"error": "Analysis cancelled."}), 409
            raise exc
        finally:
            _pop_inline_cancel(str(cancel_id) if cancel_id else None)

    if pending_upload and not payload.get("score_path"):
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=pending_upload["ext"], dir=UPLOAD_DIR
        )
        tmp.write(pending_upload["data"])
        tmp.flush()
        tmp.close()
        payload["score_path"] = tmp.name

    job_id = str(uuid.uuid4())
    if MAX_QUEUE_SIZE and progress_tracker.active_count() >= MAX_QUEUE_SIZE:
        return jsonify({"error": "Analysis queue full. Try again shortly."}), 429
    progress_tracker.create_job(job_id, ANALYZER_NAMES)
    worker = threading.Thread(
        target=_run_job,
        args=(job_id, payload),
        daemon=True,
    )
    worker.start()

    return jsonify({"job_id": job_id})


@app.post("/api/analyze")
def analyze():
    return _handle_analyze()


@app.post("/api/analyze_sync")
def analyze_sync():
    return _handle_analyze(force_inline=True)


@app.post("/api/cancel/<cancel_id>")
def cancel_inline(cancel_id):
    if _cancel_inline(cancel_id):
        return jsonify({"ok": True, "cancel_id": cancel_id})
    return jsonify({"ok": False, "error": "Unknown cancel id"}), 404


@app.get("/api/progress/<job_id>")
def progress(job_id):
    if not progress_tracker.has_job(job_id):
        return jsonify({"error": "Unknown job"}), 404

    def generate():
        last_heartbeat = time.time()
        last_progress = None
        while True:
            event = progress_tracker.pop_event(job_id, timeout=0.5)
            if event:
                yield f"data: {json.dumps(event)}\n\n"
                last_heartbeat = time.time()
                if event.get("type") == "done":
                    break
                continue

            progress = progress_tracker.get_job_progress(job_id)
            if progress is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                break
            if progress != last_progress:
                yield f"data: {json.dumps({'type': 'progress', 'data': progress})}\n\n"
                last_progress = progress

            if progress_tracker.is_done(job_id):
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            now = time.time()
            if now - last_heartbeat >= 10:
                last_heartbeat = now
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.get("/api/result/<job_id>")
def result(job_id):
    if not progress_tracker.has_job(job_id):
        return jsonify({"error": "Unknown job"}), 404
    payload = progress_tracker.get_job_progress(job_id) or {}
    result_data = progress_tracker.get_result(job_id)
    response = {
        "done": payload.get("status") in {"done", "error"},
        "error": payload.get("error"),
        "result": result_data,
    }
    if response["done"]:
        progress_tracker.cleanup_job(job_id)
    return jsonify(make_json_safe(response))


@app.get("/healthz")
def healthz():
    version_file = os.path.join(os.path.dirname(__file__), ".healthz_version")
    version = None
    try:
        with open(version_file, "r", encoding="utf-8") as handle:
            version = handle.read().strip()
    except OSError:
        version = None
    return jsonify({"ok": True, "version": version})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
