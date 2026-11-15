"""Explicit adapter for historical v1 release regression fixtures."""
from njd.release import create_release as _create_release

def create_release(*args, **kwargs):
    return _create_release(*args, **kwargs, legacy=True)
