import argparse
import pathlib
import sys
from typing import Dict, Iterable, List, Optional

try:
    from PIL import Image
except ImportError:
    Image = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = REPO_ROOT / ".tmp" / "mta-subway-bullets"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "assets" / "route_symbols"

# Keys represent local runtime symbol filenames (without extension).
# Values are candidate upstream stem names (case-insensitive) expected from louh/mta-subway-bullets PNG assets.
SYMBOL_SOURCE_CANDIDATES: Dict[str, List[str]] = {
    "1": ["1"],
    "2": ["2"],
    "3": ["3"],
    "4": ["4"],
    "5": ["5"],
    "5D": ["5d", "5"],
    "6": ["6"],
    "6D": ["6d"],
    "7": ["7"],
    "7D": ["7d"],
    "A": ["a"],
    "B": ["b"],
    "C": ["c"],
    "D": ["d"],
    "E": ["e"],
    "F": ["f"],
    "G": ["g"],
    "J": ["j"],
    "L": ["l"],
    "M": ["m"],
    "N": ["n"],
    "Q": ["q"],
    "R": ["r"],
    "W": ["w"],
    "Z": ["z"],
    "S": ["s"],
    "SF": ["sf"],
    "FD": ["fd"],
    "SIR": ["sir"],
}


def _find_png_by_stem(source_dir: pathlib.Path, stems: Iterable[str]) -> Optional[pathlib.Path]:
    candidate_map: Dict[str, pathlib.Path] = {}
    for path in source_dir.rglob("*.png"):
        candidate_map[path.stem.lower()] = path
    for stem in stems:
        match = candidate_map.get(stem.lower())
        if match:
            return match
    return None


def _resize_to_square(source: pathlib.Path, target: pathlib.Path, max_px: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required. Install dependencies from requirements.txt before running this script.")

    with Image.open(source) as img:
        rgba = img.convert("RGBA")
        bbox = rgba.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
        rgba.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (max_px, max_px), (0, 0, 0, 0))
        offset_x = (max_px - rgba.width) // 2
        offset_y = (max_px - rgba.height) // 2
        canvas.alpha_composite(rgba, (offset_x, offset_y))
        canvas.save(target, format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor and normalize route symbol PNGs from a local louh/mta-subway-bullets checkout."
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="Path to local louh/mta-subway-bullets directory (or nested PNG directory).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Destination directory for local runtime route symbols.",
    )
    parser.add_argument(
        "--max-px",
        type=int,
        default=10,
        help="Square dimension for output assets (must match runtime max asset size).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing PNG files in output directory before writing new files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing files.",
    )
    args = parser.parse_args()

    source_dir = pathlib.Path(args.source_dir).resolve()
    output_dir = pathlib.Path(args.output_dir).resolve()
    max_px = int(args.max_px)

    if max_px <= 0:
        raise ValueError("--max-px must be > 0")
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if args.clean:
        for path in output_dir.glob("*.png"):
            if args.dry_run:
                print(f"[dry-run] delete {path}")
            else:
                path.unlink()

    missing: List[str] = []
    copied = 0

    for symbol_key, candidates in SYMBOL_SOURCE_CANDIDATES.items():
        source = _find_png_by_stem(source_dir, candidates)
        if source is None:
            missing.append(symbol_key)
            continue

        target = output_dir / f"{symbol_key}.png"
        if args.dry_run:
            print(f"[dry-run] {source} -> {target}")
        else:
            _resize_to_square(source, target, max_px)
        copied += 1

    print(f"Symbol files generated: {copied}")
    if missing:
        print("Missing symbols: " + ",".join(missing))
        return 2

    print("All configured symbols generated successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
