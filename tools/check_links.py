#!/usr/bin/env python3
"""Link check for dist/: every internal href/src must resolve to a built file; every external link must answer 2xx/3xx.
preconnect/dns-prefetch hints are skipped. Exit 1 on any failure."""
import concurrent.futures as cf, pathlib, re, sys, urllib.parse, urllib.request, html
D = pathlib.Path(__file__).resolve().parent.parent / "dist"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
ext, bad = {}, []
for f in D.rglob("*.html"):
    page = "/" + str(f.relative_to(D)).replace("index.html", "")
    for tag in re.findall(r"<(?:a|link|img|script|iframe)\b[^>]*>", f.read_text()):
        if re.search(r'rel="(?:preconnect|dns-prefetch)"', tag): continue
        for u in re.findall(r'(?:href|src)="([^"]+)"', tag):
            u = html.unescape(u)
            if u.startswith(("mailto:", "tel:", "#", "data:", "javascript:")): continue
            if u.startswith("http"): ext.setdefault(u, page); continue
            p = urllib.parse.urljoin(page, u).split("#")[0].split("?")[0]
            t = D / p.lstrip("/")
            if not (t.is_file() or (t / "index.html").is_file()): bad.append(f"{page}: missing internal {u}")
def check(u):
    for m in ("HEAD", "GET"):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, method=m, headers=UA), timeout=25) as r:
                if r.status < 400: return None
        except Exception as x: err = getattr(x, "code", str(x))
    return f"{ext[u]}: {u} -> {err}"
with cf.ThreadPoolExecutor(12) as ex: bad += [r for r in ex.map(check, ext) if r]
print(f"checked {len(ext)} external links + internal links in {len(list(D.rglob('*.html')))} pages")
if bad: print("\n".join(sorted(bad))); sys.exit(1)
print("OK: 0 broken links")
