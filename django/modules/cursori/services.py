"""
services.py — logica di business per l'app cursori.

Contiene:
  - gestione token di sessione
  - lookup articolo su goldreport (v_AllArticolo + v_MasterAssortimenti)
  - lookup posizione da Db_Category (t_masterdataCategory)
  - utilità EAN peso-variabile (prefisso 21)
  - operazioni su ListaInventario, StampaCursori
"""
import secrets
import logging
from datetime import datetime

from django.conf import settings
from django.db import connections

from .models import ListaInventario, StampaCursori
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
# Lista inventario
# ---------------------------------------------------------------------------

def lista_get_items(token: str):
    """Articoli non ancora elaborati per il token corrente."""
    return ListaInventario.objects.filter(
        numero_richiesta=token,
        elab='0',
    ).order_by('id')


def lista_conta(token: str) -> int:
    return ListaInventario.objects.filter(numero_richiesta=token, elab='0').count()


def lista_add_articolo(token: str, articolo: dict, qta: str) -> None:
    """
    Aggiunge (o aggiorna se già presente) un articolo alla lista inventario.
    qta: stringa quantità (es. "01200" per peso-var, "1" per normale).
    """
    # Elimina eventuali duplicati preesistenti tenendo solo il più recente
    qs = ListaInventario.objects.filter(
        numero_richiesta=token,
        cod_articolo=articolo['codart'],
        elab='0',
    ).order_by('-id')
    if qs.count() > 1:
        ids_da_eliminare = list(qs.values_list('id', flat=True)[1:])
        ListaInventario.objects.filter(id__in=ids_da_eliminare).delete()

    ListaInventario.objects.update_or_create(
        numero_richiesta=token,
        cod_articolo=articolo['codart'],
        elab='0',
        defaults={
            'descrizione':   articolo['descrizione'],
            'cd_ean':        articolo['ean'],
            'qtar':          qta,
            'tipo_articolo': articolo.get('tipo_articolo', ''),
        },
    )


def lista_cancella_articolo(token: str, codart: str) -> None:
    ListaInventario.objects.filter(
        numero_richiesta=token,
        cod_articolo=codart,
        elab='0',
    ).delete()


def lista_chiudi(token: str) -> None:
    """Marca tutti gli articoli come elaborati (fine sessione)."""
    ListaInventario.objects.filter(
        numero_richiesta=token, elab='0'
    ).update(elab='1')



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
                'descr':   int(cw * 0.25),
                'tipo':    int(cw * 0.06),
                'qta':     int(cw * 0.05),
                'prz':     int(cw * 0.06),
                'gpdv':    int(cw * 0.06),
                'ccom':    int(cw * 0.06),
                'codartfo':int(cw * 0.08),
                'ean':     int(cw * 0.12),
                'forn':    int(cw * 0.18),
            }
            order = ['cod','descr','tipo','qta','prz','gpdv','ccom','codartfo','ean','forn']
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
                ('tipo',     'Tipo'),
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
                    ('tipo',     item.get_tipo_label()),
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


# ---------------------------------------------------------------------------
# Posizione articoli (riordino automatico PDV)
#
# Porting del vecchio web service mainWsAllArticolo.PosArticoli (TestRAzor4).
# Scrive sulla tabella DRAFT t_posArticoli su GoldCursori srviis (172.17.10.51),
# raggiunta via LINKED SERVER dalla connessione 'goldreport' (stesso pattern di
# modules/rio_fornitori). Un processo separato promuove t_posArticoli ->
# t_posArticoliglob, che il riordino PDV consuma. Query SEMPRE parametrizzate
# (il web service originale concatenava stringhe: SQL injection).
#
# Ciclo Elab in t_posArticoli: ''=bozza (scan), '1'=confermato (OK), 'D'=da smappare.
# ---------------------------------------------------------------------------

_POS_DB = '[172.17.10.51].goldcursori.dbo'   # GoldCursori su srviis via linked server


