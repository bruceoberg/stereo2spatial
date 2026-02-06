# stereo2spatial

Convert stereo image files to Apple spatial HEIC photos for viewing on Apple Vision Pro.

## Supported Inputs

- **MPO** files (Fujifilm FinePix W1/W3, etc.)
- **JPS** files (side-by-side JPEG stereo)
- **Separate left/right image pairs** (from dual-DSLR rigs, etc.)

## Usage

### Stereo file mode (MPO, JPS)

```sh
stereo2spatial photo.mpo                    # -> photo_spatial.heic
stereo2spatial *.mpo -o output/             # batch conversion
```

### Left/right pair mode

```sh
stereo2spatial --left DSC_001_L.jpg --right DSC_001_R.jpg
stereo2spatial --left L.tif --right R.tif --output stereo_001.heic
```

### EXIF metadata source

By default, EXIF/metadata from the source file (stereo mode) or the left image (pair mode) is embedded in the output HEIC. Use `--metadata` to specify a different source:

```sh
# Use the right image's EXIF (maybe it was the "master" camera)
stereo2spatial --left L.jpg --right R.jpg --metadata R.jpg

# Use a third reference image for metadata
stereo2spatial photo.mpo --metadata reference.jpg
```

### FOV and baseline

The tool computes horizontal FOV from EXIF data when possible:

1. **FocalLengthIn35mmFilm** tag (most reliable)
2. **FocalLength + FocalPlaneResolution** tags (sensor width derivation)
3. **FocalLength + known camera model** database (last resort)

Override with `--fov` and `--baseline`:

```sh
stereo2spatial photo.mpo --fov 63.5 --baseline 77
```

### Verbose mode

Use `-v` to see what EXIF data was found and how FOV was computed:

```sh
stereo2spatial -v photo.mpo
```

## Options

| Flag | Description |
|------|-------------|
| `--left <path>` | Left-eye image (use with `--right`) |
| `--right <path>` | Right-eye image (use with `--left`) |
| `--metadata <path>` | EXIF donor image for the output HEIC |
| `-o, --output-dir <dir>` | Output directory |
| `--output <path>` | Explicit output path (pair mode) |
| `--fov <degrees>` | Override horizontal field of view |
| `--baseline <mm>` | Override stereo baseline |
| `--suffix <str>` | Output filename suffix (default: `_spatial`) |
| `-v, --verbose` | Print EXIF/metadata details |

## Building

Requires macOS with Xcode Command Line Tools (for the Swift pair2spatial binary).

```sh
just build      # compile Swift binary
just convert photo.mpo   # build + convert
```

## Development

Uses [devenv](https://devenv.sh/) for reproducible development environment.

```sh
devenv shell
just test
```
