# Decisioni R02 e stato di P17/P18

Decisioni del 15 ottobre 2026, limitate alla demo sintetica. La richiesta del proprietario è di proseguire offline in assenza di hosting.

| Punto | Decisione implementata | Limite ancora aperto |
|---|---|---|
| P17: API/UI | FastAPI separata dall'API locale completa, quattro viste HTML/JS nello stesso dominio, asset locali; Streamlit R01 conservata | Nessuna migrazione del prodotto locale; ulteriori funzioni di sperimentazione rimangono in R01 |
| P17: persistenza | SQLite locale, transazioni su configurazione, journal e vista; niente pickle delle sessioni | Una replica/un worker, nessun DB distribuito o migrazione automatica |
| P17: esecuzione e retry | API sincrone con comandi brevi, revisioni e retry persistenti; un processo effimero per replay, kill a 20 s | Nessun job remoto di training; gli endpoint non avviano lavori di durata indefinita |
| P17: versionamento | Fingerprint di codice, lock, registro, artefatti ed evidenze; blocco del riuso di sessioni vive fra release differenti | Richiede drain/scadenza e aggiornamento amministrativo, senza adattare i journal al nuovo codice |
| P18: amministratore | Chiave casuale separata, bearer; controlli stato/pulizia remoti; strumenti completi locali preesistenti | Nessuna interfaccia remota di training/configurazione/promozione |
| P18: visitatori | Token casuale effimero, un proprietario per sessione, revoca con cascata, 404 per ID appartenenti ad altri | Non è un sistema di account o multi-tenancy aziendale |
| P18: limiti e retention | Quote numeriche, 30 minuti fissi, pulizia periodica/ripartenza, budget CPU wall-clock e SQLite | La scadenza rende l'accesso inutilizzabile subito; eliminazione fisica forense e policy backup del futuro provider non sono verificate |
| P18: hosting/costi | Pacchetto ZIP offline; container locale Linux amd64 costruito e verificato con base fissata per digest; nessun account né spesa | Provider, dominio, HTTPS, costo e prove nella destinazione da completare prima della pubblicazione |
| P18: prestazioni | Timeout massimo di 20 s e misure HTTP locali incluse nel rapporto | Gli obiettivi p95 sul futuro hosting sono criteri da provare, non risultati ottenuti |

Queste decisioni chiudono il perimetro tecnico **offline** scelto per questa consegna. Non dichiarano il completamento della pubblicazione online della roadmap, la validità predittiva dei modelli o un servizio pronto per utilizzo operativo reale.
