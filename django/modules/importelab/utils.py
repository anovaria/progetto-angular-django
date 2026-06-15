def decode_elab(raw_bytes: bytes) -> str:
    """Decodifica il file .elab (prima UTF-8, poi Latin-1)."""
    try:
        return raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return raw_bytes.decode('latin-1', errors='replace')


def _to_int(value: str):
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _to_float(value: str):
    value = value.strip().replace(',', '.')
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_elab_text(text: str):
    """
    Ritorna una lista di dict tipizzati con i campi di dominio.
    Ordine atteso delle colonne nel file:
    0: CodArtFo (str)
    1: DescrizioneArticolo (str)
    2: Iva (int)
    3: PrzAcq (float)
    4: Campo5 (float)
    5: PzXCrt (int)
    6: CrtXstr (int)
    7: StrXplt (int)
    8: TotColli (int)
    9: Ean (str)
    """

    rows = []

    for line in text.splitlines():
        raw = line.rstrip('\n\r')
        line = line.strip()
        if not line:
            continue

        cols = [c.strip() for c in line.split(';')]

        # garantisco almeno 10 colonne
        while len(cols) < 10:
            cols.append('')

        row = {
            "raw_line": raw,
            "cod_art_fo": cols[0],
            "descrizione_articolo": cols[1],
            "iva": _to_int(cols[2]),
            "prz_acq": _to_float(cols[3]),
            "campo5": _to_float(cols[4]),
            "pz_x_crt": _to_int(cols[5]),
            "crt_x_str": _to_int(cols[6]),
            "str_x_plt": _to_int(cols[7]),
            "tot_colli": _to_int(cols[8]),
            "ean": cols[9],
        }
        rows.append(row)

    return rows
