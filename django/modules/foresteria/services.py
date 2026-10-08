from .models import Prenotazione

from datetime import date
import calendar
from django.conf import settings
from django.core.mail import send_mail
import logging
MESI = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
SIGLE = ['L', 'M', 'M', 'G', 'V', 'S', 'D']
logger = logging.getLogger(__name__)

def mese_precedente(anno, mese):
    if mese == 1:
        return anno - 1, 12
    return anno, mese - 1

def mese_successivo(anno, mese):
    if mese == 12:
        return anno + 1, 1
    return anno, mese + 1
def giorni_mese(anno, mese):
    oggi = date.today()
    _, num_giorni = calendar.monthrange(anno, mese)
    giorni = []
    for n in range(1, num_giorni + 1):
        d = date(anno, mese, n)
        giorni.append({
            'numero': n,
            'data': d,
            'sigla': SIGLE[d.weekday()],
            'weekend': d.weekday() >= 5,
            'oggi': d == oggi,
        })
    return giorni

def griglia_mese(anno, mese, giorni):
    inizio_mese = date(anno, mese, 1)
    anno_succ, mese_succ = mese_successivo(anno, mese)
    inizio_mese_succ = date(anno_succ, mese_succ, 1)

    prenotazioni = Prenotazione.objects.filter(
        data_partenza__gt=inizio_mese,
        data_arrivo__lt=inizio_mese_succ,
    )

    righe = {}
    for codice, etichetta in Prenotazione.Camera.choices:
        celle = []
        for g in giorni:
            celle.append({**g, 'prenotazione': None})
        righe[codice] = {
            'camera': etichetta,
            'codice': codice,
            'celle': celle,
        }

    for p in prenotazioni:
        for i, g in enumerate(giorni):
            if p.data_arrivo <= g['data'] < p.data_partenza:
                righe[p.camera]['celle'][i]['prenotazione'] = p

    return list(righe.values())

def dati_planning(anno, mese):
    anno_prec, mese_prec = mese_precedente(anno, mese)
    anno_succ, mese_succ = mese_successivo(anno, mese)
    giorni = giorni_mese(anno, mese)

    return {
        'anno': anno,
        'mese': mese,
        'nome_mese': MESI[mese],
        'giorni': giorni,
        'anno_prec': anno_prec,
        'mese_prec': mese_prec,
        'anno_succ': anno_succ,
        'mese_succ': mese_succ,
        'griglia': griglia_mese(anno, mese, giorni),
    }

def camera_occupata(camera, arrivo, partenza, escludi_pk=None):
    conflitti = Prenotazione.objects.filter(
        camera=camera,
        data_partenza__gt=arrivo,
        data_arrivo__lt=partenza,
    )
    if escludi_pk:
        conflitti = conflitti.exclude(pk=escludi_pk)
    return conflitti.exists()

def invia_email_nuova(prenotazione):
    camera = prenotazione.get_camera_display()
    arrivo = prenotazione.data_arrivo.strftime('%d/%m/%Y')
    partenza = prenotazione.data_partenza.strftime('%d/%m/%Y')
    oggetto = f"Foresteria Gros Cidac – Nuova prenotazione camera {camera} ({arrivo} → {partenza})"
    testo = (
        f"Buongiorno,\n\n"
        f"vi comunichiamo una nuova prenotazione in foresteria:\n\n"
        f"Camera:   {camera}\n"
        f"Arrivo:   {arrivo}\n"
        f"Partenza: {partenza}\n\n"
        f"Cordiali saluti,\n"
        f"Gros Cidac S.r.l.\n\n"
        f"(Messaggio automatico, si prega di non rispondere.)"
    )
    send_mail(oggetto, testo, None, settings.FORESTERIA_EMAIL_PULIZIE)

def crea_prenotazione(form):
    prenotazione = form.save()
    try:
        invia_email_nuova(prenotazione)
        inviata = True
    except Exception:
        logger.exception('Email pulizie non inviata per la prenotazione %s', prenotazione.pk)
        inviata = False
    return prenotazione, inviata

def salva_modifica(form):
    originale = Prenotazione.objects.get(pk=form.instance.pk)
    prenotazione = form.save()

    cambiata = (
        originale.camera != prenotazione.camera
        or originale.data_arrivo != prenotazione.data_arrivo
        or originale.data_partenza != prenotazione.data_partenza
    )
    inviata = None
    if cambiata:
        try:
            invia_email_modifica(originale, prenotazione)
            inviata = True
        except Exception:
            logger.exception('Email modifica non inviata per la prenotazione %s', prenotazione.pk)
            inviata = False

    return prenotazione, inviata

def invia_email_modifica(originale, prenotazione):
    def descrivi(p):
        arrivo = p.data_arrivo.strftime('%d/%m/%Y')
        partenza = p.data_partenza.strftime('%d/%m/%Y')
        return f"Camera {p.get_camera_display()}, dal {arrivo} al {partenza}"

    oggetto = f"Foresteria Gros Cidac – MODIFICA prenotazione camera {prenotazione.get_camera_display()}"
    testo = (
        f"Buongiorno,\n\n"
        f"vi comunichiamo una modifica a una prenotazione in foresteria.\n\n"
        f"PRIMA:  {descrivi(originale)}\n"
        f"ADESSO: {descrivi(prenotazione)}\n\n"
        f"Cordiali saluti,\n"
        f"Gros Cidac S.r.l.\n\n"
        f"(Messaggio automatico, si prega di non rispondere.)"
    )
    send_mail(oggetto, testo, None, settings.FORESTERIA_EMAIL_PULIZIE)

def elimina_prenotazione(prenotazione):
    prenotazione.delete()
    try:
        invia_email_cancellazione(prenotazione)
        inviata = True
    except Exception:
        logger.exception('Email cancellazione non inviata (camera %s, %s)', prenotazione.camera, prenotazione.data_arrivo)
        inviata = False
    return inviata


def invia_email_cancellazione(prenotazione):
    camera = prenotazione.get_camera_display()
    arrivo = prenotazione.data_arrivo.strftime('%d/%m/%Y')
    partenza = prenotazione.data_partenza.strftime('%d/%m/%Y')

    oggetto = f"Foresteria Gros Cidac – CANCELLAZIONE prenotazione camera {camera} ({arrivo} → {partenza})"
    testo = (
        f"Buongiorno,\n\n"
        f"vi comunichiamo che la seguente prenotazione è stata CANCELLATA:\n\n"
        f"Camera:   {camera}\n"
        f"Arrivo:   {arrivo}\n"
        f"Partenza: {partenza}\n\n"
        f"Le pulizie previste per queste date non sono più necessarie.\n\n"
        f"Cordiali saluti,\n"
        f"Gros Cidac S.r.l.\n\n"
        f"(Messaggio automatico, si prega di non rispondere.)"
    )
    send_mail(oggetto, testo, None, settings.FORESTERIA_EMAIL_PULIZIE)