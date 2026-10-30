"""v23 = v22 aplicando lo pedido en clase (26-oct-2026) y el cierre de objetivos de la ficha v9:
- Resultados: sin citas ni métodos (6.7), Tabla 10 solo con números, sin Tabla 8 duplicada de la Figura 7.
- Objetivos: los 7 de la ficha (web y validación con 5 creadores); trabajos futuros sin el prototipo (ya existe).
- 4.11 Página web y validación con usuarios (SUS, Bangor et al., 2008) y 6.10 con hueco para los resultados reales.
- Introducción recortada; citas en Trabajos relacionados; portada con un solo nombre de asesora."""
import copy, json, re, sys
from pathlib import Path
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.enum.text import WD_COLOR_INDEX
from docx.table import Table
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v22.docx")


def P(s, nth=0):
    hits = [p for p in d.paragraphs if p.text.strip().startswith(s)]
    return hits[nth]


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


def clone(tpl, text, before=None, after=None):
    el = copy.deepcopy(tpl._p)
    (before._p.addprevious(el) if before is not None else after._p.addnext(el))
    q = Paragraph(el, tpl._parent)
    st(q, text)
    return q


def drop(p):
    p._p.getparent().remove(p._p)


def table_with(first):
    return next(t for t in d.tables if t.cell(0, 0).text.strip().startswith(first))


BODY = P("El minero reunió")
HEAD = P("6.7 Las redes")


def setcell(c, t):
    p = c.paragraphs[0]
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = t
    else:
        p.add_run(t)


def renum_fig(old, new):
    for p in d.paragraphs:
        if re.search(rf"Figura {old}\b", p.text):
            done = False
            for r in p.runs:
                if re.search(rf"Figura {old}\b", r.text):
                    r.text = re.sub(rf"Figura {old}\b", f"Figura {new}", r.text)
                    done = True
            if not done:
                st(p, re.sub(rf"Figura {old}\b", f"Figura {new}", p.text))


# se elimina la figura del agente autónomo (Figura 5): imagen + título (decisión del autor)
_cap5 = P("Figura 5. ")
_prev = _cap5._p.getprevious()
_cap5._p.getparent().remove(_cap5._p)
if _prev is not None and _prev.xpath(".//w:drawing"):
    _prev.getparent().remove(_prev)
_p133 = next(q for q in d.paragraphs if "(Algoritmo 5; Figura 5)" in q.text)
st(_p133, _p133.text.replace("(Algoritmo 5; Figura 5)", "(Algoritmo 5)"))
renum_fig(6, 5)
renum_fig(7, 6)
CL = json.loads((ROOT / "reports" / "tabla_clases_D099.json").read_text(encoding="utf-8"))
CV = json.loads((ROOT / "reports" / "curvas_bigru_D099.json").read_text(encoding="utf-8"))
CAPFIG = P("Figura 6. ")
th = lambda n: f"{n:,}".replace(",", " ")


def add_figure(after, img, caption, cm=15):
    ip = clone(BODY, "", after=after)
    ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ip.paragraph_format.first_line_indent = 0
    ip.add_run().add_picture(str(img), width=Cm(cm))
    return clone(CAPFIG, caption, after=ip)

# --- referencias a los elementos que se mueven o borran (antes de renumerar) ---
cap8 = P("Tabla 8. ")
tbl8 = next(t for t in d.tables if len(t.rows) > 1 and t.rows[1].cells[0].text.startswith("Elegida"))
p173 = P("El techo observado")
cap10 = P("Tabla 10. ")
tbl10 = table_with("Componente (tipo de red)")
p190 = P("Las redes neuronales participan")
p191 = P("En el ranking se probaron")
cap11 = P("Tabla 11. ")
tbl11 = table_with("Conjunto (videos)")

# 1) Tabla 8: instancias por clase y métricas por clase (salida tipo classification_report de Python)
st(cap8, "Tabla 8. Instancias por clase (support) y métricas por clase de la matriz de confusión, salida de Python (557 videos, solo contenido)")
tbl8._tbl.getparent().remove(tbl8._tbl)
f3 = lambda x: f"{x:.3f}"
n_c, n_n = int(CL["Caliente"]["support"]), int(CL["No caliente"]["support"])
# la tabla es la salida de Python (sklearn classification_report) pegada como imagen, como pidió la profesora
im8 = clone(BODY, "", after=cap8)
im8.alignment = WD_ALIGN_PARAGRAPH.LEFT
im8.paragraph_format.first_line_indent = 0
im8.add_run().add_picture(str(ROOT / "reports" / "tabla_clases_D099.png"), width=Cm(11))

for r in p173.runs:
    r.text = r.text.replace("(Tabla 8)", "(Tabla 8 y Figura 6)")

# 1b) descriptivos del conjunto (Figura 8) y curvas de pérdida (Figura 10), ambas generadas con matplotlib
cap7 = P("Figura 6. ")
_pic = cap7._p.getprevious()
if _pic is not None and _pic.xpath(".//w:drawing"):
    import docx.shape as _ds
    _rid = _pic.xpath(".//a:blip/@r:embed")[0]
    _part = d.part.related_parts[_rid]
    _part._blob = open(ROOT / "reports" / "matriz_confusion_azul_D099.png", "rb").read()
    for _e in _pic.xpath(".//wp:extent") + _pic.xpath(".//a:ext[@cx]"):
        _e.set("cy", str(int(int(_e.get("cx")) * 840 / 1040)))
