from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from . import services

"""
Modulo views per il terminale palmare (cursori).

Gestisce le funzionalità del terminale palmare aziendale:
  - Consultazione dettaglio articolo tramite scansione EAN
  - Stampa frontalini (raccolta articoli in una coda di sessione, invio alla stampante)
  - Lista inventario (rilevazione quantità a scaffale per sessione di inventario)

Ogni vista utilizza un token di sessione univoco per isolare le code di lavoro
dell'operatore corrente. Il token viene creato automaticamente se assente.
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_ip(request) -> str:
    """Restituisce l'indirizzo IP del client.

    Se la richiesta passa attraverso uno o più proxy (header X-Forwarded-For),
    viene estratto il primo IP della catena (IP originale del client).
    In assenza di proxy, si usa REMOTE_ADDR.
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

def home(request):
    """Menu principale terminale."""
    return render(request, 'cursori/home.html', {
        'pos_enabled': settings.CURSORI_POS_ENABLED,
    })


# ---------------------------------------------------------------------------
# Dettaglio articolo (solo consultazione)
# ---------------------------------------------------------------------------

def dettaglio(request):
    """Visualizza i dati di un articolo tramite scansione EAN (sola lettura).

    In caso di POST, cerca l'articolo per EAN e lo mostra nella pagina.
    Non modifica nessun dato: è una funzione di pura consultazione.
    """
    ctx = {'articolo': None, 'errore': None, 'ean': ''}

    if request.method == 'POST':
        ean = request.POST.get('ean', '').strip()
        ctx['ean'] = ean

        # Validazione: il codice deve essere composto solo da cifre
        if not ean.isdigit():
            ctx['errore'] = 'Codice non valido'
        else:
            # Ricerca per EAN; se non trovato, ripiega su CODART (stesso campo)
            art = services.get_articolo_by_ean(ean)
            if not art:
                art = services.get_articolo_by_codart(ean)
            if art:
                ctx['articolo'] = art
            else:
                ctx['errore'] = 'EAN / Cod. art. non trovato'

    return render(request, 'cursori/dettaglio.html', ctx)


# ---------------------------------------------------------------------------
# Stampa frontalini
# ---------------------------------------------------------------------------

def stampa(request):
    """Gestisce la coda di stampa frontalini per la sessione corrente.

    Flusso principale:
      - azione='scan': aggiunge l'articolo scansionato alla coda di stampa,
        poi reindirizza (Post/Redirect/Get) per evitare il doppio invio.
      - azione='nuova': azzera il token di sessione e svuota la coda.
      - GET: mostra il form di scansione con la coda attuale.

    Il token identifica la sessione dell'operatore e isola la sua coda
    da quelle di altri operatori connessi simultaneamente.
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    ip    = _get_ip(request)
    ctx = {
        'token':    token,
        'errore':   None,
        'msg':      None,
        'articolo': None,
        'ean':      '',
        'qta':      '1',
        'coda':     [],
    }

    if request.method == 'POST':
        azione = request.POST.get('azione', '')
        ean    = request.POST.get('ean', '').strip()

        if azione == 'scan':
            if not ean.isdigit():
                ctx['errore'] = 'Codice non valido'
            else:
                # Ricerca per EAN; se non trovato, ripiega su CODART (stesso campo)
                art = services.get_articolo_by_ean(ean)
                if not art:
                    art = services.get_articolo_by_codart(ean)
                if art:
                    # Aggiunge l'articolo alla coda di stampa con quantità 1
                    # e salva un messaggio di conferma in sessione per mostrarlo dopo il redirect
                    services.stampa_add_articolo(
                        token, ip, art,
                        1,
                    )
                    request.session['cursori_stampa_msg'] = f"+ {art['descrizione'][:32]}"
                    return redirect('cursori:stampa')
                else:
                    ctx['errore'] = 'EAN / Cod. art. non trovato'

        elif azione == 'nuova':
            # Azzera la coda corrente resettando il token di sessione
            services.reset_token(request, 'cursori_stampa_token')
            return redirect('cursori:stampa')

    # Recupera il messaggio di conferma dalla sessione (impostato dopo scan riuscito)
    ctx['msg']  = request.session.pop('cursori_stampa_msg', None)
    ctx['coda'] = list(services.stampa_get_items(token))
    return render(request, 'cursori/stampa.html', ctx)


def stampa_preview(request):
    """Mostra l'anteprima di stampa degli articoli nella coda corrente.

    Pagina ottimizzata per la stampa su carta (layout pulito senza UI terminale).
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    items = services.stampa_get_items(token)
    return render(request, 'cursori/stampa_preview.html', {
        'items': list(items),
        'token': token,
    })


