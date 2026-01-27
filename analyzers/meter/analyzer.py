# analyzers/meter/analyzer.py
from __future__ import annotations

from music21 import converter

from analyzers.base import BaseAnalyzer
from analyzers.shared.score_extract import extract_meter_segments
from analyzers.rhythm.rules import load_rhythm_rules
from data_processing import derive_observed_grades


class MeterAnalyzer(BaseAnalyzer):
    """
    Expects self.rules = {grade(float): RhythmGradeRules}
    """

    def analyze_confidence(self, score, grade: float) -> float | None:
        rules_for_grade = self.rules.get(grade)
        if rules_for_grade is None:
            return None

        meter_data = extract_meter_segments(score, grade=grade, rules_for_grade=rules_for_grade)
        return sum((m.confidence or 0.0) * (m.exposure or 0.0) for m in meter_data)

    def analyze_target(self, score, target_grade: float):
        rules_for_grade = self.rules.get(target_grade)
        if rules_for_grade is None:
            return [], None

        meter_data = extract_meter_segments(score, grade=target_grade, rules_for_grade=rules_for_grade)

        base_total = sum((m.confidence or 0.0) * (m.exposure or 0.0) for m in meter_data)
        total_conf = base_total

        # Apply penalties for frequent meter changes
        if target_grade < 2 and len(meter_data) > 1:
            for m in meter_data:
                m.comments["meter_changes"] = "Meter changes not common for lower grades"
            total_conf = 0.6 * base_total

        elif target_grade < 3 and len(meter_data) > 3:
            for m in meter_data:
                m.comments["meter_changes"] = "Frequent meter changes not common for mid grades"
            total_conf = 0.6 * base_total

        return meter_data, total_conf


def run_meter(score_path: str, target_grade: float):
    score = converter.parse(score_path)

    # shared rhythm rules drive both rhythm + meter
    rules = load_rhythm_rules()
    analyzer = MeterAnalyzer(rules)

    observed_grade, confidences = derive_observed_grades(
        score_factory=lambda: converter.parse(score_path),
        analyze_confidence=lambda score, g: analyzer.analyze_confidence(score, g),  
    )

    meter_segments, overall_conf = analyzer.analyze_target(score, target_grade)

    return {
        "observed_grade": observed_grade,
        "confidences": confidences,
        "meter_segments": meter_segments,
        "overall_confidence": overall_conf,
    }
