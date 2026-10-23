# Changelog — fin-ssg

All notable changes to fin-ssg are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Fixed
- CI smoke failure (reported 2026-10-22, "module not found: argparse /
  fs / strings"): `tests/smoke.py` passed an empty `--fin-libs ""` to
  finc, which finc treats as "search ONLY this path", dropping the
  built-in stdlib. The flag is now omitted when empty; the plain
  `finc -I src/vendor src/main.fin -o fin-ssg` build step was never
  affected. No workflow-file change needed. (Upstream finc hardening
  — treat empty `--fin-libs` as unset — drafted separately.)
- A naive fin-markdown swap would have regressed security.py twice:
  its link/image expansion had no URL scheme validation, and its
  emphasis passes rewrote markup inside emitted tags (`**` in a URL).
  Both are fixed in the adopted copy (allowlist + tag-aware emphasis),
  and a third gap — the 8192-line cap silently truncating long
  documents — is fixed with cursor-based chunked line iteration.

### Changed
- Adopted fin-template v0.1.0 (`src/vendor/template.fin`, via its
  `tpl_render` entry point — same four slots, auto-escaped metadata,
  `{{content|safe}}` body). Layouts may now also use the full engine
  syntax (`{{ x | filter }}`, `{% if %}`, `{% for %}`). The 32 MiB
  rendered-output bound the old engine enforced via `TextBuffer` is
  now enforced by `main.fin`'s `render_page` wrapper (a layout
  repeating `{{content}}` 64x over 600 KB still fails the page
  instead of publishing 38 MB); fin-template returns `""` (not null)
  on render failure, which is a documented wart.
- Adopted fin-markdown v0.1.0 (`src/vendor/markdown.fin`) with the
  fin-ssg hardening above: setext headings, `######` headings, fenced
  info-string classes (`<pre><code class="language-fin">` — the smoke
  assertion was updated to the class form), reference links, autolinks,
  `***`/`~~` emphasis, hard breaks. `TextBuffer`, `md_escape_into`
  and `filename_url` (which `main.fin` uses) are ported from the old
  renderer into the adopted copy.
- `tests/smoke.py`: `--fin-libs` omitted when empty (the CI fix
  above); the `<pre><code>` assertion updated to the fenced
  info-string class form (intended library upgrade).

### Added
- **fin-ssg** v0.1.0 (UNVERIFIED): static site generator CLI — `content/*.md`
  in, `public/*.html` out, plus a generated `index.html`. `---` front matter
  (title/date), `{{site_title}}`/`{{title}}`/`{{date}}`/`{{content}}` layouts
  (built-in fallback when `layout/page.html` is missing), stdlib `argparse`
  CLI (`--content/--layout/--out/--title/--help`). Vendored Markdown subset
  (`src/vendor/markdown.fin`: headings, paragraphs, bold/italic/code, fenced
  code blocks, lists, links, images, blockquotes, `---` rules) and vendored
  `{{key}}` template engine (`src/vendor/template.fin`), both marked for
  replacement when `fin-markdown` / Builder #2's `fin-template` land.
  Full lifecycle: README, `tests/smoke.sh`, GitHub Actions CI, real-format
  `finn.toml`, MIT license, `example/` demo site.