tx = clone(BODY, f"La Tabla 8 reúne las instancias por clase del problema: de las {th(n_c + n_n)} ventanas evaluadas, {th(n_c)} ({CL['pct_caliente'] * 100:.1f} %) cayeron sobre un pico real de retención y el resto no, de modo que la clase de interés es minoritaria y la exactitud global ({CL['exactitud'] * 100:.1f} %) no basta para juzgar el sistema. La Figura 7 describe la duración de los 444 videos de desarrollo y el número de videos por canal.", after=cap7)
add_figure(tx, ROOT / "reports" / "descriptivos_dataset_D099.png", "Figura 7. Descriptivos del conjunto de desarrollo: duración de los videos y videos por canal (444 videos, 349 canales).", cm=13)

# 2) 6.7: la descripción de las redes (con citas) pasa a metodología, al final de 4.9
head410 = P("4.10 Ciclo")
txt190 = p190.text.replace(" La Tabla 10 las reúne.", "")
clone(BODY, txt190, before=head410)
drop(p190)
st(p191, p191.text.replace("(Figura 8)", "(Tabla 10 y Figuras 8 y 9)"))

# 3) Tabla 10 (texto) -> tabla numérica
rows = [
    ("Modelo (444 videos, validación cruzada por canal)", "Acierto@5 (%)", "F1 temporal; p de Wilcoxon"),
    ("LightGBM R0 (referencia)", "58.8", "0.130"),
    ("BiGRU 128 (mejor red de secuencia)", "54.7", "0.121"),
    ("LightGBM + HuBERT", "59.5", "p = 0.109 frente a R0"),
    ("BiGRU + HuBERT", "60.1", "p = 0.028 frente a BiGRU (umbral 0.0125)"),
    ("EQL, 17 variables", "—", "0.1337 (LightGBM: 0.1335)"),
    ("EQL, 68 variables", "—", "0.1124; p = 0.90"),
]
tpl = copy.deepcopy(tbl10.rows[1]._tr)
for r in list(tbl10.rows)[1:]:
    tbl10._tbl.remove(r._tr)


for j, t in enumerate(rows[0]):
    setcell(tbl10.rows[0].cells[j], t)
for row in rows[1:]:
    tr = copy.deepcopy(tpl)
    tbl10._tbl.append(tr)
    for j, t in enumerate(row):
        setcell(tbl10.rows[-1].cells[j], t)
st(cap10, "Tabla 10. Desempeño de las redes neuronales de ranking frente a LightGBM")

# 4) curvas de pérdida del BiGRU (Figura 10) a continuación de la Figura 9
cap9 = P("Figura 8. ")
sobre = CV["epoca_minima"] < CV["epocas"] - 5
tcv = clone(BODY, f"La Figura 9 muestra la pérdida y la correlación de Pearson media, por época, del BiGRU de 128 unidades en los {CV['pliegues']} pliegues por canal. La pérdida de entrenamiento terminó en {CV['entrenamiento_final']:.3f}; la de validación alcanzó su mínimo ({CV['validacion_minima']:.3f}) en la época {CV['epoca_minima']} y terminó en {CV['validacion_final']:.3f}; la correlación media con el calor real llegó a {CV['correlacion_entrenamiento_final']:.3f} en entrenamiento y a {CV['correlacion_validacion_final']:.3f} en validación" + (", con una brecha que creció desde esa época (sobreajuste con unos 400 videos de entrenamiento)." if sobre else "."), after=cap9)
add_figure(tcv, ROOT / "reports" / "curvas_bigru_D099.png", "Figura 9. Pérdida y correlación de entrenamiento y de validación del BiGRU de 128 unidades (media de 10 pliegues por canal).", cm=15)

# 5) introducción: se quitan los tres párrafos que repetían la sección 2 y se escriben los 7 objetivos de la ficha
for pref in ("El problema afecta a creadores", "La literatura abordó la detección", "Otro grupo de trabajos incorporó"):
    drop(P(pref))
p44 = P("El objetivo general es desarrollar")
st(p44, "El objetivo general es desarrollar un pipeline basado en modelos de aprendizaje profundo y de ranking que, a partir del audio y la transcripción de un video conversacional, seleccione y puntúe de 0 a 99 clips verticales (9:16) con alto potencial de retención. Los objetivos específicos son: (i) construir un conjunto de datos propio de videos conversacionales en español e inglés, etiquetado con la curva de re-reproducción de YouTube; (ii) preprocesar los videos con Whisper, segmentarlos en candidatos de 15 a 90 s y extraer 71 variables de audio y texto; (iii) entrenar un modelo de ranking y una fórmula de variables ponderadas como modelos base, con validación cruzada por canal; (iv) entrenar y comparar modelos de aprendizaje profundo frente al ranker de árboles; (v) evaluar el sistema con acierto@5, F1 temporal y NDCG@10 en cohortes frescas, frente al azar y a la curva real de retención; (vi) integrar el sistema en una página web que genere cinco clips verticales con puntaje y explicación; y (vii) validar la utilidad y la usabilidad de la página con cinco creadores de podcast.")
p45 = P("Con ello se busca responder")
st(p45, "Con ello se busca responder tres preguntas. La primera es si un modelo de ranking aprendido supera al azar y a una fórmula fija de variables ponderadas en el acierto de al menos un pico de retención entre cinco clips, bajo un protocolo con hipótesis previa (Sul et al., 2023). La segunda es si los modelos de aprendizaje profundo de secuencia (BiGRU, TCN y Transformer) mejoran de forma confirmada al ranker de árboles sobre las mismas variables. La tercera es si los creadores de podcast perciben la página web como útil y usable.")
drop(P("El artículo se organiza así"))

