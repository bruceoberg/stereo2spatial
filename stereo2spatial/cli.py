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

    # Mutually exclusive input modes: stereo files OR left+right pair.

    grpInput = parser.add_argument_group("input (choose one mode)")

    grpInput.add_argument(
        "lPathInput",
        metavar="INPUT",
        nargs="*",
        type=Path,
        default=[],
        help="One or more stereo image files to convert (MPO, JPS, etc.).",
    )

    grpInput.add_argument(
        "--left",
        dest="pathLeft",
        type=Path,
        default=None,
        help="Left-eye image file (use with --right for a separate L/R pair).",
    )

    grpInput.add_argument(
        "--right",
        dest="pathRight",
        type=Path,
        default=None,
        help="Right-eye image file (use with --left for a separate L/R pair).",
    )

    parser.add_argument(
        "--metadata",
        dest="pathMetadata",
        type=Path,
        default=None,
        help=(
            "Image file whose EXIF/metadata is embedded in the output HEIC. "
            "Can be one of the pair or a separate file. "
            "Default: the source file (stereo mode) or the left image (pair mode)."
        ),
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
        "--output",
        dest="pathOutput",
        type=Path,
        default=None,
        help="Explicit output file path (pair mode only, overrides --output-dir and --suffix).",
    )

    parser.add_argument(
        "--fov",
        dest="degFov",
        type=float,
        default=None,
        help="Horizontal field of view in degrees (overrides EXIF-derived value).",
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

    parser.add_argument(
        "-v",
        "--verbose",
        dest="fVerbose",
        action="store_true",
        default=False,
        help="Print EXIF/metadata details during conversion.",
    )

    return parser


def _convertStereoFile(
    pathInput: Path,
    args: argparse.Namespace,
) -> bool:
    """Convert a single stereo format file. Returns True on success."""

    # Determine output path.

    pathDirOutput = args.pathDirOutput or pathInput.parent
    pathDirOutput.mkdir(parents=True, exist_ok=True)
    strStem = pathInput.stem + args.strSuffix
    pathOutput = pathDirOutput / (strStem + ".heic")

    try:
        pair = formats.extractPair(pathInput)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return False

    # Override metadata source if --metadata was specified.

    if args.pathMetadata:
        pair.pathMetadataSource = args.pathMetadata

    if args.fVerbose:
        _printMetadataInfo(pair)

    try:
        createSpatialHeic(
            pair=pair,
            pathOutput=pathOutput,
            degFovHorizontal=args.degFov,
            mmBaseline=args.mmBaseline,
        )
        print(f"{pathInput.name} -> {pathOutput.name}")
        return True
    except (RuntimeError, FileNotFoundError) as err:
        print(f"Error converting {pathInput.name}: {err}", file=sys.stderr)
        return False


def _convertPair(args: argparse.Namespace) -> bool:
    """Convert a left/right pair. Returns True on success."""

    for path, strLabel in [(args.pathLeft, "--left"), (args.pathRight, "--right")]:
        if not path.exists():
            print(f"Error: {strLabel} file not found: {path}", file=sys.stderr)
            return False

    if args.pathMetadata and not args.pathMetadata.exists():
        print(f"Error: --metadata file not found: {args.pathMetadata}", file=sys.stderr)
        return False

    pair = formats.extractPairFromFiles(
        pathLeft=args.pathLeft,
        pathRight=args.pathRight,
        pathMetadata=args.pathMetadata,
    )

    # Determine output path.

    if args.pathOutput:
        pathOutput = args.pathOutput
    else:
        pathDirOutput = args.pathDirOutput or args.pathLeft.parent
        pathDirOutput.mkdir(parents=True, exist_ok=True)
        strStem = args.pathLeft.stem + args.strSuffix
        pathOutput = pathDirOutput / (strStem + ".heic")

    if args.fVerbose:
        _printMetadataInfo(pair)

    try:
        createSpatialHeic(
            pair=pair,
            pathOutput=pathOutput,
            degFovHorizontal=args.degFov,
            mmBaseline=args.mmBaseline,
        )
        print(f"{args.pathLeft.name} + {args.pathRight.name} -> {pathOutput.name}")
        return True
    except (RuntimeError, FileNotFoundError) as err:
        print(f"Error converting pair: {err}", file=sys.stderr)
        return False


def _printMetadataInfo(pair: formats.StereoPair) -> None:
    """Print metadata summary for verbose mode."""

    from .exif import exifSummaryFromPath

    pathMeta = pair.pathMetadataSource
    if not pathMeta:
        print("  Metadata source: (none)", file=sys.stderr)
        return

    print(f"  Metadata source: {pathMeta.name}", file=sys.stderr)

    summary = exifSummaryFromPath(pathMeta)
    if summary.strMake or summary.strModel:
        print(f"  Camera: {summary.strMake or '?'} {summary.strModel or '?'}", file=sys.stderr)
    if summary.mmFocalLength:
        print(f"  Focal length: {summary.mmFocalLength:.1f}mm", file=sys.stderr)
    if summary.nFocalLength35mm:
        print(f"  Focal length (35mm equiv): {summary.nFocalLength35mm}mm", file=sys.stderr)
    if summary.mmSensorWidth:
        print(f"  Sensor width: {summary.mmSensorWidth:.2f}mm", file=sys.stderr)
    if summary.degFovHorizontal:
        print(f"  Computed FOV: {summary.degFovHorizontal:.1f}\u00b0", file=sys.stderr)
    else:
        print("  Computed FOV: (unavailable, will use default)", file=sys.stderr)


def main(lStrArg: list[str] | None = None) -> int:
    parser = buildParser()
    args = parser.parse_args(lStrArg)

    # Validate input mode.

    fHasLeft = args.pathLeft is not None
    fHasRight = args.pathRight is not None
    fHasStereoFiles = len(args.lPathInput) > 0

    if fHasLeft != fHasRight:
        print("Error: --left and --right must be used together.", file=sys.stderr)
        return 1

    fPairMode = fHasLeft and fHasRight

    if fPairMode and fHasStereoFiles:
        print(
            "Error: cannot combine positional stereo files with --left/--right.",
            file=sys.stderr,
        )
        return 1

    if not fPairMode and not fHasStereoFiles:
        parser.print_help(sys.stderr)
        return 1

    # Pair mode: single conversion.

    if fPairMode:
        return 0 if _convertPair(args) else 1

    # Stereo file mode: batch conversion.

    cError = 0
    cConverted = 0

    for pathInput in args.lPathInput:
        if not pathInput.exists():
            print(f"Error: file not found: {pathInput}", file=sys.stderr)
            cError += 1
            continue

        if _convertStereoFile(pathInput, args):
            cConverted += 1
        else:
            cError += 1

    if cConverted > 0:
        print(f"\nConverted {cConverted} file(s).", file=sys.stderr)

    if cError > 0:
        print(f"{cError} error(s).", file=sys.stderr)

    return 1 if cError > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
