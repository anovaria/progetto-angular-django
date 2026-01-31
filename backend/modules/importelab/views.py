from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.db import connections
from django.conf import settings
from datetime import datetime
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import os
import csv
from pathlib import Path

# Email draft (.eml) generation for environments without Outlook
from email.message import EmailMessage
from email.policy import default as email_default_policy
from io import BytesIO

def _normalize_codart_key(value):
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    keys = [s, s.lstrip("0") or "0"]
    try:
        keys.append(str(int(float(s))))
    except Exception:
        pass
    out=[]
    for k in keys:
        if k not in out:
            out.append(k)
    return out


def _rossetto_index_by_codart_v2():
    """Build index from GoldTableSnapshot rows (source_table dbo.t_Rossetto) keyed by CODART variants."""
    index = {}
    for snap in GoldTableSnapshot.objects.filter(source_table='dbo.t_Rossetto').only('payload').iterator(chunk_size=5000):
        p = snap.payload or {}
        codart = p.get('CODART') or p.get('CodArt') or p.get('codart')
        norm = dict(p)
        norm['stato'] = p.get('STATO') or p.get('Stato') or ''
        norm['descrccom'] = p.get('DESCRCCOM') or p.get('DescrCCOM') or ''
        norm['ccom'] = p.get('CCOM') or p.get('Ccom') or ''
        norm['dtaaggio'] = p.get('DTAAGGIO') or p.get('DtaAggio') or ''
        norm['descrart'] = p.get('DESCRART') or p.get('DescrArt') or ''
        for k in _normalize_codart_key(codart):
            index[k] = norm
    return index


def _rossetto_get(index, codart):
    for k in _normalize_codart_key(codart):
        r = index.get(k)
        if r:
            return r
    return None



from .goldsync import sync_gold_tables, get_preview_from_local
from .intermediate import rebuild_intermediate_queries, get_intermediate_previews