# 6) citas que faltaban en trabajos relacionados
p56 = P("En síntesis, la literatura revisada")
st(p56, p56.text.replace("sistemas de edición.", "sistemas de edición (Barua et al., 2025; Sul et al., 2023; Wang et al., 2024)."))
p60 = P("En conjunto, ningún trabajo")
st(p60, p60.text.replace("con hipótesis previa.", "con hipótesis previa (Barua et al., 2025; Sul et al., 2023).", 1))

# 7) metodología 4.11: página web y validación con usuarios
disc5 = P("5. EXPERIMENTACIÓN")
clone(head410, "4.11 Página web y validación con usuarios", before=disc5)
clone(BODY, "El sistema se integró en una página web de dos partes. El backend, escrito en Python con la biblioteca estándar, recibe el video por carga directa (hasta 4 GB) o el enlace de YouTube, lanza el pipeline como un proceso independiente y expone, mediante una interfaz HTTP, la carga del video, el avance, el resultado y el registro de la validación. El frontend es una sola página en la que el usuario arrastra su video o pega el enlace, ve los pasos del proceso y recibe cinco clips verticales con su puntaje de 0 a 99, las banderas 0/1 de las variables que lo explican y las palabras de mayor peso.", before=disc5)
clone(BODY, "La validación con usuarios sigue un diseño descriptivo con cinco creadores de podcast (P1 a P5), elegidos por conveniencia. Cada participante firma un consentimiento informado antes de comenzar y no se registran datos personales: las respuestas se guardan con el código P1 a P5. Cada uno sube un episodio propio, revisa los cinco clips y responde tres bloques: (i) una calificación de 1 a 5 para cada clip; (ii) seis afirmaciones de utilidad percibida en escala Likert de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo); y (iii) la Escala de Usabilidad del Sistema, SUS, de diez ítems (Bangor et al., 2008). El puntaje SUS se obtiene restando 1 a los ítems impares y restando de 5 los ítems pares, sumando y multiplicando por 2.5, con un rango de 0 a 100. Con cinco participantes no se aplican pruebas de hipótesis: se reportan la mediana, el mínimo y el máximo de cada medida, y la media y el rango del SUS.", before=disc5)

# 8) resultados 6.9: estructura lista; los valores se completan con las sesiones reales (no se inventan)
disc7 = P("7. DISCUSIÓN")
# 8a) inventario de experimentos: exploración estática y automática (fuerza bruta)
AM = json.loads((ROOT / "reports" / "auto_mejora" / "estado.json").read_text(encoding="utf-8"))
AN = json.loads((ROOT / "reports" / "auto_mejora_nn" / "estado.json").read_text(encoding="utf-8"))
clone(HEAD, "6.9 Inventario de experimentos: fórmula estática y exploración automática", before=disc7)
clone(BODY, f"La Tabla 12 reúne todo lo que se probó. La fórmula estática de 17 variables se fijó una vez y se evaluó sin reajustes; la exploración automática, por el contrario, recorrió miles de rondas de ensayo y error: {AM['ronda']} del agente con LightGBM y {th(AN['ronda'])} del agente neuronal con red de ecuaciones, cada uno con {AM['pruebas_reservado']} pruebas permitidas en el conjunto reservado. Ninguna familia exploratoria superó a la fórmula de forma confirmada.", before=disc7)
cap12 = clone(cap11, "Tabla 12. Experimentos realizados y modelos promovidos", before=disc7)
inv = copy.deepcopy(tbl11._tbl)
disc7._p.addprevious(inv)
TI = Table(inv, disc7._parent)
tpli = copy.deepcopy(TI.rows[1]._tr)
for r in list(TI.rows)[1:]:
    inv.remove(r._tr)
irows = [("Familia de experimentos", "Configuraciones o rondas", "Promovidas al modelo final"),
         ("Fórmula estática de 17 variables (V0 y V1)", "2", "1 (versión 0/1)"),
         ("Ranker LightGBM LambdaRank (R0)", "1", "—"),
         ("Batería de modelos adicionales", "9", "0"),
         ("Redes de secuencia (BiGRU, TCN y Transformer)", "12", "0"),
         ("Red de ecuaciones EQL (17 y 68 variables)", "2", "0"),
         ("Agente de mejora con LightGBM (exploración automática)", f"{AM['ronda']} rondas; {AM['pruebas_reservado']} pruebas", "0"),
         ("Agente neuronal EQL en GPU (exploración automática)", f"{th(AN['ronda'])} rondas; {AN['pruebas']} pruebas", "0")]
for j, t in enumerate(irows[0]):
    setcell(TI.rows[0].cells[j], t)
for row in irows[1:]:
    tr = copy.deepcopy(tpli)
    inv.append(tr)
    for j, t in enumerate(row):
        setcell(TI.rows[-1].cells[j], t)
clone(BODY, "", before=disc7)

# 8b) validación con usuarios
clone(HEAD, "6.10 Validación con usuarios", before=disc7)
ph = clone(BODY, "[COMPLETAR TRAS LAS CINCO SESIONES] Participaron cinco creadores de podcast (P1 a P5). La Tabla 13 reúne la calificación de los clips, las seis afirmaciones de utilidad percibida y el puntaje SUS. Cada valor es la mediana (mínimo–máximo) de los cinco participantes; el SUS se reporta como media y rango.", before=disc7)
for r in ph.runs:
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
capv = clone(cap11, "Tabla 13. Resultados de la validación con cinco creadores de podcast", before=disc7)
capv_el = capv._p
src = tbl11
tv = copy.deepcopy(src._tbl)
disc7._p.addprevious(tv)
TV = Table(tv, disc7._parent)
tpl = copy.deepcopy(TV.rows[1]._tr)
for r in list(TV.rows)[1:]:
    tv.remove(r._tr)
