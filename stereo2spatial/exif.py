"""EXIF metadata extraction and camera parameter computation.

Extracts FOV, focal length, and other camera metadata from EXIF data.
Supports multiple computation strategies with graceful fallback.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifTag, IFD

# -- EXIF tag constants not in Pillow's enum ------------------------------------

TAG_FOCAL_LENGTH = 0x920A  # ExifTag.FocalLength
TAG_FOCAL_LENGTH_35MM = 0xA405  # ExifTag.FocalLengthIn35mmFilm
TAG_FOCAL_PLANE_X_RES = 0xA20E  # FocalPlaneXResolution
TAG_FOCAL_PLANE_Y_RES = 0xA20F  # FocalPlaneYResolution
TAG_FOCAL_PLANE_RES_UNIT = 0xA210  # FocalPlaneResolutionUnit
TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_IMAGE_WIDTH = 0xA002  # ExifImageWidth (pixel count)
TAG_IMAGE_HEIGHT = 0xA003  # ExifImageHeight (pixel count)

# FocalPlaneResolutionUnit values -> mm conversion.

MM_PER_INCH = 25.4
MM_PER_CM = 10.0
g_mpUnitMmPerUnit: dict[int, float] = {
    2: MM_PER_INCH,  # inches
    3: MM_PER_CM,  # centimeters
}

# Width of a 35mm film frame in mm, used for FOV from 35mm-equivalent focal length.

MM_FRAME_WIDTH_35MM = 36.0

# -- Known sensor sizes (width in mm) keyed by (make_lower, model_substring) ----
#
# Used as a last-resort fallback when FocalPlaneResolution tags are absent.
# Only cameras likely to appear in Bruce's stereo workflow are listed.

g_lSensorEntry: list[tuple[str, str, float]] = [
    # Canon full-frame bodies
    ("canon", "5d", 36.0),
    ("canon", "6d", 35.8),
    ("canon", "1d x", 36.0),
    ("canon", "eos r5", 36.0),
    ("canon", "eos r6", 35.9),
    ("canon", "eos r", 36.0),

    # Canon APS-C
    ("canon", "7d", 22.4),
    ("canon", "80d", 22.5),
    ("canon", "90d", 22.3),

    # Sony full-frame
    ("sony", "ilce-7", 35.8),  # a7 series
    ("sony", "ilce-9", 35.6),

    # Sony APS-C / compact
    ("sony", "dsc-rx100", 13.2),  # 1-inch
    ("sony", "dsc-rx10", 13.2),
    ("sony", "dsc-hx", 6.17),  # small sensor compacts
    ("sony", "dsc-w", 6.17),

    # Fujifilm
    ("fujifilm", "finepix real 3d", 6.16),  # W1/W3 stereo cameras
    ("fujifilm", "finepix w", 6.16),
    ("fujifilm", "x-t", 23.5),  # X-mount APS-C
    ("fujifilm", "x-pro", 23.5),
    ("fujifilm", "gfx", 43.8),  # medium format

    # Nikon full-frame
    ("nikon", "d8", 35.9),  # D800, D810, D850
    ("nikon", "d7", 35.9),  # D700, D750, D780
    ("nikon", "z 5", 35.9),
    ("nikon", "z 6", 35.9),
    ("nikon", "z 7", 35.9),

    # Nikon APS-C
    ("nikon", "d5", 23.5),  # D5xxx series
    ("nikon", "d7", 23.5),  # D7xxx series -- note overlap with D700 full-frame
]


@dataclass
class ExifSummary:
    """Extracted camera metadata relevant to spatial photo creation."""

    strMake: str | None = None
    strModel: str | None = None
    mmFocalLength: float | None = None
    nFocalLength35mm: int | None = None
    mmSensorWidth: float | None = None
    degFovHorizontal: float | None = None
    nPixelWidth: int | None = None
    nPixelHeight: int | None = None

    # Raw EXIF dict for pass-through. Not used for computation,
    # but available for debugging/logging.

    mpTagValue: dict[int, object] = field(default_factory=dict)


def exifSummaryFromImage(img: Image.Image) -> ExifSummary:
    """Extract an ExifSummary from a PIL Image's EXIF data."""

    exif = img.getexif()
    if not exif:
        return ExifSummary()

    # Read the EXIF IFD for the detailed camera tags.

    mpExifIfd: dict[int, object] = {}
    try:
        mpExifIfd = dict(exif.get_ifd(IFD.Exif))
    except Exception:
        pass

    # Merge base-level and IFD-level tags for uniform access.

    mpTag: dict[int, object] = dict(exif)
    mpTag.update(mpExifIfd)

    strMake = _strFromTag(mpTag, TAG_MAKE)
    strModel = _strFromTag(mpTag, TAG_MODEL)
    mmFocalLength = _gFromRationalTag(mpTag, TAG_FOCAL_LENGTH)
    nFocalLength35mm = _nFromTag(mpTag, TAG_FOCAL_LENGTH_35MM)
    nPixelWidth = _nFromTag(mpTag, TAG_IMAGE_WIDTH) or img.width
    nPixelHeight = _nFromTag(mpTag, TAG_IMAGE_HEIGHT) or img.height

    # Compute sensor width from FocalPlaneResolution if available.

    mmSensorWidth = _mmSensorWidthFromFocalPlane(mpTag, nPixelWidth)

    # If FocalPlane tags didn't work, try the known-sensor database.

    if mmSensorWidth is None and strMake and strModel:
        mmSensorWidth = _mmSensorWidthFromModel(strMake, strModel)

    # Compute horizontal FOV using the best available data.

    degFov = _degFovCompute(
        nFocalLength35mm=nFocalLength35mm,
        mmFocalLength=mmFocalLength,
        mmSensorWidth=mmSensorWidth,
    )

    return ExifSummary(
        strMake=strMake,
        strModel=strModel,
        mmFocalLength=mmFocalLength,
        nFocalLength35mm=nFocalLength35mm,
        mmSensorWidth=mmSensorWidth,
        degFovHorizontal=degFov,
        nPixelWidth=nPixelWidth,
        nPixelHeight=nPixelHeight,
        mpTagValue=mpTag,
    )


