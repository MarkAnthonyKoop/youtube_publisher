# youtube_publisher

Publish music MP4s to YouTube under the **Mark Nadon / MiddleMatter Music** identity. Tags the file's MP4 metadata, runs a resumable Data API v3 upload, and is invokable as both a CLI (`python3 -m youtube_publisher …`) and a Python package whose every piece is independently importable.

---

## 1. User manual (read this first)

### Install (already done on this machine)
Required Python deps are present system-wide: `google-api-python-client`, `google-auth-oauthlib`, `mutagen`. ffmpeg is on `~/.local/bin`. Nothing else to install.

### One-time setup

```bash
# 1. Make sure a Google client_secret JSON exists somewhere we can find it.
python3 -m youtube_publisher creds                  # lists discoverable secrets

# 2. Run OAuth consent. Chrome opens; sign in as markanthonykoop@gmail.com.
python3 -m youtube_publisher auth                   # caches token at ~/.cache/youtube_publisher/
```

The cached token refreshes itself silently from then on. If your Google Cloud OAuth consent screen is in **Testing**, the refresh token expires every 7 days; in **Production** it lasts indefinitely.

### Publishing a track

```bash
# Tag MP4 + upload (defaults: Music category, privacy=private)
python3 -m youtube_publisher publish track.mp4 --title "Song Title"

# Public release with description and tags
python3 -m youtube_publisher publish track.mp4 \
    --title "Song Title" \
    --description "Released by MiddleMatter Music." \
    --tag "doom metal" --tag funk \
    --privacy public
```

### Just metadata (no upload)

```bash
python3 -m youtube_publisher tag track.mp4 --album "Album Name" --year 2026
python3 -m youtube_publisher tag track.mp4 --read     # show current tags
```

---

## 2. Reference manual

### CLI subcommands

`python3 -m youtube_publisher [--client-secrets PATH] {creds|auth|tag|upload|publish} …`

The optional top-level `--client-secrets PATH` overrides auto-discovery. Useful when multiple Google projects exist on the box.

#### `creds`
Lists every Google OAuth `client_secret*.json` the package can find. Output is `project_id<TAB>client_id<TAB>path`. No flags.

#### `auth [--revoke]`
Runs the OAuth consent flow if no valid token is cached. With `--revoke`, deletes the cached token for the chosen client.

#### `tag PATH [options]`
Writes (or reads) MP4 metadata. Defaults are Mark Nadon / MiddleMatter Music — every option is overridable.

| Flag | Meaning | Default |
| --- | --- | --- |
| `--read` | Print current tags as JSON, don't write | off |
| `--artist NAME` | Artist name | Mark Nadon |
| `--record-company NAME` | Record label / publisher | MiddleMatter Music |
| `--title TITLE` | Track title | unset |
| `--album NAME` | Album name | unset |
| `--year YYYY` | Release year | unset |

#### `upload PATH --title TITLE [options]`
Uploads an already-tagged MP4 to YouTube. Title is required.

| Flag | Meaning | Default |
| --- | --- | --- |
| `--title` | Video title (required) | — |
| `--description` | Video description | empty |
| `--tag VALUE` | Repeatable; YouTube tags | none |
| `--privacy {public,unlisted,private}` | Visibility | `private` |

Scheduled releases (the closest thing the YouTube Data API offers to a Premiere) are supported via the Python API's `publish_at` argument — no CLI flag yet. See `upload.upload_video()` below.

#### `publish PATH --title TITLE [options]`
`tag` then `upload`. Accepts every flag from both, plus `--skip-tagging` if you've already tagged the file and don't want to touch it again.

### Python API

The package's docstrings are authoritative; this is a quick map of what to import:

```python
from youtube_publisher import (
    # credential discovery
    list_client_secrets,           # -> list[ClientSecrets]
    discover_client_secrets,       # -> ClientSecrets | None
    pick_client_secrets,           # -> ClientSecrets, raises if missing

    # OAuth
    get_credentials,               # -> google.oauth2.credentials.Credentials
    revoke,                        # -> bool

    # MP4 tagging
    tag_mp4, read_mp4_tags,
    ARTIST, RECORD_COMPANY,        # default identity strings

    # YouTube upload
    upload_video,                  # resumable upload, returns {video_id, url, response}

    # End-to-end
    publish,                       # tag_mp4 + upload_video
)
```

