from django.shortcuts import render
from .services import get_articoli_nuovi

def lista_articoli_nuovi(request):
    articoli = get_articoli_nuovi()
    conteggio = len(articoli)
    return render(request, 'articoli_nuovi/lista.html', {
        'articoli': articoli,
        'conteggio': conteggio,
    })