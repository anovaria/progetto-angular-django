"""
services.py — logica di business per l'app cursori.

Contiene:
  - gestione token di sessione
  - lookup articolo su goldreport (v_AllArticolo + v_MasterAssortimenti)
  - lookup posizione da Db_Category (t_masterdataCategory)
  - utilità EAN peso-variabile (prefisso 21)
  - operazioni su StampaCursori
"""
import secrets
import logging
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import connections
from django.utils.html import escape

from .models import StampaCursori
from modules.edicola.models import EdicolaPrincipale

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token / sessione
# ---------------------------------------------------------------------------

def genera_token() -> str:
    """Token univoco a 32 caratteri hex."""
    return secrets.token_hex(16)


def get_or_create_token(request, session_key: str) -> str:
    """
    Restituisce il token attivo memorizzato in sessione per la funzione
    indicata da session_key (es. 'cursori_lista_token').
    Se non esiste lo genera e lo salva.
    """
    token = request.session.get(session_key)
    if not token:
        token = genera_token()
        request.session[session_key] = token
    return token


def reset_token(request, session_key: str) -> str:
    """Forza la creazione di un nuovo token (fine sessione / nuova rilevazione)."""
    token = genera_token()
    request.session[session_key] = token
    return token


# ---------------------------------------------------------------------------
# EAN peso-variabile (prefisso 21)
# ---------------------------------------------------------------------------

def estrai_qta_peso_variabile(ean_str: str) -> str | None:
    """
    Per EAN con prefisso 21 estrae il campo peso (5 cifre) e lo restituisce
    come stringa di 5 caratteri (es. "01200" = 1.200 kg).
    Restituisce None se l'EAN non è peso-variabile.

    Logica identica all'originale ASP.NET:
      - posizioni 7-11 dell'EAN (0-indexed) = campo peso BBBBB
      - "000XX" → grammi
      - "00XXX" → etti (decagrammi)
      - "0XXXX" → kg
      - "XXXXX" → kg > 9
    """
    ean_clean = ean_str.strip()
    if len(ean_clean) < 13:
        return None
    if not ean_clean[:2] == '21':
        return None

    eanpeso = ean_clean[7:12]   # 5 cifre peso

    if eanpeso[:3] == '000':
        eanpeso = '0' + eanpeso[3:5]
    elif eanpeso[:2] == '00':
        eanpeso = '0' + eanpeso[2:5]
    elif eanpeso[0] == '0':
        eanpeso = '0' + eanpeso[1:5]
    # else rimane invariato

    return eanpeso


# ---------------------------------------------------------------------------
# Lookup articolo su goldreport (con fallback edicola)
# ---------------------------------------------------------------------------

def _get_articolo_edicola(ean: str) -> dict | None:
    """Fallback: cerca l'articolo nella tabella locale EdicolaPrincipale."""
    try:
        ep = EdicolaPrincipale.objects.filter(ean=ean).first()
    except Exception:
        logger.exception("Errore lookup edicola per EAN %s", ean)
        return None
    if not ep:
        return None
    return {
        'codart':        str(ep.codart or '').strip(),
        'descrizione':   str(ep.descrart or '').strip(),
        'ean':           str(ep.ean or ean).strip(),
        'stato':         str(ep.stato or '').strip(),
        'prezzo_vend':   str(ep.prezzovend or '0'),
        'giac_pdv':      str(ep.giacenza_pdv or '0'),
        'giac_dep':      '0',
        'pz_xcrt':       '0',
        'tipo_articolo': 'EDICOLA',
        'tipo_riordino': '',
        'corsia':        '',
        'campata':       '',
        'facing':        '',
        'minimo':        '',
        'massimo':       '',
        'codartfo':      '',
        'ccom':          str(ep.ccom or '').strip(),
        'descrccom':     str(ep.descc or '').strip(),
        'codforn':       '',
        'descforn':      '',
    }


def _varianti_ean(ean: str) -> list[str]:
    """Restituisce le varianti dell'EAN da cercare: aggiunge/rimuove lo zero iniziale per EAN a 12/13 cifre."""
    varianti = [ean]
    if ean.isdigit():
        if len(ean) == 12:
            varianti.append('0' + ean)
        elif len(ean) == 13 and ean.startswith('0'):
            varianti.append(ean[1:])
    return varianti


