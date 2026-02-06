"""JPS (JPEG Stereo) format handler.

JPS files are standard JPEG files containing a side-by-side stereo pair.
The left half of the image is the left eye, and the right half is the
right eye. Some JPS files may be cross-eye (right-left) instead.
"""

from pathlib import Path

from PIL import Image

from ..exif import exifSummaryFromImage
from .base import StereoFormat, StereoPair


class FormatJps(StereoFormat):
    """Handler for JPS side-by-side stereo image files."""

    @staticmethod
    def lStrExtension() -> list[str]:
        return [".jps"]

    @staticmethod
    def fCanHandle(path: Path) -> bool:
        if path.suffix.lower() not in FormatJps.lStrExtension():
            return False

        try:
            with Image.open(path) as img:
                # SBS images should be roughly 2:1 aspect ratio.

                rAspect = img.width / img.height
                return rAspect > 1.5
        except OSError:
            return False

    @staticmethod
    def extractPair(path: Path) -> StereoPair:
        """Extract left/right pair from a JPS side-by-side image.

        Assumes parallel (left-right) layout. The image is split down
        the middle.
        """

        with Image.open(path) as img:
            nHalfWidth = img.width // 2

            imgLeft = img.crop((0, 0, nHalfWidth, img.height))
            imgRight = img.crop((nHalfWidth, 0, img.width, img.height))

            # JPS files sometimes carry EXIF from the capture device.

            summary = exifSummaryFromImage(img)

        return StereoPair(
            imgLeft=imgLeft,
            imgRight=imgRight,
            degFovHorizontal=summary.degFovHorizontal,
            pathSource=path,
            pathMetadataSource=path,
        )
