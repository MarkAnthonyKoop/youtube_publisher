"""Smoke test for youtube_publisher — verifies the package imports cleanly."""
import importlib


def test_import():
    mod = importlib.import_module("youtube_publisher")
    assert mod is not None


def test_main_module_importable():
    # `python3 -m youtube_publisher` works iff this import works
    importlib.import_module("youtube_publisher.__main__")
