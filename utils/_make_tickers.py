#!/usr/bin/env python3
# utils.py
# Extract tickers from filenames like "AAPL_2024_Q1_summary.md"
# and write a plain-text file (one ticker per line) for WRDS upload.

from pathlib import Path
import argparse
import re
import sys

# Match: <TICKER>_<YYYY>_Q<1-4>_summary.md  (e.g., AAPL_2024_Q1_summary.md)
FNAME_RE = re.compile(r'^([A-Za-z0-9.\-]+)_(\d{4})_Q([1-4])_summary\.md$', re.IGNORECASE)

def extract_tickers(root: Path, replace_dash: bool = True) -> set[str]:
    """Recursively scan for *.md files under root and extract tickers.
    If replace_dash=True, convert '-' to '.' to match CRSP style (e.g., BRK-B -> BRK.B).
    """
    tickers: set[str] = set()
    for p in root.rglob("*.md"):
        m = FNAME_RE.match(p.name)
        if not m:
            continue
        t = m.group(1).upper()
        if replace_dash:
            t = t.replace("-", ".")
        tickers.add(t)
    return tickers

def main():
    ap = argparse.ArgumentParser(description="Extract S&P 500 tickers from summary filenames for WRDS.")
    ap.add_argument("--root", type=Path, default=Path.cwd(),
                    help="Directory containing the summary .md files (searched recursively).")
    ap.add_argument("--out", type=Path, default=Path("sp500_tickers.txt"),
                    help="Output txt file path (one ticker per line).")
    ap.add_argument("--keep-dash", action="store_true",
                    help="Keep '-' in tickers instead of converting to '.' (default converts to '.').")
    args = ap.parse_args()

    if not args.root.exists():
        print(f"[ERROR] Root folder not found: {args.root}", file=sys.stderr)
        sys.exit(1)

    tickers = extract_tickers(args.root, replace_dash=(not args.keep_dash))
    if not tickers:
        print("[WARN] No tickers matched pattern *_YYYY_Q#_summary.md", file=sys.stderr)

    # Sort and write output
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for t in sorted(tickers):
            f.write(t + "\n")

    print(f"[OK] Wrote {len(tickers)} tickers -> {args.out}")

if __name__ == "__main__":
    main()
