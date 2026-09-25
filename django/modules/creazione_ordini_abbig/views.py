from django.shortcuts import render
from django.http import HttpResponse
from .forms import OrdineForm
from .services import crea_ordine,genera_csv,ultime_righe

def download(request):
    form = OrdineForm(request.POST)
    if form.is_valid():
        ordine = crea_ordine(form.cleaned_data, request.portal_user)
        contenuto_csv = genera_csv(ordine)
        contenuto = contenuto_csv.encode('utf-8-sig')
        response = HttpResponse(contenuto, content_type='text/csv; charset=utf-8')
        nome_file = form.cleaned_data['nome_file']
        response['Content-Disposition'] = f'attachment; filename="{nome_file}.csv"'
        return response
    else:
        righe = ultime_righe()
        return render(request, 'creazione_ordini_abbig/ordine_form.html', {'form': form, 'righe':righe})

        

def index(request):
    righe = ultime_righe()
    form = OrdineForm()
    return render(request, 'creazione_ordini_abbig/ordine_form.html', {'form': form, 'righe':righe})