def get_articolo_by_ean(ean: str) -> dict | None:
    """
    Cerca l'articolo su goldreport per codice EAN tramite v_AllArticolo.

    v_AllArticolo ha righe duplicate per EAN (TIPO 3 e 911):
    si prende la prima riga ordinando per EANPRINC DESC (preferisce EAN primario).
    DESCRART è già presente nella vista — nessuna JOIN necessaria.

    Arricchisce il risultato con la posizione da Db_Category.t_masterdataCategory.

    Restituisce un dict o None se non trovato.
    """
    sql = """
        SELECT TOP 1
            a.CODART,
            ISNULL(a.DESCRART, '')          AS DESCRART,
            a.EAN,
            ISNULL(a.STATO, '')             AS STATO,
            ISNULL(a.PREZZOVEND, 0)         AS PREZZOVEND,
            ISNULL(a.GIACENZA_PDV, 0)       AS GIAC_PDV,
            ISNULL(a.GIACENZA_DEPOSITO, 0)  AS GIAC_DEP,
            ISNULL(a.TIPO, 0)               AS TIPO,
            ISNULL(m.PZXCART, 0)            AS PZXCART,
            ISNULL(m.TIPO_RIORDINO, '')     AS TIPO_RIORDINO,
            ISNULL(m.CODFORN, '')           AS CODFORN,
            ISNULL(m.DESCFORN, '')          AS DESCFORN
        FROM dbo.v_AllArticolo a
        LEFT JOIN dbo.v_MasterAssortimenti m
            ON a.CODART = m.CODART AND m.FORNPRINC = 1
        WHERE a.EAN IN ({placeholders})
        ORDER BY a.EANPRINC DESC
    """
    varianti = _varianti_ean(ean)
    placeholders = ','.join(['%s'] * len(varianti))
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql.format(placeholders=placeholders), varianti)
            row = cur.fetchone()
    except Exception:
        logger.exception("Errore query goldreport per EAN %s", ean)
        return None

    if not row:
        return _get_articolo_edicola(ean)

    return _arricchisci_articolo(row, ean)


def get_articolo_by_codart(codart_in: str) -> dict | None:
    """
    Cerca l'articolo su goldreport per CODICE ARTICOLO tramite v_AllArticolo.

    Usato come fallback quando l'input nel campo EAN non corrisponde a un EAN
    (l'utente ha digitato direttamente il codart). Riusa lo stesso arricchimento
    posizione/dati commerciali di get_articolo_by_ean.

    Restituisce un dict o None se non trovato.
    """
    codart_in = str(codart_in or '').strip()
    if not codart_in.isdigit():
        return None
    sql = """
        SELECT TOP 1
            a.CODART,
            ISNULL(a.DESCRART, '')          AS DESCRART,
            a.EAN,
            ISNULL(a.STATO, '')             AS STATO,
            ISNULL(a.PREZZOVEND, 0)         AS PREZZOVEND,
            ISNULL(a.GIACENZA_PDV, 0)       AS GIAC_PDV,
            ISNULL(a.GIACENZA_DEPOSITO, 0)  AS GIAC_DEP,
            ISNULL(a.TIPO, 0)               AS TIPO,
            ISNULL(m.PZXCART, 0)            AS PZXCART,
            ISNULL(m.TIPO_RIORDINO, '')     AS TIPO_RIORDINO,
            ISNULL(m.CODFORN, '')           AS CODFORN,
            ISNULL(m.DESCFORN, '')          AS DESCFORN
        FROM dbo.v_AllArticolo a
        LEFT JOIN dbo.v_MasterAssortimenti m
            ON a.CODART = m.CODART AND m.FORNPRINC = 1
        WHERE a.CODART = %s
        ORDER BY a.EANPRINC DESC
    """
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [codart_in])
            row = cur.fetchone()
    except Exception:
        logger.exception("Errore query goldreport per CODART %s", codart_in)
        return None

    if not row:
        return None
    return _arricchisci_articolo(row, '')


