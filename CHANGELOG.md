# Changelog

All notable changes to fin-ssg are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `scripts/fin_header.py --check` enforces the project header on every source
  file, so the rule is reproducible instead of a one-time edit.
- `ci/install_finc.sh`: installs the pinned compiler from the published release
  index, verifying its SHA-256 and refusing a mismatch. The version lives in
  `FINC_VERSION`.
- `tests/e2e.py`: end-to-end tests that build sites and assert on the published
  files — page presence, the documented Markdown-to-HTML mapping, escaping of
  content and metadata, URL allowlisting, byte-identical repeat builds, nested
  and `..` paths, over-limit and special inputs, and preservation of the
  previous page after a failed write.
- `tests/markdown_test.fin`: library-level checks for the renderer, escaper,
  template engine and text buffer.
- CI now runs on Linux, Windows and macOS, and **executes** the tests on all
  three. The previous workflow built a compiler from source on one Linux runner
  and only ran a shell wrapper.

### Changed

- **Modules moved from `src/vendor/` to `src/`.** `finn` resolves imports as
  `-I src` plus the standard library, so `finn build` could not find a module
  under `src/vendor/` and failed before compiling. The files are the same
  libraries, adopted at v0.1.0; only their location changed, and the import
  spellings (`markdown::fin`, `template::fin`) are unchanged.
- The filesystem layer is now written against `fs::std`/`path::std` instead of
  hand-declared `openat`/`fstatat`/`CreateFileA` externs. The hand-declared
  Windows branch did not compile at all (keyword parameter names, `0x` literals,
  and function signatures that did not match their call sites), so the previous
  cross-platform claim was not true. The standard library supplies each
  target's calls; the module keeps only the policy this tool needs.
- Directory paths are joined with `normalize`, not by concatenating `/`. A
  Windows path separator, a drive letter and an already-absolute component now
  behave correctly.
- `write_atomic` verifies the published size. `fs::std::write_string` reports
  success even when the filesystem wrote fewer bytes (it ignores `fclose`), so a
  short write used to publish a truncated page; it is now refused and the
  previous page survives.
- `name_kind` probes a candidate with a non-blocking open and a seek. Opening a
  FIFO for reading blocks, so a FIFO in the content directory used to hang the
  build; it is now reported and skipped.
- The `--help` text states what the tool does rather than "procfs and statx
  required", which stopped being accurate.
- `README.md` rewritten: exact verified compiler version, install from the
  published release, the POSIX/Windows split per platform, the real public API,
  and the limits and non-goals stated as limits. Removed the link to another
  repository's CI run as evidence for this one.

### Removed

- `tests/smoke.py`, `tests/smoke.sh`, `tests/security.py`, `tests/platform.fin`.
  The first two were a wrapper plus the same work in Python; the third asserted
  on internals the new layer does not have (it required output symlinks to be
  refused rather than safely replaced); the fourth tested the removed Linux
  open-flag table. Their real coverage lives in `tests/e2e.py`.
- The `OpenFlags`/`detect_open_flags` architecture table: it hard-coded Linux
  `O_DIRECTORY`/`O_NOFOLLOW` numbers for two architectures and refused every
  other platform, which is what `fs::std` already handles.

### Fixed

- `finn.toml` could not be consumed: `finn build` failed with `Undefined
  function or type` for every imported module.
- Metadata and content escaping is now asserted end-to-end. The behaviour was
  correct; nothing was checking it.

## [0.1.0] - 2026-10-23

### Added

- First version: `content/*.md` in, `public/*.html` plus a generated
  `index.html` out. `---` front matter (`title`, `date`), layout slots
  `{{site_title}}`/`{{title}}`/`{{date}}`/`{{content}}`, a built-in fallback
  layout, and `argparse`-based CLI with `--content/--layout/--out/--title`.
- fin-markdown v0.1.0 as the renderer and fin-template v0.1.0 as the layout
  engine, both adopted with the URL allowlist, quote-safe attribute emission and
  tag-aware emphasis this project requires.
- MIT license, `example/` demo site, `finn.toml`.
