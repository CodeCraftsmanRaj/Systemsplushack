#!/usr/bin/env bash
# Run this on your Arch system and paste the output back
echo "=== TK / TCL VERSION ==="
python3 -c "import tkinter; print('tk:', tkinter.TkVersion, '| tcl:', tkinter.TclVersion)" 2>&1

echo ""
echo "=== WHICH PYTHON ==="
which python3
python3 --version

echo ""
echo "=== TK PACKAGE ==="
pacman -Q tk 2>/dev/null || echo "tk not found via pacman"

echo ""
echo "=== LIBXCB LINKED INTO LIBTK ==="
ldd $(python3 -c "import _tkinter; print(_tkinter.__file__)") 2>/dev/null | grep -E "xcb|X11|tk|tcl"

echo ""
echo "=== LIBTK FILE ==="
python3 -c "import _tkinter; print(_tkinter.__file__)"

echo ""
echo "=== XCB THREAD INIT IN LIBTK ==="
# Check if libtk itself calls XInitThreads
TKFILE=$(python3 -c "import _tkinter; print(_tkinter.__file__)" 2>/dev/null)
nm -D "$TKFILE" 2>/dev/null | grep -i "XInitThreads" || \
  objdump -T "$TKFILE" 2>/dev/null | grep -i "XInitThreads" || \
  echo "Could not inspect symbols"

echo ""
echo "=== CUSTOMTKINTER VERSION ==="
python3 -c "import customtkinter; print(customtkinter.__version__)" 2>&1

echo ""
echo "=== UV PYTHON ==="
uv run python3 -c "import sys,tkinter; print('python:', sys.version); print('tk:', tkinter.TkVersion)" 2>&1