Each module is also importable on its own (`from youtube_publisher import auth`, etc.) — useful for projects that want only metadata tagging without dragging in the YouTube API client, for example.

#### `credentials.ClientSecrets`
Frozen dataclass: `path`, `project_id`, `client_id`, `kind` (`"installed"`/`"web"`), and a `stem` property used for token cache filenames.

#### `metadata.tag_mp4(path, artist, record_company, title=None, album=None, year=None, extra=None)`
In-place; never re-encodes video. `extra` is an escape hatch for raw mutagen MP4Tags entries (e.g. `{"\xa9grp": ["Group"]}`).

#### `upload.upload_video(video_path, title, description="", tags=None, category_id="10", privacy="private", made_for_kids=False, client_secrets_path=None, progress_stream=sys.stderr, publish_at=None)`

Pass an RFC 3339 timestamp like `"2026-05-05T20:00:00.000Z"` to `publish_at` to schedule the video. YouTube requires `privacy="private"` when `publish_at` is set; the video auto-publishes at the scheduled time. The Data API has **no Premiere-specific field** — the Premiere countdown UI must be enabled in YouTube Studio after upload (one click per video). `publish_at` is the closest API-supported approximation of "instant Premiere."
`category_id="10"` is YouTube's Music category. Returns `{"video_id": …, "url": …, "response": <full API JSON>}`.

#### `auth.get_credentials(client_secrets_path=None, scopes=DEFAULT_SCOPES, port=8090, open_browser=True)`
`DEFAULT_SCOPES = ("https://www.googleapis.com/auth/youtube.upload",)`. Pass a wider tuple if you've enabled additional scopes on your OAuth consent screen.

### File system contract

| Path | Purpose |
| --- | --- |
| `~/.cache/youtube_publisher/token_<clientstem>.pickle` | One cached OAuth token per client_id |
| `~/claude/youtube_publisher/client_secret*.json` | Optional package-local secret (auto-discovered, highest priority) |
| `/mnt/c/Users/*/Downloads/client_secret_*googleusercontent.com.json` | Auto-discovered fallback |

