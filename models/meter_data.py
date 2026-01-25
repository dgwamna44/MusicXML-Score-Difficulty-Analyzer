from dataclasses import dataclass

@dataclass
class MeterData:
    measure: int
    time_signature: str
    grade: float

<<<<<<< HEAD
    type: str | None = None
    duration: int | None = None
    exposure: int | None = None
    confidence: float | None = None
    comments: str | None = None

=======
    duration: int | None = None
    exposure: int | None = None
    confidence: float | None = None
    comments: dict | None = None
>>>>>>> e685a87d21ca719a0784bc37bbbdb6d9c949820c