vrows = [("Medida", "Mediana (mín.–máx.)", "n"),
         ("Calificación de los cinco clips (1 a 5)", "—", "5"),
         ("A1. Los clips elegidos me parecen momentos interesantes", "—", "5"),
         ("A2. Publicaría estos clips con poca o ninguna edición", "—", "5"),
         ("A3. La explicación del puntaje es fácil de entender", "—", "5"),
         ("A4. El puntaje de 0 a 99 me ayuda a decidir qué publicar primero", "—", "5"),
         ("A5. La página web es fácil de usar", "—", "5"),
         ("A6. Me ahorraría tiempo frente a elegir los clips a mano", "—", "5"),
         ("Puntaje SUS (0 a 100), media y rango", "—", "5")]
for j, t in enumerate(vrows[0]):
    setcell(TV.rows[0].cells[j], t)
for row in vrows[1:]:
    tr = copy.deepcopy(tpl)
    tv.append(tr)
    for j, t in enumerate(row):
        setcell(TV.rows[-1].cells[j], t)
# la tabla va después del texto y de su título (APA: título arriba)
disc7._p.addprevious(capv_el)
disc7._p.addprevious(tv)
disc7._p.addprevious(ph._p)
ph._p.addnext(capv_el)
capv_el.addnext(tv)

# 8c) métrica final de validación de la propuesta (pedido de la profesora)
_h49 = P("4.9 Exploración automática")
clone(BODY, "Métrica final de validación de la propuesta. La propuesta metodológica se valida con una métrica principal y un criterio de éxito fijados antes de evaluar. La métrica principal es el acierto@5: la proporción de videos en los que al menos uno de los cinco clips elegidos coincide en el tiempo con un pico real de retención (valor mayor a 0.5 en la curva). Se considera cumplida si el acierto@5 del modelo supera al del azar con significancia (prueba de Wilcoxon unilateral, p < 0.05 con corrección de Bonferroni) en videos y canales que no se usaron para ajustar la fórmula. Como métricas secundarias se reportan el F1 temporal y el NDCG@10. La validación con usuarios aporta la segunda métrica final: el puntaje SUS (0 a 100), cuyo criterio es una media mayor a 70, valor desde el cual se interpreta una usabilidad aceptable (Bangor et al., 2008), junto con una mediana de 4 o más (de 5) en las afirmaciones de utilidad percibida. La propuesta se da por validada cuando se cumplen ambos criterios, el técnico y el de usuarios.", before=_h49)

# 9) trabajos futuros y conclusión
tf = P("Como trabajos futuros")
st(tf, tf.text.replace("Quinto, se diseñará un prototipo del sistema como servicio para creadores y empresas de contenido, y se contrastará su selección con el mapa de calor de retención en cohortes nuevas.", "Quinto, se desplegará la página web como servicio para varios usuarios a la vez (cola de trabajos, autenticación y servidor con GPU) y se repetirá la validación con más creadores."))
cc = P("Este trabajo propuso y evaluó")
st(cc, cc.text.rstrip() + " La página web integra todo el flujo y su validación con cinco creadores de podcast se reporta de forma descriptiva (sección 6.10).")

# 8d) Tabla 14: criterios de validación y resultado (el criterio de usuarios queda pendiente hasta las sesiones)
clone(BODY, "[COMPLETAR TRAS LAS CINCO SESIONES] La Tabla 14 contrasta la métrica final con su criterio. En los 352 videos de confirmación que no se usaron para fijar la fórmula, la variante V1 acertó al menos un pico en 53.4 % de los videos frente a 31.7 % del azar con clips cortos (Wilcoxon unilateral, p < 0.001).", before=disc7)
for _r in disc7._p.getprevious().xpath(".//w:r"):
    pass
_phh = Paragraph(disc7._p.getprevious(), disc7._parent)
for _r in _phh.runs:
    _r.font.highlight_color = WD_COLOR_INDEX.YELLOW
clone(cap11, "Tabla 14. Métrica final de validación de la propuesta: criterio y resultado", before=disc7)
_t14 = copy.deepcopy(tbl11._tbl)
disc7._p.addprevious(_t14)
_T14 = Table(_t14, disc7._parent)
_tp14 = copy.deepcopy(_T14.rows[1]._tr)
for _r in list(_T14.rows)[1:]:
    _t14.remove(_r._tr)
_rows14 = [("Métrica final", "Criterio de éxito", "Resultado"),
           ("Acierto@5 frente al azar (352 videos de confirmación)", "p < 0.05 (Wilcoxon unilateral, Bonferroni)", "53.4 % frente a 31.7 %; p < 0.001"),
           ("Puntaje SUS (5 creadores)", "media > 70", "—"),
           ("Utilidad percibida (6 afirmaciones)", "mediana >= 4 de 5", "—")]
for _j, _t in enumerate(_rows14[0]):
    setcell(_T14.rows[0].cells[_j], _t)
for _row in _rows14[1:]:
    _tr = copy.deepcopy(_tp14)
    _t14.append(_tr)
    for _j, _t in enumerate(_row):
        setcell(_T14.rows[-1].cells[_j], _t)

# 9b) trabajos futuros más cortos (extensión); sin la línea de Repurpose-10K (decisión del autor)
tf = P("Como trabajos futuros")
t = tf.text.replace("con cinco líneas", "con dos líneas")
t = re.sub(r" Segundo, se confirmará[^.]*\.", "", t)
t = re.sub(r" Tercero, se entrenará[^.]*\.", "", t)
t = re.sub(r" Cuarto, se extenderá el minero[^.]*\.", "", t)
t = t.replace("Quinto, se desplegará", "Segundo, se desplegará")
st(tf, t)

