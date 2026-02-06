from dataclasses import dataclass

@dataclass
class TempoData:
    bpm: int
    quarter_bpm: int
    beat_unit: str
    measure: int
    qtr_len: int
    grade: float
    exposure : float

    confidence: float | None = None
    comments : str | None = None
