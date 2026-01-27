from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Tuple

from django.db import transaction

from .models import (
    GoldTableSnapshot,
    ImportBatch,
    ImportRow,
    IntermediateAggPrAcq,
    IntermediateAggiornaEan,
    IntermediateAggiornamentiVari,
)

# Gold source table names (as stored in GoldTableSnapshot.source_table)
T_ROSSETTO = 'dbo.t_Rossetto'
T_EAN = 'dbo.t_t_Ean'


def _to_decimal(v: Any) -> Decimal | None:
    if v is None or v == '':
        return None
    try:
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None or v == '':
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        try:
            return int(float(v))
        except Exception:
            return None


def _get_payload_value(payload: Dict[str, Any], *keys: str) -> Any:
    """Return first matching key from payload (case-insensitive support)."""
    if not payload:
        return None
    lower_map = {str(k).lower(): k for k in payload.keys()}
    for k in keys:
        if k in payload:
            return payload[k]
        lk = str(k).lower()
        if lk in lower_map:
            return payload[lower_map[lk]]
    return None


def _load_rossetto_index() -> Dict[str, Dict[str, Any]]:
    """Index dbo.t_Rossetto by CODARTFO."""
    out: Dict[str, Dict[str, Any]] = {}
    qs = GoldTableSnapshot.objects.filter(source_table=T_ROSSETTO).only('payload')
    for snap in qs.iterator(chunk_size=2000):
        p = snap.payload or {}
        codartfo = _get_payload_value(p, 'CODARTFO', 'CodArtFo', 'codartfo')
        if codartfo is None:
            continue
        out[str(codartfo).strip()] = p
    return out


def _load_ean_set() -> set[str]:
    """Load all EAN values from dbo.t_t_Ean (field EANA)."""
    s: set[str] = set()
    qs = GoldTableSnapshot.objects.filter(source_table=T_EAN).only('payload')
    for snap in qs.iterator(chunk_size=5000):
        p = snap.payload or {}
        eana = _get_payload_value(p, 'EANA', 'EAN', 'Ean', 'eana')
        if eana is None:
            continue
        e = str(eana).strip()
        if e:
            s.add(e)
    return s


