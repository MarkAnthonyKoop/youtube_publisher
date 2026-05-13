"""Write MiddleMatter Music / Mark Nadon metadata into MP4 files.

The MP4 container's tagging spec is the iTunes/Quicktime atom set. We use
mutagen which writes them in-place without re-encoding video.

Atoms used:
  \xa9ART  artist
  aART     album artist
  \xa9wrt  composer
  cprt     copyright
  ----:com.apple.iTunes:LABEL          freeform record-label tag
  ----:com.apple.iTunes:RECORDCOMPANY  freeform record-company tag (alt readers)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen.mp4 import MP4, MP4FreeForm

ARTIST = "Mark Nadon"
RECORD_COMPANY = "MiddleMatter Music"


def _ff(text: str) -> MP4FreeForm:
    return MP4FreeForm(text.encode("utf-8"), dataformat=1)  # 1 = UTF-8


def tag_mp4(path: str | Path,
            artist: str = ARTIST,
            record_company: str = RECORD_COMPANY,
            title: str | None = None,
            album: str | None = None,
            year: int | None = None,
            extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply our standard metadata to an MP4. Returns the resulting tag dict.

    Safe to call repeatedly: tags are overwritten, not appended.
    """
    path = Path(path)
    if path.suffix.lower() not in {".mp4", ".m4a", ".m4v", ".mov"}:
        raise ValueError(f"tag_mp4 only handles MP4-family files, got: {path.suffix}")

    mp4 = MP4(str(path))
    if mp4.tags is None:
        mp4.add_tags()
    tags = mp4.tags

    tags["\xa9ART"] = [artist]
    tags["aART"] = [artist]
    tags["\xa9wrt"] = [artist]
    tags["cprt"] = [f"© {record_company}"]
    tags["----:com.apple.iTunes:LABEL"] = [_ff(record_company)]
    tags["----:com.apple.iTunes:RECORDCOMPANY"] = [_ff(record_company)]

    if title:
        tags["\xa9nam"] = [title]
    if album:
        tags["\xa9alb"] = [album]
    if year:
        tags["\xa9day"] = [str(year)]

    if extra:
        for k, v in extra.items():
            tags[k] = v if isinstance(v, list) else [v]

    mp4.save()
    return read_mp4_tags(path)


def read_mp4_tags(path: str | Path) -> dict[str, Any]:
    """Return a JSON-friendly snapshot of the MP4's tags."""
    mp4 = MP4(str(path))
    out: dict[str, Any] = {}
    if not mp4.tags:
        return out
    for k, v in mp4.tags.items():
        if isinstance(v, list):
            out[k] = [
                bytes(x).decode("utf-8", errors="replace") if isinstance(x, MP4FreeForm)
                else x
                for x in v
            ]
        else:
            out[k] = v
    return out
