"""Black-box regressions; Python is test infrastructure, never the generator."""
from pathlib import Path
from html.parser import HTMLParser
import os
import resource
import signal
import subprocess
import sys
import time
from urllib.parse import quote

BIN = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()


def run(content, out, *args, code=0, layout=None):
    result = subprocess.run(
        [str(BIN), '--content', str(content), '--layout', str(layout or WORK / 'missing'),
         '--out', str(out), *args], text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == code, (result.returncode, result.stdout, result.stderr)
    return result


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


content = WORK / "content with 'quotes'"
content.mkdir()
layout = WORK / "layout 'quoted'"
layout.mkdir()
(layout / 'page.html').write_text(
    '<!doctype html><html><head><title>{{title}}|{{site_title}}</title></head>'
    '<body><div data-title="{{title}}" data-date="{{date}}">{{content}}</div>'
    '<footer>{{unknown}}</footer></body></html>'
)
attack = """---
title: {{content}}
date: \" autofocus onfocus=\"window.__ssgExecuted=1
---
# Safe renderer

![x\" onerror=\"window.__ssgExecuted=1](missing.png)

[attribute](https://example.com/\"onmouseover=\"window.__ssgExecuted=1)

[normal](https://example.com/a?q=1&b=2)

[local](normal.html)

[mail](mailto:hello@example.com)

[encoded path](a%20b.html)

`<script>window.__ssgExecuted=1</script>`

<script>window.__ssgExecuted=1</script>

[stars](https://example.com/**not-markup**)

"""
unsafe = [
    'javascript:window.__ssgExecuted=1', 'JaVaScRiPt:window.__ssgExecuted=1',
    'data:text/html,bad', 'vbscript:bad', 'javascript&#58;bad', 'javascript&colon;bad',
    'java&#x73;cript:bad', 'java\tscript:bad', 'java\rscript:bad', 'java\nscript:bad',
    'java%73cript:bad', '%6aavascript:bad', 'javascript%3abad', '%256aavascript:bad',
    'https://example.com/%0abad', '//example.com/bad', '\\\\example.com',
]
for index, url in enumerate(unsafe):
    attack += f'[unsafe{index}]({url})\n\n'
(content / 'attack.md').write_text(attack)
(content / 'normal.md').write_text('# Normal page\n\nA normal **link target**.\n')
weird_name = 'x" onmouseover="window.__ssgExecuted=1 #?ü\n.md'
(content / weird_name).write_text('# Filename\n')
out = WORK / "output 'quoted'"
run(content, out, '--title', '{{title}}', layout=layout)
page = (out / 'attack.html').read_text()
assert '<title>{{content}}|{{title}}</title>' in page
assert '{{unknown}}' in page
parsed = Tags(page)
for tag, attrs in parsed.tags:
    assert tag != 'script'
    assert not any(key.startswith('on') for key in attrs), (tag, attrs)
    for key in ('href', 'src'):
        if key in attrs:
            assert not attrs[key].lower().startswith(('javascript:', 'data:', 'vbscript:'))
links = [a['href'] for tag, a in parsed.tags if tag == 'a']
assert len(links) == 6, links
assert 'https://example.com/a?q=1&b=2' in links
assert 'https://example.com/**not-markup**' in links
assert 'mailto:hello@example.com' in links
index_links = [a['href'] for tag, a in Tags((out / 'index.html').read_text()).tags if tag == 'a']
assert quote(weird_name[:-3] + '.html', safe='-._~') in index_links
assert (out / (weird_name[:-3] + '.html')).is_file()
assert not list(out.glob('.fin-ssg-*.tmp'))
run(content, WORK / 'empty-title', '--title', '')
assert '<title> &mdash; </title>' in (WORK / 'empty-title/index.html').read_text()

# No output mutations when a reserved name or pre-existing symlink is found.
reserved = WORK / 'reserved'
reserved.mkdir()
(reserved / 'index.md').write_text('authored homepage')
run(reserved, WORK / 'reserved-out', code=1)
assert not (WORK / 'reserved-out').exists()
(reserved / 'index.md').rename(reserved / 'INDEX.md')
run(reserved, WORK / 'reserved-out', code=1)
(reserved / 'INDEX.md').unlink()
(reserved / 'Page.md').touch()
(reserved / 'page.md').touch()
run(reserved, WORK / 'reserved-out', code=1)
assert not (WORK / 'reserved-out').exists()
sentinel = WORK / 'sentinel.txt'
sentinel.write_text('KEEP')
linkout = WORK / 'symlink-out'
linkout.mkdir()
(linkout / 'attack.html').symlink_to(sentinel)
run(content, linkout, code=1)
assert sentinel.read_text() == 'KEEP'
assert not (linkout / 'normal.html').exists()
(linkout / 'attack.html').unlink()
(linkout / 'index.html').symlink_to(sentinel)
run(content, linkout, code=1)
assert sentinel.read_text() == 'KEEP'
parent_link = WORK / 'parent-link'
parent_link.symlink_to(linkout, target_is_directory=True)
run(content, parent_link / 'nested', code=1)
assert not (linkout / 'nested').exists()
run(content, WORK / '..' / 'must-not-create', code=1)

# Input symlinks and special files cannot block or disclose outside content.
unsafe_content = WORK / 'unsafe-content'
unsafe_content.mkdir()
(unsafe_content / 'link.md').symlink_to(sentinel)
os.mkfifo(unsafe_content / 'fifo.md')
run(unsafe_content, WORK / 'unsafe-out', code=2)
assert 'KEEP' not in (WORK / 'unsafe-out/index.html').read_text()
assert sentinel.read_text() == 'KEEP'

# Existing hardlinks are replaced rather than truncating the other inode name.
hardout = WORK / 'hard-out'
hardout.mkdir()
os.link(sentinel, hardout / 'attack.html')
run(content, hardout)
assert sentinel.read_text() == 'KEEP'

# Short writes must preserve an existing destination and remove temp files.
write_content = WORK / 'write-content'
write_content.mkdir()
(write_content / 'page.md').write_text('# Large\n' + 'content ' * 500)
write_out = WORK / 'write-out'
write_out.mkdir()
(write_out / 'page.html').write_text('ORIGINAL')

def restrict_file_size():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (512, 512))