def _arricchisci_articolo(row, ean: str) -> dict:
    """Costruisce il dict articolo da una riga di v_AllArticolo, arricchendola
    con posizione e dati commerciali da Db_Category.t_masterdataCategory."""
    codart, descrizione, ean_db, stato, prezzo, giac_pdv, giac_dep, tipo, pzxcart, tipo_riordino, codforn, descforn = row
    codart = str(codart or '').strip()

    # Posizione + dati commerciali da Db_Category (sola lettura)
    corsia = campata = facing = minimo = massimo = ''
    ccom = descrccom = codartfo = ''
    try:
        sql_pos = """
            SELECT TOP 1 corsia, campata, facing, min, max,
                         ISNULL(CCOM,'')      AS CCOM,
                         ISNULL(DESCRCCOM,'') AS DESCRCCOM,
                         ISNULL(CODARTFO,'')  AS CODARTFO
            FROM [dbo].[t_masterdataCategory]
            WHERE CODART = %s
        """
        with connections['category'].cursor() as cur:
            cur.execute(sql_pos, [codart])
            pos_row = cur.fetchone()
        if pos_row:
            corsia, campata, facing, minimo, massimo, ccom, descrccom, codartfo = [
                str(v or '').strip() for v in pos_row
            ]
    except Exception:
        logger.exception("Errore lettura t_masterdataCategory per %s", codart)

    return {
        'codart':        codart,
        'descrizione':   str(descrizione or '').strip(),
        'ean':           str(ean_db or ean).strip(),
        'stato':         str(stato or '').strip(),
        'prezzo_vend':   str(prezzo or '0'),
        'giac_pdv':      str(giac_pdv or '0'),
        'giac_dep':      str(giac_dep or '0'),
        'pz_xcrt':       str(pzxcart or '0'),
        'tipo_articolo': str(tipo or '').strip(),
        'tipo_riordino': str(tipo_riordino or '').strip(),
        'corsia':        corsia,
        'campata':       campata,
        'facing':        facing,
        'minimo':        minimo,
        'massimo':       massimo,
        'codartfo':      codartfo,
        'ccom':          ccom,
        'descrccom':     descrccom,
        'codforn':       codforn,
        'descforn':      descforn,
    }


# ---------------------------------------------------------------------------
# Stampa frontalini
# ---------------------------------------------------------------------------

def stampa_get_items(token: str):
    return StampaCursori.objects.filter(
        numero_richiesta=token,
        elaborato='NO',
    )


def stampa_add_articolo(token: str, ip: str, articolo: dict,
                        num_cursori: int) -> None:
    # NB: la tabella non ha un vincolo univoco su (numero_richiesta, cod_articolo,
    # elaborato), quindi scansioni concorrenti dello stesso articolo possono aver
    # creato righe duplicate. update_or_create() andrebbe in MultipleObjectsReturned
    # appena ne trova 2: gestiamo l'upsert manualmente tollerando i duplicati.
    defaults = {
        'descrizione':  articolo['descrizione'],
        'num_cursori':  num_cursori,
        'ean':          articolo.get('ean', ''),
        'codartfo':     articolo.get('codartfo', ''),
        'prezzo_vend':  articolo.get('prezzo_vend', ''),
        'giac_pdv':     articolo.get('giac_pdv', ''),
        'giac_dep':     articolo.get('giac_dep', ''),
        'ccom':         articolo.get('ccom', ''),
        'descrccom':    articolo.get('descrccom', ''),
        'codforn':      articolo.get('codforn', ''),
        'descforn':     articolo.get('descforn', ''),
        'ip':           ip,
    }
    esistenti = list(
        StampaCursori.objects.filter(
            numero_richiesta=token,
            cod_articolo=articolo['codart'],
            elaborato='NO',
        ).order_by('id')
    )
    if esistenti:
        # Tiene la prima riga e la aggiorna; se ci sono duplicati pregressi
        # (creati da scansioni concorrenti) li elimina, auto-pulendo la coda.
        prima = esistenti[0]
        for campo, valore in defaults.items():
            setattr(prima, campo, valore)
        prima.save(update_fields=list(defaults.keys()))
        if len(esistenti) > 1:
            StampaCursori.objects.filter(
                id__in=[r.id for r in esistenti[1:]]
            ).delete()
    else:
        StampaCursori.objects.create(
            numero_richiesta=token,
            cod_articolo=articolo['codart'],
            elaborato='NO',
            **defaults,
        )


def stampa_aggiorna_qta(pk: int, token: str, qta: int) -> None:
    StampaCursori.objects.filter(pk=pk, numero_richiesta=token).update(num_cursori=qta)


def stampa_cancella_item(pk: int, token: str) -> None:
    StampaCursori.objects.filter(pk=pk, numero_richiesta=token).delete()


