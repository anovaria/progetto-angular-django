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


def crea_ordine(dati, utente):
    valida_codice_ordine(dati['codice_ordine'])

    articoli = dati['lista_articoli']       # lista di stringhe, es. ['947013', '947014']
    quantita = dati['lista_quantita']       # lista di interi, es. [14, 20]

    # 1. Prima di salvare, controlla eventuali duplicati per OGNI numero_riga
    #    (numero_riga va da 1 a len(articoli), visto che enumerate parte da 0)
    for numero_riga, (articolo, qta) in enumerate(zip(articoli, quantita), start=1):
        if Ordine.objects.filter(codice_ordine=dati['codice_ordine'], numero_riga=numero_riga).exists():
            raise ValidationError(f"La riga {numero_riga} del codice ordine '{dati['codice_ordine']}' è già stata usata.")

    # 2. Solo se NESSUNA riga è duplicata, procedi a crearle tutte
    oggi = date.today()
    ordini_creati = []
    for numero_riga, (articolo, qta) in enumerate(zip(articoli, quantita), start=1):
        ordine = Ordine.objects.create(
            codice_ordine=dati['codice_ordine'],
            numero_riga=numero_riga,
            codice_fornitore=dati['codice_fornitore'],
            codice_commerciale=dati['codice_commerciale'],
            codice_articolo=articolo,
            quantita_ordine=qta,
            data_ordine=oggi,
            data_consegna=oggi + timedelta(days=7),
            creato_da=utente['username'],
        )
        ordini_creati.append(ordine)

    return ordini_creati

def genera_csv(ordini):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(INTESTAZIONI_CSV)
    for ordine in ordini:
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
    return Ordine.objects.order_by('-codice_ordine', 'numero_riga')[:10]

def parse_lista_testo(testo):
    lista = testo.splitlines()
    righe = [riga.strip() for riga in lista if riga.strip()]
    return righe

def parse_lista_quantita(testo):
    righe = parse_lista_testo(testo)
    quantita = [int(riga) for riga in righe]
    return quantita