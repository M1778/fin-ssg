#!/bin/sh
# Native Fin frontend/codegen + existing smoke checks + regression suite.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FINC=${FINC:-finc}
OPT=${OPT:--O0}
mkdir -p "$ROOT/.finn"
WORK=$(mktemp -d "$ROOT/.finn/ssg-test.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

printf '%s\n' '== frontend check =='
"$FINC" -I "$ROOT/src/vendor" "$ROOT/src/main.fin"
printf '%s\n' "== codegen + link $OPT =="
"$FINC" "$OPT" -I "$ROOT/src/vendor" "$ROOT/src/main.fin" -o "$WORK/fin-ssg"
printf '%s\n' '== build the example site =='
"$WORK/fin-ssg" --content "$ROOT/example/content" --layout "$ROOT/example/layout" \
    --out "$WORK/site" --title 'Smoke Site'

test -f "$WORK/site/index.html"
test -f "$WORK/site/hello.html"
test -f "$WORK/site/second.html"
grep -q '<h1>Hello, Fin</h1>' "$WORK/site/hello.html"
grep -q '2026-10-20' "$WORK/site/hello.html"
grep -q '<strong>generated</strong>' "$WORK/site/hello.html"
grep -q '<em>fin-ssg</em>' "$WORK/site/hello.html"
grep -q '<code>inline code</code>' "$WORK/site/hello.html"
grep -q '<a href="https://github.com/M1778/Fin">links</a>' "$WORK/site/hello.html"
grep -q '<li>unordered item one</li>' "$WORK/site/hello.html"
grep -q '<li>first ordered item</li>' "$WORK/site/hello.html"
grep -q '<blockquote>' "$WORK/site/hello.html"
grep -q '<pre><code>' "$WORK/site/hello.html"
grep -q '<hr>' "$WORK/site/hello.html"
grep -q 'second' "$WORK/site/second.html"
grep -q 'Smoke Site' "$WORK/site/index.html"
grep -q 'href="hello.html"' "$WORK/site/index.html"
grep -q 'href="second.html"' "$WORK/site/index.html"

printf '%s\n' '== default layout =='
"$WORK/fin-ssg" --content "$ROOT/example/content" --layout "$WORK/missing" \
    --out "$WORK/default" --title Bare
test -f "$WORK/default/index.html"
if grep -q '{{content}}' "$WORK/default/index.html"; then
    printf '%s\n' 'unrendered placeholder left in output'; exit 1
fi
python3 -I "$ROOT/tests/security.py" "$WORK/fin-ssg" "$WORK"
printf '%s\n' 'SMOKE OK'
