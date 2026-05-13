# CLAUDE.md — youtube_publisher

Instructions for any AI (or human) modifying this package. Read `README.md` first; this file only adds the things a future maintainer would otherwise have to discover the hard way. Universal rules are in `~/CLAUDE.md`; machine-wide notes are in `~/claude/CLAUDE.md`.

## OAuth is already set up — do not ask the user to sign in

A valid token is cached at `~/.cache/youtube_publisher/token_677495352.pickle` for the **`sixth-storm-384809`** ("My First Project") Google Cloud project, signed in as `markanthonykoop@gmail.com`. Scope: `youtube.upload`.

`auth.get_credentials()` will pick it up automatically — silent refresh, no consent prompt. Only run `python3 -m youtube_publisher auth` if the token has been deleted, the refresh token has expired (every 7 days while the consent screen is in Testing), or you're widening scopes.

If the user asks to "log in" or "set up auth", first check `~/.cache/youtube_publisher/` — they probably don't need to.

## Identity defaults are non-negotiable

`metadata.ARTIST = "Mark Nadon"` and `metadata.RECORD_COMPANY = "MiddleMatter Music"` are the canonical attribution for everything this user releases. Don't rename them. Don't move them out of `metadata.py`. If you add a new code path that writes attribution, default to these constants — never re-hardcode the strings elsewhere.

## Stay narrow

`youtube_publisher` does exactly two things: **tag an MP4, upload it to YouTube.** Resist:

- Adding non-MP4 audio support → extract `audio_metadata` as a sibling and import from it.
- Adding Suno/Reaper/DAW integration → extract `suno_client` / `reaper_client` as siblings.
- Adding a description-templater, a thumbnail generator, a playlist organizer → siblings.
- Adding a config file, a plugin system, a database, or any kind of state beyond the OAuth token cache.

When you're tempted to grow this package, ask: *would another project (a podcast publisher, a video archiver) reuse the new code?* If yes, it belongs in a sibling.

## Files stay small and single-purpose

Every file in this package is under 150 lines. Keep it that way. If a module grows past ~200 lines, that's the signal it's doing two things — split it before you commit.

The dependency graph is strictly bottom-up:

```
publish ──► metadata
        └─► upload ──► auth ──► credentials
```

Don't introduce back-edges. Don't add a `utils.py`. Don't make `__init__.py` do work — it only re-exports.

## Don't refactor the OAuth shim, just route around it

`auth._WSLChrome` exists because Python's stdlib `webbrowser` module won't accept a path string and `google_auth_oauthlib`'s `run_local_server` hardcodes `webbrowser.get(name)`. The fix is fragile-looking but minimal. Don't try to "improve" it by re-implementing the local OAuth server — that's a much bigger surface area.

If `run_local_server` ever stops working, the next move is to call `flow.authorization_url()` + a tiny `wsgiref` server ourselves. Don't pull in a dependency for this.

## When something is broken, fix the root cause

The codebase is small enough that adding workarounds is almost always the wrong move. Trace errors to their source. Examples from this file's history:

- "could not locate runnable browser" → register a custom `webbrowser.BaseBrowser`, don't catch+swallow.
- "Scope has changed" oauthlib warning → request only the scope you have, don't set `OAUTHLIB_RELAX_TOKEN_SCOPE=1`.
- "Address already in use" on retry → use a different port, don't `time.sleep` and pray.

## Documentation contract

If you change behavior, update `README.md` in the same change. The structure is fixed: §1 user manual, §2 reference, §3 architecture. New CLI flags go in §2 tables. New modules get an entry in the §3 module layout block. New siblings get a row in the "Future siblings" table.

## Smoke test before declaring done

There's no automated test suite (intentional — too small). After any code change, run:

```bash
python3 -c "import youtube_publisher; print('import ok')"
python3 -m youtube_publisher --help >/dev/null && echo "cli ok"
python3 -m youtube_publisher creds                          # discovery
ffmpeg -y -f lavfi -i "color=c=black:s=320x240:d=1" -f lavfi -i "sine=f=440:d=1" \
       -shortest -c:v libx264 -c:a aac /tmp/yt_smoke.mp4 2>/dev/null
python3 -m youtube_publisher tag /tmp/yt_smoke.mp4 --read
rm /tmp/yt_smoke.mp4
```

If you actually changed `auth.py` or `upload.py`, also run a private upload of a 1-second clip to confirm the API path works end-to-end.
