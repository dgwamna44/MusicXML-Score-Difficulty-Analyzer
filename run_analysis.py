from analyzers.articulation import run_articulation
from analyzers.rhythm import run_rhythm
from analyzers.meter import run_meter

if __name__ == "__main__":
    FILE = r"input_files\test.musicxml"
    FILE_2 = r"input_files\multiple_meter_madness.musicxml"
    FILE_3 = r"input_files\duration_test.musicxml"
    FILE_4 = r"input_files\multiple_instrument_test.musicxml"
    FILE_5 = r"input_files\articulation_test.musicxml"

    art = run_articulation(FILE_5, 1)
    rhy = run_rhythm(FILE_4, 1)
    met = run_meter(FILE_4, 2)
    print("Zois")