def get_posizione_riordino(codart: str) -> dict:
    """
    Legge i dati 'autentici' che il riordino PDV conosce, come faceva
    DettaglioArticolo del vecchio web service:
      - corsia/campata/facing da V_coordArticoli (campi [3],[5],[7]) su srviis
      - min/max di default da t_posarticoliglob su srviis
      - gest (unità gestione: Pezzo/Collo/Strato/Pallet) e pzxcrt da t_masterData
        (Db_GoldReport) — è la sorgente autentica del pz/cartone usata dal vecchio app.
    Restituisce sempre un dict (stringhe vuote se non trovato).
    """
    corsia = campata = facing = minimo = massimo = ''
    gest = pzxcrt = ''
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(f"SELECT * FROM {_POS_DB}.V_coordArticoli WHERE codarticolo = %s", [codart])
            row = cur.fetchone()
            if row:
                corsia  = str(row[3] or '').strip()
                campata = str(row[5] or '').strip()
                facing  = str(row[7] or '').strip()
    except Exception:
        logger.exception("get_posizione_riordino: V_coordArticoli per %s", codart)
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(f"SELECT Min, Max FROM {_POS_DB}.t_posarticoliglob WHERE codarticolo = %s", [codart])
            row = cur.fetchone()
            if row:
                minimo  = str(row[0] or '').strip()
                massimo = str(row[1] or '').strip()
    except Exception:
        logger.exception("get_posizione_riordino: t_posarticoliglob per %s", codart)
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute("SELECT TOP 1 ISNULL(GEST,''), ISNULL(PZXCART,0) "
                        "FROM dbo.t_masterData WHERE CODART = %s", [codart])
            row = cur.fetchone()
            if row:
                gest = str(row[0] or '').strip()
                try:
                    pzxcrt = str(int(float(row[1])))   # '10.0' -> '10'
                except (ValueError, TypeError):
                    pzxcrt = str(row[1] or '').strip()
    except Exception:
        logger.exception("get_posizione_riordino: t_masterData per %s", codart)

    # Venduto casse correnti (t_vendutonow su srviis); default '0' come il vecchio app
    venduto = '0'
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(f"SELECT qtavend FROM {_POS_DB}.t_vendutonow WHERE CodiceArticolo = %s", [codart])
            row = cur.fetchone()
            if row and row[0] is not None:
                try:
                    venduto = ('%g' % float(row[0]))   # '12.000' -> '12', '8.735' -> '8.735'
                except (ValueError, TypeError):
                    venduto = str(row[0]).strip()
    except Exception:
        logger.exception("get_posizione_riordino: t_vendutonow per %s", codart)

    # Flag "Rio OK" (MappaOk): articolo candidato valido al riordino automatico.
    # Count su join posArticoliGlob+masterdata+Ord901+Cons901+CorsiaAbilita (corsia abilitata).
    rio_ok = False
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM {_POS_DB}.t_posArticoliGlob p
                  INNER JOIN {_POS_DB}.t_masterdata m ON p.codArticolo = m.CODART
                  INNER JOIN {_POS_DB}.t_Ord901 o ON o.CODART = m.CODART
                  INNER JOIN {_POS_DB}.t_Cons901 c ON c.CODARTICOLO = o.CODART
                  INNER JOIN (SELECT Corsia FROM {_POS_DB}.t_CorsiaAbilita WHERE note IS NOT NULL) co
                          ON p.Corsia = co.Corsia
                WHERE m.CODART = %s
            """, [codart])
            row = cur.fetchone()
            rio_ok = bool(row and (row[0] or 0) > 0)
    except Exception:
        logger.exception("get_posizione_riordino: MappaOk per %s", codart)

    return {'corsia': corsia, 'campata': campata, 'facing': facing,
            'minimo': minimo, 'massimo': massimo, 'gest': gest, 'pzxcrt': pzxcrt,
            'venduto': venduto, 'rio_ok': rio_ok}


# Query Oracle: giacenze + unità di gestione (Gest) dell'originale DettaglioArticolo,
# chiave artcexr = codart (artcexr = etichetta = codice articolo).
_SQL_DATI_ORACLE = """
    with ord as (
        select distinct at.aracinr acinr, max(at.aradfin) dtaf
        from artuc at where at.aratfou='1' and at.arasite='10001' group by at.aracinr)
    select
        NVL(PKSTOCK.GETSTOCKENQTEVALADATE(1, 10001,
            PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL(1, ARACINR, ARASEQVL), TRUNC(sysdate+1)), 0) GIAC_PDV,
        trunc(NVL(PKSTOCK.GETSTOCKENQTEVALADATE(1, 901,
            PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL(1, ARACINR, ARASEQVL), TRUNC(sysdate+1)), 0)
            / PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL)) GIAC_DEP,
        PKARTUL.GETLIBLTYPEUL(1, ARACINL, 'IT') GEST
    from artrac, ord, artcoca, artattri, artuv, aveprix, artuc, tsv_strucrel
    where 1=1 and artcinr=acinr and artcinr=arccinr and arcieti='1'
      and trunc(sysdate) between arcddeb and arcdfin
      and artcinr=aatcinr and aatccla='SARGC'
      and trunc(sysdate) between AATDDEB and AATDFIN
      and artcinr=ARVCINR and arvcinv=avicinv
      and trunc(sysdate) between AVIDDEB and AVIDFIN
      and artcinr=aracinr and aratfou='1' and arasite='10001'
      and to_date(aradfin)=to_date(dtaf)
      and artcinr=TSSRECINR
      and artcexr = :codart
