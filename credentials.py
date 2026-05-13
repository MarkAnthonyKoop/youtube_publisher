"""Discover Google OAuth client_secret JSON files on this machine.

The file the user downloads from
  https://console.cloud.google.com/apis/credentials
is a JSON with shape `{"installed": {...}}` or `{"web": {...}}`.

We search a small set of well-known locations (the package dir, the older
~/claude/tools location, and the user's Windows Downloads folder under WSL).
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_CLIENT_SECRETS = PACKAGE_DIR / "client_secret.json"

SEARCH_GLOBS: tuple[str, ...] = (
    str(PACKAGE_DIR / "client_secret*.json"),
    str(Path.home() / "claude/tools/client_secrets*.json"),
    str(Path.home() / "claude/tools/client_secret*.json"),
    "/mnt/c/Users/*/Downloads/client_secret*googleusercontent.com.json",
)


@dataclass(frozen=True)
class ClientSecrets:
    path: Path
    project_id: str
    client_id: str
    kind: str  # "installed" or "web"

    @property
    def stem(self) -> str:
        """Stable identifier used to namespace the OAuth token cache."""
        return self.client_id.split("-", 1)[0] or self.project_id


def _load(path: Path) -> ClientSecrets | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for kind in ("installed", "web"):
        if kind in data:
            d = data[kind]
            return ClientSecrets(
                path=path,
                project_id=d.get("project_id", ""),
                client_id=d.get("client_id", ""),
                kind=kind,
            )
    return None


def list_client_secrets(extra_globs: Iterable[str] = ()) -> list[ClientSecrets]:
    """Return every client_secret JSON we can find, deduplicated by client_id."""
    seen: dict[str, ClientSecrets] = {}
    for pattern in (*SEARCH_GLOBS, *extra_globs):
        for match in sorted(glob.glob(pattern)):
            cs = _load(Path(match))
            if cs and cs.client_id not in seen:
                seen[cs.client_id] = cs
    return list(seen.values())


def discover_client_secrets(prefer_project: str | None = None) -> ClientSecrets | None:
    """Pick the first credentials file we can find.

    `prefer_project` (substring match against project_id) lets a caller bias
    selection toward a specific Google Cloud project.
    """
    candidates = list_client_secrets()
    if not candidates:
        return None
    if prefer_project:
        for c in candidates:
            if prefer_project.lower() in c.project_id.lower():
                return c
    return candidates[0]


def pick_client_secrets(path: str | os.PathLike | None = None,
                        prefer_project: str | None = None) -> ClientSecrets:
    """Resolve a ClientSecrets, raising if nothing is available."""
    if path:
        cs = _load(Path(path))
        if not cs:
            raise FileNotFoundError(f"Not a valid client_secret JSON: {path}")
        return cs
    cs = discover_client_secrets(prefer_project=prefer_project)
    if not cs:
        searched = "\n  ".join(SEARCH_GLOBS)
        raise FileNotFoundError(
            "No Google client_secret JSON found. Searched:\n  " + searched +
            "\n\nDownload one from https://console.cloud.google.com/apis/credentials "
            "(OAuth Client ID, Desktop App) and drop it into "
            f"{PACKAGE_DIR} or any of the searched paths."
        )
    return cs
