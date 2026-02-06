"""MPO (Multi-Picture Object) stereo format handler.

MPO files contain two or more JPEG images. Stereo cameras like the
Fujifilm FinePix Real 3D W1/W3 store left and right eye images as
the first two frames.
"""

from pathlib import Path

from PIL import Image

from ..exif import exifSummaryFromImage
from .base import StereoFormat, StereoPair


class FormatMpo(StereoFormat):
    """Handler for MPO stereo image files."""

    @staticmethod
    def lStrExtension() -> list[str]:
        return [".mpo"]

    @staticmethod
    def fCanHandle(path: Path) -> bool:
        if path.suffix.lower() not in FormatMpo.lStrExtension():
            return False

        # Verify it's actually an MPO with at least 2 frames.

        try:
            with Image.open(path) as img:
                img.seek(1)
                return True
        except (EOFError, OSError):
            return False

    @staticmethod
    def extractPair(path: Path) -> StereoPair:
        """Extract left/right pair from an MPO file.

        Frame 0 is the left eye, frame 1 is the right eye.
        Metadata (FOV, baseline) is extracted from EXIF if available.
        The MPO file itself is used as the metadata source for the HEIC,
        since Swift's CGImageSource can read EXIF from MPO/JPEG natively.
        """

        with Image.open(path) as img:
            # Frame 0: left eye.

            img.seek(0)
            imgLeft = img.copy()

            # Frame 1: right eye.

            img.seek(1)
            imgRight = img.copy()

        # Extract camera metadata from EXIF.

        summary = exifSummaryFromImage(imgLeft)

        return StereoPair(
            imgLeft=imgLeft,
            imgRight=imgRight,
            degFovHorizontal=summary.degFovHorizontal,
            mmBaseline=None,  # MPO baseline tags are rarely populated.
            pathSource=path,
            pathMetadataSource=path,  # CGImageSource reads EXIF from MPO directly.
        )
