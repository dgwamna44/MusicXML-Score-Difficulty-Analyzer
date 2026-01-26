from analyzers.key_range_analysis import derive_observed_grades as get_range_grades, run as run_range
from analyzers.rhythm_meter_analysis import derive_observed_grades as get_rhythm_grades, run as run_rhythm
from analyzers.tempo_duration_analysis import derive_observed_grades as get_tempo_grades, run as run_tempo
from analyzers.articulation_analysis import run as run_art

if __name__ == "__main__":
    FILE = r"input_files\test.musicxml"
    FILE_2 = r"input_files\multiple_meter_madness.musicxml"
    FILE_3 = r"input_files\duration_test.musicxml"
    FILE_4 = r"input_files\multiple_instrument_test.musicxml"
    FILE_5 = r"input_files\articulation_test.musicxml"

    art = run_art(FILE_5, 1)

    observed_tempo_grade, observed_duration_grade, tempo_confidences, duration_confidences = get_tempo_grades(FILE)
    T_DATA = run_tempo(FILE_3, 1)
    DATA = run_range(FILE, .5)
    FILE_4 = run_rhythm(FILE_4, .5)
    observed_range_grade, observed_key_grade, range_confidences, key_confidences = get_range_grades(FILE)
    observed_meter_grade, observed_rhythm_grade, meter_confidences, rhythm_confidences = get_rhythm_grades(FILE_4)


