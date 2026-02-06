from music21 import stream, tempo
from models import TempoData
from typing import List

def _quarter_bpm(mark: tempo.MetronomeMark) -> int | None:
    if hasattr(mark, "getQuarterBPM") and mark.getQuarterBPM() is not None:
        return int(round(mark.getQuarterBPM()))
    if mark.number and mark.referent and mark.referent.quarterLength:
        return int(round(mark.number * mark.referent.quarterLength))
    if mark.number:
        return int(round(mark.number))
    return None


def _beat_unit(mark: tempo.MetronomeMark) -> str:
    if mark.referent and getattr(mark.referent, "fullName", None):
        return str(mark.referent.fullName)
    if mark.referent and getattr(mark.referent, "name", None):
        return str(mark.referent.name)
    return "quarter"


def build_tempo_marks(score) -> List[tuple[int, int, str, int]]:
    marks = []
    for m in score.parts[0].getElementsByClass(stream.Measure):
        for t in m.getElementsByClass(tempo.MetronomeMark):
            if t.number:
                qpm = _quarter_bpm(t)
                beat_unit = _beat_unit(t)
                if qpm is not None:
                    marks.append((m.number, int(t.number), beat_unit, qpm))
    return marks


def build_tempo_segments(score, tempo_marks: List[tuple[int, int, str, int]]) -> List[TempoData]:
    measures = score.parts[0].getElementsByClass(stream.Measure)
    total_measures = measures[-1].number

    if not tempo_marks:
        # default "unknown" tempo segment; you can choose 100 or whatever default
        return [
            TempoData(
                bpm=100,
                quarter_bpm=100,
                beat_unit="quarter",
                measure=1,
                exposure=1.0,
                grade=0.0,
                qtr_len=total_measures * 4,
                confidence=0.0,
                comments="No tempo markings found; using default 100 BPM"
            )
        ]

    tempo_marks = sorted(tempo_marks, key=lambda x: x[0])
    segments: List[TempoData] = []

    for i, (start, bpm, beat_unit, quarter_bpm) in enumerate(tempo_marks):
        end_measure = tempo_marks[i + 1][0] if i + 1 < len(tempo_marks) else total_measures + 1
        length = max(0, end_measure - start)
        exposure = length / total_measures if total_measures else 0

        segments.append(
            TempoData(
                bpm=bpm,
                quarter_bpm=quarter_bpm,
                beat_unit=beat_unit,
                measure=start,
                exposure=exposure,
                grade=0.0,
                qtr_len=length * 4,
                confidence=0.0
            )
        )

    return segments


def get_tempo_score(bpm: int, low: int, high: int) -> float:
    return 1.0 if low <= bpm <= high else 0.0
