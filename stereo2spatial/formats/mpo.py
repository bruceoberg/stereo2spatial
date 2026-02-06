"""MPO (Multi-Picture Object) stereo format handler.

MPO files contain two or more JPEG images. Stereo cameras like the
Fujifilm FinePix Real 3D W1/W3 store left and right eye images as
the first two frames.
"""

from pathlib import Path

from PIL import Image

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
        """

        with Image.open(path) as img:
            # Frame 0: left eye.

            img.seek(0)
            imgLeft = img.copy()

            # Frame 1: right eye.

            img.seek(1)
            imgRight = img.copy()

        # Try to extract camera metadata from EXIF.

        degFov = _degFovFromExif(imgLeft)
        mmBaseline = _mmBaselineFromExif(imgLeft)

        return StereoPair(
            imgLeft=imgLeft,
            imgRight=imgRight,
            degFovHorizontal=degFov,
            mmBaseline=mmBaseline,
            pathSource=path,
        )


def _degFovFromExif(img: Image.Image) -> float | None:
    """Try to extract horizontal FOV from EXIF data."""

    exif = img.getexif()
    if not exif:
        return None

    # EXIF tag 0xA405 = FocalLengthIn35mmFilm

    nFocal35mm = exif.get(0xA405)
    if nFocal35mm and nFocal35mm > 0:
        # Standard 35mm frame is 36mm wide.
        # FOV = 2 * atan(36 / (2 * focal_length_35mm))

        import math

        return 2.0 * math.degrees(math.atan(36.0 / (2.0 * nFocal35mm)))

    return None


def _mmBaselineFromExif(img: Image.Image) -> float | None:
    """Try to extract stereo baseline from MPO metadata.

    The MPO spec includes tags for convergence angle and baseline,
    but these are not consistently populated. Returns None if not found.
    """

    # TODO: Parse MPO-specific tags for baseline distance.
    # The Fuji W3 has a ~77mm baseline but doesn't always write it to EXIF.

    return None
