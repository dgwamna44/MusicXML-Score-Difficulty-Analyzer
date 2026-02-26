from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field


@dataclass
class AnalyzerProgress:
    status: str = "pending"
    items_processed: int = 0
    total_items: int = 0
    progress: float = 0.0
    started_at: float | None = None
    duration: float | None = None


@dataclass
class JobProgress:
    job_id: str
    analyzers: dict[str, AnalyzerProgress]
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    current_analyzer: str | None = None
    result: dict | None = None
    error: str | None = None
    events: "queue.Queue[dict]" = field(default_factory=queue.Queue)


class ProgressTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobProgress] = {}

    def create_job(self, job_id: str, analyzer_names: list[str]) -> None:
        with self._lock:
            analyzers = {name: AnalyzerProgress() for name in analyzer_names}
            self._jobs[job_id] = JobProgress(job_id=job_id, analyzers=analyzers)

    def start_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.last_update = time.time()

    def start_analyzer(self, job_id: str, name: str, total_items: int | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            analyzer = job.analyzers.get(name)
            if not analyzer:
                return
            analyzer.status = "running"
            analyzer.started_at = time.time()
            if total_items is not None:
                analyzer.total_items = max(int(total_items), 0)
            job.current_analyzer = name
            job.last_update = time.time()

    def update_analyzer_progress(
        self,
        job_id: str,
        name: str,
        *,
        items_processed: int,
        total_items: int | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            analyzer = job.analyzers.get(name)
            if not analyzer:
                return
            analyzer.items_processed = max(int(items_processed), 0)
            if total_items is not None:
                analyzer.total_items = max(int(total_items), 0)
            total = analyzer.total_items
            analyzer.progress = (
                min(1.0, analyzer.items_processed / total) if total else analyzer.progress
            )
            job.last_update = time.time()

    def complete_analyzer(self, job_id: str, name: str, duration: float | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            analyzer = job.analyzers.get(name)
            if not analyzer:
                return
            analyzer.status = "done"
            analyzer.progress = 1.0
            if duration is None and analyzer.started_at is not None:
                duration = time.time() - analyzer.started_at
            analyzer.duration = duration
            if job.current_analyzer == name:
                job.current_analyzer = None
            job.last_update = time.time()

    def set_result(self, job_id: str, result: dict) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.result = result
            job.status = "done"
            job.last_update = time.time()

    def set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.error = error
            job.status = "error"
            job.last_update = time.time()

    def mark_done(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job.status not in {"error"}:
                job.status = "done"
            job.last_update = time.time()

    def finalize_analyzers(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for analyzer in job.analyzers.values():
                if analyzer.status != "done":
                    analyzer.status = "done"
                    analyzer.progress = 1.0
            job.last_update = time.time()

    def push_event(self, job_id: str, event: dict) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.events.put(event)
            job.last_update = time.time()

    def pop_event(self, job_id: str, timeout: float) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        try:
            return job.events.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_job_progress(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            analyzers = {
                name: {
                    "status": a.status,
                    "progress": a.progress,
                    "items_processed": a.items_processed,
                    "total_items": a.total_items,
                    "duration": a.duration,
                }
                for name, a in job.analyzers.items()
            }
            return {
                "job_id": job.job_id,
                "status": job.status,
                "current_analyzer": job.current_analyzer,
                "analyzers": analyzers,
                "last_update": job.last_update,
                "error": job.error,
            }

    def get_result(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return job.result

    def is_done(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return True
            return job.status in {"done", "error"}

    def has_job(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs

    def cleanup_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job.status in {"pending", "running"})


progress_tracker = ProgressTracker()
