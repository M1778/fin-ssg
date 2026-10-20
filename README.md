# fin-ssg

A static site generator CLI written in [Fin](https://github.com/M1778/Fin):
Markdown files in, a static HTML site out. The "Fin is a real tooling
language" demo — think a tiny Hugo.

> **Verification status:** UNVERIFIED — written strictly against the Fin
> v0.4.0 [agent guide](https://github.com/M1778/Fin/blob/master/docs/agent-guide.md)
> and the stdlib sources. No working `finc` exists in the dev environment yet;
> the first thing to do when one appears is `sh tests/smoke.sh`.

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
All text is HTML-escaped.

Not supported yet (degrade to literal text, never abort): nested lists,
tables, reference links, setext headings, headings deeper than `###`,
multi-line quote merging, recursive content directories, filenames with
newlines. These are the natural issues to file once `fin-markdown` exists.

## Vendored code

`fin-markdown` does not exist yet and `M1778/template` is a project
scaffold, not a templating engine — so both are hand-rolled inside this
repo and clearly marked:

- `src/vendor/markdown.fin` — `// VENDORED — replace with fin-markdown when available`
- `src/vendor/template.fin` — `// VENDORED — replace with fin-template (Builder #2) when available`

They are imported by name (`import { md_to_html } from markdown::fin`),
the same spelling verified Fin libraries (finson, zhttp) use. If codegen
ever refuses an imported Fin function body, the documented fallback is to
inline the two files into `src/main.fin` — they are dependency-free by
construction, so the move is mechanical.

## Tests & CI

```sh
sh tests/smoke.sh   # frontend check + build + example site + HTML assertions
```

`.github/workflows/ci.yml` installs the Fin toolchain, runs the frontend
check, builds the binary, and runs the smoke test on every push/PR.

## License

MIT — see [LICENSE](LICENSE).
