#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:-alpha1}"
ARCH="x86_64"
APPDIR="$SCRIPT_DIR/dist/nora.AppDir"
OUTPUT_PATH="$SCRIPT_DIR/dist/Nora-${VERSION}-${ARCH}.AppImage"
BINARY="$SCRIPT_DIR/dist/nora"
ICON="$SCRIPT_DIR/src/assets/nora.png"
DESKTOP_FILE="$SCRIPT_DIR/nora.desktop"

# Verify prerequisites
if [[ ! -f "$BINARY" ]]; then
    echo "ERROR: PyInstaller binary not found at $BINARY"
    echo "Run 'npm run build:linux' first."
    exit 1
fi

# Download tools to build-tools/ if not cached
TOOLS_DIR="$SCRIPT_DIR/build-tools"
mkdir -p "$TOOLS_DIR"

LINUXDEPLOY="$TOOLS_DIR/linuxdeploy-x86_64.AppImage"
LINUXDEPLOY_GTK="$TOOLS_DIR/linuxdeploy-plugin-gtk.sh"
APPIMAGETOOL="$TOOLS_DIR/appimagetool-x86_64.AppImage"

if [[ ! -f "$LINUXDEPLOY" ]]; then
    echo "Downloading linuxdeploy..."
    curl -fsSL -o "$LINUXDEPLOY" \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x "$LINUXDEPLOY"
fi

if [[ ! -f "$LINUXDEPLOY_GTK" ]]; then
    echo "Downloading linuxdeploy-plugin-gtk..."
    curl -fsSL -o "$LINUXDEPLOY_GTK" \
        "https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh"
    chmod +x "$LINUXDEPLOY_GTK"
fi

if [[ ! -f "$APPIMAGETOOL" ]]; then
    echo "Downloading appimagetool..."
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

# Assemble AppDir skeleton
echo "Assembling AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp "$BINARY" "$APPDIR/usr/bin/nora"
chmod +x "$APPDIR/usr/bin/nora"

# Run linuxdeploy with GTK plugin
# DEPLOY_GTK_VERSION=3: force GTK3 (avoids GTK4 on newer systems)
# NO_STRIP=1: preserve GObject introspection metadata embedded in .so files
# APPIMAGE_EXTRACT_AND_RUN=1: allows linuxdeploy (itself an AppImage) to run without FUSE
export PATH="$TOOLS_DIR:$PATH"
export DEPLOY_GTK_VERSION=3
export NO_STRIP=1
export ARCH="$ARCH"
export OUTPUT="$OUTPUT_PATH"
export APPIMAGE_EXTRACT_AND_RUN=1

# Resolve libraries that linuxdeploy's dependency walker misses.
# - libgirepository: loaded at runtime by PyInstaller's bundled _gi.so to
#   resolve .typelib files; without it, gi.require_version('Gtk', '3.0')
#   fails with "Namespace Gtk not available" on systems that don't have
#   libgirepository installed (e.g. minimal Docker containers).
# - libwebkit2gtk + libjavascriptcoregtk: pywebview's renderer; only pulled
#   in via gi at runtime, so linuxdeploy doesn't see them from the binary.
resolve_lib() {
    local soname="$1"
    local path
    path="$(ldconfig -p 2>/dev/null | awk -v s="$soname" '$1 == s { print $NF; exit }')"
    if [[ -z "$path" || ! -f "$path" ]]; then
        echo "ERROR: required library '$soname' not found on build host." >&2
        echo "Install it via the distro package manager before running this script." >&2
        exit 1
    fi
    printf '%s' "$path"
}

LIB_GIREPOSITORY="$(resolve_lib libgirepository-1.0.so.1)"
LIB_WEBKIT2GTK="$(resolve_lib libwebkit2gtk-4.0.so.37)"
LIB_JSCOREGTK="$(resolve_lib libjavascriptcoregtk-4.0.so.18)"
LIB_SOUP="$(resolve_lib libsoup-2.4.so.1)"

echo "Running linuxdeploy (collecting GTK/WebKit2 libs)..."
"$LINUXDEPLOY" \
    --appdir "$APPDIR" \
    --executable "$APPDIR/usr/bin/nora" \
    --library "$LIB_GIREPOSITORY" \
    --library "$LIB_WEBKIT2GTK" \
    --library "$LIB_JSCOREGTK" \
    --library "$LIB_SOUP" \
    --desktop-file "$DESKTOP_FILE" \
    --icon-file "$ICON" \
    --plugin gtk

# Strip harmful GTK env overrides from the generated apprun-hook.
# The PyInstaller binary already bundles all required GTK/WebKit2 libs.
# These overrides redirect GTK to AppDir paths (themes, pixbuf loaders, input
# modules) that don't match the bundled libs and prevent the window from opening.
# We keep only GI_TYPELIB_PATH so gi can find the WebKit2 typelibs in the AppDir.
HOOK="$APPDIR/apprun-hooks/linuxdeploy-plugin-gtk.sh"
echo "Patching apprun-hook: removing conflicting GTK env overrides..."
sed -i \
    -e '/^export GTK_DATA_PREFIX/d' \
    -e '/^export GTK_THEME/d' \
    -e '/^export GDK_BACKEND/d' \
    -e '/^export GSETTINGS_SCHEMA_DIR/d' \
    -e '/^export GTK_EXE_PREFIX/d' \
    -e '/^export GTK_PATH/d' \
    -e '/^export GTK_IM_MODULE_FILE/d' \
    -e '/^export GDK_PIXBUF_MODULE_FILE/d' \
    "$HOOK"

