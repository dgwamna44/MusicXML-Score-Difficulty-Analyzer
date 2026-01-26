from dataclasses import dataclass

@dataclass
class ArticulationGradeRules:
    grade: float
    staccato: bool
    tenuto: bool
    accent: bool
    marcato: bool
    slur: bool
    multiple_articulations: bool