def vedi_stampa(request):
    """Mostra la coda di stampa corrente con possibilità di modificare le quantità.

    L'operatore può rivedere gli articoli in coda, modificarne la quantità
    o eliminarli prima di procedere con la stampa definitiva.
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    items = services.stampa_get_items(token)
    ctx = {
        'token': token,
        'items': list(items),
    }
    return render(request, 'cursori/vedi_stampa.html', ctx)


@require_POST
def stampa_salva_qta(request):
    """Aggiorna le quantità degli articoli in coda di stampa.

    Elabora tutti i campi del form con nome 'qta_<pk>',
    validando che siano numerici e impostando a 0 i valori negativi.
    Solo POST consentito (decoratore @require_POST).
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    for key, val in request.POST.items():
        if key.startswith('qta_'):
            pk = key[4:]
            # Valida che sia un ID numerico e che il valore sia un intero (anche negativo temporaneamente)
            if pk.isdigit() and val.strip().lstrip('-').isdigit():
                # Imposta la quantità minima a 0 (non si accettano quantità negative)
                services.stampa_aggiorna_qta(int(pk), token, max(0, int(val.strip())))
    return redirect('cursori:vedi_stampa')


@require_POST
def stampa_cancella(request):
    """Rimuove un singolo articolo dalla coda di stampa tramite il suo PK.

    Solo POST consentito (decoratore @require_POST).
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    pk    = request.POST.get('pk')
    if pk and pk.isdigit():
        services.stampa_cancella_item(int(pk), token)
    return redirect('cursori:vedi_stampa')


# ---------------------------------------------------------------------------
# Lista inventario
# ---------------------------------------------------------------------------

def lista(request):
    """Gestisce la rilevazione di inventario da terminale palmare.

    Flusso in tre fasi per ogni articolo:
      1. azione='scan': cerca l'articolo per EAN e lo mostra per la conferma.
      2. azione='ok': conferma l'aggiunta con la quantità inserita dall'operatore.
      3. azione='nuova': azzera la lista (nuovo giro di inventario).

    Il totale articoli rilevati viene mostrato nel titolo della pagina.
    """
    token = services.get_or_create_token(request, 'cursori_lista_token')
    ctx = {
        'token':    token,
        'errore':   None,
        'msg':      None,
        'articolo': None,
        'ean':      '',
        'qta':      '1',
        'items':    [],
        'totale':   0,
    }

    if request.method == 'POST':
        azione = request.POST.get('azione', '')
        ean    = request.POST.get('ean', '').strip()
        ctx['ean'] = ean

        if azione == 'scan':
            if not ean.isdigit():
                ctx['errore'] = 'Codice non valido'
            else:
                # Ricerca per EAN; se non trovato, ripiega su CODART (stesso campo)
                art = services.get_articolo_by_ean(ean)
                if not art:
                    art = services.get_articolo_by_codart(ean)
                if art:
                    ctx['articolo'] = art
                else:
                    ctx['errore'] = 'EAN / Cod. art. non trovato'

        elif azione == 'ok':
            # Conferma l'aggiunta dell'articolo con la quantità inserita
            codart = request.POST.get('codart', '').strip()
            qta    = request.POST.get('qta', '1').strip()
            art    = services.get_articolo_by_ean(ean) if ean else None
            if not art and ean:
                art = services.get_articolo_by_codart(ean)
            if art and codart:
                services.lista_add_articolo(token, art, qta)
                request.session['cursori_lista_msg'] = f"+ {art['descrizione'][:32]}"
            return redirect('cursori:lista')

        elif azione == 'nuova':
            # Svuota la lista corrente e ricomincia da capo
            services.reset_token(request, 'cursori_lista_token')
            return redirect('cursori:lista')

    # Recupera il messaggio di conferma dalla sessione e popola il contesto
    ctx['msg']    = request.session.pop('cursori_lista_msg', None)
    ctx['items']  = services.lista_get_items(token)
    ctx['totale'] = services.lista_conta(token)
    return render(request, 'cursori/lista.html', ctx)


@require_POST
def lista_cancella(request):
    """Rimuove un articolo dalla lista inventario tramite il codice articolo.

    Solo POST consentito (decoratore @require_POST).
    """
    token  = services.get_or_create_token(request, 'cursori_lista_token')
    codart = request.POST.get('codart', '').strip()
    if codart:
        services.lista_cancella_articolo(token, codart)
    return redirect('cursori:lista')


@require_POST
def lista_chiudi(request):
    """Chiude la sessione di inventario: salva i dati definitivamente e azzera il token.

    Dopo la chiusura l'operatore viene reindirizzato al menu principale.
    Solo POST consentito (decoratore @require_POST).
    """
    token = services.get_or_create_token(request, 'cursori_lista_token')
    services.lista_chiudi(token)
    # Resetta il token in modo che la prossima apertura parta da una lista pulita
    services.reset_token(request, 'cursori_lista_token')
    return redirect('cursori:home')


@require_POST
def stampa_invia(request):
    """Invia la coda di stampa al servizio di stampa frontalini.

    Se l'invio ha successo ('Inviata'), azzera il token e torna al menu.
    In caso di errore, rimanda alla pagina vedi_stampa con il messaggio di errore.
    Solo POST consentito (decoratore @require_POST).
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    ip    = _get_ip(request)
    esito = services.stampa_invia(token, ip)
    if esito == 'Inviata':
        # Invio riuscito: pulizia della coda di sessione
        services.reset_token(request, 'cursori_stampa_token')
        return redirect('cursori:home')
    # Invio fallito: rimane nella pagina con il messaggio di errore
    return render(request, 'cursori/vedi_stampa.html', {
        'token':  token,
        'items':  list(services.stampa_get_items(token)),
        'errore': f'Errore invio: {esito}',
    })


