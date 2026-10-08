from django.shortcuts import render,redirect,get_object_or_404
from datetime import date
import calendar
from .services import elimina_prenotazione, griglia_mese,crea_prenotazione,salva_modifica,dati_planning
from .forms import PrenotazioneForm
from .models import Prenotazione
from django.conf import settings
from django.contrib import messages

def planning(request):
    oggi = date.today()
    anno = int(request.GET.get('anno', oggi.year))
    mese = int(request.GET.get('mese', oggi.month))
    contesto = dati_planning(anno, mese)
    return render(request, 'foresteria/planning.html', contesto)

def nuova_prenotazione(request):
    iniziali = {
        'camera': request.GET.get('camera'),
        'data_arrivo': request.GET.get('data'),
    }
    if request.method == 'POST':
        form = PrenotazioneForm(request.POST, initial=iniziali)
        if form.is_valid(): 
            _, inviata = crea_prenotazione(form)
            destinatari = ', '.join(settings.FORESTERIA_EMAIL_PULIZIE)
            if inviata:
                messages.success(request, f'Prenotazione salvata. Email inviata a: {destinatari}')
            else:
                messages.warning(request, 'Prenotazione salvata, ma l\'email alla ditta di pulizie NON è partita. Avvisare l\'IT.')
            return redirect('foresteria:planning')

    else:
        form = PrenotazioneForm(initial=iniziali)
    return render(request, 'foresteria/prenotazione_form.html', {'form': form})

def modifica_prenotazione(request, pk):
    prenotazione = get_object_or_404(Prenotazione, pk=pk)

    if request.method == 'POST':
        form = PrenotazioneForm(request.POST, instance=prenotazione)
        if form.is_valid():
            prenotazione, inviata = salva_modifica(form)
            destinatari = ', '.join(settings.FORESTERIA_EMAIL_PULIZIE)
            if inviata is True:
                messages.success(request, f'Prenotazione modificata. Email inviata a: {destinatari}')
            elif inviata is False:
                messages.warning(request, 'Prenotazione modificata, ma l\'email alla ditta di pulizie NON è partita. Avvisare l\'IT.')
            else:
                messages.success(request, 'Prenotazione modificata.')
            return redirect('foresteria:planning')
    else:
        form = PrenotazioneForm(instance=prenotazione)

        return render(request, 'foresteria/prenotazione_form.html', {'form': form, 'prenotazione': prenotazione})

def cancella_prenotazione(request, pk):
    prenotazione = get_object_or_404(Prenotazione, pk=pk)

    if request.method != 'POST':
        return redirect('foresteria:modifica', pk=pk)

    inviata = elimina_prenotazione(prenotazione)
    destinatari = ', '.join(settings.FORESTERIA_EMAIL_PULIZIE)
    if inviata:
        messages.success(request, f'Prenotazione cancellata. Email inviata a: {destinatari}')
    else:
        messages.warning(request, 'Prenotazione cancellata, ma l\'email alla ditta di pulizie NON è partita. Avvisare l\'IT.')
    return redirect('foresteria:planning')