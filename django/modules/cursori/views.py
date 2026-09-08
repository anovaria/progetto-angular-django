from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages

from . import services

"""
Modulo views per il terminale palmare (cursori).

Gestisce le funzionalità del terminale palmare aziendale:
  - Consultazione dettaglio articolo tramite scansione EAN
  - Stampa frontalini (raccolta articoli in una coda di sessione, invio alla stampante)

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
    return render(request, 'cursori/home.html')


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


@require_POST
def stampa_invia_email(request):
    """Invia la coda di stampa frontalini via email all'indirizzo indicato dall'operatore.

    Si affianca alla stampa fisica (STAMPA): stessa logica di esito/pulizia coda.
    Solo POST consentito (decoratore @require_POST).
    """
    token = services.get_or_create_token(request, 'cursori_stampa_token')
    email = request.POST.get('email', '')
    esito = services.stampa_invia_email(token, email)
    if esito == 'Inviata':
        services.reset_token(request, 'cursori_stampa_token')
        return redirect('cursori:home')
    return render(request, 'cursori/vedi_stampa.html', {
        'token':  token,
        'items':  list(services.stampa_get_items(token)),
        'errore': f'Errore invio: {esito}',
    })
