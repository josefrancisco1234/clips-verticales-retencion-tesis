"""Genera docs/diagramas/index.html a partir de los .mmd (Mermaid) para verlos en el navegador.

    python scripts/render_diagramas.py
El HTML permite descargar cada diagrama en SVG para pegarlo en el documento de tesis.
"""
from __future__ import annotations

import html
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "docs" / "diagramas"
TITLES = {
    "01_pipeline_inferencia": ("1. Pipeline de inferencia",
                               "De un video largo a clips 9:16 con score. Entre paréntesis, la técnica y el paper que sustenta cada bloque."),
    "02_datos_y_etiquetas": ("2. Datos y etiquetas",
                             "De dónde salen los videos y las dos etiquetas: la curva Most Replayed y los clips elegidos por humanos."),
    "03_protocolo_experimental": ("3. Protocolo experimental",
                                  "Desarrollo en v1, hipótesis preregistrada y confirmación en videos nuevos."),
}

PAGE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Diagramas del sistema</title>
<style>
  :root {{ --bg:#fbfbfd; --fg:#1b1b1f; --muted:#5c5f6b; --card:#fff; --line:#e3e3ea; --accent:#3b6ea5; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#15161a; --fg:#e9e9ee; --muted:#a2a5b2; --card:#1d1f25; --line:#2c2f38; --accent:#7fb2e5; }} }}
  :root[data-theme="dark"] {{ --bg:#15161a; --fg:#e9e9ee; --muted:#a2a5b2; --card:#1d1f25; --line:#2c2f38; --accent:#7fb2e5; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 -apple-system,Segoe UI,Roboto,sans-serif; padding:24px 16px 64px; }}
  header {{ max-width:1100px; margin:0 auto 28px; }}
  h1 {{ font-size:1.5rem; margin:0 0 6px; }}
  p.sub {{ color:var(--muted); margin:0; }}
  section {{ max-width:1100px; margin:0 auto 28px; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; }}
  h2 {{ font-size:1.12rem; margin:0 0 4px; }}
  p.desc {{ color:var(--muted); margin:0 0 14px; font-size:.93rem; }}
  .bar {{ display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap; }}
  button {{ font:inherit; font-size:.86rem; padding:5px 11px; border-radius:8px; border:1px solid var(--line);
            background:transparent; color:var(--accent); cursor:pointer; }}
  button:hover {{ background:var(--line); }}
  .box {{ overflow:auto; }}
  .mermaid {{ background:transparent; }}
  code {{ color:var(--muted); font-size:.8rem; }}
</style></head><body>
<header><h1>Diagramas del sistema de generación de clips</h1>
<p class="sub">Tesis · Universidad de Lima · generado por <code>scripts/render_diagramas.py</code> desde <code>docs/diagramas/*.mmd</code></p></header>
{sections}
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  const dark = matchMedia("(prefers-color-scheme: dark)").matches;
  mermaid.initialize({{ startOnLoad:true, theme: dark ? "dark" : "neutral", flowchart:{{ curve:"basis", padding:12 }} }});
  window.addEventListener("load", () => setTimeout(() => {{
    document.querySelectorAll("[data-dl]").forEach(b => b.onclick = () => {{
      const svg = document.getElementById(b.dataset.dl).querySelector("svg");
      const blob = new Blob([svg.outerHTML], {{type:"image/svg+xml"}});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = b.dataset.dl + ".svg"; a.click();
    }});
  }}, 800));
</script></body></html>"""

SECTION = """<section>
  <h2>{title}</h2><p class="desc">{desc}</p>
  <div class="bar"><button data-dl="{key}">Descargar SVG</button><code>docs/diagramas/{key}.mmd</code></div>
  <div class="box" id="{key}"><pre class="mermaid">{code}</pre></div>
</section>"""


def main() -> None:
    sections = []
    for key, (title, desc) in TITLES.items():
        src = (DIR / f"{key}.mmd").read_text(encoding="utf-8")
        code = "\n".join(l for l in src.splitlines() if not l.startswith("%%"))
        sections.append(SECTION.format(key=key, title=title, desc=desc, code=html.escape(code)))
    out = DIR / "index.html"
    out.write_text(PAGE.format(sections="\n".join(sections)), encoding="utf-8")
    print(f"escrito {out}")


if __name__ == "__main__":
    main()
