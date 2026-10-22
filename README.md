# fin-ssg

A static site generator CLI written in [Fin](https://github.com/M1778/Fin):
Markdown files in, a static HTML site out. The "Fin is a real tooling
language" demo — think a tiny Hugo.

> **Verification status:** Native frontend, linking, and execution verified on
> Linux x86_64 and ARM64 with Fin 0.4.0 (contract 3), at both `-O0` and `-O2`.
> [Native run 39508662175](https://github.com/M1778/fin-sdk/actions/runs/39508662175)
> passed this project's smoke, security, and architecture mapping suites on both
> Linux hosts after correcting the architecture-specific open flags.
> The generator remains entirely Fin; Python 3 is used only for black-box tests.
>
> The filesystem layer now selects its calls for the native target, so macOS and
> Windows are compiled from the same source as Linux. What is verified natively
> is stated per platform below; the Linux behaviour is unchanged.

## What it does

```
content/hello.md   ─┐
content/second.md  ─┤─▶  fin-ssg  ─▶  public/hello.html
layout/page.html   ─┘               public/second.html
                                    public/index.html
```

- Reads every `*.md` in the content directory (flat, no recursion).
- Optional `---` front matter at the top of a file sets `title:` and `date:`.
  Without it, the title falls back to the file slug.
- Renders Markdown with a vendored subset (see below), wraps the fragment in
  `layout/page.html` (`{{site_title}}`, `{{title}}`, `{{date}}`, `{{content}}`
  slots), and writes `<slug>.html`.
- Generates `index.html`: the site title plus one link per page.
- If `layout/page.html` is missing, a minimal built-in layout is used.

## Build

Requires `finc` 0.4.0+ (contract 3):

```sh
finc -I src/vendor src/main.fin        # frontend check
finc -I src/vendor src/main.fin -o fin-ssg   # codegen + link
```

## Run

```sh
./fin-ssg [--content DIR] [--layout DIR] [--out DIR] [--title TITLE]
```

| Flag | Default | Meaning |
| ---- | ------- | ------- |
| `--content`, `-c` | `content` | directory with `.md` files |
| `--layout`, `-l` | `layout` | directory holding `page.html` |
| `--out`, `-o` | `public` | output directory (created if missing) |
| `--title`, `-t` | `My Site` | site title for `<title>` and `index.html` |
| `--help`, `-h` | | show help and exit |

Exit codes: `0` = all pages built, `1` = usage/environment error,
`2` = some pages failed (each is named; the rest were still built).

## Example session

```sh
$ ./fin-ssg --content example/content --layout example/layout \
            --out public --title "My Fin Blog"
built example/content/hello.md -> public/hello.html
built example/content/second.md -> public/second.html
fin-ssg: 2 page(s) + index -> public/ (0 skipped)

$ ls public
hello.html  index.html  second.html
```

## Markdown subset (v0.1)

Block: `#`/`##`/`###` headings, paragraphs, fenced code blocks
(\`\`\`), `-`/`*` unordered lists, `1.` ordered lists, `>` blockquotes,
`---` horizontal rules.
Inline: \`code\`, `**bold**`, `*italic*`, `[text](url)`, `![alt](url)`.
All text and quoted attributes are HTML-escaped. Links allow `http`, `https`,
`mailto`, and relative URLs; images allow `http`, `https`, and relative URLs.
Unsafe schemes, control characters, scheme entity obfuscation, protocol-relative
URLs, and encoded structural/control bytes degrade to literal Markdown.
Percent-encoded spaces in relative paths remain supported. Filenames are
URL-encoded in the index, including quotes, spaces, Unicode and newlines.

Not supported yet (degrade to literal text, never abort): nested lists,
tables, reference links, setext headings, headings deeper than `###`,
multi-line quote merging, recursive content directories. Inline nesting beyond
16 levels becomes literal text. Layout substitutions are single-pass: metadata
containing `{{content}}` stays literal and cannot introduce another substitution.

## Filesystem safety and limits

- Linux x86_64 or aarch64, macOS, or Windows. The filesystem calls are chosen
  for the native target (ADR 0051 addendum): Linux uses `openat`/`fstatat` with
  the architecture-specific `O_DIRECTORY`/`O_NOFOLLOW` values, which runtime
  `uname` selects; macOS uses the same `*at` family without `statx`; Windows
  uses `CreateFileA` with the backup-semantics and open-reparse-point flags.
  An unknown Linux architecture fails explicitly before filesystem access. No
  compiled C bridge is required. No shell commands enumerate content; native
  `fs::std::walk_dir` enumerates a pinned directory.
- Content, layout and output paths reject symlinks in **every** component and
  reject `..`. Use direct paths, not symlink aliases. Missing output parents are
  created. Missing layouts use the default; unsafe/unreadable layouts fail.
- Only regular input files are read. Symlinks, FIFOs, embedded NUL bytes and
  files larger than 4 MiB are reported, not silently shortened.
- `index.md` (any ASCII case) is reserved; ASCII case-folded output-name
  collisions are rejected before publication. Existing output
  symlinks, directories and other special files fail preflight. Regular files
  are replaced through exclusive same-directory temporary files, checked writes,
  `fsync`, close and descriptor-relative rename. Existing hardlinks are replaced,
  not truncated. Atomicity is **per file**, not an all-or-nothing site transaction;
  partial successes remain on a later failure. No stale-output cleanup is done.
- Limits: 256 arguments / 65,536 total argv bytes (including executable name),
  4,096 Markdown files, 4 MiB per input/layout, 32 MiB per rendered output/index.
  Limits fail explicitly. There is no line-count limit; empty option values and
  quoted directory names are preserved. Input directories must remain stable
  during enumeration; concurrent addition/removal is not a supported snapshot.
- Layouts are trusted HTML. Place metadata only in text or quoted attributes,
  not executable JavaScript/CSS or URL-valued attributes; use `{{content}}` only
  in an HTML body context. The tool does not sanitize arbitrary layout HTML.
  Keep the output directory owned by the build user, not writable by adversaries.
- Known toolchain limitation: O0 can evaluate an allocating indexed-assignment
  RHS twice. This repository uses local temporaries before owned-array assignment,
  but the pinned native `fs::std::walk_dir` still contains such an assignment;
  directory enumeration can therefore leak a duplicated filename allocation.
  Compiler/stdlib fixes are outside this repository; this is not a claim of
  fully leak-free O0 execution.

## Vendored code

`fin-markdown` does not exist yet and `M1778/template` is a project
scaffold, not a templating engine — so both are hand-rolled inside this
repo and clearly marked:

- `src/vendor/markdown.fin` — native Fin Markdown parsing, URL checks, escaping,
  and bounded amortized text buffers.
- `src/vendor/template.fin` — native Fin single-pass four-slot template engine.

Both are imported by name (`import { md_to_html } from markdown::fin`) and
compile through the native backend. Returned renderer strings are explicitly
owned and released after each page.

## Tests & CI

```sh
sh tests/smoke.sh   # frontend + native build + examples + security regressions
OPT=-O2 sh tests/smoke.sh
# Override compiler/library paths if needed:
FINC=/path/to/finc FIN_LIBS=/path/to/lib/std sh tests/smoke.sh
```

The regression benchmark renders **20,001 lines** (10,000 `line`/blank pairs
plus a tail sentinel), preserving the tail. Observed wall times on the test host
were approximately 0.011 s at O0 and 0.007 s at O2; these are illustrative local
measurements, not portable performance thresholds.

`.github/workflows/ci.yml` installs the Fin toolchain, runs the frontend
check, builds the binary, and runs the smoke test on every push/PR.

## License

MIT — see [LICENSE](LICENSE).
