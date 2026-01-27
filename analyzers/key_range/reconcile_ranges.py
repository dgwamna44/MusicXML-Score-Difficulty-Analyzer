import pandas as pd
from pathlib import Path
from functools import reduce
from music21 import pitch

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2] 
RANGE_DIR = BASE_DIR / "data" / "range"

MASTER_RANGE = {}
COMBINED_RANGES = {}

def unpack_range_file(path: Path, publisher_id: int, master: dict) -> None:
    df = pd.read_csv(path)

    if "Instrument" not in df.columns:
        raise ValueError(f"{path} missing 'Instrument' column. Found: {list(df.columns)}")

    grade_columns = [c for c in df.columns if c != "Instrument"]
    if not grade_columns:
        raise ValueError(f"{path} has no grade columns besides 'Instrument'.")

    for _, row in df.iterrows():
        inst = str(row["Instrument"]).strip()
        if not inst:
            continue

        master.setdefault(inst, {})
        master[inst].setdefault(publisher_id, {})

        for grade_col in grade_columns:
            cell = row.get(grade_col)

            # skip blanks
            if pd.isna(cell):
                continue

            s = str(cell).strip()
            if not s:
                continue

            delimiter = "," if "," in s else "-"
            try:
                midi_vals = [pitch.Pitch(r.strip()).midi for r in s.split(delimiter)]
            except Exception as e:
                raise ValueError(f"Bad pitch cell in {path} inst={inst} grade={grade_col} value={s}") from e

            master[inst][publisher_id][float(grade_col)] = midi_vals


def load_ranges(range_dir: Path):
    range_dir = Path(range_dir)
    if not range_dir.exists():
        raise FileNotFoundError(f"Range dir not found: {range_dir.resolve()}")

    files = sorted([p for p in range_dir.iterdir() if p.suffix.lower() == ".csv"])
    if not files:
        raise FileNotFoundError(f"No CSV files found in: {range_dir.resolve()}")

    master = {}
    for i, f in enumerate(files, start=1):
        unpack_range_file(f, i, master)

    # quick sanity check
    num_instruments = len(master)
    num_publishers = len(files)
    sample_inst = next(iter(master.keys()), None)

    if num_instruments == 0:
        raise RuntimeError("Loaded 0 instruments from range CSVs. Check parsing assumptions.")

    print(f"[Ranges] Loaded {num_instruments} instruments from {num_publishers} CSVs. "
          f"Example instrument: {sample_inst}")

    return master



def reconcile_ranges():
    """
    Computes core + extended ranges across all publishers.
    """
    for inst, collections in MASTER_RANGE.items():
        COMBINED_RANGES[inst] = {}
        all_grades = sorted({g for c in collections.values() for g in c.keys()})
        max_grade = float(all_grades[-1])

        for g in all_grades:
            lows, highs = [], []
            discrete_sets = []

            for pub_data in collections.values():
                if g in pub_data:
                    vals = pub_data[g]
                    if len(vals) == 2:
                        lows.append(vals[0])
                        highs.append(vals[1])
                    else:
                        discrete_sets.append(set(vals))

            g = float(g)
            if lows:
                # continuous range
                ext_low, ext_high = min(lows), max(highs)
                core_low, core_high = max(lows), min(highs)
                core = None if core_low > core_high else [core_low, core_high]
                extended = [ext_low, ext_high]
            else:
                # discrete pitches
                union = reduce(set.union, discrete_sets)
                intersection = reduce(set.intersection, discrete_sets)
                core = sorted(list(union))
                extended = sorted(list(intersection))

            COMBINED_RANGES[inst][g] = {
                "core": core,
                "extended": extended
            }

        # Fill upward
        grades_sorted = sorted(COMBINED_RANGES[inst].keys())
        for i in range(1, len(grades_sorted)):
            prev = grades_sorted[i-1]
            curr = grades_sorted[i]
            pdat = COMBINED_RANGES[inst][prev]
            cdat = COMBINED_RANGES[inst][curr]

            if isinstance(cdat["core"], list) and isinstance(pdat["core"], list):
                cdat["core"] = sorted(set(cdat["core"]) | set(pdat["core"]))
                cdat["extended"] = sorted(set(cdat["extended"]) & set(pdat["extended"]))
            else:
                if pdat["core"] and cdat["core"]:
                    cdat["core"][0] = min(cdat["core"][0], pdat["core"][0])
                    cdat["core"][1] = max(cdat["core"][1], pdat["core"][1])
                cdat["extended"][0] = min(cdat["extended"][0], pdat["extended"][0])
                cdat["extended"][1] = max(cdat["extended"][1], pdat["extended"][1])

        # final total range
        final = COMBINED_RANGES[inst][max_grade]
        COMBINED_RANGES[inst]["total_range"] = [
            final["core"][0] if final["core"] else final["extended"][0],
            final["extended"][1]
        ]

    return COMBINED_RANGES
