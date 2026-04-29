#!/usr/bin/env python3
"""
Binary-patch libwebkit2gtk-4.0.so.37's hardcoded helper-directory path.

WebKitGTK 4.0 (Ubuntu 22.04 build host) compiles the path
/usr/lib/x86_64-linux-gnu/webkit2gtk-4.0 into the shared library as the
location of WebKitNetworkProcess/WebKitWebProcess/injected-bundle/. There
is no environment variable to override this (WEBKIT_EXEC_PATH does not
exist in this version — verified via strings(1)). Distros that don't
ship webkit2gtk-4.0 at that exact path (Fedora 40+, RHEL 10+) therefore
can't run AppImages built on Ubuntu.

Fix: replace the 40-character hardcoded string with a same-length fixed
/tmp path. The AppRun hook later symlinks that /tmp path to the bundled
helpers dir, so WebKit's hardcoded execve()/dlopen() calls resolve
correctly on any distro.

Must run BEFORE PyInstaller embeds libwebkit into the bundle.
"""
import sys
from pathlib import Path

OLD = b"/usr/lib/x86_64-linux-gnu/webkit2gtk-4.0"
NEW = b"/tmp/.nora-webkit2gtk-4.0-helpers-AAAAAA"
assert len(OLD) == len(NEW) == 40

DEFAULT_LIB = "/usr/lib/x86_64-linux-gnu/libwebkit2gtk-4.0.so.37"


def patch(lib_path: Path) -> int:
    data = lib_path.read_bytes()
    count = data.count(OLD)
    if count == 0:
        if data.count(NEW) > 0:
            print(f"{lib_path}: already patched ({data.count(NEW)} occurrences of {NEW.decode()})")
            return 0
        print(f"ERROR: {OLD.decode()!r} not found in {lib_path}", file=sys.stderr)
        sys.exit(1)
    lib_path.write_bytes(data.replace(OLD, NEW))
    print(f"{lib_path}: patched {count} occurrence(s) -> {NEW.decode()}")
    return count


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LIB)
    if not target.exists():
        print(f"ERROR: {target} does not exist", file=sys.stderr)
        sys.exit(1)
    patch(target)
