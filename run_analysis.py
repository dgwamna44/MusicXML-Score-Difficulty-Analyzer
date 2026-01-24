from analyzers.key_range_analysis import derive_observed_grades as get_range_grades, run as run_range
from analyzers.rhythm_meter_analysis import run as run_rhythm
from analyzers.tempo_duration_analysis import derive_observed_grades as get_tempo_grades, run as run_tempo

if __name__ == "__main__":
    FILE = "input_files\multiple_instrument_test.musicxml"
    FILE_2 = "input_files\multiple_meter_madness.musicxml"
    FILE_3 = "input_files\duration_test.musicxml"

    observed_tempo_grade, observed_duration_grade, tempo_confidences, duration_confidences = get_tempo_grades(FILE)
    T_DATA = run_tempo(FILE_3, 1)
    DATA = run_range(FILE, .5)
    DATA_2 = run_rhythm(FILE, .5)
    observed_range_grade, observed_key_grade, range_confidences, key_confidences = get_range_grades(FILE)


