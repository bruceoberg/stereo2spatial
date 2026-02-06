"""Combiner module: invokes pair2spatial to create spatial HEIC files."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from .formats.base import StereoPair

# Default camera parameters for when metadata is unavailable.

DEG_FOV_DEFAULT = 55.0
MM_BASELINE_DEFAULT = 65.0


def pathPair2Spatial() -> Path:
    """Locate the pair2spatial binary.

    Searches in order:
      1. build/pair2spatial  (local justfile build)
      2. On PATH via shutil.which
    """

    # Local build directory (relative to project root).

    pathLocal = Path(__file__).parent.parent / "build" / "pair2spatial"
    if pathLocal.is_file():
        return pathLocal

    pathWhich = shutil.which("pair2spatial")
    if pathWhich is not None:
        return Path(pathWhich)

    raise FileNotFoundError(
        "pair2spatial binary not found. Run 'just build' to compile it."
    )


def createSpatialHeic(
    pair: StereoPair,
    pathOutput: Path,
    degFovHorizontal: float | None = None,
    mmBaseline: float | None = None,
) -> Path:
    """Convert a StereoPair to a spatial HEIC file.

    Uses the pair's embedded metadata for FOV/baseline if available,
    falling back to the explicit arguments, then to defaults.

    Returns the output path.
    """

    degFov = degFovHorizontal or pair.degFovHorizontal or DEG_FOV_DEFAULT
    mmBase = mmBaseline or pair.mmBaseline or MM_BASELINE_DEFAULT

    pathBinary = pathPair2Spatial()

    # Save left/right images as temporary files for pair2spatial.

    with tempfile.TemporaryDirectory(prefix="stereo2spatial_") as strDirTmp:
        dirTmp = Path(strDirTmp)
        pathLeft = dirTmp / "left.jpg"
        pathRight = dirTmp / "right.jpg"

        pair.imgLeft.save(pathLeft, format="JPEG", quality=95)
        pair.imgRight.save(pathRight, format="JPEG", quality=95)

        lStrCmd = [
            str(pathBinary),
            str(pathLeft),
            str(pathRight),
            str(pathOutput),
            "--fov",
            str(degFov),
            "--baseline",
            str(mmBase),
        ]

        # Pass the metadata source image so Swift can copy its EXIF into the HEIC.

        pathMetadata = pair.pathMetadataSource
        if pathMetadata and pathMetadata.is_file():
            lStrCmd.extend(["--metadata", str(pathMetadata)])

        result = subprocess.run(
            lStrCmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"pair2spatial failed (exit {result.returncode}):\n{result.stderr}"
            )

        if result.stderr:
            # pair2spatial writes status to stderr.

            print(result.stderr, end="")

    return pathOutput