def stampa_invia(token: str, ip: str) -> str:
    """
    Stampa la lista articoli in orizzontale sulla stampante configurata in CURSORI_PRINTER_NAME.
    Usa GDI (win32ui) con orientamento landscape e layout a tabella.
    """
    items = list(StampaCursori.objects.filter(numero_richiesta=token, elaborato='NO'))
    if not items:
        return 'Nessun articolo in coda'

    import win32print  # type: ignore
    import win32ui     # type: ignore
    import win32con    # type: ignore
    import win32gui    # type: ignore

    ora = datetime.now().strftime('%d/%m/%Y %H:%M')
    printer_name = getattr(settings, 'CURSORI_PRINTER_NAME', '')

    try:
        # --- Imposta landscape via DEVMODE ---
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            props   = win32print.GetPrinter(hPrinter, 2)
            devmode = props['pDevMode']
            devmode.Orientation = win32con.DMORIENT_LANDSCAPE
            devmode.Fields |= win32con.DM_ORIENTATION
        finally:
            win32print.ClosePrinter(hPrinter)

        hdc_h = win32gui.CreateDC('WINSPOOL', printer_name, devmode)
        hDC   = win32ui.CreateDCFromHandle(hdc_h)
        fonts = []
        doc_started = False
        try:
            dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
            dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)
            pw    = hDC.GetDeviceCaps(win32con.HORZRES)
            mx    = int(dpi_x * 0.4)
            my    = int(dpi_y * 0.4)

            def make_font(bold=False, size_pt=10):
                f = win32ui.CreateFont({
                    'name':   'Arial',
                    'height': -int(dpi_y * size_pt / 72),
                    'weight': win32con.FW_BOLD if bold else win32con.FW_NORMAL,
                })
                fonts.append(f)
                return f

            font_title  = make_font(bold=True,  size_pt=12)
            font_header = make_font(bold=True,  size_pt=9)
            font_data   = make_font(bold=False, size_pt=9)
            font_small  = make_font(bold=False, size_pt=8)

            def line_h(font):
                hDC.SelectObject(font)
                tm = hDC.GetTextMetrics()
                return tm['tmHeight'] + tm['tmExternalLeading'] + int(dpi_y * 0.5 / 72)

            lh_title  = line_h(font_title)
            lh_header = line_h(font_header)
            lh_data   = line_h(font_data)
            lh_small  = line_h(font_small)

            cw = pw - 2 * mx
            col = {
                'cod':     int(cw * 0.08),
                'descr':   int(cw * 0.31),
                'qta':     int(cw * 0.05),
                'prz':     int(cw * 0.06),
                'gpdv':    int(cw * 0.06),
                'ccom':    int(cw * 0.06),
                'codartfo':int(cw * 0.08),
                'ean':     int(cw * 0.12),
                'forn':    int(cw * 0.18),
            }
            order = ['cod','descr','qta','prz','gpdv','ccom','codartfo','ean','forn']
            def x_of(keys):
                return mx + sum(col[k] for k in order[:order.index(keys)])

            pens = []
            def draw_line(y, thick=1):
                pen = win32ui.CreatePen(win32con.PS_SOLID, thick, 0x000000)
                pens.append(pen)
                hDC.SelectObject(pen)
                hDC.MoveTo((mx, y))
                hDC.LineTo((pw - mx, y))

            # Altezza stampabile: oltre questa quota GDI taglia il contenuto,
            # quindi qui scatta il salto pagina.
            ph    = hDC.GetDeviceCaps(win32con.VERTRES)
            y_max = ph - my

            headers = [
                ('cod',      'Cod. Art.'),
                ('descr',    'Descrizione'),
                ('qta',      'Qta'),
                ('prz',      'Prezzo'),
                ('gpdv',     'G.PDV'),
                ('ccom',     'CCom'),
                ('codartfo', 'Cd.Forn'),
                ('ean',      'EAN'),
                ('forn',     'Fornitore'),
            ]

            def draw_intestazione():
                """Disegna titolo + intestazione colonne in cima alla pagina
                corrente e restituisce la y da cui iniziare le righe dati."""
                yy = my
                hDC.SelectObject(font_title)
                hDC.TextOut(mx, yy, 'LISTA ARTICOLI CURSORI')
                hDC.SelectObject(font_small)
                hDC.TextOut(mx + int(cw * 0.5), yy + int(lh_title * 0.15),
                            f'Data: {ora}   IP: {ip}   Totale: {len(items)} articoli')
                yy += lh_title + int(dpi_y * 0.05)

                draw_line(yy, thick=2)
                yy += int(dpi_y * 0.05)

                hDC.SelectObject(font_header)
                for key, label in headers:
                    hDC.TextOut(x_of(key), yy, label)
                yy += lh_header

                draw_line(yy)
                yy += int(dpi_y * 0.04)
                return yy

            hDC.StartDoc('Lista Articoli Cursori')
            doc_started = True
            hDC.StartPage()
            y = draw_intestazione()

            for item in items:
                # Se la prossima riga uscirebbe dall'area stampabile, chiudo la
                # pagina e ne apro una nuova ridisegnando titolo e intestazione.
                if y + lh_data + int(dpi_y * 0.02) > y_max:
                    hDC.EndPage()
                    hDC.StartPage()
                    y = draw_intestazione()

                hDC.SelectObject(font_data)
                qta_val = str(item.num_cursori) if item.num_cursori else ''
                vals = [
                    ('cod',      item.cod_articolo),
                    ('descr',    item.descrizione[:38]),
                    ('qta',      qta_val),
                    ('prz',      item.prezzo_vend or ''),
                    ('gpdv',     item.giac_pdv or ''),
                    ('ccom',     item.ccom or ''),
                    ('codartfo', item.codartfo or ''),
                    ('ean',      item.ean or ''),
                    ('forn',     item.descforn[:28] if item.descforn else ''),
                ]
                for key, val in vals:
                    hDC.TextOut(x_of(key), y, str(val))
                y += lh_data

                draw_line(y, thick=1)
                y += int(dpi_y * 0.02)

            hDC.EndPage()
            hDC.EndDoc()
            doc_started = False
        except Exception:
            if doc_started:
                try:
                    hDC.AbortDoc()
                except Exception:
                    pass
            raise
        finally:
            hDC.DeleteDC()
            for f in fonts:
                try:
                    f.DeleteObject()
                except Exception:
                    pass
            for p in pens:
                try:
                    p.DeleteObject()
                except Exception:
                    pass

    except Exception:
        logger.exception('Errore stampa lista cursori (token=%s, printer=%s)', token, printer_name)
        return 'Errore stampa — contattare ITD'

    # --- Marca come stampati ---
    StampaCursori.objects.filter(numero_richiesta=token, elaborato='NO').update(elaborato='SI')
    return 'Inviata'


