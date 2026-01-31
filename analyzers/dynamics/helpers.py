import pandas as pd
from music21 import dynamics, stream


def load_dynamics_table(path: str = r"data/dynamics_guidelines.csv") -> dict[float, dict[str, bool]]:
    """
    Returns: {grade: {dynamic: bool}}
    CSV format:
      - first column: dynamic marking (e.g., "pp", "mf", "cresc")
      - remaining columns: grades (e.g., 0.5, 1, 1.5, ...)
      - values: TRUE/FALSE
    """
    df = pd.read_csv(path)
    if df.empty:
        return {}

    dynamic_col = df.columns[0]
    rules: dict[float, dict[str, bool]] = {}

    for col in df.columns[1:]:
        grade = float(col)
        rules[grade] = {}
        for _, row in df.iterrows():
            dynamic = str(row[dynamic_col]).strip()
            val = row[col]
            if pd.isna(val):
                continue
            rules[grade][dynamic] = str(val).strip().upper() == "TRUE"

    return rules


def load_dynamics_rules(path: str = r"data/dynamics_guidelines.csv") -> dict[float, dict[str, bool]]:
    return load_dynamics_table(path)

def derive_dynamics_data(score):
    total_length = len(score.parts[0].recurse().getElementsByClass(stream.Measure)) * 4
    part_rows = {}
    for idx, part in enumerate(score.parts):
        part_name = part.partName or f"Part {idx + 1}"
        dyns = []
        end_offset = part.highestTime
        part_dyns = list(part.recurse().getElementsByClass(dynamics.Dynamic))
        part_dyns.sort(key=lambda d: d.getOffsetInHierarchy(part))

        for i, d in enumerate(part_dyns):
            start = d.getOffsetInHierarchy(part)
            end = part_dyns[i + 1].getOffsetInHierarchy(part) if i + 1 < len(part_dyns) else end_offset
            data = {
                "part": part_name,
                "measure": d.measureNumber,
                "dynamic": d.value,
                "start_qL": start,
                "end_qL": end,
                "effective_duration": max(0.0, end - start),
            }
            data["exposure"] = round(data["effective_duration"] / total_length, 3) if total_length else 0.0
            dyns.append(data)
        part_rows[part_name] = dyns
    return part_rows
