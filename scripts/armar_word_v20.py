"""v20 = v19 + citas faltantes: Bonferroni (Dunn 1961), Stouffer (1949), ListNet (Cao 2007), NMS (Neubeck y Van Gool 2006)."""
import copy, sys
import docx
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v19.docx")
def rep(a, b, all_=True):
    n = 0
    for p in d.paragraphs:
        if a not in p.text: continue
        done = False
        for r in p.runs:
            if a in r.text:
                r.text = r.text.replace(a, b) if all_ else r.text.replace(a, b, 1); done = True; n += 1
        if not done:  # el texto cruza runs
            for r in p.runs[1:]: r._r.getparent().remove(r._r)
            p.runs[0].text = p.text.replace(a, b); n += 1
    return n
print("bonf", rep("con el umbral de Bonferroni", "con el umbral de Bonferroni (Dunn, 1961)"))
print("bonf2", rep("aplicó el umbral de Bonferroni", "aplicó el umbral de Bonferroni (Dunn, 1961)"))
print("bonf3", rep("una corrección de Bonferroni sobre 50 pruebas", "una corrección de Bonferroni (Dunn, 1961) sobre 50 pruebas"))
print("stouffer", rep("con el método de Stouffer de forma descriptiva", "con el método de Stouffer (Stouffer et al., 1949) de forma descriptiva"))
print("listnet", rep("(ListNet)", "(ListNet; Cao et al., 2007)"))
print("nms", rep("(supresión de no máximos)", "(supresión de no máximos; Neubeck & Van Gool, 2006)"))
i0 = max(k for k, p in enumerate(d.paragraphs) if p.text.strip().startswith("REFERENCIAS"))
refs = [p for p in d.paragraphs[i0 + 1:] if p.text.strip()]
NEW = [("Cao", "Cao, Z., Qin, T., Liu, T.-Y., Tsai, M.-F., & Li, H. (2007). Learning to rank: From pairwise approach to listwise approach. En Proceedings of the 24th International Conference on Machine Learning (pp. 129–136). ACM. https://doi.org/10.1145/1273496.1273513"),
       ("Dunn", "Dunn, O. J. (1961). Multiple comparisons among means. Journal of the American Statistical Association, 56(293), 52–64. https://doi.org/10.1080/01621459.1961.10482090"),
       ("Neubeck", "Neubeck, A., & Van Gool, L. (2006). Efficient non-maximum suppression. En 18th International Conference on Pattern Recognition (pp. 850–855). IEEE. https://doi.org/10.1109/ICPR.2006.479"),
       ("Stouffer", "Stouffer, S. A., Suchman, E. A., DeVinney, L. C., Star, S. A., & Williams, R. M. (1949). The American soldier: Adjustment during army life (Vol. 1). Princeton University Press.")]
for key, txt in NEW:
    after = None
    for p in d.paragraphs[i0 + 1:]:
        if p.text.strip() and p.text.strip().split(",")[0] < key: after = p
    el = copy.deepcopy(after._p); after._p.addnext(el)
    q = docx.text.paragraph.Paragraph(el, after._parent)
    for r in q.runs[1:]: r._r.getparent().remove(r._r)
    q.runs[0].text = txt; q.runs[0].italic = False
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx")
print([p.text[:25] for p in docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx").paragraphs[i0 + 1:] if p.text.strip()][:12])

# ---- v20b: cobertura de lo trabajado (fuga D-018, cola de confirmación, ética) ----
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx")
def add(prefix, extra):
    for p in d.paragraphs:
        if prefix in p.text and len(p.text) > 200:
            p.runs[-1].text = p.runs[-1].text.rstrip() + " " + extra; return 1
    raise KeyError(prefix)
add("El tercer mecanismo", "Las candidatas que superan el umbral en desarrollo cuando el presupuesto del reservado ya se agotó pasan a una cola que se confirma una sola vez en la cohorte fresca 3 (D-091), cuya descarga y cálculo de variables están en curso al cerrar este trabajo.")
add("validación cruzada de 10 particiones agrupada por canal", "En una versión inicial se detectó una fuga de información, porque una variable codificaba la posición del clip dentro del video (D-018); desde entonces ninguna variable puede codificarla y todas las particiones se agrupan por canal.")
add("Las limitaciones del estudio son cuatro", "Además, los videos originales no se redistribuyen y la publicación de clips de terceros requeriría el permiso de sus autores; en este trabajo solo se conservan identificadores, transcripciones y variables derivadas.")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx"); print("v20b ok")
