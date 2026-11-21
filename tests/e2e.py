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

"""End-to-end tests for fin-ssg: build sites and assert on the emitted files.

The site is the product, so "the process exited 0" proves nothing here. Every
check reads a published file, parses it, and asserts on what a browser would
see. A separate CLI section covers the diagnostics, and that is the only place
an exit code is the assertion.

Portable by construction: no shell, no POSIX-only call, no fixed path. Windows
runs the same file.

Usage:
    python3 -I tests/e2e.py --finc PATH [--opt=-O0]
"""
import argparse
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
BINARY_NAME = "fin-ssg.exe" if os.name == "nt" else "fin-ssg"


def run(command, cwd=None, timeout=300):
    result = subprocess.run([str(part) for part in command], cwd=cwd,
                            text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(str(p) for p in command)}\n"
                         f"{result.stdout}\n{result.stderr}")
    return result


def finish(label):
    """A checker that names the group and the ordinal of the failing check.

    The ordinal is what makes a failure in CI diagnosable without a debugger:
    "CLI contract #7" is a line you can count, "CLI contract" is not.
    """
    state = {"n": 0}

    def check(condition, detail=""):
        state["n"] += 1
        if not condition:
            where = f" [{detail}]" if detail else ""
            raise SystemExit(f"failed: {label} #{state['n']}{where}")
    return check


