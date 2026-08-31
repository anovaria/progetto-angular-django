from datetime import datetime
from django.db.models import F
from .models import EntrataMerciOverride, V_RicevimentiGoldArtFo


def calcola_base_ean(ean, tipo):
    if tipo == 6:
        base = "00000" + ean[:7]
    elif tipo == 7:
        base = "0" + ean[:11]
    else:
        base = ean[:12]
    return base

def calcola_checksum_ean13(base_12_cifre):
    dispari = sum(int(base_12_cifre[i]) for i in range(0, 12, 2))
    pari = sum(int(base_12_cifre[i]) for i in range(1, 12, 2))
    totale = dispari + pari * 3
    resto = totale % 10
    checksum = (10 - resto) % 10
    return checksum

def calcola_ean13(ean, tipo):
    base = calcola_base_ean(ean, tipo)
    if len(base) < 12:
        return None
    checksum = calcola_checksum_ean13(base)
    return base + str(checksum)

def get_righe_pdv(request):
    stati_selezionati = request.GET.getlist('stato')
    queryset = (
        V_RicevimentiGoldArtFo.objects
        .filter(sito=10001, eanprinc=1, settore='GROCERY')
        .order_by(F('codartfo').desc(nulls_last=True), 'contr_comm')
        )
    if stati_selezionati:
        queryset = queryset.filter(stato__in=stati_selezionati)

    data_ric_selezionata = request.GET.get('data_ric')  # arriva come 'AAAA-MM-GG', es. '2026-08-17'
    if data_ric_selezionata:
        data_gold_formato = datetime.strptime(data_ric_selezionata, '%Y-%m-%d').strftime('%d/%m/%Y')  # devi convertirla in 'GG/MM/AAAA' per confrontarla col campo 'data' di Gold
        queryset = queryset.filter(data=data_gold_formato)

    ids_gold = list(queryset.values_list('cod_interno_ric', flat=True))
    overrides = EntrataMerciOverride.objects.filter(cod_interno_ric__in=ids_gold)
    overrides_dict = {(o.cod_interno_ric, o.cod_art): o.data_ricevimento_modificata for o in overrides}
    righe_finali = []
    combinazioni_viste = set()
    for riga in queryset:
        chiave = (riga.cod_interno_ric, riga.cod_art)
        if chiave in combinazioni_viste:
            continue
        combinazioni_viste.add(chiave)

        if chiave in overrides_dict:
            data_finale = overrides_dict[chiave]
        else:
            data_finale = datetime.strptime(riga.data, '%d/%m/%Y').date()
        ean_calcolato = calcola_ean13(riga.ean, riga.tipo)
        righe_finali.append({
            'cod_interno_ric': riga.cod_interno_ric,
            'data_ricevimento': data_finale,
            'settore': riga.settore,
            'reparto': riga.reparto,
            'contr_comm': riga.contr_comm,
            'codartfo': riga.codartfo,
            'cod_art': riga.cod_art,
            'desc_art': riga.desc_art,
            'stato': riga.stato,
            'unita_misura': riga.unita_misura,
            'quantita_ricevuta': riga.quantita_ricevuta,
            'corsia': riga.corsia,
            'campata': riga.campata,
            'giacenza_pdv': riga.giacenza_pdv,
            'ean_13': ean_calcolato if ean_calcolato else riga.ean,
            'barcode_valido': ean_calcolato is not None,
        })
    return righe_finali

REPARTI_MAGAZZINO = ['BEVANDE', 'DROGHERIA ALIMENTARE']
def get_righe_magazzino(request):
    stati_selezionati = request.GET.getlist('stato')
    queryset = (
        V_RicevimentiGoldArtFo.objects
        .filter(sito=901, eanprinc=1, reparto__in=REPARTI_MAGAZZINO, giacenza_pdv__lte=5)
        .order_by('reparto', F('codartfo').desc(nulls_last=True), 'contr_comm')
        )
    if stati_selezionati:
        queryset = queryset.filter(stato__in=stati_selezionati)

    data_ric_selezionata = request.GET.get('data_ric')  # arriva come 'AAAA-MM-GG', es. '2026-08-17'
    if data_ric_selezionata:
        data_gold_formato = datetime.strptime(data_ric_selezionata, '%Y-%m-%d').strftime('%d/%m/%Y')  # devi convertirla in 'GG/MM/AAAA' per confrontarla col campo 'data' di Gold
        queryset = queryset.filter(data=data_gold_formato)
    ids_gold = list(queryset.values_list('cod_interno_ric', flat=True))
    overrides = EntrataMerciOverride.objects.filter(cod_interno_ric__in=ids_gold)
    overrides_dict = {(o.cod_interno_ric, o.cod_art): o.data_ricevimento_modificata for o in overrides}
    righe_finali = []
    combinazioni_viste = set()
    for riga in queryset:
        chiave = (riga.cod_interno_ric, riga.cod_art)
        if chiave in combinazioni_viste:
            continue
        combinazioni_viste.add(chiave)

        if chiave in overrides_dict:
            data_finale = overrides_dict[chiave]
        else:
            data_finale = datetime.strptime(riga.data, '%d/%m/%Y').date()

        ean_calcolato = calcola_ean13(riga.ean, riga.tipo)
        righe_finali.append({
            'cod_interno_ric': riga.cod_interno_ric,
            'data_ricevimento': data_finale,
            'reparto': riga.reparto,
            'contr_comm': riga.contr_comm,
            'codartfo': riga.codartfo,
            'cod_art': riga.cod_art,
            'desc_art': riga.desc_art,
            'stato': riga.stato,
            'unita_misura': riga.unita_misura,
            'quantita_ricevuta': riga.quantita_ricevuta,
            'pzxcart': riga.pzxcart,
            'giacenza_pdv': riga.giacenza_pdv,
            'ean_13': ean_calcolato if ean_calcolato else riga.ean,
            'barcode_valido': ean_calcolato is not None,
        })
    return righe_finali