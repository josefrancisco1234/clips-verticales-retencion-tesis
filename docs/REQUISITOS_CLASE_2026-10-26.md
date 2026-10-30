# Lo que pidió la profesora en la clase del 26-oct-2026 (semana 10, resultados)

Fuente: transcripción automática de Zoom (audio, 2 h 30 min), curso SEM.INVES.I / 951. La transcripción es ruidosa; lo de abajo es lo que se entiende con claridad.

## Entrega de la semana 10
- Metodología documentada, **código 100 %** y **resultados 100 %**.
- **Validación con usuarios** hecha, con **consentimientos informados** e **instrumentos llenados**.
- En la sustentación se muestra cómo funciona el código. Tiempos oídos: 15 min de exposición + 5 min de preguntas.
- La siguiente entrega es Discusión, Conclusiones y Abstract.

## Cómo redactar Resultados
1. Orden lógico según los objetivos de la ficha, agrupado por acciones: dataset / procesamiento, modelos, explicabilidad y validación con usuarios.
2. Presentar con **tablas y figuras**, no con párrafos largos.
3. **Tablas**: solo valores numéricos en filas y columnas (métricas). Nada de texto largo en celdas.
4. Poner en **negrita** la métrica que gana. Si hay varias bases o cohortes, reportar los resultados de cada una.
5. **Figuras sacadas de Python** (matriz de confusión, curvas, mapas de calor, histogramas, boxplots). **Nada hecho en Word.** Ejes con etiquetas.
6. Norma APA 7: número y título de la tabla o figura. **Prohibido "Elaboración propia".** La figura va con número y título alineados a la izquierda, debajo.
7. No repetir la misma información en tabla y figura: elegir una.
8. **Tiempo pasado.**
9. En Resultados **no hay discusión, ni citas, ni comparación con otros autores, ni métodos nuevos**. Eso va en Discusión.
10. Reportar **todos** los experimentos, también los malos (incluida fuerza bruta). No esconder resultados negativos.
11. Validación con usuarios: instrumentos traducidos a estadística, con tablas y figuras.
12. El preprocesamiento va en Metodología, no en Resultados.
13. El Abstract no se valora; si se incluye, solo ahí pueden ir resultados además de en Resultados y Conclusiones.

## Otras clases leídas (transcripción de Zoom, 2026-10-29)
- **27-oct** (lo general): entregables en Blackboard de la Nota 2: **código visible y con el enlace abierto** (si no abre, nota 0), ficha corregida, **artículo corregido hasta Resultados**, diapositiva de exposición, **2 actas de asesoría**, **consentimientos informados** (obligatorios si hay personas), plantilla Excel de resúmenes de artículos. La plantilla del PPT lleva: título, problema, objetivo, revisión de la literatura, marco teórico, metodología, experimentos, resultados y referencias. Exposición: **15 min + 5 min del jurado**; quien falte tiene 0. Mejor tener el código listo para explicarlo en clase que mandar un video.
  - Un dataset ya existente se describe en **Experimentación** (muestras en entrenamiento/validación/prueba, por clase, máquina usada), no en Metodología. Un dataset propio sí se explica.
  - Páginas: máximo 25–30 en total. Introducción 1–1.5 caras, marco teórico 2–3, experimentación ~2, resultados 2–2.5, metodología 3–4.
  - Marco teórico: citar todos los párrafos, las **ecuaciones** (una sola cita si traen texto) y las **figuras** (APA 7: *Nota.* … *Tomado de*). Las imágenes no deben venir de una IA sin fuente.