def exifSummaryFromPath(path: Path) -> ExifSummary:
    """Extract an ExifSummary from an image file path."""

    with Image.open(path) as img:
        return exifSummaryFromImage(img)


def degFovFromPath(path: Path) -> float | None:
    """Convenience: extract just horizontal FOV from an image file."""

    return exifSummaryFromPath(path).degFovHorizontal


# -- Private helpers -----------------------------------------------------------


def _degFovCompute(
    nFocalLength35mm: int | None,
    mmFocalLength: float | None,
    mmSensorWidth: float | None,
) -> float | None:
    """Compute horizontal FOV in degrees using the best available data.

    Strategy order:
      1. FocalLengthIn35mmFilm (most reliable, already normalized)
      2. FocalLength + sensor width (from FocalPlane tags or model DB)
    """

    # Strategy 1: 35mm-equivalent focal length.

    if nFocalLength35mm and nFocalLength35mm > 0:
        return 2.0 * math.degrees(
            math.atan(MM_FRAME_WIDTH_35MM / (2.0 * nFocalLength35mm))
        )

    # Strategy 2: actual focal length + known sensor width.

    if mmFocalLength and mmFocalLength > 0 and mmSensorWidth and mmSensorWidth > 0:
        return 2.0 * math.degrees(
            math.atan(mmSensorWidth / (2.0 * mmFocalLength))
        )

    return None


def _mmSensorWidthFromFocalPlane(
    mpTag: dict[int, object],
    nPixelWidth: int | None,
) -> float | None:
    """Derive sensor width from FocalPlaneXResolution and image width.

    sensor_width_mm = pixel_width / (FocalPlaneXRes * unit_to_mm)
    """

    gFocalPlaneXRes = _gFromRationalTag(mpTag, TAG_FOCAL_PLANE_X_RES)
    if not gFocalPlaneXRes or gFocalPlaneXRes <= 0:
        return None

    nUnit = _nFromTag(mpTag, TAG_FOCAL_PLANE_RES_UNIT)
    mmPerUnit = g_mpUnitMmPerUnit.get(nUnit or 0)
    if mmPerUnit is None:
        return None

    if not nPixelWidth or nPixelWidth <= 0:
        return None

    # FocalPlaneXRes is pixels per unit. Sensor width = pixels / (pixels/unit) * mm/unit.

    return (nPixelWidth / gFocalPlaneXRes) * mmPerUnit


def _mmSensorWidthFromModel(strMake: str, strModel: str) -> float | None:
    """Look up sensor width from the known camera model database."""

    strMakeLower = strMake.strip().lower()
    strModelLower = strModel.strip().lower()

    for strEntryMake, strEntryModel, mmWidth in g_lSensorEntry:
        if strEntryMake in strMakeLower and strEntryModel in strModelLower:
            return mmWidth

    return None


def _strFromTag(mpTag: dict[int, object], nTag: int) -> str | None:
    """Extract a string value from an EXIF tag, or None."""

    val = mpTag.get(nTag)
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace").strip("\x00 ")
    return str(val).strip()


def _nFromTag(mpTag: dict[int, object], nTag: int) -> int | None:
    """Extract an integer value from an EXIF tag, or None."""

    val = mpTag.get(nTag)
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _gFromRationalTag(mpTag: dict[int, object], nTag: int) -> float | None:
    """Extract a float from an EXIF rational or numeric tag, or None."""

    val = mpTag.get(nTag)
    if val is None:
        return None

    # Pillow returns IFDRational which acts like a float.

    try:
        g = float(val)
        return g if g > 0 else None
    except (ValueError, TypeError):
        return None