from .forms import ElabUploadForm, OrderEmailForm
from .outlook import create_outlook_mail_with_attachment
from .utils import decode_elab, parse_elab_text
from .models import (
    ImportBatch,
    ImportRow,
    GoldTableSnapshot,
    IntermediateAggPrAcq,
    IntermediateAggiornaEan,
    IntermediateAggiornamentiVari,
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _format_ddmmyyyy_to_yyyymmdd(value) -> str:
    """Format dates like Access: from 'dd/mm/yyyy' (or similar) to 'yyyymmdd'.

    The legacy Access queries used Mid(DATA_ORDINE,7,4)&Mid(...,4,2)&Mid(...,1,2).
    If the input is already a date/datetime or an ISO string, we try to normalize.
    Returns 8 chars; if cannot parse, returns '00000000'.
    """
    if value is None:
        return "00000000"
    # datetime/date
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%Y%m%d")
    except Exception:
        pass
    s = str(value).strip()
    if not s:
        return "00000000"

    # common legacy format dd/mm/yyyy
    if len(s) >= 10 and s[2] in ("/", "-") and s[5] in ("/", "-"):
        dd = s[0:2]
        mm = s[3:5]
        yyyy = s[6:10]
        if yyyy.isdigit() and mm.isdigit() and dd.isdigit():
            return f"{yyyy}{mm}{dd}"

    # ISO yyyy-mm-dd or yyyy/mm/dd
    if len(s) >= 10 and s[4] in ("-", "/") and s[7] in ("-", "/"):
        yyyy = s[0:4]
        mm = s[5:7]
        dd = s[8:10]
        if yyyy.isdigit() and mm.isdigit() and dd.isdigit():
            return f"{yyyy}{mm}{dd}"

    # already yyyymmdd
    if len(s) >= 8 and s[:8].isdigit():
        return s[:8]
    return "00000000"


def _safe_str(value) -> str:
    return "" if value is None else str(value)



def _fetch_ordini_rossetto_rows_from_txt(txt_path: str):
    """Read a TXT export of dbo_t_OrdiniRossetto and return rows as dicts.

    Supports:
    - header row (preferred) with column names, delimited by ;,|,tab,comma
    - NO header (your current file): uses deterministic fixed positions for the Rossetto export
      (CSV with delimiter ';' and quotechar '"').

    Required keys returned: CODARTFO, COLLIORD, DATA_ORDINE, DATA_CONSEGNA, DCDCEXCDE
    """
    import csv
    import re

    def norm(s: str) -> str:
        return re.sub(r"[^A-Z0-9_]", "", (s or "").strip().upper())

    # Read all non-empty lines first
    with open(txt_path, "r", encoding="utf-8", errors="replace", newline="") as fp:
        raw = fp.read()

    raw_lines = [ln for ln in raw.splitlines() if ln.strip() != ""]
    if not raw_lines:
        return []

    sample = raw_lines[0]
    likely_semicolon = sample.count(";") >= 3

    if likely_semicolon:
        with open(txt_path, "r", encoding="utf-8", errors="replace", newline="") as fp:
            reader = csv.reader(fp, delimiter=";", quotechar='"')
            rows = [r for r in reader if any((c or "").strip() for c in r)]

        if not rows:
            return []

        required = {"CODARTFO", "COLLIORD", "DATA_ORDINE", "DATA_CONSEGNA", "DCDCEXCDE"}
        first_norm = [norm(c) for c in rows[0]]
        has_header = any(h in required for h in first_norm)

        if has_header:
            idx = {first_norm[i]: i for i in range(len(first_norm))}
            missing = [c for c in required if c not in idx]
            if missing:
                raise ValueError(f"Header TXT mancante colonne: {missing}. Header letto: {first_norm}")

            out = []
            for parts in rows[1:]:
                out.append({
                    "CODARTFO": parts[idx["CODARTFO"]].strip() if idx["CODARTFO"] < len(parts) else "",
                    "COLLIORD": parts[idx["COLLIORD"]].strip() if idx["COLLIORD"] < len(parts) else "",
                    "DATA_ORDINE": parts[idx["DATA_ORDINE"]].strip() if idx["DATA_ORDINE"] < len(parts) else "",
                    "DATA_CONSEGNA": parts[idx["DATA_CONSEGNA"]].strip() if idx["DATA_CONSEGNA"] < len(parts) else "",
                    "DCDCEXCDE": parts[idx["DCDCEXCDE"]].strip() if idx["DCDCEXCDE"] < len(parts) else "",
                })
            return out

        # NO header: deterministic mapping for your export (verified on dbo_t_OrdiniRossetto_giovedi.txt)
        def safe(parts, i):
            return parts[i].strip() if i < len(parts) else ""

        out = []
        for parts in rows:
            out.append({
                "DATA_ORDINE": safe(parts, 2),
                "DATA_CONSEGNA": safe(parts, 3),
                "CODARTFO": safe(parts, 9),
                "DCDCEXCDE": safe(parts, 10),
                "COLLIORD": safe(parts, 11),
            })
        return out

    # Fallback: delimiter detection without quotes
    delimiter = None
    for d in ["	", "|", ","]:
        if sample.count(d) >= 3:
            delimiter = d
            break
    if delimiter is None:
        raise ValueError("Separatore TXT non riconosciuto. Attesi ';' (consigliato), tab, '|', ','.")

    required_list = ["CODARTFO", "COLLIORD", "DATA_ORDINE", "DATA_CONSEGNA", "DCDCEXCDE"]
    first_parts = [c.strip() for c in raw_lines[0].split(delimiter)]
    first_norm = [norm(p) for p in first_parts]
    has_header = any(h in set(required_list) for h in first_norm)

    rows_out = []
    if has_header:
        idx = {first_norm[i]: i for i in range(len(first_norm))}
        missing = [c for c in required_list if c not in idx]
        if missing:
            raise ValueError(f"Header TXT mancante colonne: {missing}. Header letto: {first_norm}")
        for ln in raw_lines[1:]:
            parts = [c.strip() for c in ln.split(delimiter)]
            rows_out.append({
                "CODARTFO": parts[idx["CODARTFO"]] if idx["CODARTFO"] < len(parts) else "",
                "COLLIORD": parts[idx["COLLIORD"]] if idx["COLLIORD"] < len(parts) else "",
                "DATA_ORDINE": parts[idx["DATA_ORDINE"]] if idx["DATA_ORDINE"] < len(parts) else "",
                "DATA_CONSEGNA": parts[idx["DATA_CONSEGNA"]] if idx["DATA_CONSEGNA"] < len(parts) else "",
                "DCDCEXCDE": parts[idx["DCDCEXCDE"]] if idx["DCDCEXCDE"] < len(parts) else "",
            })
        return rows_out

    raise ValueError("TXT senza header non supportato per questo formato. Usa export con ';' e virgolette oppure aggiungi header.")
    # No header: try heuristic mapping on first data row
    parts0 = first_parts
    date_idxs = [i for i, v in enumerate(parts0) if looks_like_date(v)]
    cod_idxs = [i for i, v in enumerate(parts0) if looks_like_codartfo(v)]
    colli_idxs = [i for i, v in enumerate(parts0) if (v or "").strip().isdigit()]

    if not cod_idxs or len(date_idxs) < 2:
        raise ValueError("Impossibile inferire le colonne dal TXT senza header. Aggiungi la riga di intestazione con i nomi dei campi.")

    cod_i = cod_idxs[0]
    colli_i = None
    for i in colli_idxs:
        if i not in date_idxs and i != cod_i:
            colli_i = i
            break
    if colli_i is None:
        for i in range(len(parts0)):
            if i != cod_i and parts0[i].strip().isdigit():
                colli_i = i
                break

    d1_i, d2_i = date_idxs[0], date_idxs[1]

    candidates = [(i, len(parts0[i].strip())) for i in range(len(parts0)) if i not in {cod_i, colli_i, d1_i, d2_i} and parts0[i].strip()]
    dcdc_i = max(candidates, key=lambda x: x[1])[0] if candidates else 0

    def map_parts(parts):
        return {
            "CODARTFO": parts[cod_i] if cod_i < len(parts) else "",
            "COLLIORD": parts[colli_i] if colli_i < len(parts) else "",
            "DATA_ORDINE": parts[d1_i] if d1_i < len(parts) else "",
            "DATA_CONSEGNA": parts[d2_i] if d2_i < len(parts) else "",
            "DCDCEXCDE": parts[dcdc_i] if dcdc_i < len(parts) else "",
        }

    rows_out.append(map_parts(parts0))
    for ln in raw_lines[1:]:
        rows_out.append(map_parts(split_row(ln)))
    return rows_out

def _fetch_ordini_rossetto_rows():
    """Fetch rows for Rossetto order export.

    Priority:
    1) Offline test TXT (if present in ELAB_SOURCE_DIR)
    2) GoldReport connection (connections['goldreport'])

    Returns list[dict] with keys CODARTFO, COLLIORD, DATA_ORDINE, DATA_CONSEGNA, DCDCEXCDE.
    """
    # 1) Optional offline test mode
    txt_name = getattr(settings, "ORDINI_TXT_TEST_FILE", "dbo_t_OrdiniRossetto_giovedi.txt")
    source_dir = getattr(settings, "ELAB_SOURCE_DIR", "")
    if source_dir:
        txt_path = Path(source_dir) / txt_name
        if txt_path.exists():
            return _fetch_ordini_rossetto_rows_from_txt(str(txt_path))

    # 2) GoldReport
    candidates = [
        getattr(settings, "ORDINI_ROSSETTO_TABLE", ""),
        "dbo_t_OrdiniRossetto",
        "dbo.t_OrdiniRossetto",
        "dbo.dbo_t_OrdiniRossetto",
    ]
    candidates = [c for c in candidates if c]

    wanted = ["CODARTFO", "COLLIORD", "DATA_ORDINE", "DATA_CONSEGNA", "DCDCEXCDE"]

    last_err = None
    with connections["goldreport"].cursor() as cur:
        for table in candidates:
            # attempt explicit projection
            try:
                cur.execute(
                    f"SELECT CODARTFO, COLLIORD, DATA_ORDINE, DATA_CONSEGNA, DCDCEXCDE FROM {table}"
                )
                rows = cur.fetchall()
                out = []
                for r in rows:
                    out.append({
                        "CODARTFO": r[0],
                        "COLLIORD": r[1],
                        "DATA_ORDINE": r[2],
                        "DATA_CONSEGNA": r[3],
                        "DCDCEXCDE": r[4],
                    })
                return out
            except Exception as e:
                last_err = e

            # fallback: select * and map by column name
            try:
                cur.execute(f"SELECT * FROM {table}")
                cols = [c[0] for c in cur.description]
                idx = {c.upper(): i for i, c in enumerate(cols)}
                missing = [w for w in wanted if w not in idx]
                if missing:
                    raise RuntimeError(
                        f"Tabella {table}: colonne mancanti {missing} (trovate: {cols})"
                    )
                rows = cur.fetchall()
                out = []
                for r in rows:
                    out.append({k: r[idx[k]] for k in wanted})
                return out
            except Exception as e:
                last_err = e

    raise RuntimeError(
        f"Impossibile leggere dbo_t_OrdiniRossetto su connessione goldreport. Ultimo errore: {last_err}"
    )


def generate_ordine_ext_file(destination_dir: str) -> str:
    """Generate the Ordine.ext file (legacy Rossetto format) into destination_dir.

    Output record is 95 chars (as in legacy Access export):
      5 spaces + 0060235 + CODARTFO(7) + 32 spaces + COLLIORD(5 zero-pad)
      + DATA_ORDINE(yyyymmdd) + DATA_CONSEGNA(yyyymmdd) + DCDCEXCDE(6)
      + DATA_ORDINE(yyyymmdd) + progressivo(9 zero-pad)
    """
    os.makedirs(destination_dir, exist_ok=True)
    output_name = getattr(settings, "ORDER_EXT_FILENAME", "Ordine.ext")
    output_path = os.path.join(destination_dir, output_name)

    rows = _fetch_ordini_rossetto_rows()

    fixed_espr1 = " " * 5
    fixed_espr2 = "0060235"
    fixed_espr4 = " " * 32

    lines = []
    for i, r in enumerate(rows, start=1):
        codartfo = _safe_str(r.get("CODARTFO"))
        colliord = _safe_str(r.get("COLLIORD"))
        data_ordine = _format_ddmmyyyy_to_yyyymmdd(r.get("DATA_ORDINE"))
        data_consegna = _format_ddmmyyyy_to_yyyymmdd(r.get("DATA_CONSEGNA"))
        dcdcexcde = _safe_str(r.get("DCDCEXCDE"))

        espr3 = codartfo[:7]
        espr5 = colliord.strip()
        espr5 = espr5.zfill(5) if espr5.isdigit() else espr5.rjust(5, "0")[-5:]

        # Mid(DCDCEXCDE, 8, 6) in Access => python [7:13]
        espr8 = dcdcexcde[7:13].ljust(6)

        espr11 = str(i).zfill(9)

        line = (
            fixed_espr1 +
            fixed_espr2 +
            espr3 +
            fixed_espr4 +
            espr5 +
            data_ordine +
            data_consegna +
            espr8 +
            data_ordine +
            espr11
        )
        lines.append(line)

    # Write with CRLF, like legacy exports
    with open(output_path, "w", encoding="utf-8", newline="") as fp:
        for line in lines:
            fp.write(line)
            fp.write("\r\n")

    return output_path

def _save_uploaded_file_to_batch_folder(file_obj, batch_id: int) -> tuple[str, str]:
    """Salva una copia del file caricato in una cartella server-side per il batch.
    Ritorna (batch_folder, saved_filename).
    """
    root = getattr(settings, "IMPORT_FILES_DIR", os.path.join(os.path.dirname(__file__), "_import_files"))
    root = os.path.abspath(root)
    _ensure_dir(root)
    stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{batch_id}_{stamp}_{file_obj.name}"
    batch_folder = os.path.join(root, f"batch_{batch_id}_{stamp}")
    _ensure_dir(batch_folder)
    saved_path = os.path.join(batch_folder, safe_name)
    with open(saved_path, "wb") as out:
        for chunk in file_obj.chunks():
            out.write(chunk)
    return batch_folder, safe_name

@csrf_exempt
def dashboard_view(request):
    """
    Cruscotto unico:
    - GET: mostra form upload + lista batch; se ?batch=id mostra anche le righe di quel batch
    - POST: carica file, salva batch + righe, poi redirect su ?batch=<id>
    """
    # lista ultimi batch
    batches = ImportBatch.objects.order_by('-uploaded_at')[:50]

    selected_batch = None
    rows = None
    search_query = ""

    # batch selezionato via querystring
    batch_id = request.GET.get('batch')
    if batch_id:
        selected_batch = get_object_or_404(ImportBatch, pk=batch_id)


    # AUTO_SELECT_LATEST_BATCH: se non specificato ?batch=, usa l'ultimo batch caricato
    if (not batch_id) and batches:
        selected_batch = batches[0]
    if request.method == 'POST':
        # upload file .elab
        form = ElabUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            raw_bytes = f.read()
            text = decode_elab(raw_bytes)
            parsed_rows = parse_elab_text(text)

            batch = ImportBatch.objects.create(
                filename=f.name,
                raw_content=text,
            )

            # Salva una copia server-side del file importato (per ritrovare la cartella del batch)
            try:
                batch_folder, saved_name = _save_uploaded_file_to_batch_folder(f, batch.id)
                batch.import_dir = batch_folder
                batch.import_saved_name = saved_name
                batch.save(update_fields=['import_dir', 'import_saved_name'])
            except Exception:
                # Non bloccare l'import se la copia su disco fallisce
                pass

            objs = []
            for i, row in enumerate(parsed_rows, start=1):
                objs.append(ImportRow(
                    batch=batch,
                    line_number=i,
                    raw_line=row["raw_line"],
                    cod_art_fo=row["cod_art_fo"],
                    descrizione_articolo=row["descrizione_articolo"],
                    iva=row["iva"],
                    prz_acq=row["prz_acq"],
                    campo5=row["campo5"],
                    pz_x_crt=row["pz_x_crt"],
                    crt_x_str=row["crt_x_str"],
                    str_x_plt=row["str_x_plt"],
                    tot_colli=row["tot_colli"],
                    ean=row["ean"],
                ))
            if objs:
                ImportRow.objects.bulk_create(objs)

            url = reverse('importelab:dashboard')
            return redirect(f"{url}?batch={batch.id}")
    else:
        form = ElabUploadForm()

    # se ho un batch selezionato, recupero le sue righe con eventuale filtro di ricerca
    if selected_batch:
        qs = selected_batch.rows.all()
        search_query = (request.GET.get('q') or '').strip()
        if search_query:
            qs = qs.filter(
                Q(cod_art_fo__icontains=search_query) |
                Q(descrizione_articolo__icontains=search_query) |
                Q(ean__icontains=search_query)
            )
        rows = list(qs)

    gold_preview = None
    gold_sync_info = request.session.get('gold_sync_last')
    if request.GET.get('gold') == '1':
        gold_preview = get_preview_from_local(limit=5)

    
    intermediate_preview = None
    intermediate_info = request.session.get('intermediate_last')
    if request.GET.get('inter') == '1' and selected_batch:
        intermediate_preview = get_intermediate_previews(selected_batch, limit=5)
    context = {
        'form': form,
        'batches': batches,
        'selected_batch': selected_batch,
        'rows': rows,
        'search_query': search_query,
        'gold_preview': gold_preview,
        'gold_sync_info': gold_sync_info,
        'intermediate_preview': intermediate_preview,
        'intermediate_info': intermediate_info,
    }
    return render(request, 'importelab/dashboard.html', context)
def _normalize_codart_key(value):
    """Return normalized string keys for matching CODART across sources."""
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    keys = [s]
    keys.append(s.lstrip("0") or "0")
    try:
        i = int(float(s))
        keys.append(str(i))
    except Exception:
        pass
    # unique preserve order
    out=[]
    for k in keys:
        if k not in out:
            out.append(k)
    return out


def _rossetto_index_by_codart():
    """Index GoldTableSnapshot rows (source_table dbo.t_Rossetto) by CODART with robust normalization."""
    index = {}
    qs = GoldTableSnapshot.objects.filter(source_table='dbo.t_Rossetto').only('payload')
    for snap in qs.iterator(chunk_size=5000):
        p = snap.payload or {}
        codart = p.get('CODART') or p.get('CodArt') or p.get('codart')
        # normalize fields used in reports
        p_norm = dict(p)
        p_norm['stato'] = p.get('STATO') or p.get('Stato') or ''
        p_norm['descrccom'] = p.get('DESCRCCOM') or p.get('DescrCCOM') or ''
        p_norm['ccom'] = p.get('CCOM') or p.get('Ccom') or ''
        p_norm['dta_aggio'] = p.get('DTAAGGIO') or p.get('DtaAggio') or ''
        p_norm['descrart'] = p.get('DESCRART') or p.get('DescrArt') or ''
        for k in _normalize_codart_key(codart):
            index[k] = p_norm
    return index


def _rossetto_get(index, codart):
    for k in _normalize_codart_key(codart):
        r = index.get(k)
        if r is not None:
            return r
    return None

@csrf_exempt
@require_http_methods(["GET", "POST"])
def delete_batch_view(request, pk: int):
    """
    Conferma ed elimina un batch (e tutte le sue righe correlate).
    """
    batch = get_object_or_404(ImportBatch, pk=pk)

    if request.method == "POST":
        batch.delete()
        return redirect(reverse('importelab:dashboard'))

    rows_count = batch.rows.count()
    return render(
        request,
        'importelab/confirm_delete.html',
        {'batch': batch, 'rows_count': rows_count},
    )

@csrf_exempt
@require_http_methods(["POST"])
def sync_gold_view(request):
    """Sync Gold SQL Server tables into local SQLite snapshots and redirect back with preview."""
    limit = getattr(settings, 'GOLD_SYNC_LIMIT', 0)
    summaries = sync_gold_tables(limit=limit)
    # store a lightweight message in session
    request.session['gold_sync_last'] = {
        'synced_at': datetime.now().isoformat(timespec='seconds'),
        'summary': {k: {'rows_fetched': v['rows_fetched']} for k, v in summaries.items()},
    }
    request.session.modified = True
    url = reverse('importelab:dashboard')
    return redirect(f"{url}?gold=1")

@csrf_exempt
@require_http_methods(["POST"])
def regen_intermediate_view(request):
    """Rigenera le 3 query intermedie per il batch selezionato e torna in dashboard con preview."""
    batch_id = request.POST.get('batch_id') or request.GET.get('batch')
    batch = None
    if batch_id:
        batch = get_object_or_404(ImportBatch, pk=batch_id)
    else:
        batch = ImportBatch.objects.order_by('-uploaded_at').first()
        if not batch:
            url = reverse('importelab:dashboard')
            return redirect(url)

    counts = rebuild_intermediate_queries(batch)
    request.session['intermediate_last'] = {
        'batch_id': batch.id,
        'filename': batch.filename,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'counts': counts,
    }

    url = reverse('importelab:dashboard')
    return redirect(f"{url}?batch={batch.id}&inter=1")



# -----------------------------
# REPORTS (HTML + PDF)
# -----------------------------

def _get_batch_from_request(request):
    batch_id = request.GET.get('batch')
    if batch_id:
        return get_object_or_404(ImportBatch, pk=batch_id)
    return ImportBatch.objects.order_by('-uploaded_at').first()

def _get_batch_from_request_or_latest(request):
    """Backward-compatible helper for report views."""
    return _get_batch_from_request(request)

def _draw_pdf_header(c, title, print_date, page_num):
    from reportlab.lib.units import mm
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20*mm, 280*mm, title)
    c.setFont("Helvetica", 9)
    c.drawRightString(190*mm, 280*mm, f"Data stampa: {print_date}")
    c.setFont("Helvetica", 8)
    c.drawRightString(190*mm, 10*mm, f"Pagina {page_num}")


