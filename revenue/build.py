"""Wrap app.html (the artifact page fragment) into a standalone index.html for GitHub Pages / local use."""
from pathlib import Path

here = Path(__file__).parent
body = (here / "app.html").read_text(encoding="utf-8")
head = ('<!doctype html><html lang="th"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
(here / "index.html").write_text(head + body + "</body></html>\n", encoding="utf-8")
print("wrote", here / "index.html")
