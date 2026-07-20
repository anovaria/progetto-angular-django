import openpyxl
from django.http import HttpResponse
from django.shortcuts import render
from .models import MasterdataAll


def ricerca(request):
    """Ricerca articoli su t_masterdataall (DB Gold) per codice Gold, EAN
    o codice articolo fornitore.

    Replica i tre fogli del vecchio Excel Ricerca_Ean_CodGold_CodFor:
    l'utente incolla una lista di codici nella textarea, sceglie il tipo
    di ricerca con i tab e ottiene i dati anagrafici da Gold in tempo reale.
    """
    # Stato iniziale: None = prima visita, il template non mostra la tabella
    risultati = None
    non_trovati = []
    # Default "gold" — serve anche al template per evidenziare il tab attivo
    tipo = "gold"

    if request.method == "POST":
        # Tipo di ricerca dal campo hidden valorizzato dai tab (gold/ean/fornitore)
        tipo = request.POST.get("tipo_ricerca", "gold")
        # Testo grezzo della textarea: un codice per riga
        codici = request.POST.get("codici", "")
        # Pulizia: spezza per riga, toglie gli spazi, scarta le righe vuote
        codiciclean = [c.strip() for c in codici.split("\n") if c.strip()]

        # Il tab scelto determina il campo del modello su cui filtrare
        if tipo == "gold":
            campo = "codart"
        elif tipo == "ean":
            campo = "ean"
            # Gli EAN in tabella sono a 13 cifre: padding con zeri iniziali
            # (es. "80703853" -> "0000080703853")
            codiciclean = [c.zfill(13) for c in codiciclean]
        else:
            campo = "codartfo"

        # Filtro dinamico: {"codart__in": [...]} — **filtro lo spacchetta
        # come argomento nominato della query
        filtro = {campo + "__in": codiciclean}

        # Salva in sessione per l'export Excel (che arriva in GET, senza form)
        request.session['ricerca_gold_codici'] = codiciclean
        request.session['ricerca_gold_tipo'] = tipo

        # Query sul DB Gold (read-only) — .using() forza il database goldreport
        risultati = MasterdataAll.objects.using('goldreport').filter(**filtro)

        # Codici cercati ma assenti in Gold: confronto tra insiemi.
        # getattr legge il campo dinamicamente (r.codart / r.ean / r.codartfo)
        trovati = set(getattr(r, campo) for r in risultati)
        non_trovati = [c for c in codiciclean if c not in trovati]
    else:
        # GET = prima visita o "Pulisci": svuota la sessione della ricerca
        request.session.pop('ricerca_gold_codici', None)
        request.session.pop('ricerca_gold_tipo', None)

    return render(request, "ricerca_gold/ricerca.html", {
        "risultati": risultati,
        "non_trovati": non_trovati,
        "tipo": tipo,
    })


def export_excel(request):
    """Esporta in Excel i risultati dell'ultima ricerca effettuata.

    Arriva in GET (è un link), quindi codici e tipo di ricerca vengono
    riletti dalla sessione dove li ha salvati la view ricerca.
    """
    # Codici già puliti (e già paddati se EAN) dalla view ricerca
    codiciclean = request.session.get('ricerca_gold_codici', [])
    tipo = request.session.get('ricerca_gold_tipo', 'gold')

    # Stessa logica campo/filtro della ricerca — deve produrre gli stessi risultati
    if tipo == "gold":
        campo = "codart"
    elif tipo == "ean":
        campo = "ean"
    else:
        campo = "codartfo"

    filtro = {campo + "__in": codiciclean}
    risultati = MasterdataAll.objects.using('goldreport').filter(**filtro)

    # Costruzione del file Excel in memoria
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ricerca Gold"

    # Riga di intestazione — stesso ordine delle colonne della tabella HTML
    ws.append(['Cod. Art. Fornitore', 'Cod. Art. Gold', 'Cod. Fornitore',
               'Descrizione', 'Fornitore', 'CCOM', 'Descr. CCOM',
               'EAN', 'Stato', 'IVA', 'Prezzo Acq.'])

    # Una riga per ogni articolo trovato
    for r in risultati:
        ws.append([r.codartfo, r.codart, r.codforn, r.descrart, r.descforn,
                   r.ccom, r.descrccom, r.ean, r.stato, r.iva, r.pracq])

    # Risposta HTTP con content_type Excel: il browser avvia il download
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # attachment = forza il download con questo nome file
    response['Content-Disposition'] = 'attachment; filename="ricerca_gold.xlsx"'
    wb.save(response)
    return response