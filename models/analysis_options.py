from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisOptions:
    run_observed: bool = True
    string_only: bool = False