def _pdf_new_page(c, title, print_date, page_num):
    from reportlab.lib.units import mm
    c.showPage()
    _draw_pdf_header(c, title, print_date, page_num)
    return 270*mm  # y start


def report_r_aggprezziacq_view(request):
    batch = _get_batch_from_request(request)
    base_rows = list(IntermediateAggPrAcq.objects.filter(batch=batch)) if batch else []
    rows = []
    for r in base_rows:
        codfo = r.ccom
        rows.append({
            'dtaaggio': r.dta_aggio,
            'cod_art_fo': r.cod_art_fo,
            'codart': r.codart,
            'descrart': r.descrart,
            'stato': r.stato,
            'cidac_prezzo': r.cidac_prezzo,
            'az': r.az,
            'ros_pracq': r.ros_pracq,
            'ros_iva': r.ros_iva,
            'ccom': codfo,
            'codfo': int(codfo) if str(codfo).isdigit() else codfo,
            'descrccom': r.descrccom,
        })
    # ordering similar to Access report: by DTAAGGIO then CodFo then Rep/SRep/CCOM when available
    rows.sort(key=lambda x: (str(x.get('dtaaggio','')), str(x.get('codfo','')), str(x.get('cod_art_fo',''))))

    ctx = {
        'title': 'Aggiornamento Prezzi di listino Rossetto',
        'batch': batch,
        'rows': rows,
        'rows_count': len(rows),
        'print_date': timezone.now().strftime('%d/%m/%Y'),
        'pdf_url': f"{reverse('importelab:report_r_aggprezziacq_pdf')}?batch={batch.id}" if batch else "#",
    }
    return render(request, 'importelab/report_r_aggprezziacq.html', ctx)


