# Changelog — Portale Intranet

Tutte le modifiche rilevanti al portale, in ordine cronologico inverso (la più recente in alto).
Linguaggio orientato alla funzionalità: il dettaglio tecnico è nel codice e nella documentazione
(`Z:\Progetti IT\2026\Portale\Architettura\`).

Categorie usate: **Nuovo** (funzionalità), **Modificato**, **Corretto**, **Documentazione**.

*Changelog e documentazione redatti da A. Novaria con l'assistenza di **Claude Code** (Claude — Anthropic).*

---

## 2026-06-15

### Modificato
- **Piano Promo — si vede di nuovo "tutto".** Rimossa la deduplicazione per priorità
  (EXPO > EXPO-COLLI > COLLI) introdotta a inizio giugno, che teneva una sola riga per
  articolo facendo sparire le altre occorrenze. Ora la riga è identificata dalla combinazione
  **articolo + piano + codice expo + ordine in corso**: lo stesso articolo compare su righe
  distinte per ogni piano, per ogni **testa espositore (Cod. Art. Expo)** e per ogni tipo di
  ordine (EXPO, COLLI, ...), come nella versione originale. Le sessioni esistenti recuperano
  le righe mancanti al primo "Aggiorna lista", senza perdere stato e note di quelle già presenti.
- **Piano Promo — ordinamento staging per Cod. Art. Expo.** La tabella di dettaglio ordina ora
  anche per codice expo (dopo piano, fornitore e articolo): le diverse teste espositore dello
  stesso articolo compaiono consecutive.

### Nuovo
- **Piano Promo — filtro fornitore nel dettaglio.** Nell'intestazione della colonna *Fornitore*
  c'è un campo di ricerca che nasconde al volo le righe che non corrispondono (ricerca per
  testo, senza ricaricare la pagina); convive con il pulsante "Nascondi Ordinato".

## 2026-06-12

### Modificato
- **Piano Promo — sessioni su più piani.** "Aggiungi articoli" su una sessione esistente ora
  **accumula** i piani Gold nei parametri salvati invece di sostituirli: "Aggiorna lista"
  riesegue la query su tutti i piani mai aggiunti alla sessione, senza più perdere gli
  articoli dei piani precedenti.
- **Piano Promo — una riga per articolo e piano.** Rivista la deduplicazione introdotta il
  02/06, che teneva una sola riga per articolo anche quando l'articolo era presente in più
  piani (facendo "sparire" le altre occorrenze): ora lo stesso articolo presente in più piani
  occupa una riga per piano, ciascuna con il proprio stato/nota. La deduplicazione resta solo
  per i veri doppioni (stesso articolo nello stesso piano), dove vince la riga con priorità
  EXPO > EXPO-COLLI > COLLI. Per le sessioni esistenti che avevano perso righe basta
  "Aggiorna lista" (se il piano è ancora tra le promo future); stati e note delle righe
  eliminate a suo tempo non sono recuperabili.
- **Piano Promo — contatore totale articoli.** Accanto ai contatori ordinati / da ordinare /
  neutri, sia nella lista sessioni sia nel dettaglio, ora compare anche il totale articoli
  della sessione.

## 2026-06-11

### Nuovo
- **Assortimento Abbig — nuova app per l'assortimento abbigliamento.** Sostituisce il flusso
  manuale con cui gli utenti preparavano il report assortimento: copia-incolla di 11 colonne
  in un Excel temporaneo e macro (`Inser_Row.xlsm`) per inserire le righe vuote di annotazione.
  L'app legge la vista `v_abbigliamento` (GoldReport, rigenerata ogni mattina) e offre:
  - **filtri a cascata** Reparto → Fornitore → CCOM (con descrizione); dopo "Visualizza"
    compaiono anche i filtri Linea e Collezione, che si riapplicano al volo;
  - **staging raggruppato per linea** con checkbox per articolo e per intera linea e bottone
    "Sposta in fondo i selezionati" per riordinare la lista prima della stampa (se si sposta
    una linea completa, si sposta anche la sua intestazione);
  - **report stampabile dal browser** che rispetta l'ordine dello staging: righe vuote per le
    annotazioni a mano (numero configurabile 0–10), colori alternati per blocco articolo,
    riga di separazione in grassetto tra gli articoli, scala di stampa all'85% (come il
    vecchio layout Excel, che il driver di stampa non permetteva più di impostare) e piè di
    pagina con il solo numero di pagina ("1 di 2") al posto di URL/data/titolo del browser
    (richiede Edge/Chrome aggiornati, versione 131+).
  Niente più file Excel intermedi né macro. Visibile ai gruppi `abbigliamento` e `itd`.
  Installata in produzione e validata dagli utenti.

### Modificato
- **Carico Promo Reparto — modal "Articoli Inseriti" multi-operatore.** Il modal mostra ora
  gli articoli accodati da tutti gli operatori, distinguendo i propri da quelli altrui:
  si possono rimuovere le **singole righe** (solo le proprie, con la X a fine riga) e il
  bottone "Svuota tutto" è diventato **"Svuota miei"** (rimuove solo gli articoli inseriti
  dall'utente corrente, senza più cancellare il lavoro dei colleghi). Tabella più compatta
  (intestazioni fisse, testo troncato con ellissi) e stampa in orizzontale con numerazione
  pagine "N di M" al posto di URL/data del browser.
- **Stampa Offerte Future — eliminati i doppioni.** Un articolo presente a listino con più
  fornitori compariva più volte nella lista; ora viene mostrata una sola riga per
  articolo/piano.

### Corretto
- **Riordino Fornitori NEW [TEST] — falsi errori sull'esito dell'import Oracle.** Il portale
  trattava come errore il parametro diagnostico `P_F_ERR` della procedura Gold `sil_rioDash`,
  che però viene valorizzato anche sui successi (es. "FASE 2: COMPLETATA"): un import riuscito
  poteva essere segnalato come fallito. Allineata l'interpretazione a quella del vecchio
  eseguibile (analisi del sorgente PL/SQL, vedi Documentazione del 09/06): l'esito si giudica
  sull'assenza di eccezione e sul codice numerico `Stato` (0/1 = fallimento inequivocabile),
  mentre `P_F_ERR` viene solo registrato nei log come messaggio diagnostico.

## 2026-06-09

### Corretto
- **Cursori — Stampa Frontalini: le liste lunghe stampavano solo la prima pagina.** Inviando
  in stampa una coda che occupava più di un foglio, ne usciva una sola pagina e gli articoli
  successivi venivano persi. Causa: la routine di stampa non gestiva il salto pagina e tutto
  ciò che superava l'altezza del foglio veniva tagliato. Aggiunta la paginazione: al
  riempimento del foglio si passa automaticamente a una nuova pagina, ristampando titolo e
  intestazione delle colonne.
- **Cursori — Stampa Frontalini: errore nell'aggiungere articoli alla coda.** Scansionando
  un articolo la pagina poteva andare in errore (`MultipleObjectsReturned`), bloccando
  l'operatore. Causa: in coda potevano formarsi righe duplicate dello stesso articolo
  (scansioni concorrenti / doppio invio) e la logica di inserimento non gestiva il caso.
  Corretta la funzione di aggiunta articolo: ora aggiorna la riga esistente e rimuove
  automaticamente eventuali doppioni pregressi, auto-pulendo la coda senza interventi sul
  database.
- **Riordino Fornitori NEW [TEST] — l'invio reale a Gold non partiva.** Sul servizio di test
  l'invio restava bloccato in dry-run (generava solo il CSV) nonostante la configurazione
  fosse impostata per l'invio reale. Causa: nella variabile d'ambiente del servizio (NSSM)
  era stato scritto `RIO_DASH_DRY_RUN   = 0` con spazi attorno all'`=`; NSSM non rimuove gli
  spazi, quindi la variabile veniva creata con un nome errato e il portale ripiegava sul
  default sicuro (dry-run). Corretta la riga in `RIO_DASH_DRY_RUN=0` e riavviato il servizio:
  la proposta viene ora trasferita realmente a Gold (CSV → SFTP → import Oracle → script finale).

### Documentazione
- Aggiunta alla guida operativa la voce di troubleshooting "resta in dry-run anche con
  `RIO_DASH_DRY_RUN=0`": gli spazi attorno all'`=` nell'ambiente NSSM invalidano la variabile,
  e l'ambiente NSSM viene letto solo al riavvio del servizio.
- **Riordino Fornitori — documentato il sorgente della procedura Oracle `sil_rioDash`.**
  Recuperato da Gold e inserito nel documento di migrazione (§9.7) il sorgente PL/SQL completo
  della procedura che importa la proposta d'ordine su Gold, con la mappa del flusso interno e
  la spiegazione della semantica dei suoi esiti (`Stato`/`P_F_ERR`). Questo chiarisce perché il
  portale giudica l'esito sul codice `Stato` (e non sul messaggio diagnostico) e copre il primo
  dei prerequisiti per l'eventuale futura scrittura diretta su Oracle senza file/SP/script.

## 2026-06-08

### Modificato
- **Posizione Articoli e Parametri Rio nascoste in produzione.** Su indicazione della
  direzione (il vecchio riordino automatico PDV non va più usato), le due funzioni legate
  al vecchio riordino sono state disattivate in produzione: la voce "Posizione Articoli"
  sparisce dal menu del palmare e "Parametri Rio" dal menu del portale, e l'accesso diretto
  agli indirizzi è bloccato. Il codice resta in piedi: potranno essere riattivate (anche solo
  in ambiente di test per lo sviluppo) tramite due interruttori di configurazione
  (`CURSORI_POS_ENABLED`, `RIO_PDV_ENABLED`), in vista del nuovo riordino.

### Documentazione
- Prodotta l'analisi tecnica as-is del vecchio sistema di riordino automatico PDV
  (app TestRAzor4, web service `mainWsAllArticolo`, database GoldCursori su srviis, batch
  `updGlob`), con sintesi per la direzione: `Z:\Progetti IT\2026\Portale\Analisi-preventivi\
  Analisi-Vecchio-Riordino.md`.
- Aggiornata la documentazione tecnica (variabili d'ambiente, menu, endpoint) con i due
  interruttori `CURSORI_POS_ENABLED` / `RIO_PDV_ENABLED`.
- Mappate le tabelle/viste che il portale legge da srviisnew (Db_GoldReport, Db_Category,
  goldcursori): per ognuna chi la consuma, come viene popolata (job SQL Server Agent →
  stored procedure `GrosCidac.dbo.task_*` → `sp_Create_*`) e con che cadenza. Evidenziate le
  dipendenze residue dal vecchio server srviis. Documento:
  `Z:\Progetti IT\2026\Portale\Analisi-preventivi\05-tabelle-srviisnew-etl.md`.
- Prodotto il "ricettario" delle query Oracle dell'ETL (`06-etl-query-oracle.md`): per ogni
  tabella le sorgenti Oracle e la logica di popolamento, il motore `sp_Importa_Tabella_DaGold`,
  l'orchestrazione job → `task_*` → `sp_Create_*` e la scheda integrale di `t_masterData`.

## 2026-06-06

### Documentazione
- Aggiornata la documentazione tecnica (01-architettura, 02-database, 03-api, 04-guide)
  con i moduli Riordino Fornitori NEW, Parametri Rio e la funzione Posizione Articoli.

## 2026-06-04

### Nuovo
- **Riordino Fornitori [TEST] — trasferimento a Gold in Python.** Il modulo `rio_fornitori_new`
  ora genera la proposta su srviisnew e invia il file a Gold (CSV → SFTP → import Oracle → script
  finale) direttamente dal portale, sostituendo il vecchio eseguibile `trasffilerioDash.exe`.
  Parte in **dry-run** (genera solo il CSV) finché non si abilita l'invio reale.
- **Parametri Rio (`riordino_pdv`).** Nuova pagina (solo ITD) che mostra in sola lettura la
  schedulazione settimanale del riordino automatico PDV.
- **Posizione Articoli nei Cursori.** Porting della vecchia funzione ASP.NET (TestRAzor4):
  scan e conferma della posizione degli articoli per il riordino automatico PDV, con giacenze
  e unità di gestione live da Oracle. Anche questa con guardia dry-run sulle scritture.

## 2026-06-02

### Nuovo
- **Riordino Fornitori [TEST] (`rio_fornitori_new`).** Prima versione del modulo su srviisnew:
  ricerca fornitore per CCOM, parametri proposta, lancio della stored procedure e gestione delle
  email di notifica del fornitore.

### Modificato
- Piano Promo: aggiustamenti alla logica delle viste.
- Carico Promo Reparto: migliorie alla schermata principale.

## 2026-05-28

### Modificato
- Welfare: aggiornamenti alle schermate (contabilità, dashboard, lista da consegnare,
  ricerca voucher, storico consegne).
- Asso Articoli: refactor delle viste.
- Piano Promo: aumentata la lunghezza massima del campo "gold".

## 2026-05-23

### Corretto
- Riordino Fornitori: corretto l'errore nell'invio della mail di riordino.

### Modificato
- Carico Promo Reparto e ImportElab (sync verso Gold): migliorie e correzioni minori.
- Scarico Promo: aggiornamento dello storico.
