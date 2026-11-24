#!/usr/bin/env bash
# usage: scripts/sand3d-env.sh [--make]
# Prints the path of a Python that imports sand3d, or nothing (exit 1) when there is none.
# --make: when none is found, make one beside you (./.venv, Python 3.13) and print it.
#   PY=$(scripts/sand3d-env.sh) && "$PY" build.py
# sand3d needs Python 3.13 (Blender 5.2 as the bpy module) or 3.11 (Blender 4.5): pip has no bpy for 3.12 or 3.14.
set -uo pipefail
here=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
make=0
[ "${1:-}" = "--make" ] && make=1
found=""
for py in "${SAND3D_PYTHON:-}" "$PWD/.venv/bin/python" "$here/../../../.venv/bin/python" \
          "$HOME/GitHub/sand3d/.venv/bin/python" python3.13 python3.11 python; do
  [ -n "$py" ] || continue
  command -v "$py" >/dev/null 2>&1 || continue
  if "$py" -I -c "import sand3d" >/dev/null 2>&1; then
    found=$py
    break
  fi
done
if [ -z "$found" ] && [ "$make" = 1 ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv -p 3.13 .venv && uv pip install -p .venv sand3d
  else
    python3.13 -m venv .venv && .venv/bin/python -m pip install sand3d
  fi
  [ -x .venv/bin/python ] && found=$PWD/.venv/bin/python
fi
[ -n "$found" ] || { echo "no Python here imports sand3d; run with --make to create ./.venv" >&2; exit 1; }
echo "$found"