def report_r_aggprezziacq_pdf_view(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    batch = _get_batch_from_request(request)
    rows = list(IntermediateAggPrAcq.objects.filter(batch=batch)) if batch else []

    resp = HttpResponse(content_type='application/pdf')
    fname = f"r_AggPrezziAcq_batch{batch.id if batch else 'NA'}.pdf"
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'

    c = canvas.Canvas(resp, pagesize=A4)
    print_date = timezone.now().strftime('%d/%m/%Y')
    page_num = 1
    _draw_pdf_header(c, "Aggiornamento Prezzi di listino Rossetto", print_date, page_num)

    y = 270*mm
    c.setFont("Helvetica", 9)
    if batch:
        c.drawString(20*mm, y, f"Batch: {batch.filename} ({batch.uploaded_at:%d/%m/%Y %H:%M})")
        y -= 8*mm

    # Prepara righe + ordinamento (Access: raggruppa per DataAgg, poi CodFo)
    prepared = []
    for r in rows:
        codfo_val = (int(r.ccom) if getattr(r, 'ccom', '').strip().isdigit() else getattr(r, 'ccom', ''))
        prepared.append({
            'dtaaggio': r.dta_aggio or '',
            'codfo': codfo_val,
            'descrccom': r.descrccom or '',
            'codart': r.codart,
            'cod_art_fo': r.cod_art_fo,
            'stato': r.stato,
            'descrart': r.descrart,
            'cidac_prezzo': r.cidac_prezzo,
            'ros_pracq': r.ros_pracq,
            'ros_iva': r.ros_iva,
        })
    prepared.sort(key=lambda x: (str(x['dtaaggio']), str(x['codfo']), str(x['cod_art_fo'])))

    current_date = None
    current_codfo = None

    for r in prepared:
        if r['dtaaggio'] != current_date:
            current_date = r['dtaaggio']
            current_codfo = None
            # Header DataAgg
            if y < 30*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento Prezzi di listino Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(20*mm, y, f"Data Agg.: {current_date}")
            y -= 7*mm

        if r['codfo'] != current_codfo:
            current_codfo = r['codfo']
            if y < 28*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento Prezzi di listino Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20*mm, y, f"CodFo {current_codfo}  {r.get('descrccom','')}")
            y -= 6*mm
            c.setFont("Helvetica", 9)

        lines = [
            f"CodArticolo: {r['codart']}  |  CodArtFo: {r['cod_art_fo']}  |  Stato: {r['stato']}",
            f"{r['descrart']}",
            f"Prezzo CIDAC {r['cidac_prezzo']}  --->  Ros PrAcq {r['ros_pracq']}  IVA {r['ros_iva']}",
        ]
        for line in lines:
            wrapped = simpleSplit(line, "Helvetica", 9, 170*mm)
            for w in wrapped:
                if y < 20*mm:
                    page_num += 1
                    y = _pdf_new_page(c, "Aggiornamento Prezzi di listino Rossetto", print_date, page_num)
                    y -= 10*mm
                c.drawString(20*mm, y, w)
                y -= 5*mm
        y -= 4*mm

    c.save()
    return resp


