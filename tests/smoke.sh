#!/bin/sh
# Native Fin frontend/codegen + existing smoke checks + regression suite.
#
# A thin wrapper: tests/smoke.py does the work, because a shell script is not
# something Windows has. The compiler and the library come from FINC and
# FIN_LIBS, and the optimization level from OPT.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 -I "$ROOT/tests/smoke.py" --finc "${FINC:-finc}" \
    --fin-libs "${FIN_LIBS:-}" --opt="${OPT:--O0}"
