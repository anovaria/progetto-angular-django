from datetime import datetime
from django.shortcuts import render
from .models import V_RicevimentiGoldArtFo,EntrataMerciOverride
from django.db.models import F
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse

REPARTI_PDV = ['BEVANDE', 'CURA CASA', 'CURA PERSONA E PROFUMERIA', 'DROGHERIA ALIMENTARE']

def entrata_merci_pdv(request):
    stati_selezionati = request.GET.getlist('stato')
    queryset = (
        V_RicevimentiGoldArtFo.objects
        .filter(sito=10001, eanprinc=1, reparto__in=REPARTI_PDV)
        .order_by(F('codartfo').desc(nulls_last=True), 'contr_comm')
        )
    if stati_selezionati:
        queryset = queryset.filter(stato__in=stati_selezionati)
    
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
            'ean_13': riga.ean
        })
    paginator = Paginator(righe_finali, 30)  # 30 righe per pagina, es.
    numero_pagina = request.GET.get('pagina')
    pagina_corrente = paginator.get_page(numero_pagina)  
    return render(request, 'entrata_merci/entrata_merci_pdv.html', {
        'merciPdv': pagina_corrente,
        'conteggio':len(righe_finali)
    })
def modifica_data(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    cod_art = request.POST.get('cod_art')
    valore = request.POST.get('valore')
    utente = request.portal_user.get('username')
    try:
        data_finale = datetime.strptime(valore, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'errore': 'Data non valida'}, status=400)
    EntrataMerciOverride.objects.update_or_create(
        cod_interno_ric= pk,
        cod_art = cod_art,
        defaults={
            'data_ricevimento_modificata': data_finale,
            'utente': utente,
        }
    )
    return JsonResponse({'ok': True})