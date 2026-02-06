"""Command-line interface for stereo2spatial."""

import argparse
import sys
from pathlib import Path

from . import formats
from .combiner import createSpatialHeic


def buildParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stereo2spatial",
        description="Convert stereo image files (MPO, JPS, ...) to Apple spatial HEIC photos.",
    )

    parser.add_argument(
        "lPathInput",
        metavar="INPUT",
        nargs="+",
        type=Path,
        help="One or more stereo image files to convert.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        dest="pathDirOutput",
        type=Path,
        default=None,
        help="Output directory (default: same directory as input file).",
    )

    parser.add_argument(
        "--fov",
        dest="degFov",
        type=float,
        default=None,
        help="Horizontal field of view in degrees (overrides metadata).",
    )

    parser.add_argument(
        "--baseline",
        dest="mmBaseline",
        type=float,
        default=None,
        help="Stereo baseline in millimeters (overrides metadata).",
    )

    parser.add_argument(
        "--suffix",
        dest="strSuffix",
        type=str,
        default="_spatial",
        help="Suffix to add before .heic extension (default: '_spatial').",
    )

    return parser


def main(lStrArg: list[str] | None = None) -> int:
    parser = buildParser()
    args = parser.parse_args(lStrArg)

    lStrExt = formats.lStrSupportedExtension()
    cError = 0
    cConverted = 0

    for pathInput in args.lPathInput:
        if not pathInput.exists():
            print(f"Error: file not found: {pathInput}", file=sys.stderr)
            cError += 1
            continue

        # Determine output path.

        pathDirOutput = args.pathDirOutput or pathInput.parent
        pathDirOutput.mkdir(parents=True, exist_ok=True)
        strStem = pathInput.stem + args.strSuffix
        pathOutput = pathDirOutput / (strStem + ".heic")

        try:
            pair = formats.extractPair(pathInput)
        except ValueError as err:
            print(f"Error: {err}", file=sys.stderr)
            cError += 1
            continue

        try:
            createSpatialHeic(
                pair=pair,
                pathOutput=pathOutput,
                degFovHorizontal=args.degFov,
                mmBaseline=args.mmBaseline,
            )
            cConverted += 1
            print(f"{pathInput.name} -> {pathOutput.name}")
        except (RuntimeError, FileNotFoundError) as err:
            print(f"Error converting {pathInput.name}: {err}", file=sys.stderr)
            cError += 1

    if cConverted > 0:
        print(f"\nConverted {cConverted} file(s).", file=sys.stderr)

    if cError > 0:
        print(f"{cError} error(s).", file=sys.stderr)

    return 1 if cError > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
