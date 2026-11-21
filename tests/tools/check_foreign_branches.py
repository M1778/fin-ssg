#!/usr/bin/env python3
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

"""Type-check a platform branch that no lane on this host can compile.

WHY THIS EXISTS
---------------
Fin's preprocessor keeps only the branch for the host being compiled. A syntax error in the
Windows branch of `platform.fin` is therefore invisible on Linux and macOS -- and two such
errors shipped this month:

    @define platform_rename(from: string, ...)   # `from` is a hard keyword
    if ((attributes & 0x10) != ...)              # Fin has no hex literals

Both were found only when a Windows CI lane finally parsed the file. A round trip through CI
costs ten minutes and tells you one error at a time.

This flips the guards so the *other* platform's branch becomes the live one, runs the front
end on this host, and restores the file. The `@define`d C functions never link here and do
not need to: the errors this catches are lexical, syntactic and type-shaped, all of which are
found before code generation.

    python3 tests/tools/check_foreign_branches.py --finc build/finc \
        --file src/vendor/platform.fin --needle FIN_TARGET_WINDOWS

Exit 0 when the branch type-checks, 1 when it does not, and it always restores the file --
including on failure -- because leaving a tree with flipped guards is worse than the bug it
was checking for.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--finc", required=True)
    ap.add_argument("--file", required=True, help="the source holding the guarded branch")
    ap.add_argument("--needle", required=True, help="the macro whose branch to make live")
    ap.add_argument("--entry", required=True, help="the program to type-check")
    ap.add_argument("--include", action="append", default=[], help="an -I directory")
    ap.add_argument("--keep", action="store_true", help="leave the flipped copy beside the file")
    args = ap.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 1

    original = target.read_text(encoding="utf-8")
    if f"#c_ifdef {args.needle}" not in original:
        print(
            f"error: {target} has no `#c_ifdef {args.needle}`, so there is no branch to flip",
            file=sys.stderr,
        )
        return 1

    # The host's own macro is the one to invert: on Linux the Windows branch is dead, and on
    # Windows the Linux branch is. Derived rather than passed, so this cannot be pointed at
    # the branch that is already live.
    host = {
        "linux": "FIN_TARGET_LINUX",
        "darwin": "FIN_TARGET_DARWIN",
        "win32": "FIN_TARGET_WINDOWS",
    }.get(sys.platform.split("-")[0] if sys.platform.startswith("linux") else sys.platform)
    if host is None:
        print(f"error: no host macro known for {sys.platform}", file=sys.stderr)
        return 1
    if host == args.needle:
        print(
            f"error: --needle {args.needle} is the host's own branch; it is already compiled "
            f"by every build here, so flipping it tests nothing",
            file=sys.stderr,
        )
        return 1
    # A file need not name its own platform: platform.fin guards `FIN_TARGET_WINDOWS` and
    # lets `#c_else` be "everything else". In that shape the host's macro does not appear, and
    # the rewrite still works -- renaming the wanted guard to the host macro makes it live and
    # leaves the `#c_else` branches dead, which is the opposite of what the host normally
    # compiles and therefore the thing worth checking.
    has_host_guard = f"#c_ifdef {host}" in original

    # Two shapes occur. A file may guard both branches explicitly (`#c_ifdef X` / `#c_ifdef
    # Y`), or guard one and let `#c_else` be the other -- which is what platform.fin does, so
    # the POSIX branch has no macro of its own to name. The rewrite below covers both: rename
    # the wanted guard to the host's, and disable the host's own so the two do not collide.
    flipped = original
    if has_host_guard:
        flipped = flipped.replace(f"#c_ifdef {host}", f"#c_ifdef {host}_DISABLED_FOR_CHECK")
    flipped = flipped.replace(f"#c_ifdef {args.needle}", f"#c_ifdef {host}")
    if flipped == original:
        print("error: the flip changed nothing; the guard spelling is not what this expects",
              file=sys.stderr)
        return 1

    backup = None
    try:
        # A copy rather than an edit in place: the entry file imports by name, so the module
        # tree has to stay where it is and only this one file may differ.
        backup = target.with_suffix(target.suffix + ".branchcheck-backup")
        shutil.copy2(target, backup)
        target.write_text(flipped, encoding="utf-8")

        argv = [args.finc, args.entry]
        for inc in args.include:
            argv.extend(["-I", inc])
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode == 0:
            print(f"ok: the {args.needle} branch of {target} type-checks")
            return 0
        print(
            f"\nerror: the {args.needle} branch of {target} does not type-check.\n"
            "This is the check a Windows or macOS CI lane would make, done on this host.",
            file=sys.stderr,
        )
        return 1
    finally:
        if backup is not None:
            shutil.move(str(backup), str(target))
        elif target.read_text(encoding="utf-8") != original:
            target.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