def rebuild_intermediate_queries(batch: ImportBatch) -> Dict[str, int]:
    """Rigenera le 3 query intermedie per il batch dato usando le snapshot Gold in SQLite."""
    ros_idx = _load_rossetto_index()
    ean_set = _load_ean_set()

    rows = ImportRow.objects.filter(batch=batch).only(
        'cod_art_fo', 'descrizione_articolo', 'ean', 'iva', 'prz_acq', 'pz_x_crt', 'crt_x_str', 'str_x_plt'
    )

    q1_objs: List[IntermediateAggPrAcq] = []
    q2_objs: List[IntermediateAggiornaEan] = []
    q3_objs: List[IntermediateAggiornamentiVari] = []

    for r in rows.iterator(chunk_size=2000):
        cod_fo = (r.cod_art_fo or '').strip()
        if not cod_fo:
            continue

        ros = ros_idx.get(cod_fo)
        if not ros:
            continue

        # --- Q1: q_AggPrAcqu (PRACQ diverso)
        ros_pracq = r.prz_acq
        cidac_pracq_raw = _get_payload_value(ros, 'PRACQ')
        cidac_pracq = _to_decimal(cidac_pracq_raw)
        if cidac_pracq is not None and ros_pracq is not None and cidac_pracq != ros_pracq:
            q1_objs.append(IntermediateAggPrAcq(
                batch=batch,
                dta_aggio=str(_get_payload_value(ros, 'DTAAGGIO') or ''),
                cod_art_fo=cod_fo,
                codart=str(_get_payload_value(ros, 'CODART') or ''),
                descrart=str(_get_payload_value(ros, 'DESCRART') or ''),
                stato=str(_get_payload_value(ros, 'STATO') or ''),
                cidac_prezzo=str(cidac_pracq_raw or ''),
                az='Agg',
                ros_pracq=ros_pracq,
                sett=str(_get_payload_value(ros, 'SETT') or ''),
                rep=str(_get_payload_value(ros, 'REP') or ''),
                srep=str(_get_payload_value(ros, 'SREP') or ''),
                ccom=str(_get_payload_value(ros, 'CCOM') or ''),
                descrccom=str(_get_payload_value(ros, 'DESCRCCOM') or ''),
                ros_iva=r.iva,
                cidac_iva=_to_int(_get_payload_value(ros, 'IVA')),
            ))

        # --- Q2: q_AggiornaEan (EAN dell'elab non presente in dbo_t_t_Ean)
        ean = (r.ean or '').strip()
        if ean and ean not in ean_set:
            q2_objs.append(IntermediateAggiornaEan(
                batch=batch,
                cod_art_fo=cod_fo,
                descrizione_articolo=r.descrizione_articolo or '',
                ean=ean,
                codart=str(_get_payload_value(ros, 'CODART') or ''),
            ))

        # --- Q3: q_AggiornamentiVari
        # Conditions from Access:
        # (PzXCrt diff AND ETICEAN=1) OR (CrtXstr diff) OR (StrXplt diff)
        cidac_pzxcrt = _to_int(_get_payload_value(ros, 'PZXCRT'))
        cidac_strato = _to_int(_get_payload_value(ros, 'STRATO'))
        cidac_pallet = _to_int(_get_payload_value(ros, 'PALLET'))
        eticean = _to_int(_get_payload_value(ros, 'ETICEAN'))  # 1 means true

        rpzxcrt = r.pz_x_crt
        rcrtstr = r.crt_x_str
        rstrplt = r.str_x_plt

        diff_pzxcrt = (rpzxcrt is not None and cidac_pzxcrt is not None and (rpzxcrt - cidac_pzxcrt) != 0)
        diff_crtstr = (rcrtstr is not None and cidac_strato is not None and (rcrtstr - cidac_strato) != 0)
        diff_strplt = (rstrplt is not None and cidac_pallet is not None and (rstrplt - cidac_pallet) != 0)

        cond = (diff_pzxcrt and eticean == 1) or diff_crtstr or diff_strplt
        if cond:
            q3_objs.append(IntermediateAggiornamentiVari(
                batch=batch,
                cod_art_fo=cod_fo,
                codart=str(_get_payload_value(ros, 'CODART') or ''),
                descrizione_articolo=r.descrizione_articolo or '',
                ean=ean,
                cidac_pz_x_crt=cidac_pzxcrt,
                agg_pz_x_crt='AGG' if diff_pzxcrt else '',
                r_pz_x_crt=rpzxcrt,
                cidac_crt_x_str=cidac_strato,
                agg_crt_x_str='AGG' if diff_crtstr else '',
                r_crt_x_str=rcrtstr,
                r_str_x_plt=rstrplt,
                cidac_str_x_plt=cidac_pallet,
                agg_str_x_plt='AGG' if diff_strplt else '',
            ))

    with transaction.atomic():
        IntermediateAggPrAcq.objects.filter(batch=batch).delete()
        IntermediateAggiornaEan.objects.filter(batch=batch).delete()
        IntermediateAggiornamentiVari.objects.filter(batch=batch).delete()

        if q1_objs:
            IntermediateAggPrAcq.objects.bulk_create(q1_objs, batch_size=1000)
        if q2_objs:
            IntermediateAggiornaEan.objects.bulk_create(q2_objs, batch_size=1000)
        if q3_objs:
            IntermediateAggiornamentiVari.objects.bulk_create(q3_objs, batch_size=1000)

    return {
        'q_AggPrAcqu': len(q1_objs),
        'q_AggiornaEan': len(q2_objs),
        'q_AggiornamentiVari': len(q3_objs),
    }


def get_intermediate_previews(batch: ImportBatch, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """Return first N rows for each intermediate table as list of dicts (for UI preview)."""
    def _model_to_dict(obj: Any, fields: Tuple[str, ...]) -> Dict[str, Any]:
        return {f: getattr(obj, f) for f in fields}

    q1 = IntermediateAggPrAcq.objects.filter(batch=batch).order_by('rep', 'srep', 'ccom', 'cod_art_fo')[:limit]
    q2 = IntermediateAggiornaEan.objects.filter(batch=batch).order_by('descrizione_articolo', 'cod_art_fo')[:limit]
    q3 = IntermediateAggiornamentiVari.objects.filter(batch=batch).order_by('cod_art_fo')[:limit]

    return {
        'q_AggPrAcqu': [_model_to_dict(o, (
            'dta_aggio','cod_art_fo','codart','descrart','stato','cidac_prezzo','az','ros_pracq',
            'sett','rep','srep','ccom','descrccom','ros_iva','cidac_iva'
        )) for o in q1],
        'q_AggiornaEan': [_model_to_dict(o, ('cod_art_fo','descrizione_articolo','ean','codart')) for o in q2],
        'q_AggiornamentiVari': [_model_to_dict(o, (
            'cod_art_fo','codart','descrizione_articolo','ean',
            'cidac_pz_x_crt','agg_pz_x_crt','r_pz_x_crt',
            'cidac_crt_x_str','agg_crt_x_str','r_crt_x_str',
            'r_str_x_plt','cidac_str_x_plt','agg_str_x_plt'
        )) for o in q3],
    }
