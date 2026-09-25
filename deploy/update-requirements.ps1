# update-requirements.ps1
# Rigenera requirements.txt dal venv di sviluppo, escludendo le dipendenze
# di pip-audit (strumento di solo audit locale, non serve su test/produzione).
# Pensato per girare automaticamente ad ogni "npm run dev".

$BackendPath = "C:\portale\django"

# Pacchetti da escludere: albero delle dipendenze di pip-audit.
# Se in futuro installi un altro tool di solo-sviluppo, aggiungilo qui.
$escludi = @(
    'pip_audit', 'cyclonedx-python-lib', 'packageurl-python', 'py-serializable',
    'license-expression', 'boolean\.py', 'CacheControl', 'pip-api',
    'pip-requirements-parser', 'rich', 'markdown-it-py', 'mdurl', 'Pygments',
    'msgpack', 'filelock', 'platformdirs', 'tomli', 'tomli_w'
)
$pattern = "^(" + ($escludi -join '|') + ")=="

Push-Location $BackendPath
& .\venv\Scripts\python.exe -m pip freeze | Select-String -NotMatch $pattern | Out-File requirements.txt -Encoding utf8
Pop-Location

Write-Host "[OK] requirements.txt aggiornato" -ForegroundColor Green