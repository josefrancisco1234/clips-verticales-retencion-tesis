"""v18 = v17 + agente autónomo (D-095) como mecanismo central; resultados leídos de reports/auto_mejora/rondas.jsonl."""
import json, sys
from pathlib import Path
import docx
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v17.docx")
def P(s):
    for p in d.paragraphs:
        if p.text.strip().startswith(s): return p
    raise KeyError(s)
def st(p, t):
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = t
H = [json.loads(l) for l in open(ROOT/"reports"/"auto_mejora"/"rondas.jsonl", encoding="utf-8")]
est = json.load(open(ROOT/"reports"/"auto_mejora"/"estado.json", encoding="utf-8"))
pr = [h for h in H if "p_wilcoxon" in h]
prom = [h for h in H if h["promovido"]]
mejor = min(pr, key=lambda h: h["p_wilcoxon"]) if pr else None

p = P("El segundo es el explorador de ecuaciones")
st(p, "El tercer mecanismo, y el central, es un agente autónomo que ejecuta el ciclo sin intervención humana: no hay una persona pidiendo mejoras, el agente las genera, las prueba y decide. En cada ronda crea 10 variables nuevas como expresiones matemáticas sobre las 68 variables base (producto, diferencia, razón, máximo, mínimo, suavizado, derivada temporal, distancia a la mediana y contraste con el entorno), las criba con validación cruzada agrupada por canal solo en el conjunto de desarrollo, y gasta una prueba del conjunto reservado únicamente si la mejor candidata supera en 0.002 el F1 del campeón en desarrollo. El conjunto reservado tiene un presupuesto de 25 pruebas y la promoción exige una prueba de Wilcoxon unilateral con p menor que 0.05/25 (corrección de Bonferroni), de modo que repetir rondas no regala falsos descubrimientos. Si una variable se promueve, el campeón la incorpora y el agente sigue desde ahí; cada diez rondas refresca el minero de literatura. El explorador de ecuaciones (sección 4.9) aporta además fórmulas legibles, y toda mejora promovida debe confirmarse una sola vez en una cohorte fresca con la hipótesis escrita antes (Algoritmo 5). Cada ronda queda en la bitácora, incluidos los resultados negativos. El agente corre de forma continua (scripts/auto_mejora.py, decisión D-095) y guarda su estado en disco, por lo que puede detenerse y reanudarse sin perder el campeón.")
st(P("En el Algoritmo 5, las"), "En el Algoritmo 5, las líneas 3 a 6 corresponden al minero y a la generación de variables, la línea 7 a la cribada, las líneas 8 a 11 al campeón/retador con presupuesto y confirmación, y la línea 12 al registro.")
t = P("Cuando el explorador recibió las 68")
base = t.text
if H:
    s = f" El agente autónomo completó {len(H)} rondas; en {len(pr)} gastó una prueba del conjunto reservado y promovió {len(prom)} variables"
    if mejor: s += f" (la candidata más cercana, {mejor['mejor_candidato']}, obtuvo p = {mejor['p_wilcoxon']:.3f}, frente al umbral de 0.002)"
    s += "."
    st(t, base + s)

import re, copy
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
for p in d.paragraphs:
    if "<w:drawing" in p._p.xml: continue
    for r in p.runs:
        if re.search(r"Figura ([5-9])", r.text): r.text = re.sub(r"Figura ([5-9])", lambda m: f"Figura {int(m.group(1))+1}", r.text)
cap4 = P("Figura 4. ")
pic = d.add_paragraph(); pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
pic.add_run().add_picture(str(ROOT/"reports"/"agente_auto.png"), width=Inches(6.4)); pic.paragraph_format.keep_with_next = True
cap5 = copy.deepcopy(cap4._p); cap4._p.addnext(pic._p); pic._p.addnext(cap5)
from docx.text.paragraph import Paragraph
c5 = Paragraph(cap5, cap4._parent)
for r in c5.runs[1:]: r._r.getparent().remove(r._r)
c5.runs[0].text = "Figura 5. "; c5.runs[0].bold = True
rr = c5.add_run("Agente autónomo de mejora: una ronda (izquierda) y los valores p de sus pruebas en el conjunto reservado (derecha)."); rr.bold = False; rr.italic = True
q = P("El tercer mecanismo")
q.runs[-1].text = q.runs[-1].text.replace("(Algoritmo 5).", "(Algoritmo 5; Figura 5).")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v18.docx")
print(len(H), len(pr), len(prom), mejor and mejor["p_wilcoxon"])
