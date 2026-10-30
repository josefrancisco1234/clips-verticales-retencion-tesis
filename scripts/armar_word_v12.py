"""Arma Articulo_Investigacion_CIS2026_v12.docx a partir de la v11 (sin tocarla): agrega la sección 6.5 con los resultados de octubre 2026."""
import copy
import json
import sys
from pathlib import Path

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"F:\TESISJF\tesisOFICIAL_entrega\tesisOFICIAL\Articulo_Investigacion_CIS2026_v11.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v12.docx")
eql = json.loads((ROOT / "reports" / "explorador_ecuaciones" / "rondas.jsonl").read_text(encoding="utf-8").splitlines()[-1])
ap = json.loads((ROOT / "reports" / "explorar_D081" / "resultado.json").read_text(encoding="utf-8"))
d075 = json.loads((ROOT / "reports" / "confirmacion_D075" / "resultado.json").read_text(encoding="utf-8"))
fr = json.loads((ROOT / "reports" / "frontera_D076" / "resultado.json").read_text(encoding="utf-8"))
po = json.loads((ROOT / "reports" / "alcance_podcast_D084.json").read_text(encoding="utf-8"))

d = docx.Document(str(SRC))
P = d.paragraphs
idx = lambda start: next(i for i, p in enumerate(P) if p.text.strip().startswith(start))  # noqa: E731
i_disc = idx("7. DISCUSI")
head_tpl, body_tpl = P[idx("6.3 ")], P[idx("6.3 ") + 1]
cap_tpl = P[idx("TABLA V.")]
anchor = P[i_disc]


def add_par(tpl, text):
    el = copy.deepcopy(tpl._p)
    anchor._p.addprevious(el)
    p = docx.text.paragraph.Paragraph(el, anchor._parent)
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)
    return p


m = d075["metodos"]
add_par(head_tpl, "6.5 Resultados posteriores a la confirmación y exploración automática de ecuaciones")
add_par(body_tpl, (
    f"Tras las cohortes frescas se amplió el conjunto con {d075['n_videos']} videos nuevos de {d075['n_canales']} canales (campaña D-071). "
    f"La mezcla preregistrada de R0 con un submodelo de las 17 variables no se confirmó: en estos videos R0 acertó en {m['R0']['hit5']:.1%}, "
    f"el submodelo en {m['M17']['hit5']:.1%} y la mezcla en {m['MIX']['hit5']:.1%} (azar {m['azar']['hit5']:.1%}), con una diferencia de F1 de "
    f"{d075['MIX_vs_R0']['dif_F1']:+.4f} (p = {d075['MIX_vs_R0']['p_unilateral']:.2f}). La mejora de +0.010 vista en desarrollo era ruido."))
add_par(body_tpl, (
    "Se probó además una familia nueva de diez variables de frontera entre segmentos (la mayor pausa, pausas de más de dos segundos, el silencio en los "
    f"bordes, el reinicio del tono, la caída de energía y la confianza de las palabras). Añadirlas a R0 subió el F1 de "
    f"{fr['metodos']['R0']['F1']:.3f} a {fr['metodos']['R0+B']['F1']:.3f} (p = {fr['R0+B_vs_R0']['p_wilcoxon_bilateral']:.3f}) y al submodelo de 17 variables "
    f"de {fr['metodos']['M17']['F1']:.3f} a {fr['metodos']['M17+B']['F1']:.3f} (p = {fr['M17+B_vs_M17']['p_wilcoxon_bilateral']:.2f}); ninguna cumplió el criterio preregistrado "
    "de p < 0.025. Con el ciclo campeón/retador, la red BiGRU rindió por debajo de LightGBM en dos rondas (F1 0.110 frente a 0.134, p = 0.94), por lo que el campeón no cambió."))