# 9c) se quita todo lo de Repurpose-10K y su verificación con clips humanos (decisión del autor)
p42 = P("Sul et al. (2023) construyeron Mr. HiSum")
t = p42.text
i = t.index(" Por otra parte, Wu et al. (2025)")
st(p42, t[:i] + " Ambos conjuntos usan la curva de re-reproducción como etiqueta débil de los momentos destacados.")
p51 = P("La Tabla 1 compara los trabajos revisados")
t = p51.text.replace(" y los de clips de curación (Repurpose-10K) ampliaron", " ampliaron").replace("Park et al., 2025; Wu et al., 2025; Liu", "Park et al., 2025; Liu")
st(p51, t)
p214 = P("Los hallazgos tienen una implicancia")
st(p214, "Los hallazgos tienen una implicancia para el uso de la curva Most Replayed como etiqueta (Sul et al., 2023; Park et al., 2025): mide la re-reproducción de la audiencia general, por lo que se denomina al puntaje un indicador de retención y no de viralidad, en la línea de la definición de engagement de Li et al. (2024a).")
p217 = P("Las limitaciones del estudio son")
t = p217.text.replace("Las limitaciones del estudio son cuatro", "Las limitaciones del estudio son tres")
t = t.replace("; además, el contraste con la curación humana se apoya en 11 videos y es solo indicativo.", ".")
t = t.replace("la señal visual se probó solo de forma gruesa y no se evaluó con usuarios reales, por lo que", "la señal visual se probó solo de forma gruesa, por lo que")
j = t.index(" Cuarto, la curva mide"); k = t.index(" Además, los videos originales")
st(p217, t[:j] + t[k:])
trs = [r for r in table_with("Trabajo").rows if r.cells[0].text.startswith("Wu et al. (2025)")]
for r in trs:
    r._tr.getparent().remove(r._tr)
for q in [q for q in d.paragraphs if q.text.startswith("Wu, Y., Zhu, W.")]:
    drop(q)

# 10) portada: un solo nombre de la asesora
for p in d.paragraphs:
    if "Angela Gabriela" in p.text:
        st(p, p.text.replace("Angela Gabriela Maywa", "Angela Gabriela Mayhua Quispe").replace("Angela Gabriela Mayhua", "Angela Gabriela Mayhua Quispe").replace("Quispe Quispe", "Quispe"))

# 11) referencia nueva (verificada en Crossref, DOI 10.1080/10447310802205776)
last = [p for p in d.paragraphs if re.match(r"^Barua|^Bangor|^Brooke|^Ba", p.text.strip())]
refs_head = P("REFERENCIAS")
ref_ps = []
nxt = refs_head._p.getnext()
while nxt is not None:
    if nxt.tag.endswith("}p"):
        pp = Paragraph(nxt, refs_head._parent)
        if pp.text.strip():
            ref_ps.append(pp)
    nxt = nxt.getnext()
newref = "Bangor, A., Kortum, P. T., & Miller, J. T. (2008). An empirical evaluation of the System Usability Scale. International Journal of Human–Computer Interaction, 24(6), 574–594. https://doi.org/10.1080/10447310802205776"
placed = False
for pp in ref_ps:
    if pp.text.strip() > newref[:20] and not placed:
        clone(pp, newref, before=pp)
        placed = True
if not placed:
    clone(ref_ps[-1], newref, after=ref_ps[-1])

# 11b) Figura 1: pipeline de la metodología en bloques (pedido del autor), generado con matplotlib
_cap1 = P("Figura 1. ")
_ip = Paragraph(_cap1._p.getprevious(), _cap1._parent)
for _r in list(_ip.runs):
    _r._r.getparent().remove(_r._r)
_ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
_ip.add_run().add_picture(str(ROOT / "reports" / "pipeline_metodologia_D099.png"), width=Cm(16.2))

_pp = next(q for q in d.paragraphs if q.text.startswith("La Figura 1 resume el pipeline"))
_t = _pp.text
_i = _t.index("La Figura 1 resume"); _j = _t.index("Cada etapa guarda")
st(_pp, _t[:_i] + "La Figura 1 resume el pipeline: el audio y la transcripción del video se preprocesan, se extraen las variables, se convierten en percentiles dentro de cada video y se dividen por canal; luego se puntúan con el modelo final y con los modelos de comparación, se evalúan, se seleccionan los clips y se validan con creadores. " + _t[_j:])

# 11b2) estado del arte: nueva subsección 2.5 con trabajos verificados (llegar a 26 artículos citados)
_h25 = P("2.5 Comparación de los trabajos")
_h24 = P("2.4 Engagement y popularidad")
_sec_ref = [q for q in d.paragraphs if "sección 2.5" in q.text]
for _q in _sec_ref:
    st(_q, _q.text.replace("sección 2.5", "sección 2.6"))
