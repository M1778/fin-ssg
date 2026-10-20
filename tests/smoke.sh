#!/bin/sh
# Smoke test: builds fin-ssg and runs it against example/. Fails loudly.
set -eu
cd "$(dirname "$0")/.."

echo "== frontend check =="
finc -I src/vendor src/main.fin

echo "== codegen + link =="
finc -I src/vendor src/main.fin -o fin-ssg

echo "== build the example site =="
rm -rf /tmp/fin-ssg-smoke
./fin-ssg --content example/content --layout example/layout \
          --out /tmp/fin-ssg-smoke --title "Smoke Site"

echo "== assertions =="
test -f /tmp/fin-ssg-smoke/index.html
test -f /tmp/fin-ssg-smoke/hello.html
test -f /tmp/fin-ssg-smoke/second.html
# front matter title + date rendered through the layout
grep -q "<h1>Hello, Fin</h1>" /tmp/fin-ssg-smoke/hello.html
grep -q "2026-10-20" /tmp/fin-ssg-smoke/hello.html
# inline markup subset
grep -q "<strong>generated</strong>" /tmp/fin-ssg-smoke/hello.html
grep -q "<em>fin-ssg</em>" /tmp/fin-ssg-smoke/hello.html
grep -q "<code>inline code</code>" /tmp/fin-ssg-smoke/hello.html
grep -q '<a href="https://github.com/M1778/Fin">links</a>' /tmp/fin-ssg-smoke/hello.html
grep -q "<li>unordered item one</li>" /tmp/fin-ssg-smoke/hello.html
grep -q "<li>first ordered item</li>" /tmp/fin-ssg-smoke/hello.html
grep -q "<blockquote>" /tmp/fin-ssg-smoke/hello.html
grep -q "<pre><code>" /tmp/fin-ssg-smoke/hello.html
grep -q "<hr>" /tmp/fin-ssg-smoke/hello.html
# fallback title (no front matter -> slug)
grep -q "second" /tmp/fin-ssg-smoke/second.html
# index lists both pages with the site title
grep -q "Smoke Site" /tmp/fin-ssg-smoke/index.html
grep -q 'href="hello.html"' /tmp/fin-ssg-smoke/index.html
grep -q 'href="second.html"' /tmp/fin-ssg-smoke/index.html

echo "== default layout path (no --layout dir) =="
rm -rf /tmp/fin-ssg-smoke2
./fin-ssg --content example/content --layout /tmp/does-not-exist \
          --out /tmp/fin-ssg-smoke2 --title "Bare"
test -f /tmp/fin-ssg-smoke2/index.html
if grep -q "{{content}}" /tmp/fin-ssg-smoke2/index.html; then
  echo "unrendered placeholder left in output!"
  exit 1
fi

echo "SMOKE OK"
