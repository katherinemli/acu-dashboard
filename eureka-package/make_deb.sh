#!/bin/bash
# Build ACU DEB package

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="/tmp/acu-deb-build"
PACKAGE_NAME="acu"
VERSION="1.0.0"
DEB_NAME="${PACKAGE_NAME}_${VERSION}_amd64.deb"

echo "Building ACU DEB package..."
echo "=================================="
echo "Project: $PROJECT_DIR"
echo "Build dir: $BUILD_DIR"
echo "Output: $DEB_NAME"
echo ""

# Clean old build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create DEB structure
INSTALL_ROOT="$BUILD_DIR/$PACKAGE_NAME-$VERSION"
mkdir -p "$INSTALL_ROOT"

# Copy debian metadata
cp -r "$SCRIPT_DIR/debian" "$INSTALL_ROOT/"
chmod +x "$INSTALL_ROOT/debian/postinst"
chmod +x "$INSTALL_ROOT/debian/prerm"
chmod +x "$INSTALL_ROOT/debian/postrm"

# Copy systemd services
mkdir -p "$INSTALL_ROOT/etc/systemd/system"
cp "$SCRIPT_DIR/etc/systemd/system/"*.service "$INSTALL_ROOT/etc/systemd/system/"

# Install application files
mkdir -p "$INSTALL_ROOT/opt/acu"
cp -r "$PROJECT_DIR/acu-daemon" "$INSTALL_ROOT/opt/acu/"
cp -r "$PROJECT_DIR/backend" "$INSTALL_ROOT/opt/acu/"
cp -r "$PROJECT_DIR/frontend/dist" "$INSTALL_ROOT/opt/acu/frontend" 2>/dev/null || echo "Note: frontend not built, skipping dist/"

# Create skeleton dirs
mkdir -p "$INSTALL_ROOT/var/log/acu"
mkdir -p "$INSTALL_ROOT/var/lib/acu"

# Build DEB package
echo "Building package..."
cd "$BUILD_DIR"
dpkg-deb --build "$PACKAGE_NAME-$VERSION" "$DEB_NAME" 2>&1 | grep -v "^dpkg-deb:" || true

# Copy to project root
cp "$BUILD_DIR/$DEB_NAME" "$SCRIPT_DIR/$DEB_NAME"

echo ""
echo "✅ Build complete!"
echo "Location: $SCRIPT_DIR/$DEB_NAME"
echo ""
echo "Install with:"
echo "  sudo dpkg -i $DEB_NAME"
echo "  sudo apt-get install -f  # (if deps missing)"
echo ""
echo "Start services:"
echo "  sudo systemctl start acu-daemon"
echo "  sudo systemctl start acu-backend"
echo ""
echo "View logs:"
echo "  sudo journalctl -u acu-backend -f"
echo "  sudo journalctl -u acu-daemon -f"
