#!/usr/bin/env python3
"""Build dist/ for Cloudflare Pages Direct Upload, injecting GA4 gtag.js into every HTML page.
Same setup as djchezerecta.com: anonymize_ip, no Google signals, no ad personalization,
gtag.js loaded ~1.5s after the window load event. Google verification files are copied untouched."""
import pathlib, shutil, re
GA = "G-29XZ8MKWQS"
R = pathlib.Path(__file__).resolve().parent.parent
D = R / "dist"
SNIP = ('<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());'
        f'gtag("config","{GA}",{{anonymize_ip:true,allow_google_signals:false,allow_ad_personalization_signals:false}});'
        'addEventListener("load",function(){setTimeout(function(){var s=document.createElement("script");s.async=1;'
        f's.src="https://www.googletagmanager.com/gtag/js?id={GA}";document.head.appendChild(s)}},1500)}});</script>')
SKIP = {"dist", "tools", "node_modules"}  # top-level dirs never shipped
NOCOPY = {"README.md", "JARVIS_DNS.md"}
NONSITE_EXT = {".md", ".py", ".toml", ".lock", ".log"}
if D.exists(): shutil.rmtree(D)
for p in R.rglob("*"):
    rel = p.relative_to(R)
    if p.is_dir() or rel.parts[0] in SKIP or "node_modules" in rel.parts: continue
    if any(x.startswith(".") for x in rel.parts): continue  # hidden files/dirs (.git, .gitignore, ...)
    if str(rel) in NOCOPY or p.suffix in NONSITE_EXT or p.name in {"package.json", "package-lock.json"}: continue
    out = D / rel; out.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".html" and not re.fullmatch(r"google[0-9a-f]+\.html", p.name):
        h = p.read_text()
        if GA not in h:
            assert "</head>" in h, f"no </head> in {rel}"
            h = h.replace("</head>", SNIP + "</head>", 1)
        out.write_text(h)
    else:
        shutil.copy2(p, out)
print("built", D)
