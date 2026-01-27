from __future__ import annotations

from typing import Any, Dict, List, Tuple

import base64
import datetime as _dt
import decimal
import uuid

import pyodbc
from django.conf import settings
from django.db import transaction

from .models import GoldTableSnapshot
from django.db import connections

GOLD_TABLES: Tuple[str, str, str] = (
    'dbo.t_OrdiniRossetto',
    'dbo.t_Rossetto',
    'dbo.t_t_Ean',
)


def _json_safe(value: Any) -> Any:
    """Convert common SQL Server/pyodbc types to JSON-serializable values."""
    if value is None:
        return None
    if isinstance(value, decimal.Decimal):
        # Preserve precision by converting to string (safer than float)
        return str(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, uuid.UUID):
        return str(value)
    return value

def _fetch_rows(table_name: str, limit: int = 0) -> List[Dict[str, Any]]:
    """Fetch rows from SQL Server Gold table using Django connection."""
    sql = f"SELECT * FROM {table_name}"
    if limit and limit > 0:
        sql = f"SELECT TOP ({limit}) * FROM {table_name}"

    with connections['goldreport'].cursor() as cur:
        cur.execute(sql)
        columns = [col[0] for col in cur.description] if cur.description else []
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        row_dict = {columns[i]: r[i] for i in range(len(columns))}
        out.append({k: _json_safe(v) for k, v in row_dict.items()})
    return out


def sync_gold_tables(limit: int = 0) -> Dict[str, Dict[str, Any]]:
    """Synchronize configured Gold tables into local SQLite snapshots (Strategy B)."""
    if limit is None:
        limit = 0

    summaries: Dict[str, Dict[str, Any]] = {}

    for table in GOLD_TABLES:
        rows = _fetch_rows(table, limit=limit)
        preview = rows[:5]

        with transaction.atomic():
            GoldTableSnapshot.objects.filter(source_table=table).delete()
            objs = [GoldTableSnapshot(source_table=table, payload=row) for row in rows]
            if objs:
                GoldTableSnapshot.objects.bulk_create(objs, batch_size=1000)

        summaries[table] = {
            'rows_fetched': len(rows),
            'preview': preview,
        }

    return summaries


def get_preview_from_local(limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    previews: Dict[str, List[Dict[str, Any]]] = {}
    for table in GOLD_TABLES:
        qs = GoldTableSnapshot.objects.filter(source_table=table).order_by('id')[:limit]
        previews[table] = [obj.payload for obj in qs]
    return previews