st(_h25, "2.6 Comparación de los trabajos y brecha identificada")
_nh = clone(_h24, "2.5 Señales de voz y de texto asociadas con la atención de la audiencia", before=_h25)
clone(BODY, "Varios trabajos recientes relacionaron señales de audio, de texto y de comportamiento con la atención de la audiencia, casi siempre fuera de la selección de clips. En video educativo, Tseng (2021) comparó con 42 estudiantes el comportamiento de visualización con y sin anotaciones del docente y Parker et al. (2024) propusieron un marco motivacional del engagement con el video educativo; Suen y Su (2026) analizaron 210 videos de cursos masivos y 738 respuestas de estudiantes para estudiar cómo las expresiones vocales del docente, medidas con análisis acústico y de sentimiento, influyen en el compromiso afectivo. En podcasts, Reddy et al. (2021) mostraron que el vocabulario, la emoción y la sintaxis de la transcripción predicen el engagement de los oyentes. En videos cortos, Sun et al. (2025) exploraron modelos multimodales grandes que integran audio, imagen y lenguaje para predecir el engagement, y Cao y Aral (2025) estudiaron cómo las características de más de 90 000 campañas de video se relacionan con el engagement de la audiencia. En la detección de momentos destacados, Lei et al. (2021) publicaron QVHighlights, con más de 10 000 videos de YouTube anotados con puntajes de saliencia por clip, y Pei et al. (2024) propusieron un método de highlights incremental con más de 5 100 videos de transmisiones en vivo. En el habla, Żygis et al. (2025) describieron las características acústicas de los gritos de aliento en eventos deportivos, lo que respalda usar la prosodia y los eventos de audio como señales de intensidad; Banzina y Niebuhr (2023) estudiaron cómo se pausa en discursos carismáticos, Patel et al. (2023) mostraron que el habla con pausas se percibe más engañosa y Suen et al. (2026) predijeron el compromiso afectivo a partir de la expresividad del orador en video educativo. Estos trabajos apoyan el uso de pausas, prosodia, eventos de audio y rasgos del texto como variables, pero ninguno los combinó para elegir clips de un video conversacional ni los contrastó con la curva de re-reproducción.", before=_h25)

# 11c) Tabla 3: columna con la fuente (paper y DOI) de cada una de las 71 variables + referencias nuevas
import unicodedata
from docx.shared import Pt as _Pt
FV = json.loads((ROOT / "reports" / "fuentes_71_variables_D099.json").read_text(encoding="utf-8"))
APA = json.loads((ROOT / "reports" / "refs_apa_71_D099.json").read_text(encoding="utf-8"))
# D-099: la Tabla 3 solo cita literatura de 2021 en adelante (R = trabajo que relaciona la señal con engagement); sin fuente 2021+ verificada se deja "—"
_T3 = json.loads((ROOT / "reports" / "refs_apa_tabla3_2021_D099.json").read_text(encoding="utf-8"))
_T2 = json.loads((ROOT / "reports" / "refs_apa_2021_D099.json").read_text(encoding="utf-8"))
_NEW = {"zygis": ("Żygis", 2025, "10.1515/phon-2024-0034"), "patel": ("Patel", 2023, "10.1044/2023_jslhr-22-00618"), "cao": ("Cao", 2025, "10.1108/jrim-04-2024-0212"),
        "reddy": ("Reddy", 2021, "10.48550/arXiv.2106.06605"), "suen2": ("Suen", 2026, "10.48550/arXiv.2605.17463"), "sun": ("Sun", 2025, "10.48550/arXiv.2508.02516"),
        "banzina": ("Banzina", 2023, "10.2478/9788366675728-014"), "suen": ("Suen", 2026, "10.1109/TCSS.2026.3636388")}
_suen_old = FV["refs"].get("suen", {})
for _k, (_a, _y, _d) in _NEW.items():
    if _k == "suen" and _suen_old:
        continue
    FV["refs"][_k] = {"doi": "https://doi.org/" + _d, "titulo": _k, "autores": [_a], "anio": _y, "venue": ""}
for _k, _v in _T3.items():
    FV["refs"][_k] = {"doi": "https://doi.org/" + _v["doi"], "titulo": _k, "autores": [_v["autor"]], "anio": _v["anio"], "venue": ""}
_R = {"k_top_terms_pm": "reddy", "k_content_ratio": "reddy", "k_novelty": "reddy", "k_keyphrase_pm": "glazkova", "k_keybert_sim": "glazkova",
      "s_pos_mean": "feng reddy", "s_neg_mean": "feng reddy", "s_polarity_mean": "feng reddy", "s_polarity_std": "feng reddy",
      "s_intensity_mean": "suen2", "s_intensity_max": "suen2", "h_first_intensity": "suen2", "s_second_person": "atad", "h_second_person": "atad", "l_pron_12_vs_3": "atad",
      "s_hook_words": "lequere", "h_hook_word": "lequere", "s_laughs": "mueller", "a_rms_mean": "ringler suen2", "a_rms_p95": "ringler suen2", "a_rms_std": "ringler suen2",
      "a_pitch_std": "suen2 suen", "a_pitch_range": "suen2 suen", "a_voiced_ratio": "suen", "a_energy_delta": "zygis", "a_speech_rate": "wangg",
      "a_pause_ratio": "banzina patel", "a_long_pauses_pm": "banzina patel", "l_silence": "banzina patel", "f_topic_drift": "solbiati", "f_duration": "cao",
      "f_filler_rate": "braun", "l_fillers": "braun", "l_entropy": "reddy", "l_type_token": "reddy", "l_word_len": "gkikas",
      "e_laugh_max": "mueller", "e_laugh_mean": "mueller", "e_laugh_frac": "mueller", "e_laugh_tail": "mueller", "e_laugh_after": "mueller",
      "e_cheering_max": "zygis", "e_cheering_mean": "zygis", "e_music_max": "gu", "e_music_mean": "gu"}
for _v, _i in FV["variables"].items():
    _i["definicion"] = []
    _i["relacion"] = _R.get(_v, "").split()
