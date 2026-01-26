from dataclasses import dataclass, field

@dataclass
class MeterData:
    measure: int
    time_signature: str
    grade: float

    type: str | None = None
    duration: int | None = None
    exposure: int | None = None
    confidence: float | None = None
    comments: dict = field(default_factory=dict)

