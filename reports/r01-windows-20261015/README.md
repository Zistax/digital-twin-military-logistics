# Verifica supplementare R01 su Windows

Il pacchetto originale R01 e i rapporti Linux sono stati recuperati dall'esecuzione interrotta. ZIP e tutti i 250 file inclusi sono stati verificati tramite SHA256; vedere `../r01-recovery-20261015/integrity.json`. Il pacchetto originale resta invariato.

Su CPython 3.12.14 / Windows AMD64, in un ambiente virtuale dedicato con le dipendenze bloccate:

- Smoke nativo passato: missioni, retry, scadenza esatta, previsione periodica, annullamento, rifiuto del modello non promosso e recupero manuale.
- API e Streamlit avviati come processi reali su loopback; prova AppTest collegata all'API HTTP passata, con creazione sessione/missione, avanzamento, aggiornamento e chiusura. Entrambi i processi sono stati arrestati dal launcher.
- Quattro test di rilascio passati. La prova che crea un symlink è bloccata da Windows (`WinError 1314`, privilegio non disponibile), prima di esercitare il rifiuto del pacchetto. Non è conteggiata come passata. Il rifiuto dei symlink resta verificato dalla suite Linux originale.
- Ruff sui nuovi script e file di rilascio passato.

Questa verifica aggiuntiva non sostituisce i 353 test e 16 sotto-test della suite Linux originale. Non verifica il programma di installazione `setup_local.py` su Windows: il runtime incorporato disponibile non ha completato `ensurepip`, quindi le dipendenze sono state installate usando un pip esterno diretto al nuovo ambiente virtuale. macOS resta non verificato.

Il primo tentativo dei server nell'ambiente limitato è andato in timeout; la ripetizione fuori da tale ambiente ha completato l'intero flusso. I file `smoke.json` e `servers.json` conservano gli esiti riusciti. Nessun modello promosso; nessuna pubblicazione online.
