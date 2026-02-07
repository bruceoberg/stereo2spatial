"""Stereo image format registry.

Discovers and manages format handlers. To add a new format, create a
module in this package with a class that inherits from StereoFormat.
"""

from pathlib import Path

from .base import StereoFormat, StereoPair
from .jps import FormatJps
from .mpo import FormatMpo
from .pair import extractPairFromFiles
from .psd import FormatPsd

# All known format handlers, checked in order.

g_lClsFormat: list[type[StereoFormat]] = [
    FormatMpo,
    FormatJps,
    FormatPsd,
]


def lStrSupportedExtension() -> list[str]:
    """Return all file extensions supported across all formats."""

    lStr: list[str] = []
    for clsFormat in g_lClsFormat:
        lStr.extend(clsFormat.lStrExtension())
    return lStr


def formatForPath(path: Path) -> StereoFormat | None:
    """Return the appropriate format handler for the given file, or None."""

    for clsFormat in g_lClsFormat:
        if clsFormat.fCanHandle(path):
            return clsFormat()
    return None


def extractPair(path: Path) -> StereoPair:
    """Extract a stereo pair from any supported format.

    Raises ValueError if the file format is not recognized.
    """

    fmt = formatForPath(path)
    if fmt is None:
        lStrExt = lStrSupportedExtension()
        raise ValueError(
            f"Unsupported stereo format: {path.suffix!r}. "
            f"Supported extensions: {', '.join(lStrExt)}"
        )

    return fmt.extractPair(path)


__all__ = [
    "StereoFormat",
    "StereoPair",
    "FormatMpo",
    "FormatJps",
    "FormatPsd",
    "extractPair",
    "extractPairFromFiles",
    "formatForPath",
    "lStrSupportedExtension",
]
