# Trasladar el proyecto a otra máquina (sin nube propietaria)

Todo lo de aquí es software libre y funciona sin cuenta ni servidor de terceros.

| Qué mover | Tamaño | Herramienta recomendada |
|---|---|---|
| Código, configs, manifests, docs, modelos entrenados (`desarrollo/`) | ~31 MB | **git** (versionado) o **Syncthing** |
| Datos derivados: transcripciones, curvas, features, etiquetas humanas | ~200 MB | **Syncthing** o **croc** |
| Pesos externos (rostros, PANNs) | 313 MB | Se vuelven a descargar, o Syncthing |
| Audio WAV 16 kHz | ~12 GB | Syncthing (quitando la exclusión), o `pack_for_gpu.py --audio opus` (~1 GB) |
| Entorno `.venv` | — | **Nunca**: se recrea en cada máquina |

---

## Opción A · Syncthing (recomendada): sincronización continua P2P

[Syncthing](https://syncthing.net) es software libre (MPL-2.0). Conecta las dos PC directamente,
sin nube y sin cuenta. Si están en la misma red, va a velocidad de LAN; si no, usa retransmisores
cifrados. Ya quedó instalado y con identidad generada en esta laptop.

**ID de dispositivo de esta laptop:**

```
VIZGRMB-K5JZRFI-ZML5HYL-EZONCWC-R7J7QVC-MGGVHXH-JZYXYRY-PC3THAS
```

### Pasos

1. **En la PC con GPU**, instalar y arrancar:

   ```bash
   winget install Syncthing.Syncthing
   syncthing
   ```

   Se abre el panel en <http://127.0.0.1:8384>. Ahí aparece su propio ID en *Actions → Show ID*.

2. **En esta laptop**, arrancar Syncthing igual y en *Add Remote Device* pegar el ID de la otra PC.
   Aceptar la solicitud que aparece del otro lado.

3. **Compartir dos carpetas** desde esta laptop (*Add Folder → Sharing → marcar el otro dispositivo*):

   | Carpeta | Ruta | Notas |
   |---|---|---|
   | `tesis-codigo` | `…\tesisOFICIAL\desarrollo` | Ya tiene `.stignore` que excluye `.venv`, cachés y datos |
   | `tesis-datos` | `C:\tesis_data` | Ya tiene `.stignore` que excluye `.venv`, `outputs`, `cache` y el audio |

4. **Si quieres llevar también el audio** (necesario para recalcular features acústicas o construir el
   grupo U de HuBERT en la GPU), edita `C:\tesis_data\.stignore` y borra la línea `data/raw/wav`.

5. En la PC con GPU, apuntar la carpeta recibida a `C:\tesis_data` y seguir `docs/SETUP_GPU.md`.

**Cuidado:** la sincronización es bidireccional. Si ambas máquinas entrenan a la vez, los archivos de
`reports/` y `models/` pueden entrar en conflicto (Syncthing conserva ambas versiones con el sufijo
`.sync-conflict`). Lo práctico es trabajar en una máquina a la vez.

---

## Opción B · croc: envío puntual cifrado

[croc](https://github.com/schollz/croc) es software libre (MIT). Transfiere un archivo entre dos
máquinas con una frase clave, sin configuración previa. Ya está instalado aquí.

```bash
# 1) En esta laptop: generar el paquete y enviarlo
C:\tesis_data\.venv\Scripts\python scripts\pack_for_gpu.py
croc send C:\tesis_data\transfer\tesis_gpu_AAAAMMDD_HHMM.zip

# croc imprime una frase como:  1234-palabra-palabra-palabra

# 2) En la PC con GPU: recibirlo
winget install schollz.croc
croc 1234-palabra-palabra-palabra

# 3) Restaurar
C:\tesis_data\.venv\Scripts\python scripts\unpack_transfer.py tesis_gpu_AAAAMMDD_HHMM.zip
```

Con `--audio opus` el paquete incluye el audio comprimido (~1 GB) y `unpack_transfer.py` lo
reconvierte a WAV de 16 kHz al restaurarlo.

Alternativa con interfaz gráfica: [LocalSend](https://localsend.org) (`winget install LocalSend.LocalSend`),
también libre, funciona en la red local como AirDrop.

---

## Opción C · git para el código

El repositorio ya está inicializado en `desarrollo/`. Sirve cualquier remoto: un servidor propio con
[Forgejo](https://forgejo.org) o [Gitea](https://about.gitea.com), o incluso una carpeta compartida.

```bash
# remoto en un disco externo o carpeta de red (sin servicios de terceros)
git init --bare E:\tesis.git
git remote add origen E:\tesis.git
git add -A && git commit -m "estado actual" && git push -u origen master

# en la PC con GPU
git clone E:\tesis.git desarrollo
```

`.gitignore` ya excluye datos pesados y el entorno, así que el repositorio se mantiene en ~31 MB.
Los datos derivados viajan por Syncthing o croc, no por git.

---

## Verificación al llegar

```bash
C:\tesis_data\.venv\Scripts\python scripts\check_env.py     # debe decir "Listo para ejecutar"
C:\tesis_data\.venv\Scripts\python -m pytest                # 32 pruebas
C:\tesis_data\.venv\Scripts\python scripts\build_dashboard.py --serve   # panel con el estado
```
