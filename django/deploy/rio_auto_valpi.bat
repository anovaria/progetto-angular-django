@echo off
REM ============================================================================
REM  Riordino Fornitori AUTOMATICO - PILOTA Valpi Alimentare (DRY-RUN)
REM ----------------------------------------------------------------------------
REM  Lanciato da Windows Task Scheduler su Srv-Dev1 (dove gira il portale).
REM  Sostituisce - in parallelo, per validazione - il task legacy di srviis per
REM  Valpi Alimentare (CCOM 805387).
REM
REM  NB CADENZA: il task legacy gira il LUNEDI' e il GIOVEDI' alle 07:03
REM  -> schedularlo /SC WEEKLY /D MON,THU /ST 07:03 allineando la fase.
REM
REM  DRY-RUN: la SP calcola la proposta e genera il CSV, viene mandata la mail di
REM  riepilogo, ma NON si invia nulla a Gold (SFTP/sil_rioDash/SSH saltati).
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

REM Destinatario mail di riepilogo: silve@ (legacy) e' una casella morta. In attesa
REM di un destinatario dedicato per questo fornitore, si usa la casella tecnico@
REM (sostituisce il default RIO_AUTO_MAIL_TO di test = alessandro.novaria@).
set RIO_AUTO_MAIL_TO=tecnico@groscidac.it

REM Parametri allineati allo script legacy del task srviis per Valpi Alimentare:
REM   OrdineFornitore_04_dash @contrcomme=805387 @ggcons=1 @ggcop=7 @tipOrd=0 @perc=50
REM Con @tipOrd=0 il @perc=50 e' ININFLUENTE (la SP usa Qtaord grezzo, non Qtaord1),
REM quindi NON si passano --tip-ord/--riduzione (default 0).
REM Per il CUTOVER reale: cambiare --dry-run in --no-dry-run.
venv\Scripts\python.exe manage.py rio_auto --ccom 805387 --gg-cons 1 --gg-cop 7 --dry-run

REM Propaga il codice di uscita del comando a Task Scheduler (0 = ok, !=0 = errori).
exit /b %ERRORLEVEL%
