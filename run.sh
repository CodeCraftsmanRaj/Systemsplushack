#!/usr/bin/env bash
# =============================================================================
# run.sh — Launch the Systemss Plus app with XCB crash prevention.
#
# WHY THIS EXISTS:
#   On Arch-based systems (EndeavourOS, Manjaro, etc.) the system `tk` package
#   is compiled with XCB threading support.  When Tk calls XInitThreads()
#   internally it races with XCB's sequence counter and aborts:
#       [xcb] Unknown sequence number while appending request
#       [xcb] You called XInitThreads, this is not your fault
#       [xcb] Aborting, sorry about that.
#
#   os.environ inside Python is TOO LATE — libxcb.so is already mapped into
#   memory by the dynamic linker before Python's main() runs.  The vars must
#   exist in the SHELL ENVIRONMENT that spawns Python.  This script does that.
#
# USAGE (from project root):
#   chmod +x run.sh
#   ./run.sh
# =============================================================================

# --- 1. Force pure-Xlib backend, bypassing the buggy XCB layer in Tk --------
export GDK_BACKEND=x11
export DISPLAY="${DISPLAY:-:0}"
export TK_SILENCE_DEPRECATION=1

# --- 2. Single-thread ALL numeric / parallel libraries ----------------------
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export LOKY_MAX_CPU_COUNT=1
export VECLIB_MAXIMUM_THREADS=1

# --- 3. Qt shims (harmless if Qt is not present) ----------------------------
export QT_QPA_PLATFORM=xcb
export QT_XCB_NO_MITSHM=1

# --- 4. Locate client_app/main.py reliably ----------------------------------
# Works whether you run this script from the project root OR from inside
# client_app/ — it always resolves relative to the script's own location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/client_app/main.py" ]; then
    # Script lives in project root (the normal case)
    APP_DIR="$SCRIPT_DIR/client_app"
elif [ -f "$SCRIPT_DIR/main.py" ]; then
    # Script was placed inside client_app/
    APP_DIR="$SCRIPT_DIR"
else
    echo "ERROR: Could not find client_app/main.py" >&2
    echo "       Expected it at: $SCRIPT_DIR/client_app/main.py" >&2
    exit 1
fi

echo "Launching from: $APP_DIR"
cd "$APP_DIR"
exec uv run main.py "$@"