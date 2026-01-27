from app_data import RHYTHM_TOKEN_MAP
from analyzers.rhythm.helpers import check_syncopation, get_quarter_length
from analyzers.rhythm.rules import normalize_tuplet_class

def rule_dotted(note, rules, target_grade):
    if "d" not in note.rhythm_token:
        return (1, None, None)
    if rules.allow_dotted:
        return (1, None, None)
    return (0, f"dotted rhythms not common for grade {target_grade}", "Dotted Rhythm")

def rule_syncopation(note, rules, target_grade):
    _, is_sync = check_syncopation(
        note.duration,
        note.offset
    )
    if not is_sync:
        return (1, None, None)
    return (1, None, None) if rules.allow_syncopation else (0, f"syncopation not common for grade {target_grade}", "Syncopation")


def rule_subdivision(note, rules, target_grade):
    note_duration = get_quarter_length(note.rhythm_token)
    if note_duration is None:
        return (1, None, None)
    max_allowed = RHYTHM_TOKEN_MAP.get(rules.max_subdivision, {}).get("duration", 0)
    if note_duration <= max_allowed:
        return (1, None, None)
    else:
        return (0, f"subdivisions smaller than {rules.max_subdivision} not common for grade {target_grade}", "Subdivision")

def rule_tuplet(note, rules, target_grade):
    if note.tuplet_id is None:
        return (1, None, None)
    if not rules.allow_tuplet:
        return (0, "Triplets not common for given grade", "Tuplets")
    if tuplet_class := normalize_tuplet_class(note.tuplet_class):
        if tuplet_class in rules.allowed_tuplet_classes:
            return (1, None, None)
        else:
            return (0, f"{tuplet_class} tuplets not common for grade {target_grade}", "Tuplets")
        