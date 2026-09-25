# Portale — contesto generale

Monorepo Django ("portale") che sostituisce progressivamente app legacy (Access, ASP.NET, macro Excel) con moduli Django, in un percorso di autonomia dal vecchio collega uscito (~2025) e dalle app legacy. Vedi memoria di progetto per lo stato aggiornato di ogni iniziativa.

## Struttura

- `django/project_core/settings/` — `base.py`, `dev.py`, `prod.py`. L'ambiente attivo è determinato da `DJANGO_ENV` (vedi nota NSSM sotto), non dalla sola variabile `DB_DEFAULT_NAME`.
- `django/modules/<nome_app>/` — un'app Django per funzionalità/modulo di business (es. `riordino_pdv`, `ortofrutta`, `ins_articoli`, `ins_art_mass_abbig`, `assortimento_abbig`, `giacenze_negative`, `scaricopromo`, ecc.). Ogni modulo ha tipicamente `views.py`, `services.py`, `templates/<nome_app>/`.
- `deploy/` — script PowerShell di deploy/manutenzione: `deploy-prod.ps1`, `deploy-test.ps1`, `sync-test-from-prod.ps1`, `security-audit.ps1`, `update-requirements.ps1`.

## Infrastruttura (rete)

- `srviisnew` (172.17.10.52) — server principale attuale, destinazione della migrazione da `srviis` (172.17.10.51, legacy).
- `Gold` (172.17.10.41) — sistema esterno (Gold/GoldReport/GoldCursori) con job SQL Agent che alimentano/consumano dati; molte anomalie "misteriose" sono in realtà timing/comportamento lato Gold, non bug del portale — verificare sempre prima lì.
- `Srv-Dev1` (172.17.10.19) — ambiente di sviluppo.
- DB test: `DjangoIntranet-test`. Attenzione: `prod.py` + `DJANGO_ENV=test` scavalca la var NSSM `DB_DEFAULT_NAME`, che quindi è fuorviante se letta da sola.

## Convenzioni

- Naming URL Django: `app_name`/namespace/URL con **trattino**, non underscore (es. `ins-art-mass-abbig`, non `ins_art_mass_abbig`).
- `app_name` in `MENU_CONFIG` è anche la chiave di permesso in `user_app_permissions` — cambiarlo con cautela, impatta i permessi utente.
- Le `print()` del DB attivo in `prod.py` sono volute (per orientarsi in shell) — non rimuoverle.
- NSSM non taglia gli spazi nelle variabili d'ambiente (`CHIAVE = val` rompe il nome della chiave); dopo modifiche va riavviato il servizio per rileggerle.

## Workflow con l'utente

- Rispondere sempre in italiano.
- "Aggiorna la doc" = aggiornare doc tecnica su NAS (Z:\Progetti IT\2026\Portale\Architettura\) + `CHANGELOG.md` + mail di riepilogo al capo.
- Nei test reali su Gold, l'utente vuole essere coinvolto passo passo, non solo bloccato sul write finale.
- Recuperare il "cosa" è successo da git/codice; chiedere all'utente solo il "perché"/contesto esterno non derivabile dal repo.
- Access è dismesso: i dati merchandiser sono gestiti solo dal portale Django, non serve più considerare l'app Access.

## Sessioni per modulo

Questo repo si presta a sessioni Claude Code separate per modulo (nome fisso via `claude -n <nome-app>` o `/rename`, ripresa con `claude --resume <nome-app>` da qualunque cartella del repo). Il contesto trasversale (questo file + la memoria di progetto) è comunque sempre disponibile in ogni sessione, quindi non serve un'unica sessione monolitica per "vedere tutto".
