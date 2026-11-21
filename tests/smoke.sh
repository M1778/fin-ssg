#!/bin/sh
# =============================================================================
# Fin Programming Language
#
# Made with ❤️ for someone special.
#
# This project is genuinely built on love and dedication, a way to express your love can be done through Fin.
# Fin is a semi-object-orientated programming language that specialized in control, giving so much control to the user while asking for the bare minimum.
# Fin is the name of the Angel from BlackNightmare-Stories not yet published.
# “Love is the reason this project exists”
# -----------------------------------------------------------------------------
# Author: M1778
# Repository: https://github.com/M1778/fin-ssg
# Profile: https://github.com/M1778M/
# -----------------------------------------------------------------------------
# Copyright (C) 2027 M1778
#
# This file is part of fin-ssg, a project for the Fin Programming Language.
#
# Licensed under the MIT License. See LICENSE in the repository root.
#
# SPDX-License-Identifier: MIT
# =============================================================================

# Native Fin frontend/codegen + existing smoke checks + regression suite.
#
# A thin wrapper: tests/smoke.py does the work, because a shell script is not
# something Windows has. The compiler and the library come from FINC and
# FIN_LIBS, and the optimization level from OPT.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 -I "$ROOT/tests/smoke.py" --finc "${FINC:-finc}" \
    --fin-libs "${FIN_LIBS:-}" --opt="${OPT:--O0}"
