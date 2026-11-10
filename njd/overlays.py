"""One ordered interpretation of saved evidence and durable human decisions."""
from pathlib import Path

from njd.corrections import apply_corrections
from njd.locations import apply_locations
from njd.reviews import apply_reviews
from njd.source_aliases import apply_saved_source_aliases
from njd.storage import apply_decisions,load_dataset


def apply_saved_overlays(data,data_dir):
    root=Path(data_dir)
    for filename,apply in (('locations.json',apply_locations),
                           ('corrections.json',apply_corrections),
                           ('reviews.json',apply_reviews),
                           ('decisions.json',apply_decisions)):
        path=root/filename
        if path.exists():data=apply(data,load_dataset(path))
    return apply_saved_source_aliases(data,root)
