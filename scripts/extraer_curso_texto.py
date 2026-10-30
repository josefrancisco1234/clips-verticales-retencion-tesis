"""Extrae el texto de las PPTX, DOCX, XLSX y PDF del curso a archivos .txt (para revisarlos)."""
import sys
from pathlib import Path

import docx
import openpyxl
from pptx import Presentation
from pypdf import PdfReader

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\curso_SEMINARIO")
OUT = SRC / "_texto"
OUT.mkdir(exist_ok=True)
for f in sorted(SRC.iterdir()):
    if not f.is_file():
        continue
    out = []
    try:
        if f.suffix == ".pptx":
            for i, s in enumerate(Presentation(str(f)).slides, 1):
                out.append(f"--- diapositiva {i} ---")
                for sh in s.shapes:
                    if sh.has_text_frame:
                        out += [p.text for p in sh.text_frame.paragraphs if p.text.strip()]
                    if getattr(sh, "has_table", False) and sh.has_table:
                        for r in sh.table.rows:
                            out.append(" | ".join(c.text for c in r.cells))
                if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
                    out.append("[notas] " + s.notes_slide.notes_text_frame.text)
        elif f.suffix == ".docx":
            d = docx.Document(str(f))
            out += [p.text for p in d.paragraphs if p.text.strip()]
            for t in d.tables:
                for r in t.rows:
                    out.append(" | ".join(dict.fromkeys(c.text.strip() for c in r.cells)))
        elif f.suffix == ".xlsx":
            for ws in openpyxl.load_workbook(str(f), data_only=True).worksheets:
                out.append(f"--- hoja {ws.title} ---")
                for r in ws.iter_rows(values_only=True):
                    if any(r):
                        out.append(" | ".join("" if v is None else str(v) for v in r))
        elif f.suffix == ".pdf":
            for i, p in enumerate(PdfReader(str(f)).pages, 1):
                out.append(f"--- página {i} ---")
                out.append(p.extract_text() or "")
    except Exception as e:  # noqa: BLE001
        out.append(f"ERROR: {e}")
    texto = "\n".join(out)
    (OUT / (f.name + ".txt")).write_text(texto, encoding="utf-8")
    print(f"{len(texto):7d} caracteres | {f.name}")
