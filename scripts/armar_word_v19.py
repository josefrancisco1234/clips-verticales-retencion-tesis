"""v19 = v18 + agente neuronal (D-096) + Figura 6 (workflow unificado), renumerando las figuras siguientes."""
import copy, re, sys
from pathlib import Path
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v18.docx")
def P(s):
    for p in d.paragraphs:
        if p.text.strip().startswith(s): return p
    raise KeyError(s)
def st(p, t):
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = t
for p in d.paragraphs:
    if "<w:drawing" in p._p.xml: continue
    for r in p.runs:
        if re.search(r"Figura ([6-9])\b", r.text): r.text = re.sub(r"Figura ([6-9])\b", lambda m: f"Figura {int(m.group(1))+1}", r.text)
st(P("El tercer mecanismo"), "El tercer mecanismo, y el central, es un agente neuronal autónomo que ejecuta el ciclo sin intervención humana y en la GPU: no hay una persona pidiendo mejoras. El modelo que se mejora es una red de ecuaciones (EQL), una red neuronal cuya salida es una ecuación legible. En cada ronda el agente propone diez candidatos: cinco mutaciones de la arquitectura (anchos de cada tipo de unidad, profundidad, penalización L1 y tasa de aprendizaje) y cinco variables de entrada nuevas, que son una variable base de las 68 o una expresión matemática sobre ellas (producto, diferencia, razón, máximo, mínimo, suavizado, derivada temporal, distancia a la mediana o contraste con el entorno). Cada candidato se entrena con validación cruzada agrupada por canal solo en el conjunto de desarrollo, y el mejor gasta una prueba del conjunto reservado únicamente si supera en 0.002 el F1 del campeón. Esa prueba usa tres semillas, Wilcoxon unilateral y una corrección de Bonferroni sobre 50 pruebas (las 25 del primer agente más 25 nuevas), de modo que repetir rondas no regala falsos descubrimientos. Si el candidato se promueve, el campeón adopta la nueva arquitectura o la nueva variable; cada diez rondas el agente refresca el minero de literatura. Toda mejora promovida debe confirmarse una sola vez en una cohorte fresca con la hipótesis escrita antes (Algoritmo 5; Figura 5). Cada ronda queda en la bitácora, incluidos los resultados negativos (scripts/auto_mejora_nn.py, decisión D-096). Un primer agente que usaba LightGBM como evaluador (D-095) completó más de 70 rondas sin promover ninguna variable y quedó como línea base.")
cap5 = P("Figura 5. ")
pic = d.add_paragraph(); pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
pic.add_run().add_picture(str(ROOT/"reports"/"workflow_unificado.png"), width=Inches(6.5)); pic.paragraph_format.keep_with_next = True
cap6 = copy.deepcopy(cap5._p); cap5._p.addnext(pic._p); pic._p.addnext(cap6)
c6 = Paragraph(cap6, cap5._parent)
for r in c6.runs[1:]: r._r.getparent().remove(r._r)
c6.runs[0].text = "Figura 6. "; c6.runs[0].bold = True
rr = c6.add_run("Workflow unificado: construcción de datos (ETL y base de datos), uso del sistema sobre un video nuevo y ciclo de mejora automática con red neuronal."); rr.bold = False; rr.italic = True
# mención en el texto, justo después del párrafo del agente
ag = P("El tercer mecanismo")
nuevo = copy.deepcopy(ag._p); ag._p.addnext(nuevo)
q = Paragraph(nuevo, ag._parent)
st(q, "La Figura 6 reúne los tres flujos y el ciclo de mejora: la base de datos (A) alimenta el ranking que se aplica a un video nuevo (B) y el entrenamiento del agente (C); el heatmap solo califica, y un nuevo campeón vuelve al ranking únicamente después de la confirmación.")
for p in d.paragraphs:
    if p.text.startswith("Figura 5. Matriz"):  # el rótulo comparte párrafo con la imagen y el renumerado lo omitió
        p.runs[0].text = "Figura 7. "
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v19.docx"); print("ok")