_t3 = next(t for t in d.tables if t.rows[0].cells[0].text.strip() == "Variable" and len(t.rows) > 60)
_grid = _t3._tbl.tblGrid
_gc = _grid.findall(qn("w:gridCol"))
_newgc = copy.deepcopy(_gc[-1]); _grid.append(_newgc)
_W = [1420, 380, 2500, 540, 3728]
for g, w_ in zip(_grid.findall(qn("w:gridCol")), _W):
    g.set(qn("w:w"), str(w_))


def _cell_text(tc, text, size=5.2, bold=None):
    para = tc.findall(qn("w:p"))[0]
    for extra in tc.findall(qn("w:p"))[1:]:
        tc.remove(extra)
    rs = para.findall(qn("w:r"))
    for r_ in rs[1:]:
        para.remove(r_)
    pp = Paragraph(para, None)
    run = pp.runs[0] if pp.runs else pp.add_run("")
    run.text = text
    run.font.size = _Pt(size)
    if bold is not None:
        run.font.bold = bold
    pPr = para.find(qn("w:pPr"))
    if pPr is not None:
        jc = pPr.find(qn("w:jc"))
        if jc is not None:
            jc.set(qn("w:val"), "left")


def _short(k):
    x = dict(FV["refs"][k])
    if k == "whisper":
        x.update(anio=2023, doi="proceedings.mlr.press/v202/radford23a")
    x["autores"] = [("Spärck Jones" if a_.upper() == "SPARCK JONES" else a_) for a_ in x["autores"]]
    return f"{x['autores'][0]} ({x['anio']}), {x['doi'].replace('https://doi.org/', '').replace('https://aclanthology.org/', 'aclanthology.org/').rstrip('/')}"


for ri, row in enumerate(_t3.rows):
    tcs = row._tr.findall(qn("w:tc"))
    ntc = copy.deepcopy(tcs[-1])
    row._tr.append(ntc)
    if ri == 0:
        _cell_text(ntc, "Fuente 2021+ (trabajo que relaciona la señal con engagement)", size=6.0, bold=True)
    else:
        v = row.cells[0].text.strip()
        info = FV["variables"].get(v)
        if info:
            partes = []
            if info["definicion"]:
                partes.append("D: " + _short(info["definicion"][0]))
            if info["relacion"]:
                partes.append("R: " + _short(info["relacion"][0]))
            _cell_text(ntc, " | ".join(partes) if partes else "Fórmula propia de los autores: " + " ".join(row.cells[2].text.split()), bold=False)
        else:
            _cell_text(ntc, "Fórmula propia de los autores: " + " ".join(row.cells[2].text.split()), bold=False)
    for tc_, w_ in zip(row._tr.findall(qn("w:tc")), _W):
        tcPr = tc_.find(qn("w:tcPr"))
        if tcPr is not None:
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is not None:
                tcW.set(qn("w:w"), str(w_)); tcW.set(qn("w:type"), "dxa")
_cap3 = P("Tabla 3. ")
st(_cap3, "Tabla 3. Las 71 variables, su fórmula, su peso en la fórmula de puntuación (— = no entra a la fórmula) y el trabajo de 2021 en adelante que relaciona esa señal con engagement o atención (sin fuente 2021+ verificada, la fórmula es propia de los autores y se transcribe en la columna de fuente)")

# referencias nuevas, en orden alfabético, sin repetir las que ya están
_h = P("REFERENCIAS")
_refs = []
_n = _h._p.getnext()
while _n is not None:
    if _n.tag.endswith("}p"):
        _q = Paragraph(_n, _h._parent)
        if _q.text.strip():
            _refs.append(_q)
    _n = _n.getnext()
_have = " ".join(q.text.lower() for q in _refs)
_norm = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
_usadas = {k for v in FV["variables"].values() for k in v["definicion"] + v["relacion"]}
APA.update(json.loads((ROOT / "reports" / "refs_apa_2021_D099.json").read_text(encoding="utf-8")))
_usadas |= set(_T2)
APA.update({k: v["apa"] for k, v in _T3.items()})
_usadas |= {k for v in FV["variables"].values() for k in v["relacion"] if k in _T3}
_nuevas = 0
for k in sorted(_usadas, key=lambda k: _norm(APA.get(k, ""))):
    ref = APA.get(k)
    if not ref or k == "whisper":
        continue
    doi = ref.split("https://")[-1].replace("doi.org/", "").lower()
    if doi in _have or doi.replace("aclanthology.org/", "") in _have:
        continue
    _refs = [q for q in d.paragraphs if q in _refs or False] or _refs
    _tpl = _refs[0]
    _pos = next((q for q in _refs if _norm(q.text) > _norm(ref)), None)
    _nq = clone(_tpl, ref, before=_pos) if _pos is not None else clone(_tpl, ref, after=_refs[-1])
    _refs.insert(_refs.index(_pos) if _pos is not None else len(_refs), _nq)
    _have += " " + ref.lower()
    _nuevas += 1
print("referencias nuevas:", _nuevas)

# párrafo en 4.5 sobre la fuente de cada variable
_h46 = P("4.6 Modelos de ranking")
_n_def = sum(1 for v in FV["variables"].values() if v["definicion"])
_n_rel = sum(1 for v in FV["variables"].values() if v["relacion"])
clone(BODY, f"Las variables se calculan con herramientas abiertas y con fórmulas propias descritas en la Tabla 3. Para cada una se buscó, solo entre trabajos de 2021 en adelante, un artículo que relacione ese tipo de señal con engagement, atención, carisma o detección de momentos destacados: {_n_rel} de las 71 variables tienen esa fuente verificada con su DOI y las {71 - _n_rel} restantes no la tienen, de modo que esas variables se dedujeron de la matemática propia, a partir de la fórmula que figura en la Tabla 3. Las fuentes cubren una familia de señales y no prueban que cada variable por separado prediga la retención; esa relación se evaluó con los experimentos de la sección 6. Los umbrales de pausa de 0.3 s y de 1 s, el umbral de 0.75 de las banderas y los pesos de la fórmula son decisiones o resultados de este trabajo y no provienen de un trabajo previo.", before=_h46)

