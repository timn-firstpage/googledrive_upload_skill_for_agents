# Copy outside the repository; paths only, never key contents.
$env:GDRIVE_SA_KEY_FILE = Join-Path $env:LOCALAPPDATA 'gdrive-upload\service-account.json'
$env:GDRIVE_ROOT_FOLDER_ID = '0AOx3b-buiVeqUk9PVA'
$env:GDRIVE_PYTHON = Join-Path $env:LOCALAPPDATA 'gdrive-upload\venv\Scripts\python.exe'
# GOOGLE_APPLICATION_CREDENTIALS is an alternative, not another key.
