"""Separate left/right image pair handler.

Handles the case where left and right eye images are stored as
separate files (e.g. from a dual-DSLR stereo rig). This handler
is not auto-detected by extension; it is invoked directly by the
CLI when --left and --right are specified.
"""

from pathlib import Path

from PIL import Image

from ..exif import exifSummaryFromPath
from .base import StereoPair


def extractPairFromFiles(
    pathLeft: Path,
    pathRight: Path,
    pathMetadata: Path | None = None,
) -> StereoPair:
    """Build a StereoPair from two separate image files.

    pathMetadata: optional third image whose EXIF is used as the
    metadata source. If None, the left image is used.
    """

    imgLeft = Image.open(pathLeft)
    imgRight = Image.open(pathRight)

    # Determine the metadata source.

    pathMetadataSource = pathMetadata or pathLeft

    # Extract FOV from the metadata source's EXIF.

    summary = exifSummaryFromPath(pathMetadataSource)

    return StereoPair(
        imgLeft=imgLeft,
        imgRight=imgRight,
        degFovHorizontal=summary.degFovHorizontal,
        pathSource=pathLeft,
        pathMetadataSource=pathMetadataSource,
    )
