from copy import deepcopy
from time import perf_counter
import argparse

from music21 import converter

from analyzers.articulation.articulation import run_articulation
from analyzers.rhythm import run_rhythm
from analyzers.meter import run_meter
from analyzers.key_range import run_key_range
from analyzers.availability.availability import run_availability
from analyzers.tempo_duration import run_tempo_duration
from analyzers.dynamics import run_dynamics
from models import AnalysisOptions

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target-only",
        "--target_only",
        action="store_true",
        help="Skip observed-grade analysis and run target-grade analysis only.",
    )
    parser.add_argument(
        "--strings-only",
        "--strings_only",
        action="store_true",
        help="Use string-only key/range guidelines.",
    )
    args = parser.parse_args()

    target_grade = 3

    test_files = [r"input_files\test.musicxml",
                  r"input_files\multiple_meter_madness.musicxml",
                  r"input_files\duration_test.musicxml",
                  r"input_files\multiple_instrument_test.musicxml",
                  r"input_files\articulation_test.musicxml",
                  r"input_files\chord_test.musicxml",
                  r"input_files\dynamics_test.musicxml",
                  r"input_files\ijo.musicxml"]
    
    score_path = test_files[-1]
    base_score = converter.parse(score_path)
    score_factory = lambda: deepcopy(base_score)

    def progress_bar(name):
        bar_width = 50
        started = perf_counter()
        label_started = {}

        def _cb(grade, idx, total, label=None):
            if label not in label_started:
                label_started[label] = perf_counter()
            elapsed = perf_counter() - label_started[label]
            filled = int((idx / total) * bar_width) if total else 0
            bar = "[" + ("#" * filled) + ("-" * (bar_width - filled)) + "]"
            suffix = f" {label}" if label else ""
            print(
                f"{name}{suffix} {bar} {idx}/{total} (grade {grade}) {elapsed:.1f}s",
                end="\r",
                flush=True,
            )
            if idx >= total:
                print()

        return _cb

    def target_progress_bar(total):
        bar_width = 50
        started = perf_counter()

        def _cb(idx, name):
            elapsed = perf_counter() - started
            filled = int((idx / total) * bar_width) if total else 0
            bar = "[" + ("#" * filled) + ("-" * (bar_width - filled)) + "]"
            print(f"target_only {bar} {idx}/{total} ({name}) {elapsed:.1f}s", end="\r", flush=True)
            if idx >= total:
                print()

        return _cb

    options = AnalysisOptions(
        run_observed=not args.target_only,
        string_only=args.strings_only,
    )
    target_only = args.target_only
    analyzers = [
        ("availability", run_availability),
        ("dynamics", run_dynamics),
        ("key_range", run_key_range),
        ("tempo_duration", run_tempo_duration),
        ("articulation", run_articulation),
        ("rhythm", run_rhythm),
        ("meter", run_meter),
    ]
    target_progress = target_progress_bar(len(analyzers))

    results = {}
    for idx, (name, fn) in enumerate(analyzers, start=1):
        results[name] = fn(
            score_path,
            target_grade,
            score=score_factory(),
            score_factory=score_factory,
            progress_cb=None if target_only else progress_bar(name),
            analysis_options=options,
        )
        if target_only:
            target_progress(idx, name)

    ava = results["availability"]
    dyn = results["dynamics"]
    kr = results["key_range"]
    temp = results["tempo_duration"]
    art = results["articulation"]
    rhy = results["rhythm"]
    met = results["meter"]
    
    print("done")
