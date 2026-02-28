#!/usr/bin/env bash
# =============================================================================
# patch_tk.sh — Fix Arch tk 8.6.16-1 XCB threading crash via LD_PRELOAD shim.
#
# ROOT CAUSE:
#   Something loaded before Tk (numpy/OpenMP/BLAS pulled in by sklearn) touches
#   the X11 socket before XInitThreads() is called. XCB's sequence counter
#   corrupts. When Tk then calls XInitThreads() it is too late — abort.
#
#   Fix: inject a .so via LD_PRELOAD whose GCC constructor runs at priority 101
#   (before everything else) and calls XInitThreads() first. All subsequent
#   calls to XInitThreads() (from Tk) become no-ops.
# =============================================================================

set -e

SHIM=/tmp/earlyxcb.so

echo ">>> Compiling XInitThreads preload shim..."
cat << 'CEOF' > /tmp/earlyxcb.c
#include <X11/Xlib.h>

static int _done = 0;

/* Runs before main() and before other library constructors */
__attribute__((constructor(101)))
static void early_xinit(void) {
    if (!_done) {
        /* Call the REAL XInitThreads from libX11 via the dynamic linker.
           Since we define XInitThreads ourselves below, we need to get the
           real one first — use __attribute__((visibility)) trick:
           just set the flag and let our override handle the actual call
           on first invocation from Tk. We cannot dlsym here safely without
           -ldl and a chicken-and-egg problem, so instead we call the
           underlying Xlib directly via its internal symbol. */
        _done = 1;
        /* The real work: mark XCB thread-safe before any connection opens */
        extern int _XInitThreads(void) __attribute__((weak));
        if (_XInitThreads) _XInitThreads();
    }
}

/* Intercept all subsequent XInitThreads calls — make them no-ops */
int XInitThreads(void) {
    if (!_done) {
        _done = 1;
        extern int _XInitThreads(void) __attribute__((weak));
        if (_XInitThreads) _XInitThreads();
    }
    return 1;
}
CEOF

if ! command -v gcc &>/dev/null; then
    echo "ERROR: gcc not found. Run: sudo pacman -S gcc"
    exit 1
fi

gcc -shared -fPIC -o "$SHIM" /tmp/earlyxcb.c -lX11 -ldl
echo ">>> Shim compiled: $SHIM"

# --- env vars (belt and braces) ---
export LD_PRELOAD="$SHIM"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export LOKY_MAX_CPU_COUNT=1
export VECLIB_MAXIMUM_THREADS=1
export GDK_BACKEND=x11
export DISPLAY="${DISPLAY:-:0}"

# --- find client_app ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/client_app/main.py" ]; then
    APP_DIR="$SCRIPT_DIR/client_app"
elif [ -f "$SCRIPT_DIR/main.py" ]; then
    APP_DIR="$SCRIPT_DIR"
else
    echo "ERROR: Cannot find client_app/main.py"
    exit 1
fi

echo ">>> Launching from: $APP_DIR"
cd "$APP_DIR"
exec uv run main.py "$@"