def report_r_aggean_view(request):
    batch = _get_batch_from_request(request)
    base_rows = list(IntermediateAggiornaEan.objects.filter(batch=batch)) if batch else []

    ros_idx = _rossetto_index_by_codart_v2()
    rows = []
    for r in base_rows:
        ros = _rossetto_get(ros_idx, r.codart)
        if not ros:
            # Access report uses INNER JOIN with Rossetto: if no match, the row is excluded
            continue
        codfo_raw = ros.get("ccom") or ""
        codfo = int(codfo_raw) if str(codfo_raw).isdigit() else (codfo_raw or "")
        dta = ros.get("dtaaggio") or ""
        rows.append({
            "dtaaggio": dta,
            "codfo": codfo,
            "descrccom": ros.get("descrccom") or "",
            "stato": ros.get("stato") or "",
            "ean": r.ean or "",
            "codart": r.codart or "",
            "cod_art_fo": r.cod_art_fo or "",
            "descrart": ros.get("descrart") or r.descrizione_articolo or "",
        })

    # Access report ordering appears to follow CODART descending within CodFo (as in sample)
    def _codart_int(v):
        try:
            return int(str(v).strip())
        except Exception:
            return -1

    rows.sort(key=lambda x: (
        str(x.get("codfo") or ""),
        -_codart_int(x.get("codart")),
        str(x.get("cod_art_fo") or ""),
        str(x.get("ean") or ""),
    ))

    data_agg = rows[0]["dtaaggio"] if rows else ""
    print_date = timezone.now().strftime("%d/%m/%Y")

    ctx = {
        "title": "Aggiornamento EAN Rossetto",
        "print_date": print_date,
        "batch": batch,
        "rows": rows,
        "rows_count": len(rows),
        "data_agg": data_agg,
        "pdf_url": reverse("importelab:report_r_aggean_pdf") + (f"?batch={batch.id}" if batch else ""),
    }
    return render(request, "importelab/report_r_aggean.html", ctx)

