# rules_key_range.py
from app_data import (
    GRADE_TO_KEY_TABLE,
    PUBLISHER_CATALOG_FREQUENCY,
    MAJOR_DIATONIC_MAP,
    MINOR_DIATONIC_MAP
)
from utilities import confidence_curve
from utilities.instrument_rules import clarinet_break_allowed, crosses_break




# ------------------------------
# KEY CONFIDENCE
# ------------------------------

def publisher_key_support(key, grade):
    return sum(max_grade <= grade for max_grade in GRADE_TO_KEY_TABLE[key].values())


def publisher_key_confidence(key, grade):
    total_sources = len(GRADE_TO_KEY_TABLE[key])
    evidence = publisher_key_support(key, grade)
    return confidence_curve(evidence, normalize=total_sources, k=2.0, max_conf=0.80)


def catalog_key_confidence(key, grade):
    exposure = sum(
        count for g, count in PUBLISHER_CATALOG_FREQUENCY[key].items() if g <= grade
    )
    total = sum(PUBLISHER_CATALOG_FREQUENCY[key].values()) or 1
    return confidence_curve(exposure, normalize=total, k=1.2, max_conf=0.20)


def total_key_confidence(key, grade):
    return publisher_key_confidence(key, grade) + catalog_key_confidence(key, grade)


# ------------------------------
# RANGE CONFIDENCE
# ------------------------------

def harmonic_tolerance_penalty(grade):
    return 0.45 - ((grade - 1) * 0.1)


def compute_range_confidence(note, core, ext, total, target_grade, key_quality):
    """
    Computes per-note range confidence with harmonic penalties.
    """
    midi = note.sounding_midi_value
    rel = note.relative_key_index

    # -------------- Range position --------------
    if core and core[0] <= midi <= core[1]:
        conf = 1.0
    elif ext[0] <= midi <= ext[1]:
        conf = 0.6
        note.comments["range"] = f"{note.written_pitch} in extended range for grade {target_grade}"
    elif total[0] <= midi <= total[1]:
        conf = 0.25
        note.comments["range"] = f"{note.written_pitch} out of range for grade {target_grade}"
    else:
        conf = 0.0
        note.comments["range"] = f"{note.written_pitch} out of range altogether for {note.instrument}"

    # -------------- Clarinet break penalty --------------
    if clarinet_break_allowed(target_grade, note.instrument) is not None:
        if crosses_break(note.written_pitch):
            allowed = clarinet_break_allowed(target_grade, note.instrument)
            if allowed:
                conf = max(0.0, conf - 0.1)
                note.comments["crosses_break"] = f"Clarinet break crossed (allowed for grade {target_grade}/{note.instrument})"
            else:
                conf = max(0.0, conf - 0.25)
                note.comments["crosses_break"] = f"Clarinet break crossed (not allowed for grade {target_grade})"

    # -------------- Harmonic Tolerance Penalty --------------
    penalty = harmonic_tolerance_penalty(target_grade)
    if key_quality == "major":
        if rel not in MAJOR_DIATONIC_MAP:
            conf = max(0.0, conf - penalty)
    else:  # minor
        if (rel not in MINOR_DIATONIC_MAP) and rel != 11:
            conf = max(0.0, conf - penalty)

    return max(0.0, conf)
