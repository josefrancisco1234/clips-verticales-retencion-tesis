"""Borrador de las 2 actas de asesoría (Nota 2). Los textos salen de lo conversado en el proyecto; fecha, hora y firmas se completan a mano."""
import sys
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TITULO = "Selección automática de clips verticales con alto potencial de retención en videos conversacionales a partir de señales de audio y texto"
ACTAS = [
    ("ACTA DE ASESORÍA N.° 1 (metodología)",
     ["Se revisó la metodología de la propuesta: un sistema abierto y auditable que, a partir solo del audio y la transcripción de un video largo conversacional, calcula 71 variables por clip candidato, las convierte en percentiles dentro de su propio video y las combina en un puntaje de 0 a 99 para elegir los cinco mejores clips verticales.",
      "Se explicó que la curva Most Replayed de YouTube se usa únicamente para calificar el sistema, nunca como entrada."],
     ["Separar con claridad el conjunto propio de datos (metodología) del conjunto de la literatura (experimentación).",
      "Sustentar cada variable y cada fórmula con trabajos publicados.",
      "Presentar los resultados con tablas numéricas y figuras generadas en Python, no con gráficos de Word."],
     ["Ajustar la metodología del artículo según las recomendaciones.", "Citar la fuente de cada variable de la fórmula."]),
    ("ACTA DE ASESORÍA N.° 2 (primer avance de código)",
     ["Se presentó el primer avance del código: ingesta del video, transcripción, generación de candidatos de 15 a 90 s, extracción de variables, ranking y renderizado vertical 9:16 con subtítulos.",
      "Se consultó cuál sería la métrica final de validación de la propuesta metodológica y qué equivale a un video de alta retención en la curva de YouTube.",
      "Respuesta dada: la métrica principal es el acierto@5, la proporción de videos donde al menos uno de los cinco clips coincide en el tiempo con un pico de la curva por encima de 0.5, que debe superar al azar con significancia (Wilcoxon unilateral, p < 0.05 con Bonferroni) en videos y canales no usados para ajustar la fórmula. Como secundarias, F1 temporal y NDCG@10 y, con usuarios, un SUS medio mayor a 70 y una mediana de utilidad de 4 o más.",
      "Un momento de alta retención se definió como un tramo de la curva Most Replayed con valor mayor a 0.5, respaldado por Sul et al. (2023), cuyo estudio con usuarios halló 64.8 % de acuerdo con esa etiqueta."],
     ["Incorporar la métrica final de validación al artículo.", "Sustentar la equivalencia entre alta retención y la curva de YouTube con literatura de 2021 en adelante."],
     ["Agregar la métrica final y su sustento al artículo.", "Continuar con la validación con usuarios y sus consentimientos informados."]),
]
d = docx.Document()
st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
for n, (titulo, temas, recs, acuerdos) in enumerate(ACTAS):
    if n:
        d.add_page_break()
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Universidad de Lima · Ingeniería de Sistemas · Seminario de Investigación"); r.font.size = Pt(9)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(titulo); r.bold = True; r.font.size = Pt(14)
    t = d.add_table(rows=0, cols=2); t.style = "Table Grid"
    for k, v in (("Estudiante", "José Francisco Núñez del Prado Vega"), ("Asesora", "Angela Gabriela Mayhua Quispe"),
                 ("Título del trabajo", TITULO), ("Fecha", "[COMPLETAR]"), ("Hora de inicio y fin", "[COMPLETAR]"), ("Modalidad", "[COMPLETAR: presencial o virtual]")):
        c = t.add_row().cells; c[0].text = k; c[1].text = v
        c[0].paragraphs[0].runs[0].bold = True
    for head, items in (("Temas tratados", temas), ("Recomendaciones dadas", recs), ("Acuerdos y próximos pasos", acuerdos)):
        h = d.add_paragraph(); h.paragraph_format.space_before = Pt(10); h.add_run(head).bold = True
        for it in items:
            d.add_paragraph(it, style="List Bullet")
    d.add_paragraph(); d.add_paragraph()
    s = d.add_table(rows=2, cols=2)
    s.cell(0, 0).text = "______________________________"; s.cell(0, 1).text = "______________________________"
    s.cell(1, 0).text = "José Francisco Núñez del Prado Vega\nEstudiante"; s.cell(1, 1).text = "Angela Gabriela Mayhua Quispe\nAsesora"
    q = d.add_paragraph(); q.paragraph_format.space_before = Pt(8)
    q.add_run("BORRADOR: redactado a partir de lo trabajado en el proyecto. Verificar con la asesora que el contenido, el orden de las dos actas y las recomendaciones coincidan con lo que ocurrió en cada reunión, y completar fecha, hora y firmas antes de entregar.").italic = True
d.save(r"F:\TESISJF\ENTREGA_NOTA2_FINAL\5_Actas_de_asesoria\Actas_de_asesoria_1_y_2_BORRADOR.docx")
print("ok")
