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
) -> Tuple[Optional[float], Dict[float, Optional[float]]]:
    """
    Runs confidence-only analysis for each grade and derives an observed grade.

    Parameters
    ----------
    score_factory:
        A callable that returns a *fresh* parsed score each time.
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

    for grade in grades:
        score = score_factory()
        confidences[grade] = analyze_confidence(score, float(grade))

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
    """
    If curve is high + flat -> lowest grade.
    Else -> grade with max confidence (ties -> lowest grade among ties).
    """

    # drop None
    filtered = {g: c for g, c in confidences.items() if c is not None}
    if not filtered:
        return None

    grades = sorted(filtered.keys())
    values = [filtered[g] for g in grades]

    # "too easy" = high AND flat
    if min(values) >= flat_threshold and (max(values) - min(values)) <= flat_epsilon:
        return grades[0]

    # otherwise pick max confidence; tie-break to lowest grade
    best_val = max(values)
    best_grades = [g for g in grades if filtered[g] == best_val]
    return min(best_grades)