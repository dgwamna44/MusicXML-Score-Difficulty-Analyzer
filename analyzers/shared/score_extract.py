from music21 import meter, stream
from models import MeterData, RhythmGradeRules
from analyzers.meter.helpers import classify_meter, meter_segment_confidence

def extract_meter_segments(
    score,
    *,
    grade: float,
    rules_for_grade: RhythmGradeRules
) -> list[MeterData]:
    segments: list[MeterData] = []
    

    meters = score.parts[0].recurse().getElementsByClass(meter.TimeSignature)
    total_measures = score.parts[0].measure(-1).number

    if not meters:
        meters = [meter.TimeSignature("4/4")]

    for i, ts in enumerate(meters):
        start_measure = ts.getContextByClass(stream.Measure).number

        if i < len(meters) - 1:
            next_measure = meters[i + 1].getContextByClass(stream.Measure).number
            duration_measures = next_measure - start_measure
        else:
            duration_measures = total_measures - start_measure + 1

        m = MeterData(
            measure=start_measure,
            time_signature=ts.ratioString,
            grade=grade,
        )

        m.duration = duration_measures
        m.exposure = (duration_measures / total_measures) if total_measures else 0.0

        m.type = classify_meter(ts)  # "simple"/"compound"/"odd"/"mixed"
        m.confidence = meter_segment_confidence(m, rules_for_grade)

        if m.confidence == 0:
            m.comments["Time Signature"] = (
                f"{m.time_signature} not common for grade {grade}"
            )

        segments.append(m)

    return segments