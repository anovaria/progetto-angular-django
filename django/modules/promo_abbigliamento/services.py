from .models import PromoTestata,PromoStorico
import re
import csv
import io

CODICE_RE = re.compile(r'^M(\d{4})$')

def prossimo_codice_promo():
    """Trova il progressivo più alto tra storico e nuove, propone il successivo."""
    codici_promo_storico = PromoStorico.objects.values_list('codice_promo', flat=True)
    codici_promo_testate = PromoTestata.objects.values_list('codice_promo', flat=True)
    tutti_i_codici = list(codici_promo_storico) + list(codici_promo_testate)
    massimo = 0
    for cd in tutti_i_codici:
        match = CODICE_RE.match(cd.strip())
        if match: 
            numero = int(match.group(1))
            massimo = max(massimo, numero)
    prossimo = massimo + 1 if massimo else 1
    return f'M{prossimo:04d}'

def codice_gia_usato(codice_promo):
    """Vero se il codice esiste già in storico o tra le nuove."""
    return PromoTestata.objects.filter(codice_promo=codice_promo).exists() or PromoStorico.objects.filter(codice_promo=codice_promo).exists()

def descrizione_valida(descrizione: str) -> bool:
    """Vero se la descrizione rispetta il limite di 50 caratteri di Gold."""
    return len(descrizione or '') <= 50

def genera_csv_promo(promo: PromoTestata) -> bytes:
    """Genera il CSV per l'import Gold, formato Copia_di_Inser_Testate_Promoz.xlsx."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow([
        'Colonna1', 'Colonna2', 'Colonna3',
        'Colonna4', 'Colonna5',
    ])
    writer.writerow([
        promo.tipo_promo,
        promo.codice_promo,
        promo.descrizione,
        promo.data_inizio_sellout.strftime('%d/%m/%Y'),
        promo.data_fine_sellout.strftime('%d/%m/%Y'),
    ])
    return buffer.getvalue().encode('cp1252')