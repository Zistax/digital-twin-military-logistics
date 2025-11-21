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
echo Controllo vulnerabilita' nelle dipendenze (pip-audit)...
echo ==============================

pip-audit

if errorlevel 1 (
    echo.
    echo ATTENZIONE: pip-audit ha trovato potenziali vulnerabilita'.
    echo Leggi bene l'output sopra e valuta se aggiornare alcune dipendenze.
) else (
    echo Nessuna vulnerabilita' nota trovata nelle dipendenze.
)

echo.
echo Controllo sicurezza completato.
echo ==============================

pause