"""


def get_dati_oracle(codart: str):
    """
    Dati LIVE da Oracle GOLDPROD (come il vecchio web service DettaglioArticolo,
    connessione "GOLDTEST" = utente GOLDCEN):
      - giac_pdv = stock sito 10001
      - giac_dep = stock sito 901 diviso pz/cartone (in colli)
      - gest     = unità di gestione (Pezzo/Collo/Strato/Pallet) = DESC_UNITA_GESTIONE
    Usa i settings CURSORI_ORACLE_* (password ereditata da quella GOLDCEN di rio).
    Ritorna dict {'giac_pdv':int, 'giac_dep':int, 'gest':str} oppure None se Oracle
    non configurato/errore (il chiamante tiene i valori ETL come fallback).
    """
    dsn  = getattr(settings, 'CURSORI_ORACLE_DSN', '')
    user = getattr(settings, 'CURSORI_ORACLE_USER', '')
    pwd  = getattr(settings, 'CURSORI_ORACLE_PASS', '')
    if not (dsn and user and pwd):
        # password/DSN non impostati -> dati Oracle disattivati (fallback ETL)
        logger.warning("get_dati_oracle: Oracle disattivato (pwd %s, dsn %s) -> fallback ETL",
                       'impostata' if pwd else 'VUOTA', dsn or 'VUOTO')
        return None
    try:
        import oracledb  # import lazy: dipendenza presente nei venv di test/prod
        with oracledb.connect(user=user, password=pwd, dsn=dsn,
                              tcp_connect_timeout=8) as conn:
            conn.call_timeout = 12000   # ms: la query non può bloccare oltre 12s
            with conn.cursor() as cur:
                cur.execute(_SQL_DATI_ORACLE, {'codart': str(codart).strip()})
                rows = cur.fetchall()
        if not rows:
            return None
        # L'articolo può avere più unità logistiche (Collo, Pallet, ...): la query
        # restituisce una riga per unità. Il vecchio web service (while reader.Read())
        # teneva l'ULTIMA riga -> replichiamo prendendo rows[-1].
        row = rows[-1]
        return {'giac_pdv': int(row[0] or 0),
                'giac_dep': int(row[1] or 0),
                'gest':     str(row[2] or '').strip()}
    except Exception:
        logger.exception("get_dati_oracle: errore codart=%s", codart)
        return None


def pos_get_items(token: str) -> list[dict]:
    """Righe inserite nella sessione corrente (per VediPosArticoli)."""
    sql = (f"SELECT id, Corsia, Campata, codArticolo, Descrizione, Capienza, Min, Max, facing, Elab "
           f"FROM {_POS_DB}.t_posArticoli WHERE NumeroRichiesta = %s ORDER BY id DESC")
    rows: list[dict] = []
    try:
        with connections['goldreport'].cursor() as cur:
            cur.execute(sql, [token])
            for r in cur.fetchall():
                rows.append({
                    'id':          r[0],
                    'corsia':      str(r[1] or '').strip(),
                    'campata':     str(r[2] or '').strip(),
                    'codart':      str(r[3] or '').strip(),
                    'descrizione': str(r[4] or '').strip(),
                    'capienza':    str(r[5] or '').strip(),
                    'min':         str(r[6] or '').strip(),
                    'max':         str(r[7] or '').strip(),
                    'facing':      str(r[8] or '').strip(),
                    'elab':        str(r[9] or '').strip(),
                })
    except Exception:
        logger.exception("pos_get_items: errore token=%s", token)
    return rows


def pos_salva(token: str, articolo: dict, corsia: str, campata: str, facing: str,
              capienza: str, minimo: str, massimo: str, azione: str) -> str:
    """
    Replica mainWsAllArticolo.PosArticoli (azioni 0-4) con query parametrizzate.
    Scrive su t_posArticoli su srviis (target del riordino PDV).
      '0' scan  -> INSERT bozza (Elab='') o UPDATE posizione se gia presente
      '1' OK    -> UPDATE + MinimoRio = Max-Min, Elab='1' (solo righe con Capienza='')
      '2' Togli -> INSERT/UPDATE Elab='D' (smappa dal riordino)
      '3' CLR (modo togli) -> DELETE righe Elab='D'
      '4' CLR (normale)    -> DELETE bozza (Elab='')
    """
    T = f"{_POS_DB}.t_posArticoli"
    codart = str(articolo.get('codart', '')).strip()
    descr  = articolo.get('descrizione', '')
    stato  = articolo.get('stato', '')
    ean    = articolo.get('ean', '')
    now    = datetime.now().strftime('%Y%m%d%H%M%S')

    # pz/cartone: normalizza a intero (la sorgente puo restituire '12.0' -> '12')
    pzcrt = str(articolo.get('pz_xcrt', '') or '').strip()
    try:
        pzcrt = str(int(float(pzcrt)))
    except (ValueError, TypeError):
        pass

    cols = ("NumeroRichiesta, Corsia, Campata, codArticolo, Descrizione, Stato, "
            "qtaXCrt, cdEan, Capienza, Min, Max, dataIns, facing, Elab")

    # Guard di sicurezza: con CURSORI_POS_DRY_RUN attivo (default) le SCRITTURE non
    # toccano il DB di produzione, vengono solo loggate. Le COUNT restano (letture).
    dry = getattr(settings, 'CURSORI_POS_DRY_RUN', True)

    try:
        with connections['goldreport'].cursor() as cur:

            def _w(sql: str, params: list) -> None:
                """Esegue una scrittura, o la logga soltanto se dry-run è attivo."""
                if dry:
                    logger.warning("[CURSORI_POS_DRY_RUN] write NON eseguita | %s | params=%s", sql, params)
                else:
                    cur.execute(sql, params)

            if azione == '0':
                cur.execute(
                    f"SELECT COUNT(*) FROM {T} WHERE Corsia=%s AND Campata=%s "
                    f"AND codArticolo=%s AND Elab='' AND NumeroRichiesta=%s",
                    [corsia, campata, codart, token])
                if (cur.fetchone()[0] or 0) <= 0:
                    _w(f"INSERT INTO {T}({cols}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'')",
                       [token, corsia, campata, codart, descr, stato, pzcrt, ean,
                        capienza, minimo, massimo, now, facing])
                else:
                    _w(f"UPDATE {T} SET Capienza=%s, Min=%s, Max=%s, Corsia=%s, Campata=%s, "
                       f"facing=%s, dataUpg=%s WHERE codArticolo=%s AND NumeroRichiesta=%s",
                       [capienza, minimo, massimo, corsia, campata, facing, now, codart, token])

            elif azione == '1':
                minimorio = int(str(massimo).strip()) - int(str(minimo).strip())
                _w(f"UPDATE {T} SET Capienza=%s, Min=%s, Max=%s, Corsia=%s, Campata=%s, "
                   f"facing=%s, MinimoRio=%s, Elab='1' "
                   f"WHERE codArticolo=%s AND Capienza='' AND NumeroRichiesta=%s",
                   [capienza, minimo, massimo, corsia, campata, facing, str(minimorio), codart, token])

            elif azione == '2':
                cur.execute(
                    f"SELECT COUNT(*) FROM {T} WHERE Corsia=%s AND Campata=%s "
                    f"AND codArticolo=%s AND Elab='D' AND NumeroRichiesta=%s",
                    [corsia, campata, codart, token])
                if (cur.fetchone()[0] or 0) <= 0:
                    _w(f"INSERT INTO {T}({cols}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'D')",
                       [token, corsia, campata, codart, descr, stato, pzcrt, ean,
                        capienza, minimo, massimo, now, facing])
                else:
                    _w(f"UPDATE {T} SET Elab='D', dataUpg=%s "
                       f"WHERE codArticolo=%s AND NumeroRichiesta=%s",
                       [now, codart, token])

            elif azione == '3':
                cur.execute(f"SELECT COUNT(*) FROM {T} WHERE codArticolo=%s AND Elab='D'", [codart])
                if (cur.fetchone()[0] or 0) > 0:
                    _w(f"DELETE FROM {T} WHERE codArticolo=%s AND Elab='D'", [codart])

            else:  # '4' / default
                _w(f"DELETE FROM {T} WHERE codArticolo=%s AND NumeroRichiesta=%s AND Elab=''",
                   [codart, token])

        return 'DRY-RUN: nessuna scrittura' if dry else 'Operazione Eseguita'
    except ValueError:
        return 'Min/Max non validi'
    except Exception:
        logger.exception("pos_salva: errore azione=%s codart=%s", azione, codart)
        return 'Errore non aggiornato'
