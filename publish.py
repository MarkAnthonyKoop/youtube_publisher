"""End-to-end: tag the MP4, then upload it."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from .metadata import ARTIST, RECORD_COMPANY, tag_mp4
from .upload import PRIVACY_PRIVATE, upload_video


def publish(video_path: str | Path,
            title: str,
            description: str = "",
            tags: Iterable[str] | None = None,
            privacy: str = PRIVACY_PRIVATE,
            artist: str = ARTIST,
            record_company: str = RECORD_COMPANY,
            year: int | None = None,
            album: str | None = None,
            skip_tagging: bool = False,
            client_secrets_path: str | os.PathLike | None = None) -> dict:
    """Tag the MP4 with artist/label, then upload to YouTube."""
    video_path = Path(video_path)

    if not skip_tagging:
        tag_mp4(
            video_path,
            artist=artist,
            record_company=record_company,
            title=title,
            album=album,
            year=year,
        )

    return upload_video(
        video_path,
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
        client_secrets_path=client_secrets_path,
    )
