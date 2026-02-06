# stereo2spatial

Convert stereo image files (MPO, JPS, ...) to Apple spatial HEIC photos viewable on Apple Vision Pro.

## Requirements

- macOS (Apple Silicon or Intel)
- Xcode Command Line Tools (`xcode-select --install`)
- [devenv](https://devenv.sh/) (manages Python and tooling)

## Setup

```bash
git clone <repo-url>
cd stereo2spatial
devenv shell
just build
```

## Usage

```bash
# Convert a single MPO file
just convert photo.mpo

# Convert multiple files
just convert *.mpo *.jps

# Specify output directory
just convert -o output/ photo.mpo

# Override camera parameters
just convert --fov 53.7 --baseline 77 photo.mpo
```

Or using the Python entry point directly:

```bash
uv run stereo2spatial photo.mpo
```

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| MPO    | `.mpo`    | Multi-Picture Object (Fuji W3, etc.) |
| JPS    | `.jps`    | JPEG Stereo (side-by-side) |

## Architecture

**stereo2spatial** (Python) handles format detection, image extraction, and
orchestration. **pair2spatial** (Swift) handles the final HEIC packaging with
Apple's spatial photo metadata via the ImageIO framework.

```
stereo file  →  [Python: extract L/R pair]  →  [Swift: pair2spatial]  →  spatial .heic
```

The Swift component is necessary because Apple's spatial photo metadata
(`kCGImagePropertyGroupTypeStereoPair`, camera intrinsics) requires the
macOS ImageIO framework, which isn't accessible from Python.

## Project Structure

```
stereo2spatial/
├── devenv.nix              # Development environment
├── justfile                # Build & run recipes
├── pyproject.toml          # Python project config
├── swift/
│   └── Pair2Spatial.swift  # Swift CLI: L/R images → spatial HEIC
└── stereo2spatial/
    ├── __init__.py
    ├── cli.py              # Python CLI entry point
    ├── combiner.py         # Invokes pair2spatial binary
    └── formats/
        ├── __init__.py     # Format registry
        ├── base.py         # StereoFormat base class
        ├── mpo.py          # MPO handler
        └── jps.py          # JPS handler
```
