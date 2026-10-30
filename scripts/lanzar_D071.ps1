while (Get-Process -Id 27284 -ErrorAction SilentlyContinue) { Start-Sleep 60 }
Set-Location 'D:\tesis\desarrollo'
& 'C:\tesis_data\.venv\Scripts\python.exe' -u scripts\ampliar_dataset_D071.py *> 'C:\tesis_data\logs\ampliacion_D071.out.log'
