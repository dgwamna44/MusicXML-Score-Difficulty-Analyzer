from copy import deepcopy

from models import BaseAnalyzer
from utilities import get_rounded_grade
from music21 import converter
from statistics import mean

from data_processing import derive_observed_grades
from .helpers import load_dynamics_rules, derive_dynamics_data

class DynamicsAnalyzer(BaseAnalyzer):
    
    def analyze_confidence(self, score, grade: float):
        return analyze_dynamics_confidence(score, self.rules, grade)

    def analyze_target(self, score, target_grade: float):
        return analyze_dynamics_target(score, self.rules, target_grade)
    
def run_dynamics(score_path, target_grade, *, score=None, score_factory=None, progress_cb=None, run_observed=True):
    rounded_grade = get_rounded_grade(target_grade)
    rules = load_dynamics_rules()[rounded_grade]
    analyzer = DynamicsAnalyzer(rules)

    if score_factory is None:
        if score is not None:
            score_factory = lambda: deepcopy(score)
        elif score_path is not None:
            score_factory = lambda: converter.parse(score_path)
        else:
            raise ValueError("score_path or score_factory is required")

    if run_observed:
        observed, confidences = derive_observed_grades(
            score_factory=score_factory,
            analyze_confidence=analyzer.analyze_confidence,
            progress_cb=progress_cb,
        )
    else:
        observed, confidences = None, {}

    if score is None:
        score = score_factory()
    analysis_notes, overall_conf = analyzer.analyze_target(score, target_grade)

    return {
        "observed_grade": observed,
        "confidences": confidences,
        "analysis_notes": analysis_notes,
        "overall_confidence": overall_conf,
    }

def analyze_dynamics_confidence(score, rules, grade):
    confidences = []
    dynamics_data = derive_dynamics_data(score)
    for part in dynamics_data:
        for dynamic in dynamics_data[part]:
            conf = dynamic["exposure"] if rules[dynamic['dynamic']] == True else 0
            confidences.append(conf)
    return mean(confidences) if len(confidences) > 1 else None

        
def analyze_dynamics_target(score, rules, target_grade):
    analysis_notes = {}
    dynamics_data = derive_dynamics_data(score)
    confidences = []
    for part_name, part_dyns in dynamics_data.items():
        part_confidence = []
        analysis_notes[part_name] = {}
        for dynamic in part_dyns:
            dyn_name = dynamic["dynamic"]
            if rules.get(dyn_name) is True:
                part_confidence.append(dynamic["exposure"])
            else:
                part_confidence.append(0)
                analysis_notes[part_name][dyn_name] = (
                    f"{dyn_name} at measure {dynamic['measure']} not common for grade {target_grade}."
                )
        confidences.append(sum(part_confidence))
    overall_conf = mean(confidences) if confidences else 0.0
    return analysis_notes, overall_conf
