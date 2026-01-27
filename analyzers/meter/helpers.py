from models import RhythmGradeRules

def meter_segment_confidence(segment, rules: RhythmGradeRules):
    c = segment.type
    if c == "compound":
        return 1 if rules.allow_compound else 0
    if c == "mixed":
        return 1 if rules.allow_mixed_compound else 0
    if c == "odd":
        return 1 if rules.allow_easy_compound else 0
    return 1  # simple meter always allowed

def classify_meter(ts):
    num, denom = map(int, ts.ratioString.split("/"))
    if num in (2, 3, 4) and denom == 4:
        return "simple"
    elif num in (6, 9, 12) and denom == 8:
        return "compound"
    elif denom == 8 and num % 3 != 0:
        return "odd"
    else:
        return "mixed"
