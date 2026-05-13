"""CLI entry point.

Examples:
  python3 -m youtube_publisher creds                          # list discoverable Google client_secret JSONs
  python3 -m youtube_publisher auth                           # run OAuth flow + cache token
  python3 -m youtube_publisher tag song.mp4                   # write artist/label metadata only
  python3 -m youtube_publisher tag song.mp4 --read            # show current MP4 tags
  python3 -m youtube_publisher upload song.mp4 --title "X"    # upload (already-tagged) file
  python3 -m youtube_publisher publish song.mp4 --title "X"   # tag + upload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import auth, credentials, metadata, upload
from .publish import publish as _publish


def _cmd_creds(args: argparse.Namespace) -> int:
    found = credentials.list_client_secrets()
    if not found:
        print("No client_secret JSONs discovered.", file=sys.stderr)
        return 1
    for cs in found:
        print(f"{cs.project_id}\t{cs.client_id}\t{cs.path}")
    return 0


def _cmd_auth(args: argparse.Namespace) -> int:
    if args.revoke:
        removed = auth.revoke(args.client_secrets)
        print("revoked" if removed else "no token cached")
        return 0
    creds = auth.get_credentials(args.client_secrets)
    print(f"OK; valid={creds.valid}; scopes={list(creds.scopes or [])}")
    return 0


def _cmd_tag(args: argparse.Namespace) -> int:
    if args.read:
        tags = metadata.read_mp4_tags(args.path)
        print(json.dumps(tags, indent=2, default=str))
        return 0
    out = metadata.tag_mp4(
        args.path,
        artist=args.artist,
        record_company=args.record_company,
        title=args.title,
        album=args.album,
        year=args.year,
    )
    print(json.dumps(out, indent=2, default=str))
    return 0


def _cmd_upload(args: argparse.Namespace) -> int:
    result = upload.upload_video(
        args.path,
        title=args.title,
        description=args.description or "",
        tags=args.tag,
        privacy=args.privacy,
        client_secrets_path=args.client_secrets,
    )
    print(json.dumps({"video_id": result["video_id"], "url": result["url"]}, indent=2))
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    result = _publish(
        args.path,
        title=args.title,
        description=args.description or "",
        tags=args.tag,
        privacy=args.privacy,
        artist=args.artist,
        record_company=args.record_company,
        album=args.album,
        year=args.year,
        skip_tagging=args.skip_tagging,
        client_secrets_path=args.client_secrets,
    )
    print(json.dumps({"video_id": result["video_id"], "url": result["url"]}, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="youtube_publisher")
    p.add_argument("--client-secrets", dest="client_secrets",
                   help="Path to a Google client_secret JSON. Auto-discovered if omitted.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("creds", help="list discoverable client_secret JSONs")

    sp_auth = sub.add_parser("auth", help="run OAuth flow / refresh token")
    sp_auth.add_argument("--revoke", action="store_true", help="forget cached token")

    sp_tag = sub.add_parser("tag", help="write or read MP4 metadata")
    sp_tag.add_argument("path", type=Path)
    sp_tag.add_argument("--read", action="store_true")
    sp_tag.add_argument("--artist", default=metadata.ARTIST)
    sp_tag.add_argument("--record-company", default=metadata.RECORD_COMPANY)
    sp_tag.add_argument("--title")
    sp_tag.add_argument("--album")
    sp_tag.add_argument("--year", type=int)

    def _add_upload_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("path", type=Path)
        sp.add_argument("--title", required=True)
        sp.add_argument("--description", default="")
        sp.add_argument("--tag", action="append", default=[],
                        help="repeatable; e.g. --tag rock --tag instrumental")
        sp.add_argument("--privacy",
                        choices=[upload.PRIVACY_PUBLIC, upload.PRIVACY_UNLISTED, upload.PRIVACY_PRIVATE],
                        default=upload.PRIVACY_PRIVATE)

    sp_up = sub.add_parser("upload", help="upload a video to YouTube")
    _add_upload_args(sp_up)

    sp_pub = sub.add_parser("publish", help="tag MP4 then upload")
    _add_upload_args(sp_pub)
    sp_pub.add_argument("--artist", default=metadata.ARTIST)
    sp_pub.add_argument("--record-company", default=metadata.RECORD_COMPANY)
    sp_pub.add_argument("--album")
    sp_pub.add_argument("--year", type=int)
    sp_pub.add_argument("--skip-tagging", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "creds": _cmd_creds,
        "auth": _cmd_auth,
        "tag": _cmd_tag,
        "upload": _cmd_upload,
        "publish": _cmd_publish,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
