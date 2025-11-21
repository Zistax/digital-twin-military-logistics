@echo off

echo ==============================
echo Attivo l'ambiente virtuale...
echo ==============================

call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERRORE: impossibile attivare l'ambiente .venv
    pause
    exit /b 1
)

echo.
echo ==============================
echo Linting con Ruff...
echo ==============================

ruff check src tests
if errorlevel 1 (
    echo.
    echo ATTENZIONE: Ruff ha trovato problemi.
    echo Controlla i messaggi sopra (E/F) e correggili.
) else (
    echo Nessun problema trovato da Ruff.
)

echo.
echo ==============================
echo Controllo formattazione con Black (senza modificare i file)...
echo ==============================

black --check src tests
if errorlevel 1 (
    echo.
    echo ATTENZIONE: Black suggerisce modifiche di formattazione.
    echo Per applicarle automaticamente esegui:
    echo   black src tests
) else (
    echo Formattazione OK secondo Black.
)

echo.
echo ==============================
echo Test con coverage (pytest-cov)...
echo ==============================

pytest --cov=src --cov-report=term-missing

echo.
echo ==============================
echo Controlli di qualita' completati.
echo ==============================

echo.
echo Vuoi eseguire anche i controlli di sicurezza (pip-audit)? [S/N]
set /p RUNSEC=

if /I "%RUNSEC%"=="S" (
    call run_security.bat
) else (
    echo Salto i controlli di sicurezza.
)


pause

