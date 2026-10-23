#!/usr/bin/env python3
"""Build and exercise the static site generator.

The portable entry point: it runs the same checks as tests/smoke.sh on
every platform, because a shell script is not one of them.

Usage:
    python3 -I tests/smoke.py [--finc PATH] [--fin-libs PATH] [--opt O0|O2]
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def run(command, cwd=None, env=None, check=True):
    result = subprocess.run([str(part) for part in command], cwd=cwd, env=env,
                            text=True, capture_output=True, timeout=300)
    if check and result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(str(p) for p in command)}\n"
                         f"{result.stdout}\n{result.stderr}")
    return result


def expect(condition, label):
    if not condition:
        raise SystemExit(f"failed: {label}")


def build(compiler, stdlib, source, output, extra=()):
    # The vendored modules are found through the include path, the way the
    # generator itself finds them.
    # NOTE: --fin-libs must be omitted entirely when empty. finc treats an
    # explicitly passed empty --fin-libs as "search ONLY this path", which
    # drops the built-in stdlib and fails with "module not found: argparse /
    # fs / strings" (this broke CI's smoke step even though the plain
    # `finc -I src/vendor src/main.fin -o fin-ssg` build step passed).
    command = [compiler, source, "-I", ROOT / "src" / "vendor"]
    if stdlib:
        command += ["--fin-libs", stdlib]
    command += ["-o", output]
    run([*command, *extra], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finc", default=os.environ.get("FINC", "finc"))
    parser.add_argument("--fin-libs", default=os.environ.get("FIN_LIBS", ""))
    parser.add_argument("--opt", default=os.environ.get("OPT", "-O0"))
    options = parser.parse_args()

    compiler = shutil.which(options.finc) or options.finc
    stdlib = options.fin_libs
    vendor = ROOT / "src" / "vendor"

    with tempfile.TemporaryDirectory(prefix="fin-ssg-") as directory:
        work = Path(directory)
        binary = work / ("fin-ssg.exe" if os.name == "nt" else "fin-ssg")

        print("== frontend check ==", flush=True)
        run([compiler, "-I", vendor, ROOT / "src" / "main.fin"], cwd=ROOT)

        print(f"== codegen + link {options.opt} ==", flush=True)
        build(compiler, stdlib, ROOT / "src" / "main.fin", binary, [options.opt])

        print("== open-flag mapping ==", flush=True)
        mapping = work / ("platform-test.exe" if os.name == "nt" else "platform-test")
        build(compiler, stdlib, ROOT / "tests" / "platform.fin", mapping, [options.opt])
        run([mapping], cwd=ROOT)

        print("== build the example site ==", flush=True)
        site = work / "site"
        run([binary, "--content", ROOT / "example" / "content",
             "--layout", ROOT / "example" / "layout",
             "--out", site, "--title", "Smoke Site"], cwd=ROOT)
        for name in ("index.html", "hello.html", "second.html"):
            expect((site / name).is_file(), f"{name} was written")
        hello = (site / "hello.html").read_text(encoding="utf-8")
        for fragment in ("<h1>Hello, Fin</h1>", "2026-10-20", "<strong>generated</strong>",
                         "<em>fin-ssg</em>", "<code>inline code</code>",
                         '<a href="https://github.com/M1778/Fin">links</a>',
                         "<li>unordered item one</li>", "<li>first ordered item</li>",
                         "<blockquote>",
                         # fin-markdown emits the fence info string as a
                         # language class (adopted 2026-10-23); the old
                         # vendored renderer dropped it and always emitted
                         # bare <pre><code>. The example fence is ```fin.
                         '<pre><code class="language-fin">', "<hr>"):
            expect(fragment in hello, f"hello.html carries {fragment!r}")
        expect("second" in (site / "second.html").read_text(encoding="utf-8"),
               "second.html carries its title")
        index = (site / "index.html").read_text(encoding="utf-8")
        expect("Smoke Site" in index, "index.html carries the site title")
        expect('href="hello.html"' in index, "index.html links hello.html")
        expect('href="second.html"' in index, "index.html links second.html")

        print("== default layout ==", flush=True)
        default = work / "default"
        run([binary, "--content", ROOT / "example" / "content",
             "--layout", work / "missing", "--out", default, "--title", "Bare"], cwd=ROOT)
        expect((default / "index.html").is_file(), "the default layout was used")
        expect("{{content}}" not in (default / "index.html").read_text(encoding="utf-8"),
               "no unrendered placeholder is left in the output")

        print("== security, CLI, filesystem and limits regressions ==", flush=True)
        run([sys.executable, "-I", ROOT / "tests" / "security.py", binary, work], cwd=ROOT)

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
