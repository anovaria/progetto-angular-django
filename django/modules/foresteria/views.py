from django.shortcuts import render
from datetime import date
import calendar

def planning(request):
    oggi = date.today()
    anno = int(request.GET.get('anno', oggi.year))
    mese = int(request.GET.get('mese', oggi.month))
    _, num_giorni = calendar.monthrange(anno, mese)
    giorni = list(range(1, num_giorni + 1))
    if mese == 1:
        mese_prec, anno_prec = 12, anno - 1
    else:
        mese_prec, anno_prec = mese - 1, anno
    if mese == 12:
        mese_succ, anno_succ = 1, anno + 1
    else:
        mese_succ, anno_succ = mese + 1, anno
    stanze = ['Monte Bianco', 'Cervino']
    contesto = {
        'anno': anno,
        'mese': mese,
        'giorni': giorni,
        'mese_prec': mese_prec,
        'anno_prec': anno_prec,
        'mese_succ': mese_succ,
        'anno_succ': anno_succ,
        'stanze': stanze,
    }
    return render(request, 'foresteria/planning.html', contesto)