# 11d) tablas numéricas de Resultados más compactas (extensión)
_HEADS = ("Familia de experimentos", "Medida", "Métrica final", "Prueba", "Modelo (444 videos", "Conjunto (videos)", "Clase de ventana")
for _tb in d.tables:
    _h0 = _tb.rows[0].cells[0].text.strip()
    if any(_h0.startswith(x) for x in _HEADS) and len(_tb.rows) < 12:
        for _row in _tb.rows:
            for _c in _row.cells:
                for _pp in _c.paragraphs:
                    _pp.paragraph_format.space_before = Pt(0)
                    _pp.paragraph_format.space_after = Pt(0)
                    for _r in _pp.runs:
                        _r.font.size = Pt(8)

# 11e) vocabulario específico: sin "solape/solapar" (decisión del autor)
_SUB = [("se solapa con un momento destacado", "comparte tiempo con un momento destacado"),
        ("el solapamiento permitido entre clips", "el porcentaje máximo de duración que un clip puede compartir con otro ya elegido"),
        ("La búsqueda eligió un solapamiento de 30 %", "La búsqueda eligió un máximo de 30 % de duración compartida entre dos clips"),
        ("el solapamiento de 30 % resultó óptimo", "el máximo de 30 % de duración compartida entre clips resultó óptimo")]
for _q in d.paragraphs:
    for _a, _b in _SUB:
        if _a in _q.text:
            _done = False
            for _r in _q.runs:
                if _a in _r.text:
                    _r.text = _r.text.replace(_a, _b); _done = True
            if not _done:
                st(_q, _q.text.replace(_a, _b))

# 12) extensión: el límite es 25-30 páginas; las figuras ocupaban páginas casi enteras, se reducen al 80 %
for k, shp in enumerate(list(d.inline_shapes)[1:]):
    f = 1.0 if k == 0 else (0.6 if k < 5 else (0.7 if k < 6 else 0.8))   # el pipeline de la Figura 1 va a ancho completo; los demás diagramas al 70 %
    shp.width, shp.height = int(shp.width * f), int(shp.height * f)

# fuente (APA) de la curva Most Replayed como referencia, en el resumen
for _q in d.paragraphs[:45]:
    for _r in _q.runs:
        if "Most Replayed de YouTube, usada" in _r.text:
            _r.text = _r.text.replace("Most Replayed de YouTube, usada", "Most Replayed de YouTube (Sul et al., 2023), usada")
    if "Most Replayed de YouTube, usada" in _q.text:
        st(_q, _q.text.replace("Most Replayed de YouTube, usada", "Most Replayed de YouTube (Sul et al., 2023), usada"))
    for _r in _q.runs:
        if "YouTube Most Replayed curve is used" in _r.text:
            _r.text = _r.text.replace("YouTube Most Replayed curve is used", "YouTube Most Replayed curve (Sul et al., 2023) is used")
# resumen: por qué 17 variables (selección con regla fijada de antemano; usar las 68 o filtrar por video no mejoró)
for _q in d.paragraphs[:45]:
    if "una fórmula de 17 variables ponderadas (pausas" in _q.text:
        st(_q, _q.text.replace("se descubrió una fórmula de 17 variables ponderadas (pausas, silencio, variación de tono y de volumen, cercanía al tema central)", "se seleccionaron, de las 71 variables calculadas, 17 con una regla fijada antes de mirar los datos de confirmación (correlación parcial mediana de al menos 0.05 y prueba del signo con corrección de Bonferroni) y se ponderaron en una fórmula (pausas, silencio, variación de tono y de volumen, cercanía al tema central); usar las 68 variables de las tablas o filtrarlas por video no mejoró la fórmula (p > 0.28)"))
    if "a formula of 17 weighted variables was discovered (pauses" in _q.text:
        st(_q, _q.text.replace("a formula of 17 weighted variables was discovered (pauses, silence, pitch and loudness variation, closeness to the central topic)", "17 of the 71 computed variables were selected with a rule fixed before looking at the confirmation data (median partial correlation of at least 0.05 and a sign test with Bonferroni correction) and weighted into a formula (pauses, silence, pitch and loudness variation, closeness to the central topic); using all 68 variables or filtering them per video did not improve the formula (p > 0.28)"))
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v23.docx")
print("ok v23")

# 12b) referencias en 9 pt con menos espacio (extensión)
from docx.shared import Pt
_h = P("REFERENCIAS")
_n = _h._p.getnext()
while _n is not None:
    if _n.tag.endswith("}p"):
        _q = Paragraph(_n, _h._parent)
        _q.paragraph_format.space_after = Pt(1)
        for _r in _q.runs:
            _r.font.size = Pt(8.5)
    _n = _n.getnext()
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v23.docx")

# 13) la carátula desbordaba y dejaba la página 2 en blanco: se quitan tres párrafos vacíos
d2 = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v23.docx")
for k in (12, 11, 2):
    q = d2.paragraphs[k]
    if not q.text.strip() and not q._p.xpath(".//w:drawing") and "<w:sectPr" not in q._p.xml:
        q._p.getparent().remove(q._p)
d2.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v23.docx")
print("ok caratula")
