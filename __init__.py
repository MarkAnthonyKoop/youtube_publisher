"""YouTube publishing toolkit.

Modular pieces — import what you need:

    from youtube_publisher import credentials, auth, metadata, upload, publish

Or use the high-level helpers re-exported here.
"""

from .credentials import (
    discover_client_secrets,
    list_client_secrets,
    pick_client_secrets,
)
from .auth import get_credentials, revoke
from .metadata import tag_mp4, read_mp4_tags, ARTIST, RECORD_COMPANY
from .upload import upload_video
from .publish import publish

__all__ = [
    "discover_client_secrets",
    "list_client_secrets",
    "pick_client_secrets",
    "get_credentials",
    "revoke",
    "tag_mp4",
    "read_mp4_tags",
    "ARTIST",
    "RECORD_COMPANY",
    "upload_video",
    "publish",
]
