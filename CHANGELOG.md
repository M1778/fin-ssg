# Changelog — fin-ssg

All notable changes to fin-ssg are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

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