# Bundle WebKit2GTK's helper executables. WebKit hardcodes the libexec path
# (WebKitNetworkProcess, WebKitWebProcess, injected-bundle/) at compile time —
# on Ubuntu 22.04 that's /usr/lib/x86_64-linux-gnu/webkit2gtk-4.0. Distros
# that don't ship webkit2gtk-4.0 at that path (Fedora 40+, RHEL 10+, etc.)
# crash at window creation with "Failed to spawn child process".
#
# The Ubuntu 22.04 libwebkit2gtk-4.0.so.37 does NOT honor WEBKIT_EXEC_PATH or
# any other helper-path env var (verified by strings(1) — no such symbols).
# So the library must be binary-patched at its source path BEFORE PyInstaller
# embeds it (see scripts/patch-libwebkit.py, invoked by CI prior to
# `npm run build:linux`). The patched string is a fixed /tmp path that the
# AppRun hook below symlinks to these bundled helpers at startup.
echo "Bundling WebKit2 helper executables..."
WEBKIT_LIBEXEC_SRC=""
for dir in \
    /usr/lib/x86_64-linux-gnu/webkit2gtk-4.0 \
    /usr/libexec/webkit2gtk-4.0 \
    /usr/lib64/webkit2gtk-4.0; do
    if [[ -x "$dir/WebKitNetworkProcess" && -x "$dir/WebKitWebProcess" ]]; then
        WEBKIT_LIBEXEC_SRC="$dir"
        break
    fi
done
if [[ -z "$WEBKIT_LIBEXEC_SRC" ]]; then
    echo "ERROR: WebKit2 helper binaries (WebKitNetworkProcess/WebKitWebProcess) not found on build host." >&2
    echo "Install libwebkit2gtk-4.0-37 (or equivalent) before running this script." >&2
    exit 1
fi
WEBKIT_LIBEXEC_DST="$APPDIR/usr/lib/x86_64-linux-gnu/webkit2gtk-4.0"
mkdir -p "$WEBKIT_LIBEXEC_DST"
cp -a "$WEBKIT_LIBEXEC_SRC/." "$WEBKIT_LIBEXEC_DST/"
echo "  bundled WebKit helpers from: $WEBKIT_LIBEXEC_SRC"

# Verify the source lib was patched (must happen before PyInstaller step).
# The patched path must match scripts/patch-libwebkit.py's NEW constant.
WEBKIT_PATCHED_PATH="/tmp/.nora-webkit2gtk-4.0-helpers-AAAAAA"
if ! strings -a "$APPDIR/usr/lib/libwebkit2gtk-4.0.so.37" | grep -qF "$WEBKIT_PATCHED_PATH"; then
    echo "ERROR: bundled libwebkit2gtk-4.0.so.37 is not patched." >&2
    echo "Run scripts/patch-libwebkit.py (with sudo) against the build host's" >&2
    echo "/usr/lib/x86_64-linux-gnu/libwebkit2gtk-4.0.so.37 BEFORE npm run build:linux." >&2
    exit 1
fi
echo "  verified bundled libwebkit is patched (helpers path: $WEBKIT_PATCHED_PATH)"

echo "Appending helpers symlink setup to apprun-hook..."
cat >> "$HOOK" <<EOF
ln -sfn "\$APPDIR/usr/lib/x86_64-linux-gnu/webkit2gtk-4.0" "$WEBKIT_PATCHED_PATH"
EOF

# Ensure WebKit2 + Soup typelibs are in the AppDir. linuxdeploy-plugin-gtk's
# wholesale copy of the system typelib dir sometimes misses WebKit2 (host
# path / pkg-config quirks), and pywebview's gtk backend requires either
# WebKit2-4.1 + Soup-3.0 or WebKit2-4.0 + Soup-2.4 to import successfully.
# Copy whatever is installed on the build host; fail loud if none is present.
TYPELIB_DST="$APPDIR/usr/lib/girepository-1.0"
mkdir -p "$TYPELIB_DST"

copy_typelib_if_present() {
    local name="$1"
    local src
    for src in \
        "/usr/lib/x86_64-linux-gnu/girepository-1.0/$name" \
        "/usr/lib/girepository-1.0/$name" \
        "/usr/lib64/girepository-1.0/$name"; do
        if [[ -f "$src" ]]; then
            cp -f "$src" "$TYPELIB_DST/"
            echo "  bundled typelib: $name"
            return 0
        fi
    done
    return 1
}

echo "Bundling WebKit2 + Soup typelibs..."
webkit_ok=0
if copy_typelib_if_present "WebKit2-4.1.typelib" && copy_typelib_if_present "Soup-3.0.typelib"; then
    copy_typelib_if_present "WebKit2WebExtension-4.1.typelib" || true
    webkit_ok=1
fi
if copy_typelib_if_present "WebKit2-4.0.typelib" && copy_typelib_if_present "Soup-2.4.typelib"; then
    copy_typelib_if_present "WebKit2WebExtension-4.0.typelib" || true
    webkit_ok=1
fi
if [[ "$webkit_ok" -eq 0 ]]; then
    echo "ERROR: no WebKit2 typelib pair found on build host." >&2
    echo "Install gir1.2-webkit2-4.0 (and libsoup2.4-1) or gir1.2-webkit2-4.1." >&2
    exit 1
fi

echo "Running appimagetool..."
"$APPIMAGETOOL" "$APPDIR" "$OUTPUT_PATH"

echo ""
echo "AppImage created: $OUTPUT_PATH"
echo "Size: $(du -sh "$OUTPUT_PATH" | cut -f1)"
