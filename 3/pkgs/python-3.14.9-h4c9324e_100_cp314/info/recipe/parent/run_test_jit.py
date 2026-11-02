import os
import sys

if os.getenv("PYTHON_JIT") is None:
    print("WARNING: PYTHON_JIT unset", file=sys.stderr)

# Strictly, sys._jit was added in 3.14
if (sys.version_info[0] == 3 and sys.version_info[1] >= 14) or sys.version_info[0] > 3:
    if sys._jit.is_available():
        if sys._jit.is_enabled():
            print("JIT available and enabled")
            sys.exit(0)
        else:
            print("JIT available but not enabled", file=sys.stderr)
    else:
        print("JIT not available", file=sys.stderr)
else:
    print(f"WARNING: cannot validate JIT using Python {sys.version}", file=sys.stderr)
    print(f"WARNING: validate using Python >= 3.14", file=sys.stderr)

sys.exit(1)
