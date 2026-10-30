# Reintenta cada 8 min hasta que YouTube deje bajar el video 3; entonces corre el pipeline (solo contenido).
$py = 'C:\tesis_data\.venv\Scripts\python.exe'
$url = 'https://www.youtube.com/watch?v=3KfZ30O2fEQ'
Set-Location 'D:\tesis\desarrollo'
for ($i = 1; $i -le 20; $i++) {
    $r = & $py -m yt_dlp --skip-download --print '%(duration)s' $url 2>&1 | Select-Object -Last 1
    "$(Get-Date -Format HH:mm) intento $i -> $r" | Out-File -Append 'C:\tesis_data\logs\reintento_video3.log' -Encoding utf8
    if ($r -match '^\d+$') {
        & $py -u scripts\generar_clips.py $url *> 'C:\tesis_data\logs\prueba_generar_3KfZ.log'
        "$(Get-Date -Format HH:mm) pipeline terminado" | Out-File -Append 'C:\tesis_data\logs\reintento_video3.log' -Encoding utf8
        break
    }
    Start-Sleep 480
}
