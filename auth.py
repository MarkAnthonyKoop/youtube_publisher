"""OAuth 2.0 for the YouTube Data API.

Tokens are cached per-client-id under ``~/.cache/youtube_publisher/``.
The OAuth consent flow opens Chrome (Windows-side under WSL) so saved
Google passwords carry the user through with one click.
"""

from __future__ import annotations

import os
import pickle
import subprocess
import webbrowser
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .credentials import ClientSecrets, pick_client_secrets

DEFAULT_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.upload",
)

TOKEN_DIR = Path.home() / ".cache" / "youtube_publisher"
CHROME_EXE = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
_BROWSER_NAME = "wsl-chrome"


class _WSLChrome(webbrowser.BaseBrowser):
    """Spawn Windows Chrome from WSL via subprocess.

    Python's stdlib `webbrowser` module needs a *registered* handler — passing
    a path string to `webbrowser.get()` doesn't work on Linux when no browser
    is on PATH. Registering a tiny BaseBrowser subclass routes around that.
    """

    def open(self, url, new=0, autoraise=True):
        try:
            subprocess.Popen(
                [CHROME_EXE, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except OSError:
            return False


def _ensure_browser_registered() -> bool:
    if not Path(CHROME_EXE).exists():
        return False
    try:
        webbrowser.get(_BROWSER_NAME)
    except webbrowser.Error:
        webbrowser.register(_BROWSER_NAME, None, _WSLChrome())
    return True


def _token_path(cs: ClientSecrets) -> Path:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    return TOKEN_DIR / f"token_{cs.stem}.pickle"


def _load_token(path: Path) -> Credentials | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            return pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError):
        return None


def _save_token(path: Path, creds: Credentials) -> None:
    with path.open("wb") as f:
        pickle.dump(creds, f)


def get_credentials(client_secrets_path: str | os.PathLike | None = None,
                    scopes: Iterable[str] = DEFAULT_SCOPES,
                    port: int = 8090,
                    open_browser: bool = True) -> Credentials:
    """Return a valid OAuth Credentials object, running the consent flow if needed."""
    cs = pick_client_secrets(client_secrets_path)
    token_file = _token_path(cs)
    creds = _load_token(token_file)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(token_file, creds)
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(str(cs.path), scopes=list(scopes))

    kwargs: dict = {"port": port, "open_browser": open_browser}
    if open_browser and _ensure_browser_registered():
        kwargs["browser"] = _BROWSER_NAME
    creds = flow.run_local_server(**kwargs)

    _save_token(token_file, creds)
    return creds


def revoke(client_secrets_path: str | os.PathLike | None = None) -> bool:
    """Forget the cached token for a given client. Returns True if one was removed."""
    cs = pick_client_secrets(client_secrets_path)
    token_file = _token_path(cs)
    if token_file.exists():
        token_file.unlink()
        return True
    return False
