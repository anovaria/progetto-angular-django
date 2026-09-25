import csv
from datetime import date, timedelta
import io
from .models import Ordine
import re
from django.core.exceptions import ValidationError

CODICE_ORDINE_DEFAULT = 'ABB0000000000'
CODICE_ORDINE_RE = re.compile(r'^ABB\d{10}$')
INTESTAZIONI_CSV = [
    'Codice ordine', 'Numero riga', 'Codice Fornitore', 'Codice Filiera',
    'Codice Commerciale', 'Codice Articolo', 'Variante Logistica', 'Sito',
    'Data ordine', 'Data consegna', 'Quantità ordine', 'Unità ordine',
    'Prezzo unitario', 'IVA ACQUISTO', 'Valuta', 'Stato',
]

def valida_codice_ordine(codice):
    if codice == CODICE_ORDINE_DEFAULT:
        raise ValidationError("Il codice ordine non è stato modificato dal valore di default.")
    if not CODICE_ORDINE_RE.match(codice):
        raise ValidationError("Il codice ordine deve essere 'ABB' seguito da 10 cifre.")
    if Ordine.objects.filter(codice_ordine=codice).exists():
        raise ValidationError(f"Il codice ordine '{codice}' è già stato usato in precedenza.")

def crea_ordine(dati, utente):
    valida_codice_ordine(dati['codice_ordine'])

    oggi = date.today()
    ordine = Ordine.objects.create(
        codice_ordine=dati['codice_ordine'],
        codice_fornitore=dati['codice_fornitore'],
        codice_commerciale=dati['codice_commerciale'],
        codice_articolo=dati['codice_articolo'],
        quantita_ordine=dati['quantita_ordine'],
        data_ordine=oggi,
        data_consegna=oggi + timedelta(days=7),
        creato_da=utente['username'],
    )
    return ordine

def genera_csv(ordine):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(INTESTAZIONI_CSV)
    writer.writerow([
        ordine.codice_ordine,
        ordine.numero_riga,
        ordine.codice_fornitore,
        ordine.codice_filiera,
        ordine.codice_commerciale,
        ordine.codice_articolo,
        ordine.variante_logistica,
        ordine.sito,
        ordine.data_ordine.strftime('%d/%m/%Y'),
        ordine.data_consegna.strftime('%d/%m/%Y'),
        ordine.quantita_ordine,
        ordine.unita_ordine,
        ordine.prezzo_unitario or '',
        ordine.iva_acquisto or '',
        ordine.valuta,
        ordine.stato,
    ])
    return buffer.getvalue()

def ultime_righe():
    return Ordine.objects.order_by('-creato_il')[:10]