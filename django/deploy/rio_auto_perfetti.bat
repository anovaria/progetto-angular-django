@echo off
REM ============================================================================
REM  Riordino Fornitori AUTOMATICO - PILOTA Perfetti (DRY-RUN)
REM ----------------------------------------------------------------------------
REM  Lanciato da Windows Task Scheduler su Srv-Dev1 (dove gira il portale).
REM  Sostituisce - in parallelo, per validazione - il task legacy di srviis per
REM  Perfetti (CCOM 807764 / 807765, cadenza Lun+Gio 07:00).
REM
REM  CANALE: --canale central riproduce il comportamento storico di questo task
REM  legacy (@dove='Central' -> ordine reale diretto in Gold via SIL_Rio, non
REM  Dashboard). Vedi rio_auto.py per i dettagli.
REM
REM  DRY-RUN: la SP calcola la proposta e genera il CSV, viene mandata la mail di
REM  riepilogo, ma NON si invia nulla a Gold (SFTP/Oracle saltati).
REM  Serve a confrontare il CSV con quello prodotto da srviis prima del cutover.
REM
REM  NB: la SP OrdineFornitore_Dash gira davvero anche in dry-run (consuma seqord,
REM  aggiorna t_masterfornrio su srviisnew). Nessun effetto su srviis (server DB
REM  diverso), quindi puo' girare in parallelo al task legacy senza interferenze.
REM
REM  Al cutover reale: cambiare --dry-run in --no-dry-run e assicurarsi che le
REM  variabili RIO_DASH_SFTP_PASS / RIO_DASH_ORACLE_PASS siano visibili a questo
REM  processo (impostarle qui sotto con "set", oppure come variabili di sistema).
REM ============================================================================
setlocal

REM Cartella django = cartella superiore a questo .bat (deploy\..). Location-relative:
REM lo stesso file funziona nel deploy di test e in quello di prod, senza percorsi cablati.
cd /d "%~dp0.."

REM Ambiente Django rilevato dal percorso del deploy (test e prod sullo stesso host):
REM se il path contiene "PortaleTest" -> test, altrimenti -> prod.
echo "%CD%" | find /I "PortaleTest" >nul && (set DJANGO_ENV=test) || (set DJANGO_ENV=prod)

REM Il modulo settings e' SEMPRE prod.py: non esiste settings/test.py. L'ambiente di
REM test = prod.py + DJANGO_ENV=test (dentro prod.py, ENV=test seleziona il DB
REM DjangoIntranet-test). Va impostato esplicitamente, altrimenti manage.py costruisce
REM project_core.settings.<DJANGO_ENV> e con DJANGO_ENV=test cerca un modulo inesistente.
set DJANGO_SETTINGS_MODULE=project_core.settings.prod

REM ----------------------------------------------------------------------------
REM  VARIABILI D'AMBIENTE (IMPORTANTE)
REM  Questo processo NON eredita l'ambiente del servizio NSSM: le var vanno date
REM  qui (o come variabili di sistema/utente dell'account che lancia il task).
REM  ATTENZIONE: NON committare password reali in questo file tracciato. Compilare
REM  la copia deployata su Srv-Dev1, con ACL ristrette, oppure usare variabili di
REM  sistema. Recuperare i valori dal servizio: nssm get Djangoportaltest AppEnvironmentExtra
REM
REM  Cartella di salvataggio copia CSV: stesso posto del vecchio flusso legacy
REM  (bcp + trasffilerioDash.exe scrivevano in C:\C3\riordino\riofo\ su srviisnew),
REM  sottocartella dedicata per non mischiare coi file dell'exe. Richiede che
REM  l'account del task (adminalessandro) abbia Change sulla share \\srviisnew\riordino
REM  (share-level, verificato 14/07/2026 - vedi anche SRV-DEV1$ per il servizio NSSM).
set RIO_DASH_DRY_RUN_DIR=\\srviisnew\riordino\riofo\portale\
REM
REM  Necessarie SEMPRE (connessione a srviisnew):
REM    set DB_GOLD_NAME=Db_GoldReport
REM    set DB_GOLD_USER=<django_user>
REM    set DB_GOLD_PASSWORD=<password>
REM    set DB_GOLD_HOST=172.17.10.52
REM    set DB_DEFAULT_NAME=<db_app>
REM    set DB_DEFAULT_USER=<user>
REM    set DB_DEFAULT_PASSWORD=<password>
REM    set DB_DEFAULT_HOST=172.17.10.52
REM
REM  Necessarie SOLO al cutover reale (--no-dry-run): invio a Gold
REM    set RIO_DASH_SFTP_PASS=<password_sftp>
REM    set RIO_DASH_ORACLE_PASS=<password_oracle>
REM ----------------------------------------------------------------------------

REM Parametri allineati allo script legacy del task srviis per Perfetti:
REM   OrdineFornitore_04_dash @ggcons=3 @ggcop=7 @tipOrd=0 @perc=50
REM (@perc e @ggcop sono ininfluenti con @tipOrd=0 / fornitore esistente; si passano
REM  comunque per fedelta'. @ggcons=3 invece conta: fissa la data consegna a +3 gg.)
REM Per il CUTOVER reale: cambiare --dry-run in --no-dry-run.
set RIO_AUTO_MAIL_TO=matteo.boccarella@groscidac.it
set RIO_AUTO_MAIL_CC=tecnico@groscidac.it
venv\Scripts\python.exe manage.py rio_auto --ccom 807764,807765 --gg-cons 3 --gg-cop 7 --canale central --no-dry-run

REM Propaga il codice di uscita del comando a Task Scheduler (0 = ok, !=0 = errori).
exit /b %ERRORLEVEL%