def report_r_aggean_pdf_view(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    batch = _get_batch_from_request(request)
    ros_idx = _rossetto_index_by_codart()
    base_rows = list(IntermediateAggiornaEan.objects.filter(batch=batch)) if batch else []

    resp = HttpResponse(content_type='application/pdf')
    fname = f"r_AggEAN_batch{batch.id if batch else 'NA'}.pdf"
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'

    c = canvas.Canvas(resp, pagesize=A4)
    print_date = timezone.now().strftime('%d/%m/%Y')
    page_num = 1
    _draw_pdf_header(c, "Aggiornamento EAN Rossetto", print_date, page_num)
    y = 270*mm

    c.setFont("Helvetica", 9)
    if batch:
        c.drawString(20*mm, y, f"Batch: {batch.filename} ({batch.uploaded_at:%d/%m/%Y %H:%M})")
        y -= 8*mm

    # Prepara righe + ordinamento (Access: raggruppa per DataAgg, poi CodFo)
    prepared = []
    for r in base_rows:
        p = ros_idx.get((r.codart or '').strip(), {})
        codfo = p.get('CCOM')
        descrccom = p.get('DESCRCCOM', '')
        descrart = p.get('DESCRART', r.descrizione_articolo)
        stato = p.get('STATO', '')
        dtaaggio = p.get('DTAAGGIO', '')
        prepared.append({
            'dtaaggio': dtaaggio or '',
            'codfo': int(codfo) if str(codfo).isdigit() else codfo,
            'descrccom': descrccom,
            'codart': r.codart,
            'cod_art_fo': r.cod_art_fo,
            'stato': stato,
            'descrart': descrart,
            'ean': r.ean,
        })
    prepared.sort(key=lambda x: (str(x['dtaaggio']), str(x['codfo']), str(x['cod_art_fo']), str(x['codart'])))

    current_date = None
    current_codfo = None

    for r in prepared:
        if r['dtaaggio'] != current_date:
            current_date = r['dtaaggio']
            current_codfo = None
            if y < 30*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento EAN Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(20*mm, y, f"Data Agg.: {current_date}")
            y -= 7*mm

        if r['codfo'] != current_codfo:
            current_codfo = r['codfo']
            if y < 28*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento EAN Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20*mm, y, f"CodFo {current_codfo}  {r.get('descrccom','')}")
            y -= 6*mm
            c.setFont("Helvetica", 9)

        lines = [
            f"CodArticolo: {r['codart']}  |  CodArtFo: {r['cod_art_fo']}  |  Stato: {r['stato']}",
            f"{r['descrart']}",
            f"AGGIUNGERE  --->  {r['ean']}",
        ]
        for line in lines:
            for w in simpleSplit(line, "Helvetica", 9, 170*mm):
                if y < 20*mm:
                    page_num += 1
                    y = _pdf_new_page(c, "Aggiornamento EAN Rossetto", print_date, page_num)
                    y -= 10*mm
                c.drawString(20*mm, y, w)
                y -= 5*mm
        y -= 4*mm

    c.save()
    return resp