class Document(HTMLParser):
    """Collects tags, attributes and visible text from a published page."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def body_text(self):
        return "".join(self.text)

    def attr(self, tag, name):
        for found, attrs in self.tags:
            if found == tag and name in attrs:
                return attrs[name]
        return None


def build_static(compiler, work):
    """Compile the generator once; the tests exercise it as a black box."""
    binary = work / BINARY_NAME
    run([compiler, "-I", ROOT / "src", ROOT / "src" / "main.fin", "-o", binary], cwd=ROOT)
    return binary


def site(binary, content, out, title="Test Site", layout=None, cwd=None):
    if layout is None:
        layout = (Path(out).parent / "no-layout") if cwd is None else "no-layout"
    command = [binary, "--content", content, "--layout", layout,
               "--out", out, "--title", title]
    return subprocess.run([str(part) for part in command], cwd=cwd,
                          text=True, capture_output=True, timeout=300)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_example_site(binary, work):
    """The shipped example builds into a site a reader can actually use."""
    check = finish("example site")
    out = work / "example-out"
    run([binary, "--content", ROOT / "example" / "content",
         "--layout", ROOT / "example" / "layout", "--out", out,
         "--title", "Example Blog"], cwd=ROOT)
    for name in ("index.html", "hello.html", "second.html"):
        check((out / name).is_file())

    hello = Document((out / "hello.html").read_text(encoding="utf-8"))
    text = hello.body_text()
    # The Markdown subset renders, not just the wrapper.
    check("<h1>Hello, Fin</h1>" in (out / "hello.html").read_text(encoding="utf-8"))
    for expected in ("Hello, Fin", "generated", "fin-ssg", "inline code",
                     "unordered item one", "first ordered item",
                     "A blockquote renders", "Happy generating"):
        check(expected in text)
    hrefs = [attrs["href"] for tag, attrs in hello.tags if tag == "a" and "href" in attrs]
    check("https://github.com/M1778/Fin" in hrefs)
    check(hello.attr("img", "src") == "fin-logo.png")
    check(any(tag == "pre" for tag, _ in hello.tags))
    check("<title>Hello, Fin &mdash; Example Blog</title>" in (out / "hello.html").read_text(encoding="utf-8"))

    index = Document((out / "index.html").read_text(encoding="utf-8"))
    hrefs = [attrs["href"] for tag, attrs in index.tags if tag == "a" and "href" in attrs]
    check("hello.html" in hrefs and "second.html" in hrefs)
    check("Example Blog" in index.body_text())
    check("2026-10-20" in index.body_text())      # front-matter date reaches the index
    check("second" in index.body_text())          # missing title falls back to the slug
    # Every page in the index exists on disk.
    for href in hrefs:
        check((out / href).is_file())


def test_markdown_to_html(binary, work):
    """Each advertised Markdown construct renders as the documented HTML."""
    check = finish("markdown subset")
    content = work / "md-content"
    content.mkdir()
    write(content / "all.md", "\n".join([
        "# Heading one",
        "",
        "## Heading two",
        "",
        "Setext one",
        "==========",
        "",
        "A paragraph with **bold**, *italic*, `code`, ~~struck~~ and a [link](https://example.com/x).",
        "",
        "- item a",
        "- item b",
        "",
        "1. first",
        "2. second",
        "",
        "> quoted",
        "",
        "```fin",
        "fun main() <noret> { }",
        "```",
        "",
        "---",
        "",
        "![alt text](pic.png)",
        "",
    ]))
    out = work / "md-out"
    result = site(binary, content, out)
    check(result.returncode == 0)
    html = (out / "all.html").read_text(encoding="utf-8")
    for fragment in ("<h1>Heading one</h1>", "<h2>Heading two</h2>", "<h1>Setext one</h1>",
                     "<strong>bold</strong>", "<em>italic</em>", "<code>code</code>",
                     "<del>struck</del>", '<a href="https://example.com/x">link</a>',
                     "<li>item a</li>", "<li>first</li>", "<blockquote>", "<hr>",
                     '<pre><code class="language-fin">', '<img src="pic.png" alt="alt text">'):
        check(fragment in html)
    parsed = Document(html)
    check(any(tag == "blockquote" for tag, _ in parsed.tags))
    # Parsing must not have to repair anything: every tag closes.
    parsed.close()


def test_front_matter(binary, work):
    """Front matter sets the title and date; a file without it uses its slug."""
    check = finish("front matter")
    content = work / "fm-content"
    content.mkdir()
    write(content / "titled.md", "---\ntitle: From Matter\ndate: 2026-01-02\n---\n\nBody\n")
    write(content / "plain.md", "# Plain body\n")
    write(content / "crlf.md", "---\r\ntitle: CRLF Title\r\ndate: 2026-03-04\r\n---\r\n\r\nBody\r\n")
    write(content / "unterminated.md", "---\ntitle: Nope\n\nNo closing fence\n")
    write(content / "colon.md", "---\ntitle: A: B\n---\n\nx\n")
    out = work / "fm-out"
    result = site(binary, content, out)
    check(result.returncode == 0)
    check("<title>From Matter &mdash; Test Site</title>" in (out / "titled.html").read_text(encoding="utf-8"))
    check("<title>plain &mdash; Test Site</title>" in (out / "plain.html").read_text(encoding="utf-8"))
    check("<title>CRLF Title &mdash;" in (out / "crlf.html").read_text(encoding="utf-8"))
    # No closing fence means no front matter; the whole file is the body.
    unterminated = (out / "unterminated.html").read_text(encoding="utf-8")
    check("unterminated &mdash;" in unterminated or "<title>unterminated" in unterminated)
    check("Nope" in unterminated)
    check("A: B" in (out / "colon.html").read_text(encoding="utf-8"))


def test_escaping(binary, work):
    """Content and metadata are escaped, never emitted as markup or script."""
    check = finish("escaping")
    content = work / "esc-content"
    content.mkdir()
    attacked = (
        "---\n"
        'title: A & B <C> "D" \'E\'\n'
        'date: <img src=x onerror="window.pwned=1">\n'
        "---\n"
        "\n"
        "Body with <script>window.pwned=1</script> and </script><b>bold?</b>.\n"
        "\n"
        "Ampersand & less < greater > quote \" apostrophe '.\n"
        "\n"
        "[attr](page.html\"onmouseover=\"window.pwned=1)\n"
        "\n"
        "![img](pic.png\"onerror=\"window.pwned=1)\n"
        "\n"
        "`<code>&amp;</code>`\n"
        "\n"
        "```js<tag>\n"
        "x <script>y</script>\n"
        "```\n"
    )
    write(content / "attack.md", attacked)
    layout = work / "esc-layout"
    layout.mkdir()
    write(layout / "page.html",
          '<!DOCTYPE html><html><head><title>{{title}}</title></head>'
          '<body><div data-title="{{title}}" data-date="{{date}}">{{content}}</div></body></html>\n')
    out = work / "esc-out"
    result = site(binary, content, out, title='Site & <Co> "Q"', layout=layout)
    check(result.returncode == 0)
    html = (out / "attack.html").read_text(encoding="utf-8")
    parsed = Document(html)

    # Nothing that arrived as data may become executable markup.
    for tag, attrs in parsed.tags:
        check(tag != "script")
        check(not any(name.startswith("on") for name in attrs))
    # The angle brackets survived as text, not as elements.
    check("<script>" not in html.replace("&lt;script&gt;", ""))
    check("&lt;script&gt;" in html)
    check("<b>bold?</b>" not in html)
    check("&amp;" in html)
    # Attribute values are quoted and escaped.
    title = parsed.attr("title", "x")  # not an attribute; exercises the helper
    check(title is None)
    check('data-title="A &amp; B &lt;C&gt; &quot;D&quot; &#39;E&#39;"' in html)
    check("<title>A &amp; B &lt;C&gt; &quot;D&quot; &#39;E&#39;</title>" in html)
    # A quote inside a URL is escaped in the source, so the browser sees one
    # attribute value and never a second attribute.
    check('href="page.html&quot;onmouseover=&quot;window.pwned=1"' in html)
    check('src="pic.png&quot;onerror=&quot;window.pwned=1"' in html)
    check('data-date="&lt;img src=x onerror=&quot;window.pwned=1&quot;&gt;"' in html)
    # The index repeats the same metadata, so it needs the same treatment.
    index = (out / "index.html").read_text(encoding="utf-8")
    check('href="attack.html"' in index)
    check("<img" not in index or "onerror" not in index)
    check("<script>" not in index)


def test_unsafe_urls(binary, work):
    """A dangerous link target degrades to text rather than becoming an attribute."""
    check = finish("unsafe URLs")
    content = work / "url-content"
    content.mkdir()
    unsafe = [
        "javascript:window.pwned=1", "JaVaScRiPt:window.pwned=1",
        "data:text/html,bad", "vbscript:bad", "javascript&colon;bad",
        "java\tscript:bad", "//example.com/bad", "\\\\example.com",
    ]
    lines = ["# Unsafe link targets", ""]
    for index, url in enumerate(unsafe):
        lines.append(f"[unsafe{index}]({url})")
        lines.append("")
    lines += ["[safe](https://example.com/a?q=1&b=2)", "",
              "[mail](mailto:hello@example.com)", "",
              "[relative](a%20b.html)", ""]
    write(content / "urls.md", "\n".join(lines))
    out = work / "url-out"
    result = site(binary, content, out)
    check(result.returncode == 0)
    parsed = Document((out / "urls.html").read_text(encoding="utf-8"))
    for tag, attrs in parsed.tags:
        for key in ("href", "src"):
            if key in attrs:
                check(not attrs[key].lower().startswith(("javascript:", "data:", "vbscript:")))
    hrefs = [attrs["href"] for tag, attrs in parsed.tags if tag == "a" and "href" in attrs]
    check("https://example.com/a?q=1&b=2" in hrefs)   # the browser sees one &
    check("mailto:hello@example.com" in hrefs)
    check("a%20b.html" in hrefs)
    check(len(hrefs) == 3)


def test_determinism(binary, work):
    """Two builds of one input are byte-identical: no clock, no listing order."""
    check = finish("determinism")
    content = work / "det-content"
    content.mkdir()
    # More than a handful, so a directory-order leak would show.
    for index in range(12):
        write(content / f"page{index:02}.md",
              f"---\ntitle: Page {index}\ndate: 2026-01-{index + 1:02}\n---\n\n# Body {index}\n")
    layout = work / "det-layout"
    layout.mkdir()
    write(layout / "page.html", "<html><body>{{content}}</body></html>\n")

    first = work / "det-first"
    second = work / "det-second"
    check(site(binary, content, first, layout=layout).returncode == 0)
    check(site(binary, content, second, layout=layout).returncode == 0)

    names_a = sorted(p.name for p in first.iterdir())
    names_b = sorted(p.name for p in second.iterdir())
    check(names_a == names_b)
    check(len(names_a) == 13)                          # 12 pages + index
    for name in names_a:
        check((first / name).read_bytes() == (second / name).read_bytes())
    # And the same output again, over an existing published tree.
    check(site(binary, content, first, layout=layout).returncode == 0)
    for name in names_a:
        check((first / name).read_bytes() == (second / name).read_bytes())
    # No temporary file was left behind.
    check(not [p for p in first.iterdir() if p.name.endswith(".tmp")])


def test_nested_and_relative_paths(binary, work):
    """A nested output directory is created; relative paths resolve from cwd."""
    check = finish("nested paths")
    content = work / "path-content"
    content.mkdir()
    write(content / "page.md", "# Nested\n")

    deep = work / "build" / "one" / "two" / "three"
    result = site(binary, "path-content", "build/one/two/three", cwd=work)
    check(result.returncode == 0)
    check((deep / "page.html").is_file())
    check((deep / "index.html").is_file())

    # A path that walks up is refused rather than written outside the tree.
    escape = work / "escaped-out"
    result = site(binary, content, work / ".." / "escaped-out")
    check(result.returncode == 1)
    check(not escape.exists())

    # A name with a separator cannot leave the output directory.
    travelling = work / "travelling-content"
    travelling.mkdir()
    for name in ("sub/name.md", "..\\name.md", ".hidden.md"):
        write(travelling / name, "# x\n")
    out = work / "travelling-out"
    result = site(binary, travelling, out)
    check(result.returncode in (0, 2))
    for published in out.iterdir():
        check(published.parent == out)


def test_default_layout(binary, work):
    """A missing layout falls back to the built-in page, fully substituted."""
    check = finish("default layout")
    content = work / "dl-content"
    content.mkdir()
    write(content / "solo.md", "---\ntitle: Solo\ndate: 2026-05-06\n---\n\n# Solo body\n")
    out = work / "dl-out"
    result = subprocess.run(
        [str(binary), "--content", str(content), "--layout", str(work / "absent"),
         "--out", str(out), "--title", "Fallback"],
        text=True, capture_output=True, timeout=300)
    check(result.returncode == 0)
    page = (out / "solo.html").read_text(encoding="utf-8")
    check("{{content}}" not in page and "{{title}}" not in page)
    check("<title>Solo &mdash; Fallback</title>" in page)
    check("Solo body" in page)
    check("<!DOCTYPE html>" in page)


def test_cli(binary, work):
    """The machine contract: exit codes and named errors."""
    check = finish("CLI contract")
    content = work / "cli-content"
    content.mkdir()
    write(content / "ok.md", "# ok\n")
    out = work / "cli-out"

    def ok(name, result, expected=0):
        check(result.returncode == expected,
              f"{name}: exit {result.returncode}, wanted {expected}; "
              f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}")

    ok("empty title builds", site(binary, content, out, title=""))
    check((out / "index.html").is_file(), "index.html from an empty title")

    help_result = subprocess.run([str(binary), "--help"], text=True, capture_output=True, timeout=60)
    ok("--help", help_result)
    check("usage: fin-ssg" in help_result.stdout, "--help text")
    check("--content" in help_result.stdout, "--help lists --content")

    ok("positional argument", subprocess.run([str(binary), "unexpected"], text=True,
                                            capture_output=True, timeout=60), expected=1)
    ok("unknown option", subprocess.run([str(binary), "--nope"], text=True,
                                       capture_output=True, timeout=60), expected=1)
    ok("absent content", site(binary, work / "absent", work / "absent-out"), expected=1)
    check(not (work / "absent-out").exists(), "no output for absent content")

    empty = work / "empty-content"
    empty.mkdir()
    ok("empty content", site(binary, empty, work / "empty-out"), expected=1)

    # A reserved homepage and case-folded collisions fail before any write.
    reserved = work / "reserved-content"
    reserved.mkdir()
    write(reserved / "index.md", "# authored home\n")
    ok("reserved index.md", site(binary, reserved, work / "reserved-out"), expected=1)
    check(not (work / "reserved-out").exists(), "no output for reserved index.md")
    (reserved / "index.md").unlink()

    # Two names differing only by case are one output file on a
    # case-insensitive filesystem, so the tool folds case on every platform and
    # refuses the collision rather than publishing one page over the other --
    # before creating the output directory.
    #
    # The situation can only be *constructed* on a case-sensitive filesystem:
    # NTFS and APFS make Page.md and page.md the same file, so a content tree
    # there cannot hold the collision in the first place. The guard still
    # matters, because it is what stops a tree authored on Linux from
    # publishing one page over another when built on Windows.
    collision = work / "collision-content"
    collision.mkdir()
    write(collision / "Page.md", "# a\n")
    if (collision / "PAGE.md").exists():
        print("  (case-insensitive filesystem: the collision cannot be built here, skipped)")
    else:
        write(collision / "page.md", "# b\n")
        collision_out = work / "collision-out"
        ok("case-folded collision", site(binary, collision, collision_out), expected=1)
        check(not collision_out.exists(), "no output for case-folded collision")


def test_limits(binary, work):
    """Inputs over the documented bounds are reported, not truncated."""
    check = finish("limits")
    content = work / "limit-content"
    content.mkdir()
    oversized = b"h" * (4 * 1024 * 1024 + 1)
    (content / "big.md").write_bytes(oversized)
    (content / "nul.md").write_bytes(b"head\x00tail")
    write(content / "good.md", "# good\n")
    out = work / "limit-out"
    result = site(binary, content, out)
    check(result.returncode == 2,
          f"exit {result.returncode}; stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}")
    check(not (out / "big.html").exists(), "no page for the over-size input")
    check(not (out / "nul.html").exists(), "no page for the NUL input")
    check((out / "good.html").is_file())
    check((out / "index.html").is_file())
    index = (out / "index.html").read_text(encoding="utf-8")
    check("good.html" in index and "big.html" not in index)

    # A failing write leaves the previous page intact.
    keep = work / "keep-content"
    keep.mkdir()
    write(keep / "k.md", "# new\n")
    keep_out = work / "keep-out"
    keep_out.mkdir()
    write(keep_out / "k.html", "PREVIOUS")
    if os.name != "nt":
        import resource
        import signal

        def restrict():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (256, 256))

        result = subprocess.run(
            [str(binary), "--content", str(keep), "--layout", str(work / "absent"),
             "--out", str(keep_out)], capture_output=True, timeout=60, preexec_fn=restrict)
        check(result.returncode != 0)
        check((keep_out / "k.html").read_text(encoding="utf-8") == "PREVIOUS")
        check(not [p for p in keep_out.iterdir() if p.name.endswith(".tmp")])


def test_special_files(binary, work):
    """A FIFO in the content directory is reported, and does not hang the build."""
    if os.name == "nt":
        return
    check = finish("special files")
    content = work / "special-content"
    content.mkdir()
    write(content / "page.md", "# page\n")
    os.mkfifo(content / "pipe.md")
    out = work / "special-out"
    result = subprocess.run(
        [str(binary), "--content", str(content), "--layout", str(work / "absent"),
         "--out", str(out)], text=True, capture_output=True, timeout=30)
    check(result.returncode == 2)
    check("pipe.md" in result.stdout)
    check((out / "page.html").is_file())
    check(not (out / "pipe.html").exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finc", default=os.environ.get("FINC", "finc"))
    parser.add_argument("--opt", default=os.environ.get("OPT", "-O0"))
    options = parser.parse_args()
    compiler = shutil.which(options.finc) or options.finc

    with tempfile.TemporaryDirectory(prefix="fin-ssg-e2e-") as directory:
        work = Path(directory)
        binary = build_static(compiler, work)
        for test in (test_example_site, test_markdown_to_html, test_front_matter,
                     test_escaping, test_unsafe_urls, test_determinism,
                     test_nested_and_relative_paths, test_default_layout, test_cli,
                     test_limits, test_special_files):
            print(f"== {test.__name__} ==", flush=True)
            test(binary, work)
    print("E2E OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
