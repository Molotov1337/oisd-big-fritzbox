#!/usr/bin/env python3
"""Download OISD Big and publish four stable, non-overlapping ABP domain lists."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import urllib.request

SOURCE = "https://big.oisd.nl"
PARTS = 4
OUT_DIR = Path(__file__).resolve().parents[1] / "lists"
ABP_DOMAIN = re.compile(r"\|\|([a-zA-Z0-9._-]+)\^")


def fetch_domains() -> set[str]:
    request = urllib.request.Request(
        SOURCE,
        headers={"User-Agent": "oisd-big-fritzbox-splitter/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as reply:
        data = reply.read(25_000_001)
    if len(data) > 25_000_000:
        raise RuntimeError("Source unexpectedly exceeds 25 MB")
    text = data.decode("utf-8-sig")
    domains: set[str] = set()
    invalid: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("!") or line == "[Adblock Plus]":
            continue
        match = ABP_DOMAIN.fullmatch(line)
        if match:
            domains.add(match.group(1).lower())
        else:
            invalid.append(line[:120])
            if len(invalid) == 5:
                break
    if invalid:
        raise RuntimeError(f"Unknown rule syntax; refusing partial export: {invalid}")
    if not 100_000 <= len(domains) <= 1_000_000:
        raise RuntimeError(f"Unexpected number of rules: {len(domains)}")
    return domains


def main() -> None:
    domains = fetch_domains()
    buckets = [[] for _ in range(PARTS)]
    for domain in sorted(domains):
        bucket = hashlib.sha256(domain.encode("ascii")).digest()[0] % PARTS
        buckets[bucket].append(domain)
    OUT_DIR.mkdir(exist_ok=True, parents=True)
    for i, bucket in enumerate(buckets, start=1):
        if not bucket:
            raise RuntimeError(f"Bucket {i} unexpectedly empty")
        header = (
            "[Adblock Plus]\n"
            f"! Title: OISD Big – Part {i} of {PARTS}\n"
            f"! Entries: {len(bucket)}\n"
            "! Source: https://big.oisd.nl\n"
            "! License: https://github.com/sjhgvr/oisd/blob/main/LICENSE\n"
            "! Maintainer of original list: Stephan van Ruth\n"
        )
        rules = "".join(f"||{domain}^\n" for domain in bucket)
        target = OUT_DIR / f"oisd-big-{i}.txt"
        target.write_text(header + rules, encoding="utf-8", newline="\n")
        print(f"{target}: {len(bucket):,} entries")
    print(f"Total unique rules: {len(domains):,}")


if __name__ == "__main__":
    main()
