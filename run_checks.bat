@echo off
echo ==============================
echo Attivo l'ambiente virtuale...
echo ==============================

call .venv\Scripts\activate.bat

echo.
echo ==============================
echo Eseguo i test con pytest...
echo ==============================

pytest

echo.
echo ==============================
echo Eseguo lo script di prova del simulatore...
echo ==============================

python -m src.sim.main_sim

echo.
echo ==============================
echo Controlli completati.
echo Premi un tasto per chiudere.
echo ==============================
pause