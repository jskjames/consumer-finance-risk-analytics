"""Download the official CFPB Consumer Complaint Database archive."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

from .config import CFPB_URL, RAW_ZIP


def download(url: str = CFPB_URL, destination: Path = RAW_ZIP, force: bool = False) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"Using existing archive: {destination}")
        return destination

    temp = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "cfri-portfolio-project/0.1"})
    print(f"Downloading {url}")
    with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as handle:
        shutil.copyfileobj(response, handle, length=1024 * 1024)

    if not zipfile.is_zipfile(temp):
        temp.unlink(missing_ok=True)
        raise ValueError("Downloaded file is not a valid ZIP archive")
    temp.replace(destination)
    print(f"Saved {destination} ({destination.stat().st_size / 1_000_000:.1f} MB)")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=CFPB_URL)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    download(args.url, force=args.force)


if __name__ == "__main__":
    main()