def report_r_agglogistica_view(request):
    batch = _get_batch_from_request(request)
    base_rows = list(IntermediateAggiornamentiVari.objects.filter(batch=batch)) if batch else []

    ros_idx = _rossetto_index_by_codart_v2()
    rows = []
    for r in base_rows:
        ros = _rossetto_get(ros_idx, r.codart)
        # Access query uses LEFT JOIN to Rossetto in the report dataset, so keep row even if ros is missing
        codfo_raw = (ros.get("ccom") if ros else "") or ""
        codfo = int(codfo_raw) if str(codfo_raw).isdigit() else (codfo_raw or "")
        dta = (ros.get("dtaaggio") if ros else "") or ""
        rows.append({
            "dtaaggio": dta,
            "codfo": codfo,
            "descrccom": (ros.get("descrccom") if ros else "") or "",
            "stato": (ros.get("stato") if ros else "") or "",
            "codart": r.codart or "",
            "cod_art_fo": r.cod_art_fo or "",
            "descrizione_articolo": r.descrizione_articolo or "",
            "pzxcrt": r.cidac_pz_x_crt or "",
            "agg_pz_x_crt": r.agg_pz_x_crt or "",
            "r_pz_x_crt": r.r_pz_x_crt or "",
            "strato": r.cidac_crt_x_str or "",
            "agg_crt_x_str": r.agg_crt_x_str or "",
            "r_crt_x_str": r.r_crt_x_str or "",
            "pallet": r.cidac_str_x_plt or "",
            "agg_str_x_plt": r.agg_str_x_plt or "",
            "r_str_x_plt": r.r_str_x_plt or "",
        })

    def _codart_int(v):
        try:
            return int(str(v).strip())
        except Exception:
            return 0

    rows.sort(key=lambda x: (
        str(x.get("codfo") or ""),
        _codart_int(x.get("codart")),
        str(x.get("cod_art_fo") or ""),
    ))

    data_agg = rows[0]["dtaaggio"] if rows else ""
    print_date = timezone.now().strftime("%d/%m/%Y")

    ctx = {
        "title": "Aggiornamento Logistica Rossetto",
        "print_date": print_date,
        "batch": batch,
        "rows": rows,
        "rows_count": len(rows),
        "data_agg": data_agg,
        "pdf_url": reverse("importelab:report_r_agglogistica_pdf") + (f"?batch={batch.id}" if batch else ""),
    }
    return render(request, "importelab/report_r_agglogistica.html", ctx)

def report_r_agglogistica_pdf_view(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    batch = _get_batch_from_request(request)
    ros_idx = _rossetto_index_by_codart()
    base_rows = list(IntermediateAggiornamentiVari.objects.filter(batch=batch)) if batch else []

    resp = HttpResponse(content_type='application/pdf')
    fname = f"r_AggLogistica_batch{batch.id if batch else 'NA'}.pdf"
    resp['Content-Disposition'] = f'attachment; filename="{fname}"'

    c = canvas.Canvas(resp, pagesize=A4)
    print_date = timezone.now().strftime('%d/%m/%Y')
    page_num = 1
    _draw_pdf_header(c, "Aggiornamento Logistica Rossetto", print_date, page_num)
    y = 270*mm

    c.setFont("Helvetica", 9)
    if batch:
        c.drawString(20*mm, y, f"Batch: {batch.filename} ({batch.uploaded_at:%d/%m/%Y %H:%M})")
        y -= 8*mm

    # Prepara righe + ordinamento (Access: raggruppa per DataAgg, poi CodFo)
    prepared = []
    for r in base_rows:
        p = ros_idx.get((r.codart or '').strip(), {})
        codfo = p.get('CCOM')
        descrccom = p.get('DESCRCCOM', '')
        stato = p.get('STATO', '')
        dtaaggio = p.get('DTAAGGIO', '')
        prepared.append({
            'dtaaggio': dtaaggio or '',
            'codfo': int(codfo) if str(codfo).isdigit() else codfo,
            'descrccom': descrccom,
            'codart': r.codart,
            'cod_art_fo': r.cod_art_fo,
            'stato': stato,
            'descrizione_articolo': r.descrizione_articolo,
            'cidac_pz_x_crt': r.cidac_pz_x_crt,
            'agg_pz_x_crt': r.agg_pz_x_crt,
            'r_pz_x_crt': r.r_pz_x_crt,
            'cidac_crt_x_str': r.cidac_crt_x_str,
            'agg_crt_x_str': r.agg_crt_x_str,
            'r_crt_x_str': r.r_crt_x_str,
            'cidac_str_x_plt': r.cidac_str_x_plt,
            'agg_str_x_plt': r.agg_str_x_plt,
            'r_str_x_plt': r.r_str_x_plt,
        })
    prepared.sort(key=lambda x: (str(x['dtaaggio']), str(x['codfo']), str(x['cod_art_fo']), str(x['codart'])))

    current_date = None
    current_codfo = None

    for r in prepared:
        if r['dtaaggio'] != current_date:
            current_date = r['dtaaggio']
            current_codfo = None
            if y < 30*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento Logistica Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(20*mm, y, f"Data Agg.: {current_date}")
            y -= 7*mm

        if r['codfo'] != current_codfo:
            current_codfo = r['codfo']
            if y < 28*mm:
                page_num += 1
                y = _pdf_new_page(c, "Aggiornamento Logistica Rossetto", print_date, page_num)
                y -= 10*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20*mm, y, f"CodFo {current_codfo}  {r.get('descrccom','')}")
            y -= 6*mm
            c.setFont("Helvetica", 9)

        lines = [
            f"CodArticolo: {r['codart']}  |  CodArtFo: {r['cod_art_fo']}  |  Stato: {r['stato']}",
            f"{r['descrizione_articolo']}",
            f"PezziXCartone: {r['cidac_pz_x_crt']} ---> {r['r_pz_x_crt']}  {r['agg_pz_x_crt'] or ''}",
            f"CartoniXStrato: {r['cidac_crt_x_str']} ---> {r['r_crt_x_str']}  {r['agg_crt_x_str'] or ''}",
            f"StratoXPallet: {r['cidac_str_x_plt']} ---> {r['r_str_x_plt']}  {r['agg_str_x_plt'] or ''}",
        ]
        for line in lines:
            for w in simpleSplit(line, "Helvetica", 9, 170*mm):
                if y < 20*mm:
                    page_num += 1
                    y = _pdf_new_page(c, "Aggiornamento Logistica Rossetto", print_date, page_num)
                    y -= 10*mm
                c.drawString(20*mm, y, w)
                y -= 5*mm
        y -= 4*mm

    c.save()
    return resp

