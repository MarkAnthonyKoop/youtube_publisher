"""Upload an MP4 to YouTube via the Data API v3."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .auth import get_credentials

CATEGORY_MUSIC = "10"

PRIVACY_PUBLIC = "public"
PRIVACY_UNLISTED = "unlisted"
PRIVACY_PRIVATE = "private"
VALID_PRIVACY = {PRIVACY_PUBLIC, PRIVACY_UNLISTED, PRIVACY_PRIVATE}


def upload_video(video_path: str | Path,
                 title: str,
                 description: str = "",
                 tags: Iterable[str] | None = None,
                 category_id: str = CATEGORY_MUSIC,
                 privacy: str = PRIVACY_PRIVATE,
                 made_for_kids: bool = False,
                 client_secrets_path: str | os.PathLike | None = None,
                 progress_stream=sys.stderr,
                 publish_at: str | None = None) -> dict:
    """Resumable upload. Returns {video_id, url, response}."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if privacy not in VALID_PRIVACY:
        raise ValueError(f"privacy must be one of {VALID_PRIVACY}, got {privacy!r}")

    creds = get_credentials(client_secrets_path)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    if tags:
        body["snippet"]["tags"] = list(tags)
    # Scheduled release: privacyStatus must be "private" until publishAt fires.
    # YouTube Data API has no Premiere-specific field — the Premiere countdown
    # toggle is set in YouTube Studio after upload.
    if publish_at:
        if privacy != PRIVACY_PRIVATE:
            raise ValueError("publish_at requires privacy=private (YouTube auto-publishes at the scheduled time)")
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and progress_stream:
            print(f"  upload {int(status.progress() * 100)}%", file=progress_stream, flush=True)

    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "response": response,
    }