def stampa_invia_email(token: str, email_to: str) -> str:
    """
    Invia la coda di stampa frontalini via email, in alternativa alla stampante fisica
    (es. quando l'operatore non ha accesso a una stampante o vuole tenere traccia).

    In caso di successo marca la coda come elaborata, come dopo la stampa: le due
    modalità di consegna si affiancano ma non si sommano sulla stessa coda.
    """
    email_to = (email_to or '').strip()
    try:
        validate_email(email_to)
    except ValidationError:
        return 'Indirizzo email non valido'

    items = list(StampaCursori.objects.filter(numero_richiesta=token, elaborato='NO'))
    if not items:
        return 'Nessun articolo in coda'

    ora = datetime.now().strftime('%d/%m/%Y %H:%M')
    righe_html = ''.join(
        '<tr>'
        f'<td>{escape(i.cod_articolo)}</td>'
        f'<td>{escape(i.descrizione)}</td>'
        f'<td>{i.num_cursori}</td>'
        f'<td>{escape(i.prezzo_vend)}</td>'
        f'<td>{escape(i.giac_pdv)}</td>'
        f'<td>{escape(i.ccom)}</td>'
        f'<td>{escape(i.codartfo)}</td>'
        f'<td>{escape(i.ean)}</td>'
        f'<td>{escape(i.descforn)}</td>'
        '</tr>'
        for i in items
    )
    html = (
        f'<p>Lista Articoli Cursori — {ora} — {len(items)} articoli</p>'
        '<table border="1" cellspacing="0" cellpadding="4" '
        'style="border-collapse:collapse; font-size:13px;">'
        '<tr><th>Cod.Art</th><th>Descrizione</th><th>Qta</th>'
        '<th>Prezzo</th><th>G.PDV</th><th>CCom</th><th>Cd.Forn</th>'
        '<th>EAN</th><th>Fornitore</th></tr>'
        f'{righe_html}</table>'
    )
    testo = f'Lista Articoli Cursori del {ora} ({len(items)} articoli). Visualizza in un client che supporta HTML.'

    try:
        msg = EmailMultiAlternatives(
            subject=f'Lista Articoli Cursori — {ora}',
            body=testo,
            to=[email_to],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
    except Exception:
        logger.exception('stampa_invia_email: errore invio a %s (token=%s)', email_to, token)
        return 'Errore invio email — contattare ITD'

    StampaCursori.objects.filter(numero_richiesta=token, elaborato='NO').update(elaborato='SI')
    return 'Inviata'