c = ap["curva"]
ex = ap["extrapolado_hit"]
add_par(body_tpl, (
    f"La curva de aprendizaje de R0 muestra que el acierto crece alrededor de un punto porcentual por cada duplicación de los datos de entrenamiento "
    f"({c['50']['0'] if isinstance(c['50'], dict) else c['50'][0]:.1%} con 50 videos y {c[str(ap['n_train'])][0]:.1%} con {ap['n_train']}); extrapolada, llegaría a "
    f"{ex['10000']:.0%} con 10 000 videos. Separar los cinco clips con una distancia mínima tampoco mejoró el resultado (p = {ap['seleccion']['p_F1']:.2f}). "
    f"Delimitar el análisis a podcast no cambió el desempeño: {po['podcast']['hit5'][0]:.1%} de acierto en {po['podcast']['n']} videos de podcast y "
    f"{po['no_podcast']['hit5'][0]:.1%} en {po['no_podcast']['n']} del resto. En conjunto, con solo audio y texto, el acierto en videos nuevos se mantiene entre 55 y 58 %."))
add_par(body_tpl, (
    "Para atender la observación de explorar nuevas formas de la fórmula, se entrenó una red de ecuaciones (Equation Learner) con penalización L1 sobre los percentiles de las 17 variables. "
    f"El explorador evaluó 12 configuraciones por ronda, las eligió con validación cruzada interna por canal y evaluó la mejor una sola vez en un conjunto de {eql['n_holdout']} videos reservados por canal. "
    f"La ecuación aprendida alcanzó F1 {eql['EQL_F1']:.3f} y acierto {eql['EQL_hit5']:.1%}, frente a {eql['LGBM_R0_F1']:.3f} y {eql['LGBM_R0_hit5']:.1%} de LightGBM con 68 variables y "
    f"{eql['V0_F1']:.3f} y {eql['V0_hit5']:.1%} de la fórmula lineal V0. La diferencia con LightGBM no es significativa (p = {eql['p_unilateral']:.2f}), así que no se adopta; "
    "su valor está en que es una ecuación breve y legible con términos cuadráticos sobre el contraste de pausas, silencio y variación del volumen, es decir, una relación no monótona que la fórmula lineal no puede expresar."))
add_par(cap_tpl, "TABLA VIII. RESUMEN DE LAS PRUEBAS POSTERIORES (TODAS SIN MEJORA CONFIRMADA)")

rows = [("Prueba", "Resultado", "Decisión"),
        ("Mezcla R0 + 17 variables (83 videos nuevos)", f"dif. F1 {d075['MIX_vs_R0']['dif_F1']:+.4f}, p = {d075['MIX_vs_R0']['p_unilateral']:.2f}", "No se adopta"),
        ("Variables de frontera (444 videos)", f"dif. F1 {fr['R0+B_vs_R0']['dif_F1']:+.4f}, p = {fr['R0+B_vs_R0']['p_wilcoxon_bilateral']:.3f}", "No pasa a confirmación"),
        ("Retador BiGRU frente a LightGBM", "dif. F1 -0.024, p = 0.94", "Campeón sin cambio"),
        ("Más datos (extrapolación a 10 000 videos)", f"acierto ≈ {ex['10000']:.0%}", "Techo con solo contenido"),
        ("Podcast frente a resto", f"{po['podcast']['hit5'][0]:.1%} vs {po['no_podcast']['hit5'][0]:.1%}", "Sin diferencia"),
        ("Red de ecuaciones (EQL) frente a LightGBM", f"dif. F1 {eql['dif_F1_EQL_vs_campeon']:+.4f}, p = {eql['p_unilateral']:.2f}", "Empate; ecuación legible")]
tab = d.add_table(rows=len(rows), cols=3)
try:
    tab.style = d.tables[0].style
except Exception:  # noqa: BLE001
    tab.style = "Table Grid"
for r, row in enumerate(rows):
    for k, txt in enumerate(row):
        tab.cell(r, k).text = txt
anchor._p.addprevious(tab._tbl)
d.save(str(DST))
d2 = docx.Document(str(DST))
print("guardado:", DST, "| párrafos:", len(d2.paragraphs), "| tablas:", len(d2.tables))
for p in d2.paragraphs:
    if p.text.startswith(("6.5", "TABLA VIII", "7. DISCUSI")):
        print("-", p.text[:90])
