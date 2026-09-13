#!/usr/bin/env python3
"""Read-only YouTube metadata collector. Python 3.10+, standard library only.

Requires YOUTUBE_API_KEY with YouTube Data API v3 enabled.
Does NOT download media, infer physical events, or certify reuse rights.
Official API reference: https://developers.google.com/youtube/v3/docs/
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE = "https://www.googleapis.com/youtube/v3/"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {n} of {path}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected an object on line {n} of {path}")
            records.append(row)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        for row in records:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


class Client:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.attempts = 0

    def get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        # Do not print request URLs: they contain the API key.
        url = BASE + endpoint + "?" + urllib.parse.urlencode(
            {"key": self.api_key, **params}
        )
        for attempt in range(3):
            self.attempts += 1
            request = urllib.request.Request(url, headers={"User-Agent": "ExemplarMetadataCollector/1.0"})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if (exc.code == 429 or exc.code >= 500) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    message = json.loads(raw).get("error", {}).get("message", "API request failed")
                except json.JSONDecodeError:
                    message = "API request failed"
                raise RuntimeError(f"YouTube HTTP {exc.code}: {message}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError("Network request failed after three attempts.") from None
        raise RuntimeError("No API response")


def search_ids(client: Client, args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    queries = [line.strip() for line in args.queries.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    queries = queries[args.start_query:args.start_query + args.limit_queries]
    if not queries:
        raise ValueError("No queries selected")
    found: dict[str, dict[str, Any]] = {}
    for query in queries:
        token = None
        for _ in range(args.pages):
            params: dict[str, Any] = dict(part="snippet", type="video", q=query,
                order=args.order, maxResults=args.max_results)
            if args.cc_only:
                params["videoLicense"] = "creativeCommon"
            if token:
                params["pageToken"] = token
            result = client.get("search", **params)
            for item in result.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                row = found.setdefault(video_id, {"video_id": video_id, "discovery_queries": []})
                if query not in row["discovery_queries"]:
                    row["discovery_queries"].append(query)
            token = result.get("nextPageToken")
            if not token:
                break
        print(f"Searched: {query}", file=sys.stderr)
    return found


def channel_ids(client: Client, args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    data = client.get("channels", part="contentDetails", id=args.channel_id)
    channels = data.get("items", [])
    if not channels:
        raise ValueError("Channel not found; supply its UC... channel ID, not a handle")
    playlist = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    found: dict[str, dict[str, Any]] = {}
    token = None
    for _ in range(args.pages):
        params = dict(part="contentDetails", playlistId=playlist, maxResults=50)
        if token:
            params["pageToken"] = token
        result = client.get("playlistItems", **params)
        for item in result.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                found[video_id] = {"video_id": video_id, "discovery_channel_id": args.channel_id}
        token = result.get("nextPageToken")
        if not token:
            break
    if token:
        print("Channel listing is partial: more pages are available.", file=sys.stderr)
    return found


def enrich(client: Client, rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ids = list(rows)
    timestamp = utc_now()
    output = []
    for offset in range(0, len(ids), 50):
        batch = ids[offset:offset + 50]
        result = client.get("videos", part="snippet,contentDetails,status", id=",".join(batch))
        resources = {item["id"]: item for item in result.get("items", [])}
        for video_id in batch:
            row = dict(rows[video_id])
            # Refresh replaces, rather than archives, old API metadata.
            row["youtube"] = resources.get(video_id)
            row["api_status"] = "available" if video_id in resources else "not_returned"
            row["api_refreshed_at"] = timestamp.isoformat()
            row["api_refresh_or_delete_by"] = (timestamp + dt.timedelta(days=30)).isoformat()
            row["url"] = f"https://www.youtube.com/watch?v={video_id}"
            row["review_status"] = "unreviewed"
            row["reuse_permission"] = "not_established"
            output.append(row)
    return output


def positive(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("Must be positive")
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="Discover candidates using a query text file")
    search.add_argument("--queries", type=Path, default=Path("youtube_queries.txt"))
    search.add_argument("--start-query", type=int, default=0, help="Zero-based query offset")
    search.add_argument("--limit-queries", type=positive, default=8)
    search.add_argument("--pages", type=positive, default=1)
    search.add_argument("--max-results", type=int, choices=range(1, 51), default=25)
    search.add_argument("--order", choices=["relevance", "date"], default="relevance")
    search.add_argument("--cc-only", action="store_true")
    channel = sub.add_parser("channel", help="Read a channel's uploads playlist")
    channel.add_argument("--channel-id", required=True)
    channel.add_argument("--pages", type=positive, default=2)
    refresh = sub.add_parser("refresh", help="Replace API metadata from an earlier JSONL file")
    refresh.add_argument("--input", type=Path, required=True)
    for command in [search, channel, refresh]:
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if getattr(args, "start_query", 0) < 0:
        parser.error("--start-query cannot be negative")
    if args.out.exists() and not args.overwrite:
        parser.error("Output exists; use another path or pass --overwrite")
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        parser.error("Set the YOUTUBE_API_KEY environment variable first")
    client = Client(api_key)
    if args.command == "search":
        rows = search_ids(client, args)
    elif args.command == "channel":
        rows = channel_ids(client, args)
    else:
        rows = {row["video_id"]: row for row in load_jsonl(args.input)}
    # Checkpoint discovered IDs before enrichment; useful if a later request fails.
    checkpoint = args.out.with_suffix(args.out.suffix + ".ids.jsonl")
    write_jsonl(checkpoint, [{k: v for k, v in r.items() if k not in {"youtube"}}
                             for r in rows.values()])
    output = enrich(client, rows)
    write_jsonl(args.out, output)
    checkpoint.unlink(missing_ok=True)
    print(f"Saved {len(output)} unique candidate records to {args.out}; "
          f"{client.attempts} HTTP attempts. No media downloaded.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
