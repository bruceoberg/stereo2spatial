"""PSD (Photoshop Document) stereo format handler.

Handles PSD files containing aligned stereo pairs in separate layers.
This supports a workflow where left and right eye images from a
dual-camera rig are placed into a Photoshop document, aligned (choosing
a convergence plane), and cropped to the overlap region.

Expected PSD structure:
  - Two pixel layers named "L" and "R" (case-insensitive)
  - Layers may have per-layer channel visibility set for anaglyph
    preview (e.g. L = red only, R = green+blue only). This is a
    non-destructive display setting in Photoshop's Advanced Blending;
    the underlying pixel data retains full color.

Naming convention (for automatic metadata discovery):
  - PSD file:      LR nnn.psd
  - Left original:  L nnn.jpg   (used as EXIF metadata source)
  - Right original:  R nnn.jpg

If the original left JPEG is found alongside the PSD, its EXIF data
is used for FOV computation and embedded in the output HEIC.
"""

import re
import sys
from pathlib import Path

from PIL import Image

from ..exif import exifSummaryFromPath
from .base import StereoFormat, StereoPair

# Threshold for detecting baked channel masking.
# If the mean intensity of a channel is below this, the channel
# is probably zeroed out from destructive editing.

G_CHANNEL_MEAN_THRESHOLD = 2.0


class FormatPsd(StereoFormat):
    """Handler for PSD stereo image files with L/R layers."""

    @staticmethod
    def lStrExtension() -> list[str]:
        return [".psd"]

    @staticmethod
    def fCanHandle(path: Path) -> bool:
        if path.suffix.lower() not in FormatPsd.lStrExtension():
            return False

        # Verify it's a PSD with layers named L and R.

        try:
            from psd_tools import PSDImage

            psd = PSDImage.open(path)
            setStrName = {layer.name.strip().upper() for layer in psd}
            return "L" in setStrName and "R" in setStrName
        except Exception:
            return False

    @staticmethod
    def extractPair(path: Path) -> StereoPair:
        """Extract left/right pair from a PSD with L and R layers.

        Each layer is composited onto the PSD canvas to preserve the
        alignment and crop performed in Photoshop.
        """

        from psd_tools import PSDImage

        psd = PSDImage.open(path)

        layerLeft = None
        layerRight = None

        for layer in psd:
            strName = layer.name.strip().upper()
            if strName == "L" and layerLeft is None:
                layerLeft = layer
            elif strName == "R" and layerRight is None:
                layerRight = layer

        if layerLeft is None or layerRight is None:
            lStrLayerName = [layer.name for layer in psd]
            raise ValueError(
                f"PSD must contain layers named 'L' and 'R'. "
                f"Found layers: {lStrLayerName}"
            )

        # Composite each layer onto the canvas. This gives us an RGBA
        # image at the PSD's canvas dimensions with the layer's pixels
        # placed at the correct (aligned) position.

        imgLeftRgba = layerLeft.composite()
        imgRightRgba = layerRight.composite()

        # Convert RGBA -> RGB. The alpha channel represents layer
        # coverage on the canvas; for a properly cropped PSD the
        # layers should fill the canvas.

        imgLeft = imgLeftRgba.convert("RGB")
        imgRight = imgRightRgba.convert("RGB")

        # Check for baked channel masking (destructive anaglyph).

        _warnIfChannelsBaked(imgLeft, "L", path)
        _warnIfChannelsBaked(imgRight, "R", path)

        # Look for the original left JPEG as a metadata source.

        pathMetadata = _pathMetadataForPsd(path)
        degFov: float | None = None

        if pathMetadata:
            summary = exifSummaryFromPath(pathMetadata)
            degFov = summary.degFovHorizontal

        return StereoPair(
            imgLeft=imgLeft,
            imgRight=imgRight,
            degFovHorizontal=degFov,
            pathSource=path,
            pathMetadataSource=pathMetadata,
        )


def _pathMetadataForPsd(pathPsd: Path) -> Path | None:
    """Find the original left JPEG matching a PSD's naming convention.

    Given 'LR nnn.psd', looks for 'L nnn.jpg' (or .jpeg) in the same
    directory. Returns None if not found.
    """

    strStem = pathPsd.stem

    # Match the pattern: starts with "LR" followed by the rest of the name.

    match = re.match(r"^[Ll][Rr](.+)$", strStem)
    if not match:
        return None

    strRest = match.group(1)
    strLeftStem = "L" + strRest

    for strExt in [".jpg", ".jpeg", ".JPG", ".JPEG"]:
        pathCandidate = pathPsd.parent / (strLeftStem + strExt)
        if pathCandidate.exists():
            return pathCandidate

    return None


def _warnIfChannelsBaked(img: Image.Image, strLayerName: str, pathPsd: Path) -> None:
    """Warn if a layer appears to have destructive channel masking.

    Photoshop's Advanced Blending channel toggles are non-destructive
    and the raw layer data retains full color. But if someone flattened
    or baked the effect, channels may be zeroed out.
    """

    try:
        import numpy as np

        aryPixel = np.array(img)

        # Check each channel's mean intensity.

        lGMean = [float(aryPixel[:, :, i].mean()) for i in range(3)]
        lStrChannel = ["R", "G", "B"]

        lStrDead: list[str] = []
        for i, gMean in enumerate(lGMean):
            if gMean < G_CHANNEL_MEAN_THRESHOLD:
                lStrDead.append(lStrChannel[i])

        if lStrDead:
            strDead = ", ".join(lStrDead)
            print(
                f"Warning: layer '{strLayerName}' in {pathPsd.name} has near-zero "
                f"{strDead} channel(s). The anaglyph channel masking may have been "
                f"baked destructively. The extracted image will lack color information "
                f"in those channels.",
                file=sys.stderr,
            )
    except ImportError:
        # numpy not available; skip the check.

        pass
