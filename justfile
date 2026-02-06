# stereo2spatial justfile

swift_src := "swift/Pair2Spatial.swift"
binary := "build/pair2spatial"

# Bypass Nix toolchain entirely: use the real system swiftc and SDK.
# Nix sets SDKROOT/DEVELOPER_DIR which poisons even /usr/bin/xcrun,
# so we must clear them for the Swift build.
swiftc := "env -u SDKROOT -u DEVELOPER_DIR -u MACOSX_DEPLOYMENT_TARGET /usr/bin/swiftc"

# List available recipes
default:
    @just --list

# Build the pair2spatial Swift CLI (lazy: skips if binary is newer than source)
build:
    @mkdir -p build
    @if [ "{{ binary }}" -nt "{{ swift_src }}" ] 2>/dev/null; then \
        echo "pair2spatial is up to date"; \
    else \
        echo "Building pair2spatial..."; \
        {{ swiftc }} -O "{{ swift_src }}" -o "{{ binary }}"; \
        echo "Built {{ binary }}"; \
    fi

# Force rebuild
rebuild:
    @mkdir -p build
    {{ swiftc }} -O {{ swift_src }} -o {{ binary }}
    @echo "Built {{ binary }}"

# Convert stereo files to spatial HEIC
convert *args: build
    uv run stereo2spatial {{ args }}

# Run tests
test: build
    uv run pytest

# Clean build artifacts
clean:
    rm -rf build/

# Show pair2spatial usage
pair2spatial-help: build
    ./{{ binary }} --help || true
