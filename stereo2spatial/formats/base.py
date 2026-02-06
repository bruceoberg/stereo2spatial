"""Base class for stereo image format handlers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class StereoPair:
    """A pair of left/right images extracted from a stereo source.

    pathMetadataSource is the file whose EXIF/metadata should be copied
    into the output HEIC. Defaults to the original source file for
    single-file formats (MPO, JPS), or the left image for pair mode.
    """

    imgLeft: Image.Image
    imgRight: Image.Image
    degFovHorizontal: float | None = None  # Source FOV if known from metadata
    mmBaseline: float | None = None  # Source baseline if known from metadata
    pathSource: Path | None = None  # Path to the original file
    pathMetadataSource: Path | None = None  # EXIF donor image (for HEIC metadata)


class StereoFormat(ABC):
    """Base class for stereo image format handlers."""

    @staticmethod
    @abstractmethod
    def lStrExtension() -> list[str]:
        """Return list of file extensions this format handles (e.g. ['.mpo'])."""
        ...

    @staticmethod
    @abstractmethod
    def fCanHandle(path: Path) -> bool:
        """Return True if this handler can process the given file."""
        ...

    @staticmethod
    @abstractmethod
    def extractPair(path: Path) -> StereoPair:
        """Extract the left/right stereo pair from the given file."""
        ...
