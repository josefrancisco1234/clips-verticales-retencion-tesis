"""Word v47: debajo de la Tabla 5 (las cuatro formas de puntuar) agrega cómo se calculó cada cifra, con los conteos reales del dataset
(reports/replicacion_D052/por_video.csv, reports/confirmacion_D048/por_video.csv, reports/confirmacion_fresca_D063/pred.npz) y las definiciones del código."""
import copy
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v46.docx")
ancla = next(p for p in d.paragraphs if p.text.strip().startswith("De azar a V0."))


def antes(texto):
    el = copy.deepcopy(ancla._p)
    ancla._p.addprevious(el)
    q = Paragraph(el, ancla._parent)
    for r in q.runs[1:]:
        r._r.getparent().remove(r._r)
    q.runs[0].text = texto
    return q


antes("Cómo se calcularon las cifras de la Tabla 5. La unidad de cálculo es cada video con su curva Most Replayed. Primero se corrige la curva (el primer tramo se iguala al segundo) y se marcan como tramos calientes los que valen más de 0.5, hasta un máximo de 20 por video. "
      "Un clip candidato cuenta como acierto si al menos 50 % de su duración cae dentro de los tramos calientes. De cada video se eligen cinco clips con el puntaje de cada forma, sin que dos se solapen más de 30 % del más corto.")
antes("Acierto@5. Por video vale 1 si al menos uno de los cinco clips es un acierto y 0 si ninguno lo es; la cifra de la tabla es la suma dividida entre el número de videos. "
      "En el grupo de videos nuevos 1 (93 videos), V0 acertó en 44 videos (44/93 = 47.3 %), V1 en 51 (51/93 = 54.8 %) y R0 en 58 (58/93 = 62.4 %). En el conjunto de confirmación (352 videos), V0 acertó en 174 (49.4 %) y V1 en 188 (53.4 %). "
      "El azar se calcula con el mismo procedimiento: en cada video se sortean cinco ventanas 100 veces, se mide el acierto en cada sorteo y se promedia; luego se promedia entre videos (en el grupo de videos nuevos 1 equivale a 25.0 videos de 93, 26.9 %; en la confirmación, a 102.5 de 352, 29.1 %).")
antes("F1 temporal. Para los cinco clips elegidos de un video se une su tiempo y se compara con el tiempo de los tramos calientes: la precisión es el tiempo de los clips que cae en tramos calientes dividido entre el tiempo total de los clips, la cobertura es el tiempo caliente cubierto dividido entre el tiempo caliente total, y F1 = 2 × precisión × cobertura / (precisión + cobertura). "
      "Por ejemplo (ilustrativo), si los cinco clips suman 200 s y 60 s caen en tramos calientes, y los tramos calientes suman 300 s, la precisión es 0.30, la cobertura 0.20 y el F1 0.24. La cifra de la tabla es el promedio del F1 entre los videos.")
antes("Calor del clip frente al video. El calor de un clip es el promedio de la curva en su tramo, ponderado por cuánto se solapa con cada tramo; la cifra es el promedio del calor de los cinco clips dividido entre el calor medio de todas las ventanas del mismo video, promediado entre videos. "
      "Un valor de 1.00x significa que los clips elegidos tienen el calor del video promedio; 1.43x, que los clips de V1 tienen 43 % más calor que ese promedio.")
antes("Qué puntúa cada forma y qué pruebas se usan. V0 suma, para cada ventana, el peso de cada una de las 17 variables por su percentil dentro del video (en estas corridas preregistradas el percentil es continuo; la versión de banderas 0/1 se compara aparte en la Tabla 11); V1 hace lo mismo, pero solo con ventanas de hasta 45 s; R0 es el puntaje de LightGBM LambdaRank, que se evalúa sobre las ventanas por tramo de la curva, por eso su azar es 31.9 %. "
      "Las diferencias entre formas se contrastan por video, con la prueba de Wilcoxon unilateral para F1 y para el acierto promedio y con la prueba exacta de McNemar para los videos en que una forma acierta y la otra no.")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v47.docx")
print("ok", len(d.element.body.xpath(".//w:drawing")), "dibujos")