- **22-oct** (consejos a otro grupo, aplican a todos): tabla por clase con muestras de entrenamiento/validación/prueba; curvas de entrenamiento vs. validación (detectar sobreajuste); la matriz de confusión se hace solo con prueba; si se compara con un paper, repetir su experimento con la misma partición; indicar batch size y equipo.
- **20-oct**: tabla de datasets con número de muestras/personas; si hay dos datasets, entrenar/validar/probar cada uno y también probar el mejor modelo en el segundo.
- **15-oct**: la Nota 2 es "exposición de código" (el enlace del Colab o repositorio debe funcionar). **Pidió a José Núñez del Prado que le envíe la ficha de investigación.** Los objetivos deben estar validados por el asesor; si hay un objetivo de implementar una plataforma, también hay que validarla.
- **19-oct**: sin requisitos generales relevantes.
- **13-oct**: no usar IA para redactar documentos ni armar el pipeline de la metodología (va contra el curso y la universidad); sí puede apoyar en partes. En la exposición de código hay que mostrar todo el proceso: carga del dataset, procesamiento y guardado de datos.
- **12-oct**: lo que falta en metodología y experimentación debe demostrarse con el proceso completo.
- **6-oct**: usar estudios recientes (la brecha, con citas de los últimos 2 años; no de 2019). Trabajos relacionados con métricas y resultados de los autores. Marco teórico define conceptos y técnicas citando autores. Los subtítulos de la metodología siguen el diagrama de flujo (fases de preparación, modelado, implementación) con pseudocódigo representativo. Con prueba piloto con usuarios: aplicar un instrumento de usabilidad o experiencia de usuario y definir la estadística. Guardar en un **acta** lo que el asesor validó (objetivos y metodología).
- **5-oct**: sin requisitos generales relevantes.
- **1-oct** (exposición de José Núñez del Prado): la profesora pidió ver el funcionamiento del algoritmo en el código, separar los resultados por base de datos, compararse con el estado del arte y mostrar métricas de la versión generada. Mencionó que el reencuadre automático aún no enfocaba bien a quien habla. Dijo que se evalúa la redacción además del código: un buen sistema mal redactado no aprueba.
- **29-sep**: exposiciones de otros; el índice del artículo es problema, objetivos, trabajos relacionados, marco teórico, metodología propuesta, experimentación y referencias.
- **7-sep y 3-sep**: usar la plantilla del PPT "Seminario 1 2026-2 semana 2" (obligatoria); trabajos relacionados como revisión crítica (soluciones previas y limitaciones, sacadas de la ficha), máximo 3 caras; todos los párrafos de la revisión de la literatura se citan; la introducción debe decir la contribución. Se anima a publicar (revistas Scopus Q3, congresos como el CIS).
- Sin leer todavía: 8, 10, 14, 15, 16, 17, 21, 22 y 24 de septiembre y las grabaciones de agosto (página 3).
- **Descarga:** el anfitrión desactivó la descarga de las grabaciones; solo se pueden ver y leer sus transcripciones.

## Revisión del documento v22 contra esa lista (hecha 2026-10-29)
- Cumple: sin "Elaboración propia"; subtítulos de Resultados ordenados; figuras generadas con matplotlib; mejores métricas en tablas.
- Por corregir:
  1. §6.7 (párrafo "Las redes neuronales participan…") cita Radford, Koh, Grootendorst, Hsu: es una cita y una descripción de método dentro de Resultados. Mover a Metodología o Marco teórico.
  2. Tabla 10 (redes neuronales) tiene celdas de texto largo (función / papel). Dejar solo números (F1, acierto@5, p) y mover el texto a Metodología.
  3. Tabla 8 (matriz de confusión) y Figura 7 muestran lo mismo. Dejar una. La profesora prefiere la matriz de Python (figura).
  4. Falta la sección de **Resultados de la validación con usuarios** (5 creadores): hoy no existe porque aún no se hicieron las sesiones.
  5. Revisar que §6 esté todo en pasado y que no haya comparaciones con otros trabajos. (Revisado: no hay futuro ni comparaciones en §6.)
  6. **Los objetivos específicos del Word (4) no coinciden con la ficha v9 (7)**: faltan la web y la validación con 5 creadores, y §9 deja el prototipo como trabajo futuro aunque ya existe.
  7. **Extensión**: el documento tiene 31 páginas (máximo 25–30). Introducción ~1 340 palabras (pedido: 1–1.5 caras), marco teórico ~1 625 (pedido: 2–3 caras), resultados ~1 930 (pedido: 2–2.5 caras).
  8. Faltan citas en dos párrafos de Trabajos relacionados (§2.5 y el de síntesis) y en la introducción.
  9. Sin instrumento de usabilidad/UX, consentimiento informado, estadística de la validación ni acta de asesoría en el texto.
  10. Datos de portada inconsistentes: código 20221730 frente al correo 20220553; la asesora aparece como "Mayhua", "Maywa" y "Mayhua Quispe".
