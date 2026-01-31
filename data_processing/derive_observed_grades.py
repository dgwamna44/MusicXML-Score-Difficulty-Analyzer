from __future__ import annotations
from typing import Callable, Dict, Optional, Tuple
from app_data import GRADES


def derive_observed_grades(
    *,
    score_factory: Callable[[], object],
    analyze_confidence: Callable[[object, float], Optional[float]],
    grades=GRADES,
    flat_threshold: float = 0.97,
    flat_epsilon: float = 0.02,
    progress_cb: Optional[Callable[..., None]] = None,
) -> Tuple[Optional[float], Dict[float, Optional[float]]]:
    """
    Runs confidence-only analysis for each grade and derives an observed grade.

    Parameters
    ----------
    score_factory:
        A callable that returns a *fresh* score each time (re-parse or clone).
        (Important: avoids cross-grade mutation / caching issues.)
    analyze_confidence:
        Function(score, grade) -> confidence (0..1) or None
    flat_threshold:
        Minimum confidence level to consider the piece "easy enough" across grades.
    flat_epsilon:
        If the confidence curve is very flat (max-min <= flat_epsilon) AND
        all values are high (min >= flat_threshold), then choose lowest grade.

    Returns
    -------
    observed_grade, confidences_dict
    """

    confidences: Dict[float, Optional[float]] = {}

    total = len(grades)
    for idx, grade in enumerate(grades, start=1):
        score = score_factory()
        confidences[grade] = analyze_confidence(score, float(grade))
        if progress_cb is not None:
            progress_cb(float(grade), idx, total)

    observed = _derive_observed_grade(
        confidences,
        flat_threshold=flat_threshold,
        flat_epsilon=flat_epsilon,
    )
    return observed, confidences


def _derive_observed_grade(
    confidences: Dict[float, Optional[float]],
    *,
    flat_threshold: float,
    flat_epsilon: float,
) -> Optional[float]:
    filtered = {g: c for g, c in confidences.items() if c is not None}
    if not filtered:
        return None

    grades = sorted(filtered.keys())
    values = [filtered[g] for g in grades]

    # "too easy" / flat-high detector:
    if min(values) >= flat_threshold and (max(values) - min(values)) <= flat_epsilon:
        return grades[0]

    # choose grade with largest improvement over previous grade
    best_grade = grades[0]
    best_delta = float("-inf")
    for i in range(1, len(grades)):
        delta = values[i] - values[i - 1]
        if delta > best_delta:
            best_delta = delta
            best_grade = grades[i]

    return best_grade