Tokens are pickle (we depend on Google's `Credentials` class) and are user-readable only by convention — `chmod 600` if your home dir is shared.

---

## 3. Architecture

### Module layout

```
youtube_publisher/
├── __init__.py      thin re-export surface
├── __main__.py      argparse CLI; one handler per subcommand
├── credentials.py   discovers/parses client_secret JSONs (no network)
├── auth.py          runs OAuth consent + caches/refreshes tokens
├── metadata.py      mutagen-based MP4 tagging (no network)
├── upload.py        YouTube Data API v3 resumable upload
└── publish.py       orchestrator: tag_mp4 → upload_video
```

Dependency direction is strictly bottom-up: `publish.py` imports `metadata` and `upload`; `upload.py` imports `auth`; `auth.py` imports `credentials`. No back-edges, no cycles, no shared mutable state. Every module can be pulled into another project on its own.

### Why these splits

- **`credentials` is offline.** It only walks the filesystem and parses JSON. Useful in isolation when another project wants to know "do I have a Google project handy?" without triggering an OAuth flow.
- **`auth` knows nothing about YouTube.** Swap `DEFAULT_SCOPES` and it authenticates against any Google API. The Chrome-on-WSL browser registration is the one platform-specific piece, isolated to a single class (`_WSLChrome`).
- **`metadata` knows nothing about Google or YouTube.** It's an MP4-tag writer that happens to default to our music identity. The default constants `ARTIST` / `RECORD_COMPANY` are the only opinion baked in; the function accepts overrides.
- **`upload` knows nothing about metadata.** A caller who already has a tagged MP4 (or a file they don't want re-tagged) can use it directly.
- **`publish` is pure orchestration.** ~30 lines. If you need a different orchestration (e.g. tag → upload → post a Slack notification), copy this file and adjust — don't expand the original.

### Future siblings, not future submodules

When the publisher grows new capabilities, prefer **parallel sibling packages** under `~/claude/` over inflating this one:

| If we need… | Build it as a sibling, not a submodule |
| --- | --- |
| Tagging FLAC, MP3, WAV, or text track sheets | `~/claude/audio_metadata/` — generic taggers; our `metadata.py` becomes a thin wrapper around it |
| Suno integration (downloading clips, polling jobs) | `~/claude/suno_client/` — already partly drafted at `~/claude/tools/suno_*.py`; consolidate |
| Reaper / Pro Tools / FL Studio control | `~/claude/<daw>_client/` — one per DAW; standardized "render to MP4" interface |
| Video composition (artwork + waveform overlay) | `~/claude/video_composer/` — wraps ffmpeg |
| YouTube playlist / description editing | extend `youtube_publisher.upload` with `youtube` scope, OR factor into `youtube_data_client/` if it grows |

`youtube_publisher` should remain "tag an MP4, then upload it." Anything broader gets its own repo and is imported.

### Things to know if you're modifying this

1. **Token scope is whatever was first granted.** If you widen `DEFAULT_SCOPES`, existing cached tokens won't have the new scope — `revoke()` first, then re-auth.
2. **`InstalledAppFlow.run_local_server` opens its own WSGI server** to catch the OAuth redirect. It hardcodes `allow_reuse_address = False`, so a failed run leaves the port in TIME_WAIT for ~30s. If you hit "Address already in use", pass `port=8091` (or any free port) — Desktop OAuth clients accept any localhost port.
3. **MP4 tagging is in-place.** The file is rewritten; back up if you care. Mutagen does atomic-ish writes, but a power failure mid-save could corrupt.
4. **The package has no test suite.** Smoke-test changes by tagging a generated MP4:
   ```bash
   ffmpeg -y -f lavfi -i "color=c=black:s=320x240:d=1" -f lavfi -i "sine=f=440:d=1" \
          -shortest -c:v libx264 -c:a aac /tmp/yt_test.mp4
   python3 -m youtube_publisher tag /tmp/yt_test.mp4
   python3 -m youtube_publisher tag /tmp/yt_test.mp4 --read
   ```
5. **Don't introduce a config file.** All identity defaults live in `metadata.py` as module constants and override via kwargs. Anything that smells like config (paths, scopes) lives at the top of its module — find-and-replace beats YAML for a one-user toolchain.

---

## 4. Next steps

Concrete additions, ordered by what the in-flight music-video work
(`bottle/`) and documentary work (`there_is_no_homeless/`) need:

1. **`--publish-at` CLI flag.** The Python API already accepts `publish_at`
   for scheduled releases; the CLI doesn't expose it. Wire it through
   `publish.py` so episodes can be scheduled from the shell without dropping
   into Python.
2. **Thumbnail upload.** `videos.thumbnails.set` on the Data API. Add a
   `--thumbnail PATH` flag to `publish` and `upload`. The OAuth scope is
   already `youtube.upload`, which covers thumbnails — no new consent.
3. **Playlist add-on-publish.** A `--playlist-id ID` flag that calls
   `playlistItems.insert` right after upload. Wider scope (`youtube`) is
   needed — bump `DEFAULT_SCOPES`, document the re-auth step.
4. **Description-from-file.** Today `--description` is a string flag; for
   long descriptions we want `--description-file PATH` (also useful for
   keeping the description in the episode `.md` under `## Description`).
5. **github-readiness:**
   - Move the client_secret auto-discovery glob from `credentials.py:27`
     (currently `/mnt/c/Users/*/Downloads/...`) into a
     `YOUTUBE_PUBLISHER_CLIENT_SECRETS` env var with the Windows path as a
     this-machine-only fallback.
   - Move the Chrome path in `auth.py:28` into a `BROWSER` env var (or just
     let `webbrowser.open` use defaults).
   - LICENSE, .gitignore.
   - Pin `google-api-python-client`, `google-auth-oauthlib`, `mutagen` in
     `requirements.txt`.
   - Fixture-based tests for `metadata.tag_mp4` (no network).