result = subprocess.run(
    [str(BIN), '--content', str(write_content), '--layout', str(WORK / 'missing'),
     '--out', str(write_out)], capture_output=True, timeout=10,
    preexec_fn=restrict_file_size,
)
assert result.returncode != 0
assert (write_out / 'page.html').read_text() == 'ORIGINAL'
assert not list(write_out.glob('.fin-ssg-*.tmp'))

# Full line scan; controlled resource failures never publish truncated text.
long_content = WORK / 'long-content'
long_content.mkdir()
(long_content / 'long.md').write_text('line\n\n' * 10000 + 'TAIL_SENTINEL\n')
start = time.monotonic()
run(long_content, WORK / 'long-out')
assert 'TAIL_SENTINEL' in (WORK / 'long-out/long.html').read_text()
print(f'20,001-line document: {time.monotonic() - start:.3f}s')
(long_content / 'long.md').write_bytes(b'x' * (4194304 + 1))
run(long_content, WORK / 'too-big', code=2)
assert not (WORK / 'too-big/long.html').exists()
(long_content / 'long.md').write_bytes(b'head\x00tail')
run(long_content, WORK / 'nul-out', code=2)
assert not (WORK / 'nul-out/long.html').exists()
# Output expansion has an independent 32 MiB bound; an old page survives.
expansion_layout = WORK / 'expansion-layout'
expansion_layout.mkdir()
(expansion_layout / 'page.html').write_text('{{content}}' * 64)
(long_content / 'long.md').write_text('x' * 600000)
expanded_out = WORK / 'expansion-out'
expanded_out.mkdir()
(expanded_out / 'long.html').write_text('OLD PAGE')
run(long_content, expanded_out, code=2, layout=expansion_layout)
assert (expanded_out / 'long.html').read_text() == 'OLD PAGE'

# Arg and file limits must reject rather than silently discard the suffix.
for args in (['--title', 'x' * 66000], ['--help'] * 257, ['unexpected']):
    result = subprocess.run([str(BIN), *args], capture_output=True, timeout=10)
    assert result.returncode == 1
many = WORK / 'many'
many.mkdir()
for i in range(4097):
    (many / f'{i:04}.md').touch()
run(many, WORK / 'many-out', code=1)
assert not (WORK / 'many-out').exists()

# CRLF metadata and malformed spans retain literal data safely.
crlf = WORK / 'crlf'
crlf.mkdir()
(crlf / 'crlf.md').write_bytes(b'---\r\ntitle: CRLF Title\r\n---\r\n# Body\r\n')
run(crlf, WORK / 'crlf-out')
assert '<title>CRLF Title &mdash;' in (WORK / 'crlf-out/crlf.html').read_text()
print('Security/CLI/filesystem/limits regressions passed')
