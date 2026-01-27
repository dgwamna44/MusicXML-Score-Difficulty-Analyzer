from models import PartialNoteData
from collections import defaultdict

def group_notes_by_beat(notes: list[PartialNoteData]):
    groups = defaultdict(list)
    for n in notes:
        if n.rhythm_token is None:
            continue
        groups[(n.measure, n.beat_index)].append(n)
    return groups