@csrf_exempt
@require_http_methods(["GET", "POST"])
def ordine_email_view(request):
    """Simula la creazione di una mail (stile Access) allegando automaticamente un file .ext.

    In assenza di Outlook installato, genera un file .eml scaricabile (non invia nulla).

    In versione portale l'allegato è il file reale <Ordine.ext>, generato (se necessario)
    direttamente da GoldReport senza tabelle di transito (versione A).
    La cartella di riferimento è quella configurata in settings.py (ELAB_SOURCE_DIR),
    che corrisponde alla cartella di lavoro dell'operatore (es. C:\\Paolo).
    """
    message = None
    error = None

    # individua ultimo batch importato (informativo)
    last_batch = ImportBatch.objects.order_by('-uploaded_at').first()
    if not last_batch:
        error = "Nessun batch importato trovato. Importa prima un file .elab."
        form = OrderEmailForm()
        return render(request, "importelab/ordine_email.html", {"form": form, "message": message, "error": error})

    # Cartella sorgente configurata (es. C:\Paolo)
    source_dir = (getattr(settings, "ELAB_SOURCE_DIR", "") or "").strip()
    if not source_dir:
        # fallback: usa la cartella batch (server-side) se ELAB_SOURCE_DIR non è configurata
        source_dir = (last_batch.import_dir or getattr(settings, "IMPORT_FILES_DIR", "")).strip()
    if not source_dir:
        # fallback finale: cartella progetto
        source_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "_import_files"))
    source_dir = os.path.abspath(source_dir)
    os.makedirs(source_dir, exist_ok=True)

    # In versione portale: l'allegato deve essere il vero file Ordine.ext
    # generato a partire da dbo_t_OrdiniRossetto su connessione 'goldreport'.
    order_name = getattr(settings, "ORDER_EXT_FILENAME", "Ordine.ext")
    attachment_path = os.path.join(source_dir, order_name)

    # Se il file non esiste ancora, lo generiamo ora (versione A: niente tabelle transito)
    if not os.path.exists(attachment_path):
        try:
            attachment_path = generate_ordine_ext_file(source_dir)
        except Exception as e:
            error = f"Impossibile generare '{order_name}' da GoldReport: {e}"
            form = OrderEmailForm()
            return render(request, "importelab/ordine_email.html", {"form": form, "message": message, "error": error})

    if request.method == "POST":
        # Specifiche replicate da Access
        to = "ordini@rossettogroup.it"
        subject = "Gros Cidac: in allegato il nostro ordine "
        body = (
            " Buongiorno, \n"
            " inviamo in allegato il file con l'ordine.\n"
            " Rimaniamo a disposizione per eventuali problematiche\n"
            " Grazie e Buon Lavoro \n"
            "\n"
        )

        # Simulazione senza Outlook: genera un .eml scaricabile
        try:
            with open(attachment_path, "rb") as fp:
                attachment_bytes = fp.read()

            eml = EmailMessage(policy=email_default_policy)
            eml["To"] = to
            eml["Subject"] = subject
            # From: se configurato nelle settings, altrimenti placeholder
            eml["From"] = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
            eml.set_content(body)
            eml.add_attachment(
                attachment_bytes,
                maintype="application",
                subtype="octet-stream",
                filename=os.path.basename(attachment_path),
            )

            # Serializza in bytes
            eml_bytes = eml.as_bytes()

            # Salva una copia su disco per audit/debug
            outbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "_outbox"))
            os.makedirs(outbox_dir, exist_ok=True)
            stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            eml_name = f"ordine_{stamp}.eml"
            eml_path = os.path.join(outbox_dir, eml_name)
            with open(eml_path, "wb") as out:
                out.write(eml_bytes)

            resp = HttpResponse(eml_bytes, content_type="message/rfc822")
            resp["Content-Disposition"] = f'attachment; filename="{eml_name}"'
            return resp
        except Exception as e:
            error = f"Errore durante la generazione del file .eml: {e}"

    form = OrderEmailForm()
    return render(
        request,
        "importelab/ordine_email.html",
        {
            "form": form,
            "message": message,
            "error": error,
            "last_batch": last_batch,
            "attachment_path": attachment_path,
            "source_dir": source_dir,
        },
    )
