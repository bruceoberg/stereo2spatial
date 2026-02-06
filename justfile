# stereo2spatial justfile

swift_src := "swift/Pair2Spatial.swift"
binary := "build/pair2spatial"

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
        swiftc -O "{{ swift_src }}" -o "{{ binary }}"; \
        echo "Built {{ binary }}"; \
    fi

# Force rebuild
rebuild:
    @mkdir -p build
    swiftc -O {{ swift_src }} -o {{ binary }}
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