# ---------------------------------------------------------------------------
# Posizione articoli (riordino automatico PDV)
# ---------------------------------------------------------------------------

def pos_articoli(request):
    """Scansione EAN e gestione posizione articolo per il riordino automatico PDV.

    Porting di PosArticoli.aspx (web service mainWsAllArticolo.PosArticoli):
      - azione='scan'  : cerca l'articolo, legge la posizione autentica da srviis
        e inserisce una bozza (Elab=''); in modo 'togli' smappa subito (Elab='D').
      - azione='ok'    : conferma la posizione (Capienza=Max=qta, MinimoRio=Max-Min,
        Elab='1'). Richiede qta e Min numerici.
      - azione='clr'   : cancella la bozza (o la riga smappata in modo 'togli').
      - azione='nuova' : nuova sessione (nuovo token).

    Le scritture vanno su t_posArticoli su GoldCursori srviis via services.pos_salva.
    """
    # Funzione disattivata (es. produzione finché non è pronto il nuovo riordino):
    # nasconde l'accesso anche a chi digita l'URL a mano. Vedi CURSORI_POS_ENABLED.
    if not settings.CURSORI_POS_ENABLED:
        return redirect('cursori:home')

    token = services.get_or_create_token(request, 'cursori_pos_token')
    ctx = {
        'token':    token,
        'errore':   None,
        'msg':      request.session.pop('cursori_pos_msg', None),
        'articolo': None,
        'pos':      None,
        'modo':     request.POST.get('modo', 'normale'),
        'ean':      '',
        'qta':      '',
    }

    if request.method == 'POST':
        azione = request.POST.get('azione', '')

        if azione == 'nuova':
            services.reset_token(request, 'cursori_pos_token')
            return redirect('cursori:pos_articoli')

        if azione == 'scan':
            ean = request.POST.get('ean', '').strip()
            ctx['ean'] = ean
            if not ean.isdigit():
                ctx['errore'] = 'Codice non valido'
            else:
                # Ricerca per EAN; se non trovato, ripiega su CODART (stesso campo)
                art = services.get_articolo_by_ean(ean)
                if not art:
                    art = services.get_articolo_by_codart(ean)
                if not art:
                    ctx['errore'] = 'EAN / Cod. art. non trovato'
                else:
                    pos = services.get_posizione_riordino(art['codart'])
                    # pz/cartone autentico da t_masterData (come il vecchio app)
                    if pos.get('pzxcrt'):
                        art['pz_xcrt'] = pos['pzxcrt']
                    # Gest da t_masterData come fallback (sovrascritto da Oracle sotto)
                    art['gest'] = pos.get('gest', '')
                    # normalizza le giacenze a intero per la visualizzazione (15.0 -> 15)
                    for _k in ('giac_pdv', 'giac_dep'):
                        try:
                            art[_k] = str(int(float(art.get(_k, '0'))))
                        except (ValueError, TypeError):
                            pass
                    # giacenze + Gest LIVE da Oracle GOLDPROD (come il vecchio app); fallback ETL
                    o = services.get_dati_oracle(art['codart'])
                    if o:
                        art['giac_pdv'] = str(o['giac_pdv'])
                        art['giac_dep'] = str(o['giac_dep'])
                        if o['gest']:
                            art['gest'] = o['gest']
                    if ctx['modo'] == 'togli':
                        # Smappa dal riordino (azione 2)
                        services.pos_salva(token, art, pos['corsia'], pos['campata'],
                                           pos['facing'], '1', '', '1', '2')
                        request.session['cursori_pos_msg'] = f"Smappato: {art['descrizione'][:28]}"
                        return redirect('cursori:pos_articoli')
                    # Modo normale: inserisce bozza (azione 0) e mostra per conferma
                    services.pos_salva(token, art, pos['corsia'], pos['campata'],
                                       pos['facing'], '', '', '', '0')
                    ctx['articolo'] = art
                    ctx['pos'] = pos

        elif azione == 'ok':
            art = {
                'codart':      request.POST.get('codart', '').strip(),
                'descrizione': request.POST.get('descrizione', ''),
                'stato':       request.POST.get('stato', ''),
                'pz_xcrt':     request.POST.get('pz_xcrt', ''),
                'ean':         request.POST.get('ean_art', ''),
            }
            corsia  = request.POST.get('corsia', '').strip()
            campata = request.POST.get('campata', '').strip()
            facing  = request.POST.get('facing', '').strip()
            qta     = request.POST.get('qta', '').strip()
            minimo  = request.POST.get('minimo', '').strip()

            if not (qta.isdigit() and minimo.isdigit() and art['codart'].isdigit()):
                ctx['errore'] = 'Qta / Min non validi'
                ctx['articolo'] = art
                ctx['pos'] = {'corsia': corsia, 'campata': campata, 'facing': facing,
                              'minimo': minimo, 'massimo': qta}
                ctx['qta'] = qta
            else:
                # Capienza = Max = qta ; MinimoRio = Max - Min (calcolato nel service)
                esito = services.pos_salva(token, art, corsia, campata, facing,
                                           qta, minimo, qta, '1')
                request.session['cursori_pos_msg'] = esito
                return redirect('cursori:pos_articoli')

        elif azione == 'clr':
            art = {'codart': request.POST.get('codart', '').strip(),
                   'ean':    request.POST.get('ean_art', '')}
            corsia  = request.POST.get('corsia', '').strip()
            campata = request.POST.get('campata', '').strip()
            facing  = request.POST.get('facing', '').strip()
            azione_clr = '3' if ctx['modo'] == 'togli' else '4'
            services.pos_salva(token, art, corsia, campata, facing, '', '', '', azione_clr)
            request.session['cursori_pos_msg'] = 'Eliminato'
            return redirect('cursori:pos_articoli')

    return render(request, 'cursori/pos_articoli.html', ctx)


def vedi_pos_articoli(request):
    """Coda delle posizioni inserite nella sessione corrente (porting VediPosArticoli.aspx)."""
    if not settings.CURSORI_POS_ENABLED:
        return redirect('cursori:home')
    token = services.get_or_create_token(request, 'cursori_pos_token')
    return render(request, 'cursori/vedi_pos_articoli.html', {
        'token': token,
        'items': services.pos_get_items(token),
    })
