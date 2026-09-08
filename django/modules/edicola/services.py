from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.db import connections, transaction

from .models import EdicolaLog, EdicolaPrincipale, SalvaPrinc


@dataclass
class RefreshResult:
    ok: bool
    inserted: int = 0
    backed_up: int = 0
    updated_dates: int = 0
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def _log(message: str, level: str = "INFO", details: str | None = None) -> None:
    EdicolaLog.objects.create(level=level, message=message, details=details)


def get_source_view_name() -> str:
    """Nome della vista/tabella GoldReport da cui leggere (configurabile)."""
    return getattr(settings, "EDICOLA_SOURCE_VIEW", "dbo.v_AssoEdicola46")


def fetch_edicola_rows_from_goldreport(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Legge righe dalla vista GoldReport (dbo.v_AssoEdicola46).

    Restituisce una lista di dict con le chiavi coerenti con i campi di EdicolaPrincipale.
    """
    view_name = get_source_view_name()

    # Nota: con SQL Server TOP richiede un intero.
    top = f"TOP {int(limit)}" if limit else ""

    sql = f"""
        SELECT {top}
            DTAAGGIO, SETT, REP, SREP, CCOM, DESCC,
            CODART, DESCRART, EANPRINC, TIPOEAN, STATO,
            PREZZOVEND, GIACENZA_PDV, EAN
        FROM {view_name}
    """.strip()

    rows: List[Dict[str, Any]] = []
    with connections["goldreport"].cursor() as cursor:
        cursor.execute(sql)
        cols = [c[0].lower() for c in cursor.description]
        for r in cursor.fetchall():
            d = dict(zip(cols, r))
            # normalizza nomi
            rows.append(
                {
                    "dtaaggio": d.get("dtaaggio"),
                    "sett": d.get("sett"),
                    "rep": d.get("rep"),
                    "srep": d.get("srep"),
                    "ccom": d.get("ccom"),
                    "descc": d.get("descc"),
                    "codart": d.get("codart"),
                    "descrart": d.get("descrart"),
                    "eanprinc": d.get("eanprinc"),
                    "tipoean": d.get("tipoean"),
                    "stato": d.get("stato"),
                    "prezzovend": d.get("prezzovend"),
                    "giacenza_pdv": d.get("giacenza_pdv"),
                    "ean": str(d.get("ean")) if d.get("ean") is not None else None,
                }
            )
    return rows


def _norm_key_part(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _make_preserve_key(codart: Any, ean: Any) -> tuple[str, str]:
    return (_norm_key_part(codart), _norm_key_part(ean))


def refresh_principale_from_goldreport(*, limit: Optional[int] = None) -> RefreshResult:
    """Aggiorna la tabella principale leggendo i dati dalla vista GoldReport.

    - Prezzo V. viene riallineato da GoldReport.
    - Data viene preservata localmente quando esiste già nell'app.

    La preservazione usa una chiave normalizzata (codart, ean), perché in SQL Server
    ed in Django i valori possono arrivare con formattazioni leggermente diverse
    (spazi o conversioni implicite a stringa).
    """

    try:
        with transaction.atomic():
            backed_up = 0

            existing_dates = {
                _make_preserve_key(obj.codart, obj.ean): obj.data
                for obj in EdicolaPrincipale.objects.exclude(data__isnull=True).only("codart", "ean", "data")
            }
            preserved_candidates = len(existing_dates)
            if preserved_candidates:
                _log(f"Date locali da preservare: {preserved_candidates}")

            _log("(1/2) Svuota: delete di edicola_principale")
            EdicolaPrincipale.objects.all().delete()

            _log("(2/2) Accoda: lettura GoldReport e insert su edicola_principale")
            rows = fetch_edicola_rows_from_goldreport(limit=limit)

            restored_dates = 0
            for row in rows:
                preserved_date = existing_dates.get(_make_preserve_key(row.get("codart"), row.get("ean")))
                if preserved_date is not None:
                    row["data"] = preserved_date
                    restored_dates += 1

            objs = [EdicolaPrincipale(**r) for r in rows]
            if objs:
                EdicolaPrincipale.objects.bulk_create(objs, batch_size=2000)
            inserted = len(objs)
            _log(f"Accoda completata: {inserted} record inseriti")
            if restored_dates:
                _log(f"Date preservate dopo refresh: {restored_dates}")

        return RefreshResult(ok=True, inserted=inserted, backed_up=backed_up, updated_dates=restored_dates)

    except Exception as e:
        _log("Errore durante refresh Edicola", level="ERROR", details=str(e))
        return RefreshResult(ok=False, warnings=[str(e)])



def clear_all_dates() -> int:
    """Azzera esplicitamente tutte le date operative inserite nell'app."""
    updated = EdicolaPrincipale.objects.exclude(data__isnull=True).update(data=None)
    _log(f"Azzeramento date eseguito: {updated} record")
    return updated
