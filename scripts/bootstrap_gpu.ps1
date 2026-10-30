# Instala TODO lo necesario en una PC con GPU NVIDIA que no tiene nada.
#
# Uso (PowerShell, desde la carpeta 'desarrollo'):
#     powershell -ExecutionPolicy Bypass -File scripts\bootstrap_gpu.ps1
#
# Qué hace: winget (Python 3.11, ffmpeg, deno, croc, syncthing) → entorno virtual →
# PyTorch con CUDA según la tarjeta → dependencias → modelos de spaCy → pesos externos → verificación.
# Es reanudable: lo que ya está instalado se omite.

param(
    [string]$DataRoot = "C:\tesis_data",
    [switch]$SkipWinget,
    [switch]$CpuOnly
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $DataRoot ".venv"
$py = Join-Path $venv "Scripts\python.exe"

function Paso($n, $t) { Write-Host "`n=== $n. $t ===" -ForegroundColor Cyan }
function Ok($t)       { Write-Host "  [OK] $t" -ForegroundColor Green }
function Aviso($t)    { Write-Host "  [AVISO] $t" -ForegroundColor Yellow }

# ---------------------------------------------------------------- 1. GPU
Paso 1 "Tarjeta gráfica"
$gpu = ""
try {
    $gpu = (& nvidia-smi --query-gpu=name,driver_version --format=csv,noheader) -join " · "
    Ok "detectada: $gpu"
} catch {
    Aviso "no se pudo ejecutar nvidia-smi. Instala el driver NVIDIA desde nvidia.com/Download y vuelve a correr esto."
    if (-not $CpuOnly) { throw "sin driver NVIDIA no tiene sentido continuar (usa -CpuOnly para forzar)" }
}

# Pascal (GTX 10xx / Titan X) no está en las compilaciones nuevas de PyTorch: se usa CUDA 12.6
$indice = if ($gpu -match "GTX 10|TITAN X|GTX TITAN|Quadro P") { "cu126" } else { "cu128" }
if ($CpuOnly) { $indice = "cpu" }
Ok "índice de PyTorch elegido: $indice"

# ---------------------------------------------------------------- 2. Programas base
if (-not $SkipWinget) {
    Paso 2 "Programas base (winget)"
    $paquetes = @(
        @{ id = "Python.Python.3.11";     nombre = "Python 3.11" },
        @{ id = "Gyan.FFmpeg";            nombre = "ffmpeg" },
        @{ id = "DenoLand.Deno";          nombre = "Deno (lo pide yt-dlp)" },
        @{ id = "schollz.croc";           nombre = "croc (transferencias)" },
        @{ id = "Syncthing.Syncthing";    nombre = "Syncthing (sincronización)" },
        @{ id = "Git.Git";                nombre = "Git" }
    )
    foreach ($p in $paquetes) {
        Write-Host "  instalando $($p.nombre) …"
        winget install --id $($p.id) -e --scope user --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Null
    }
    Ok "programas instalados (si alguno ya estaba, winget lo omitió)"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
}

# ---------------------------------------------------------------- 3. Entorno virtual
Paso 3 "Entorno virtual en $venv"
if (-not (Test-Path $py)) {
    & py -3.11 -m venv $venv
    Ok "creado"
} else { Ok "ya existía" }
& $py -m pip install --upgrade pip --quiet

# ---------------------------------------------------------------- 4. PyTorch
Paso 4 "PyTorch ($indice)"
& $py -m pip install torch --index-url "https://download.pytorch.org/whl/$indice" --quiet
$cuda = (& $py -c "import torch; print(torch.cuda.is_available())").Trim()
if ($cuda -eq "True") {
    $nombre = (& $py -c "import torch; print(torch.cuda.get_device_name(0))").Trim()
    $cc = (& $py -c "import torch; print('%d.%d' % torch.cuda.get_device_capability(0))").Trim()
    Ok "CUDA disponible: $nombre (compute capability $cc)"
} elseif (-not $CpuOnly) {
    Aviso "PyTorch no ve la GPU. Prueba otro índice: cu126 → cu121. Comando:"
    Write-Host "    $py -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --force-reinstall"
}

# ---------------------------------------------------------------- 5. Dependencias
Paso 5 "Dependencias del proyecto"
$req = Join-Path $repo "requirements.txt"
# requirements.txt fija torch CPU: se instala todo lo demás sin tocar torch
$tmp = Join-Path $env:TEMP "req_sin_torch.txt"
Get-Content $req | Where-Object { $_ -notmatch "^torch==" -and $_ -notmatch "^--extra-index-url" } | Set-Content $tmp -Encoding utf8
& $py -m pip install -r $tmp --quiet
& $py -m pip install panns_inference --quiet
Ok "instaladas"

Paso 6 "Modelos de spaCy"
& $py -m spacy download es_core_news_sm --quiet
& $py -m spacy download en_core_web_sm --quiet
Ok "es_core_news_sm y en_core_web_sm"

# ---------------------------------------------------------------- 7. Pesos externos
Paso 7 "Pesos externos (detector de rostros y PANNs)"
$ext = Join-Path $DataRoot "models_ext"
New-Item -ItemType Directory -Force -Path (Join-Path $ext "panns") | Out-Null
$descargas = @(
    @{ url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"; dst = Join-Path $ext "blaze_face_short_range.tflite" },
    @{ url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx";                  dst = Join-Path $ext "face_detection_yunet_2023mar.onnx" },
    @{ url = "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1";                                                      dst = Join-Path $ext "panns\Cnn14_mAP=0.431.pth" },
    @{ url = "https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv";                  dst = Join-Path $env:USERPROFILE "panns_data\class_labels_indices.csv" }
)
foreach ($d in $descargas) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $d.dst) | Out-Null
    if (Test-Path $d.dst) { continue }
    Write-Host "  descargando $(Split-Path -Leaf $d.dst) …"
    Invoke-WebRequest -Uri $d.url -OutFile $d.dst -UseBasicParsing
}
Ok "pesos externos listos"

# ---------------------------------------------------------------- 8. Verificación
Paso 8 "Verificación"
Push-Location $repo
& $py scripts\check_env.py
& $py -m pytest -q
Pop-Location

Write-Host "`n=== Siguiente paso ===" -ForegroundColor Cyan
Write-Host "Restaura los datos del proyecto (transcripciones, curvas y features):"
Write-Host "    $py scripts\unpack_transfer.py <paquete tesis_gpu_*.zip>"
Write-Host "Y luego abre Claude Code en esta carpeta y pégale el prompt de docs\PROMPT_GPU.md"
