"""Tests for stereo2spatial format handlers."""

from pathlib import Path

from stereo2spatial.formats import lStrSupportedExtension


def test_lStrSupportedExtension():
    lStr = lStrSupportedExtension()
    assert ".mpo" in lStr
    assert ".jps" in lStr
