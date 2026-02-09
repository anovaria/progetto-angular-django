"""
Scarico Promo - Views
Gestisce le interfacce web che replicano M_esporta e m_MettereX.
"""
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    MettereInA, MettereInE, MettereInF, MettereInI, MettereInK, MettereInS,
    PerExport, NonPossoMettereInA,
)
from .services import (
    conta_metterein, conta_export,
    valida_mettere_in_a, elabora_attributi, esporta_promo_completo,
)


def get_username(request):
    """Recupera username da header IIS/LDAP."""
    username = request.META.get('HTTP_X_REMOTE_USER', '')
    if username:
        return username.split('\\')[-1].lower()
    return request.META.get('REMOTE_USER', 'anonymous').split('\\')[-1].lower()


# ============================================================
# DASHBOARD (replica M_esporta)
# ============================================================

@csrf_exempt
def dashboard(request):
    """
    Pagina principale - replica M_esporta.
    Mostra conteggi articoli, tabella promozioni, pulsanti azione.
    """
    username = get_username(request)
    conteggi = conta_metterein()
    export_counts = conta_export()

    # Dati promozione per la griglia (replica sm_Esporta)
    promozioni = PerExport.objects.all().order_by('DataInizio', 'CodiceProdotto')

    context = {
        'username': username,
        'conteggi': conteggi,
        'export_counts': export_counts,
        'promozioni': promozioni,
        'can_export_csv': export_counts['tutti'] > 0,
        'can_crea_attributi': any(v > 0 for v in conteggi.values()),
    }
    return render(request, 'scaricopromo/dashboard.html', context)


# ============================================================
# GESTIONE "METTERE IN X" (replica m_MettereA/E/F/K)
# ============================================================

@csrf_exempt
def mettere_in(request, stato):
    """
    Form per inserire codici articolo nelle tabelle 'Mettere in X'.
    GET: mostra form + lista articoli inseriti
    POST: aggiunge articolo
    """
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if not model:
        return HttpResponse("Stato non valido", status=400)

    has_ccom = stato.upper() in ('A', 'I')

    if request.method == 'POST':
        codart = request.POST.get('codart', '').strip()
        ccom = request.POST.get('ccom', '').strip() if has_ccom else ''

        if codart:
            kwargs = {'codart': codart}
            if has_ccom:
                kwargs['ccom'] = ccom
            model.objects.create(**kwargs)

        return redirect('scaricopromo:mettere_in', stato=stato)

    articoli = model.objects.all()
    conteggi = conta_metterein()

    context = {
        'stato': stato.upper(),
        'articoli': articoli,
        'has_ccom': has_ccom,
        'count': articoli.count(),
        'conteggi': conteggi,
    }
    return render(request, 'scaricopromo/mettere_in.html', context)


@csrf_exempt
@require_POST
def elimina_articolo(request, stato, pk):
    """Elimina un articolo dalla tabella 'Mettere in X'."""
    model_map = {
        'A': MettereInA, 'E': MettereInE, 'F': MettereInF,
        'I': MettereInI, 'K': MettereInK, 'S': MettereInS,
    }
    model = model_map.get(stato.upper())
    if model:
        model.objects.filter(pk=pk).delete()
    return redirect('scaricopromo:mettere_in', stato=stato)


# ============================================================
# AZIONI (replica pulsanti M_esporta)
# ============================================================

@csrf_exempt
@require_POST
def azione_valida_a(request):
    """
    Replica Comando3_Click di m_MettereA.
    Valida articoli, genera report "non posso mettere", accoda a ordini.
    """
    non_processabili = valida_mettere_in_a()
    conteggi = conta_metterein()

    return JsonResponse({
        'success': True,
        'non_processabili': non_processabili,
        'has_warnings': len(non_processabili) > 0,
        'message': (
            f"Ci sono {len(non_processabili)} articoli da gestire manualmente!"
            if non_processabili
            else "Tutti gli articoli sono stati elaborati"
        ),
        'conteggi': conteggi,
    })


@csrf_exempt
@require_POST
def azione_crea_attributi(request):
    """
    Replica Comando15_Click di M_esporta.
    Elabora tutti gli attributi e genera CSV.
    """
    try:
        csv_path, tot_records = elabora_attributi()
        conteggi = conta_metterein()

        return JsonResponse({
            'success': True,
            'csv_path': csv_path,
            'tot_records': tot_records,
            'message': f"File Creato! {tot_records} record. Prosegui su Gold.",
            'conteggi': conteggi,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Errore: {str(e)}",
        }, status=500)


@csrf_exempt
@require_POST
def azione_esporta_csv(request):
    """
    Replica EsportaCsv_Click di M_esporta.
    Esporta promozioni in CSV (Promo + CondAcq).
    """
    username = get_username(request)

    try:
        risultato = esporta_promo_completo(username)

        return JsonResponse({
            'success': True,
            'promo_csv': risultato['promo_csv'],
            'condacq_csv': risultato['condacq_csv'],
            'tot_promo': risultato['tot_promo'],
            'tot_condacq': risultato['tot_condacq'],
            'message': "File Esportati!",
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f"Errore: {str(e)}",
        }, status=500)


# ============================================================
# REPORT "NON POSSO METTERE IN A"
# ============================================================

def report_non_posso(request):
    """
    Replica R_NonpossomettereA.
    Elenco articoli con giacenza che non si possono mettere in A.
    """
    articoli = NonPossoMettereInA.objects.all()

    # Arricchisci con dati giacenza da Gold
    codici = list(articoli.values_list('codart', flat=True))
    giacenze = {}

    if codici:
        from django.db import connections
        placeholders = ','.join(['%s'] * len(codici))
        sql = f"""
            SELECT CODARTICOLO, STATO, GIAC_PDV, GIAC_DEP
            FROM t_ArticoliGiacTutti
            WHERE CODARTICOLO IN ({placeholders})
        """
        with connections['goldreport'].cursor() as cursor:
            cursor.execute(sql, codici)
            for row in cursor.fetchall():
                giacenze[row[0]] = {
                    'stato': row[1],
                    'giac_pdv': row[2],
                    'giac_dep': row[3],
                }

    report_data = []
    for art in articoli:
        giac = giacenze.get(art.codart, {})
        report_data.append({
            'ccom': art.ccom,
            'codart': art.codart,
            'stato': giac.get('stato', ''),
            'giac_pdv': giac.get('giac_pdv', 0),
            'giac_dep': giac.get('giac_dep', 0),
        })

    context = {
        'report_data': report_data,
        'titolo': 'Elenco articoli con Giacenza che non posso mettere in A',
        'sottotitolo': 'I seguenti articoli vanno gestiti manualmente',
    }
    return render(request, 'scaricopromo/report_non_posso.html', context)


# ============================================================
# API CONTEGGI (per aggiornamento AJAX dashboard)
# ============================================================

def api_conteggi(request):
    """Restituisce conteggi aggiornati per la dashboard."""
    conteggi = conta_metterein()
    export_counts = conta_export()
    return JsonResponse({
        'conteggi': conteggi,
        'export': export_counts,
    })
