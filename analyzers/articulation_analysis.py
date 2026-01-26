from collections import defaultdict
import math
from pathlib import Path
import pandas as pd

from app_data import GRADES
from models import PartialNoteData, ArticulationGradeRules

articulation_rules = {}
analysis_notes = {}
grade_summary = {}

def get_articulation_confidence(note, rules, grade):
    # Map music21 articulation names to our field names
    art_mapping = {
        'staccato': 'staccato',
        'tenuto': 'tenuto',
        'accent': 'accent',
        'strongAccent': 'marcato',  # marcato is strongAccent in music21
        'slur': 'slur'
    }
    
    articulations = [art_mapping.get(art.name, art.name) for art in note.articulations]
    
    if len(articulations) > 1:
        return (1, None, None) if rules[grade].multiple_articulations else (0, f"Multiple articulations per note are not common for grade {grade}", "multiple_articulations")
    else:
        for art in articulations:
            if hasattr(rules[grade], art):
                return (1, None, None) if getattr(rules[grade], art) else (0, f"{art} is not common for grade {grade}", art)
        return (1, None, None)  # If no recognized articulation, assume ok


def run(score_path : str, target_grade: float):

    from music21 import converter, stream, meter
    score = converter.parse(score_path)

    df = pd.read_csv(r"data\articulation_guidelines.csv")
    for _, row in df.iterrows():
        grade = float(row["grade"])
        articulation_rules[grade] = ArticulationGradeRules(
            grade=grade,
            staccato=bool(row["staccato"]),
            tenuto=bool(row["tenuto"]),
            accent=bool(row["accent"]),
            marcato=bool(row["marcato"]),
            multiple_articulations=bool(row["mult_articulation"]),
            slur=bool(row["slur"])
        )

    overall_total_dur = 0
    overall_weighted_conf = 0

    for part in score.parts:
        part_name = part.partName

        analysis_notes[part_name] = {}
        analysis_notes[part_name]["articulation_data"] = []

        partial_notes = []
        for m in part.getElementsByClass(stream.Measure):
            for n in m.notesAndRests:
                if n.isRest or len(n.articulations) == 0:
                    continue

                data = PartialNoteData(
                    measure=m.number,
                    offset=n.offset,
                    grade=target_grade,
                    instrument=part_name,
                    duration=n.duration.quarterLength
                )
                # get the result tuple (confidence, comment, comment_type)
                confidence, comment, commment_type = get_articulation_confidence(n, articulation_rules, target_grade)
                data.articulation_confidence = confidence
                if data.articulation_confidence == 0:
                    data.comments[commment_type] = comment
                partial_notes.append(data)
        analysis_notes[part_name]["articulation_data"] = partial_notes
        total_conf = sum([i.articulation_confidence * i.duration for i in partial_notes if i.articulation_confidence is not None])
        total_dur = sum([i.duration for i in partial_notes])
        if total_dur > 0:
            part_conf = total_conf / total_dur
            analysis_notes[part_name]["articulation_confidence"] = part_conf
            overall_weighted_conf += total_conf
            overall_total_dur += total_dur
        else:
            analysis_notes[part_name]["articulation_confidence"] = None

    grade_summary["target_grade"] = target_grade
    grade_summary["overall_articulation_confidence"] = overall_weighted_conf / overall_total_dur if overall_total_dur > 0 else None

    return analysis_notes, grade_summary
                
def derive_observed_grades(score_path: str):
    TOP_CONFIDENCE_THRESHOLD = 0.97
    articulation_confidences = {}

    for grade in GRADES:
        summary = run(score_path=score_path, target_grade=grade)[1]
        articulation_confidences[grade] = summary["overall_articulation_confidence"]

    articulation_improvements = {}
    sorted_grades = sorted(GRADES)
    for i in range(1,len(sorted_grades)):
        prev_grade = sorted_grades[i-1]
        curr_grade = sorted_grades[i]
        articulation_improvements[curr_grade] = articulation_confidences[curr_grade] - articulation_confidences[prev_grade]
    
    if min(articulation_improvements.values()) > TOP_CONFIDENCE_THRESHOLD:
        observed_articulation_grade = min(GRADES)
    else:
        observed_articulation_grade = max(articulation_confidences, key=articulation_confidences.get)

    return observed_articulation_grade, articulation_confidences
