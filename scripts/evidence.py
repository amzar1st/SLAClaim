#!/usr/bin/env python3
"""Prepare immutable monitor evidence without altering the bytes to be hosted."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--url", required=True, help="Public immutable HTTPS URL of these exact bytes")
    parser.add_argument("--sla-id", default="1")
    args = parser.parse_args()
    body = args.snapshot.read_bytes()
    if len(body) > 262144:
        parser.error("Snapshot exceeds 256 KiB")
    s = json.loads(body)
    if s.get("schema") != "slaclaim/v1" or not isinstance(s.get("records"), list):
        parser.error("Expected slaclaim/v1 records")
    if urlsplit(args.url).scheme != "https":
        parser.error("Use a public HTTPS URL")
    print(json.dumps({"method": "submit_evidence", "args": [args.sla_id, args.url, hashlib.sha256(body).hexdigest()], "submit_from_monitor": s["monitor"], "bytes": len(body)}, indent=2))


if __name__ == "__main__":
    main()
