# fin-ssg

A static site generator for [Fin](https://github.com/M1778/Fin): Markdown files
in, a static HTML site out.

```
content/hello.md   ─┐
content/second.md  ─┤─▶  fin-ssg  ─▶  public/hello.html
layout/page.html   ─┘               public/second.html
                                    public/index.html
```

## What it does

- Reads every `*.md` file directly inside the content directory (flat, no
  recursion), in sorted order.
- An optional `---` front matter block at the top of a file sets `title:` and
  `date:`. Without one, the title is the file name without `.md`.
- Renders Markdown to HTML, wraps it in `layout/page.html`, and writes
  `<name>.html`. The layout has four slots: `{{site_title}}`, `{{title}}`,
  `{{date}}`, `{{content}}`.
- Generates `index.html`: the site title plus one link per page, with its date.
- Uses a minimal built-in layout when `layout/page.html` does not exist.

Output is deterministic. Pages are rendered in sorted file-name order, no
timestamp or process id reaches a published byte, and every file is written
under a temporary name and renamed into place, so building the same input twice
produces byte-identical files and a failed write leaves the previous page
intact.

## What it does not do

- No themes, no template language of its own, no plugins, no incremental
  builds, no dev server, no watcher, no stale-output cleanup.
- No nested content directories, no file watching, no drafts, no taxonomies,
  no RSS, no pagination.
- It does not sanitise a layout. A layout is trusted HTML written by you; see
  [Security posture](#security-posture).
- It cannot tell a symlink from the file it points at: a symlinked `.md` entry
  is read, and a symlinked output path is replaced by a regular file. A FIFO,
  socket or device in the content directory is refused with a warning.
- Nothing is written to a path containing a `..` component.

## Install

Requires **Fin `finc` 1.0.0** (contract 3). `finc` 1.0.1 also works and is what
this repository is developed against; see [Verification](#verification).

For `finc`, use the published release index:
<https://github.com/M1778/Fin/releases>. On Linux take the
**`x86_64-unknown-linux-musl`** archive: it is statically linked. The
`x86_64-unknown-linux-gnu` archive links `libLLVM.so.22.1` and will not start on
a machine that does not have that exact shared library (it crashes in the
dynamic loader, before `main`).

```sh
curl -fL -o finc.tar.gz \
  https://github.com/M1778/Fin/releases/download/v1.0.0/finc-1.0.0-x86_64-unknown-linux-musl.tar.gz
mkdir -p finc && tar -xzf finc.tar.gz -C finc
./finc/bin/finc --version      # finc 1.0.0 (contract 3)
```

`finc` finds its standard library relative to its own binary (`../lib/std`), so
extract the whole archive, not just `bin/finc`.

Build fin-ssg. Every module the generator imports is in `src/`, so one `-I`
finds them all:

```sh
finc -I src src/main.fin -o fin-ssg     # build
finc -I src src/main.fin                # type-check only
```

Building an executable needs a C linker driver: `cc` on Linux and macOS,
`clang` on a Visual Studio Developer shell on Windows, or whatever `FIN_CC`
names.

### With the package manager

[`finn`](https://github.com/M1778/finn) reads `finn.toml` here and resolves
imports as `-I src` plus the standard library:

```sh
finn build          # -> out/fin-ssg
finn test           # library tests under tests/
finn do test        # library tests plus the end-to-end site suite
```

## Use

```sh
./fin-ssg [--content DIR] [--layout DIR] [--out DIR] [--title TITLE]
```

| Flag | Default | Meaning |
| ---- | ------- | ------- |
| `--content`, `-c` | `content` | directory with `.md` files |
| `--layout`, `-l` | `layout` | directory holding `page.html` |
| `--out`, `-o` | `public` | output directory, created if missing (including parents) |
| `--title`, `-t` | `My Site` | site title for `<title>` and `index.html` |
| `--help`, `-h` | | print usage and exit |

Exit codes: `0` every page was built; `1` usage, environment, or index failure;
`2` some pages failed (each is named on stdout and the rest were still built).

Limits: 256 arguments / 65,536 argv bytes, 4,096 Markdown files, 4 MiB per
input file and per layout, 32 MiB per rendered page. Anything over a limit is
named and refused, never silently truncated.

### A complete example

```sh
mkdir -p site/content site/layout
printf -- '---\ntitle: Hello\ndate: 2026-01-01\n---\n\n# Hello, Fin\n\nSome **bold** text.\n' \
  > site/content/hello.md
printf '<!DOCTYPE html>\n<html><head><title>{{title}}</title></head>\n<body>{{content}}</body></html>\n' \
  > site/layout/page.html
./fin-ssg --content site/content --layout site/layout --out site/public --title "My Site"
```

```output
built hello.md -> hello.html
fin-ssg: 1 page(s) + index -> site/public/ (0 skipped)
```

`site/public/hello.html` then contains the layout with `<h1>Hello, Fin</h1>`
and `<strong>bold</strong>` in the body, and `site/public/index.html` is a
generated page listing it.

The repository's own example is [`example/`](example):

```sh
./fin-ssg --content example/content --layout example/layout \
          --out public --title "My Fin Blog"
```

## Public API

The tool is a CLI; `src/` also exposes these modules. All functions are
`pub`, and every returned string is owned by the caller.

`src/platform.fin` — the filesystem layer the CLI uses:

| Function | Result |
| -------- | ------ |
| `open_directory(path, create) <Dir>` | names an existing directory, or creates it (with parents) when `create` is true. `Dir.ok` says whether it is usable. |
| `close_directory(&Dir)` | releases the directory's name |
| `name_kind(dir, name) <int>` | `1` readable regular file, `0` missing, `-1` directory/FIFO/socket/device |
| `read_text(dir, name, limit) <string?>` | the file's text, or null when missing, special, over `limit`, or containing a NUL |
| `write_atomic(dir, dest, text) <bool>` | writes and renames into place; verifies the published size |
| `component_ok(name) <bool>` | whether `name` is a single portable path component |
| `has_parent_step(path) <bool>` | whether a path contains a `..` component |

`src/markdown.fin` — fin-markdown v0.1.0: `md_to_html`, `md_inline`,
`md_escape_html`, `md_escape_into`, `filename_url`, and the `TextBuffer`
helpers.

`src/template.fin` — fin-template v0.1.0: `template_from_string`,
`template_from_file`, `template_render`, `render_string`,
`template_render_file`, and `tpl_render`, the four-slot entry point this tool
calls.

## Markdown support

Block: `#`–`######` headings (optional closing hashes), setext headings
(`===`/`---` under a paragraph), paragraphs, fenced code blocks (```` ``` ````
with an info string emitted as `class="language-x"`), `-`/`*` unordered lists,
`1.` ordered lists, `>` blockquotes, `---`/`***`/`___` horizontal rules, hard
breaks (two trailing spaces become `<br>`).

Inline: `` `code` ``, `**bold**`, `*italic*`, `***bold italic***`,
`~~strikethrough~~`, `[text](url)`, `![alt](url)`, reference links
(`[text][id]`, `[text][]`, `[text]` with `[id]: url` definitions anywhere in
the document), autolinks (`<https://…>`).

Not supported, and degraded to literal text rather than aborting: nested lists,
tables, indented code blocks, headings deeper than `######`, multi-line quote
merging, link titles, reference images, footnote syntax, underscore emphasis.

## Security posture

- **All text is escaped.** Content, titles and dates are escaped for HTML; a
  `<script>` in a Markdown file or a `title:` line becomes text, never markup.
  Attribute values are always quoted and quote-escaped.
- **Link and image targets are allowlisted.** Links allow `http`, `https`,
  `mailto` and relative URLs; images allow `http`, `https` and relative URLs.
  Anything else — `javascript:`, `data:`, `vbscript:`, protocol-relative
  `//host`, entity-obfuscated or control-character-obfuscated schemes —
  degrades to literal Markdown text and never becomes an attribute.
- **Layouts are trusted.** A layout is HTML you wrote, so `{{content}}` is
  inserted as markup by design. Do not put untrusted text in an executable
  context (a script or a URL-valued attribute). Unknown placeholders stay
  literal, and substitutions are single-pass: metadata that itself contains
  `{{content}}` cannot introduce another substitution.
- **Output names are bounded.** `index.md` is reserved, and names that collide
  ignoring ASCII case are rejected before anything is written, so the result is
  the same on a case-insensitive filesystem. A generated name is always a
  single path component.
- **Writes are per file, not a transaction.** A site build is not all-or-nothing:
  pages that succeeded stay published if a later one fails. There is no
  stale-output cleanup, so a page whose source was deleted remains until you
  remove it.

## Platform support

| Platform | Status |
| -------- | ------ |
| Linux x86_64 | Built and tested (the CI lane, and this repository's development host). |
| Windows x86_64 | Built and tested in CI on `windows-2022`. |
| macOS arm64 | Built and tested in CI on `macos-14`. |
| Linux aarch64, macOS x86_64 | Expected to work, **not tested**. |

The filesystem layer is written entirely against `fs::std` and `path::std`, so
each target gets its own system calls from the standard library: POSIX
`open`/`rename`/`mkdir` on Linux and macOS, the UCRT plus Win32 directory calls
on Windows. No compiled C bridge is required, and no path is built by joining
strings with `/`: `normalize` applies the target's own separator rules and
knows that `C:\` is a drive rather than a directory name.

Two platform notes:

- The published *glibc* `finc` artifact for Linux does not start on a machine
  without `libLLVM.so.22.1`; use the musl artifact, as above.
- On Windows, renaming over an existing file is not atomic, so `write_atomic`
  removes the destination first. The window is small but real; POSIX
  platforms rename over it in one step.

## Testing

```sh
python3 -I tests/e2e.py --finc finc          # end-to-end, the real suite
finc -I src tests/markdown_test.fin -o t && ./t   # library-level checks
```

`tests/e2e.py` builds the generator, then builds sites and asserts on the
**published files**: that each expected page exists, that the documented
Markdown constructs appear as the documented HTML, that content and metadata
are escaped, that dangerous URLs never become attributes, that two builds are
byte-identical, that a nested output directory is created and a `..` path is
refused, that over-limit and special inputs are reported rather than truncated,
and that a failed write leaves the previous page in place. It parses every page
with Python's HTML parser, so malformed output fails the suite.

CI runs that on Linux, Windows and macOS, using the pinned compiler release;
the version is one file, [`FINC_VERSION`](FINC_VERSION), and the download is
refused unless its SHA-256 matches the published index.

## Verification

What was actually run, on Linux x86_64:

- `tests/e2e.py` and `tests/markdown_test.fin` pass with `finc` 1.0.1 and with
  the pinned `finc` 1.0.0 release (musl artifact). The repeat-build check
  compares every published file byte-for-byte.
- `finn build` and `finn test` pass with `finn` 1.0.1 against this
  `finn.toml`; `finn do test` runs the end-to-end suite too.
- The Windows branch of `src/platform.fin` was type-checked by forcing the
  `FIN_TARGET_WINDOWS` preprocessor define, and the release installer's zip
  path was exercised. This machine has no Windows host, so the Windows
  **behaviour** is covered by CI, not here.
- macOS was not run on a developer machine. Its lane is CI only.

`finc` 1.0.1 defect this repository works around, reported upstream: when two
imported modules export the same function name, the name binds to whichever
import was seen first, silently and irrespective of arity. `path::std.join`
collides this way with the `strings::std.join` that joins a Collection (pulled
in by `fs::std`), and the resulting program calls the Collection method with two
strings and crashes. `src/platform.fin` therefore normalises
`parent + "/" + child` instead of calling `join`.

## License

MIT — see [LICENSE](LICENSE). The vendored renderer and template engine are
also MIT (their upstream repositories are part of the same Fin ecosystem).
