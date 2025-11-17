@echo off
setlocal

REM Spostati nella cartella dove si trova questo .bat (root del progetto)
cd /d "%~dp0"

echo ==============================
echo Attivo l'ambiente virtuale...
echo ==============================

call ".venv\Scripts\activate.bat"

REM Rende importabile il package "sim" (che sta dentro src)
set PYTHONPATH=src

echo.
echo ==============================
echo Eseguo i test con pytest...
echo ==============================

python -m pytest

echo.
echo ==============================
echo Eseguo lo script di prova del simulatore...
echo ==============================

python -m src.sim.main_sim

echo.
echo ==============================
echo Eseguo analisi dell'ultima simulazione...
echo ==============================

python -m src.sim.analyze_last_run

echo.
echo ==============================
echo Controlli completati.
echo Premi un tasto per chiudere.
echo ==============================
pause


endlocal
