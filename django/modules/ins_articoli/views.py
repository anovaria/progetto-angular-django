from django.shortcuts import render
from datetime import date
from .config import TRACCIATO
import csv
import io
from django.http import HttpResponse

# Ordine delle colonne che l'utente incolla da Excel
COLONNE = ["barcode", "descrizione", "costo", "prezzo", "referenza", "codgold"]


def _parse_input(testo):
    """Trasforma il testo incollato in una lista di articoli.

    Attende 6 colonne separate da TAB, nell'ordine di COLONNE.
    Le colonne mancanti vengono riempite con stringa vuota, così una riga
    incompleta non fa esplodere la generazione.

    Restituisce: [{"barcode": "...", "descrizione": "...", ...}, ...]
    """
    articoli = []
    for riga in testo.split("\n"):
        riga = riga.strip()
        if not riga:
            continue
        parti = riga.split("\t")

        art = {}                                  # dizionario di questo articolo
        for i, nome in enumerate(COLONNE):        # nome + posizione insieme
            if i < len(parti):                    # la colonna esiste nella riga?
                art[nome] = parti[i].strip()      # sì → prendi il valore
            else:
                art[nome] = ""                    # no → lascia vuoto
        articoli.append(art)

    return articoli

def _genera_righe(articoli, testata, iva="22"):
    """Costruisce le righe del CSV: una per articolo, 80 valori ciascuna.

    articoli: lista di dizionari da _parse_input
    testata:  dizionario coi campi comuni (struttura, fornitore, ccom)
    iva:      aliquota, sempre 22 ma resa parametrica
    """
    oggi = date.today().strftime("%d/%m/%Y")
    fine = "31/12/2049"
    righe = []
    for art in articoli:
        riga=[]
        for col in TRACCIATO:
            tipo= col["tipo"]
            if tipo== "articolo":
                # valore incollato dall'utente per questo articolo
                valore = art.get(col["campo"],"")
            elif tipo == "testata":
                # valore comune a tutta l'infornata
                valore = testata.get(col["campo"], "")
            elif tipo == "costante":
                valore = col["valore"]
            elif tipo == "oggi":
                valore = oggi
            elif tipo == "fine":
                valore = fine
            elif tipo == "desc20":
                # primi 20 caratteri della descrizione (il MID dell'Excel)
                valore = art.get("descrizione", "")[:20]
            elif tipo == "iva":
                valore = iva
            else:
                valore =""

            riga.append(valore)     # una cella
        righe.append(riga)          # una riga completa
    return righe

def index(request):
    """Genera il CSV di creazione anagrafica articoli per Gold.

    L'utente compila i tre campi comuni all'infornata e incolla da Excel
    le sei colonne degli articoli. Sostituisce il file Inser_Articoli_10001.xlsx.
    """
    righe = None
    troppo_lunghe = []
    barcode_rotti = []
    articoli_ok = None
    testata = {"struttura": "", "fornitore": "", "ccom": ""}

    if request.method == "POST":
        # Campi comuni a tutta l'infornata
        testata = {
            "struttura": request.POST.get("struttura", "").strip(),
            "fornitore": request.POST.get("fornitore", "").strip(),
            "ccom": request.POST.get("ccom", "").strip(),
        }
        articoli = _parse_input(request.POST.get("dati", ""))
        troppo_lunghe = [
            {"riga": i, "descrizione": a["descrizione"], "lunghezza": len(a["descrizione"])}
            for i, a in enumerate(articoli, start=1)
            if len(a["descrizione"]) > 50
        ]

        # Barcode non validi: un EAN è fatto solo di cifre. Se contiene altro
        # (tipicamente "4,00687E+12") Excel l'ha convertito in notazione
        # scientifica e il codice originale è perso.
        barcode_rotti = [
            {"riga": i, "barcode": a["barcode"]}
            for i, a in enumerate(articoli, start=1)
            if a["barcode"] and not a["barcode"].isdigit()
        ]
        if not troppo_lunghe and not barcode_rotti:
            righe = _genera_righe(articoli, testata)
            request.session['ins_art_righe'] = righe
            request.session['ins_art_ccom'] = testata["ccom"]
            articoli_ok = articoli
        else:
            request.session.pop('ins_art_righe', None)
            request.session.pop('ins_art_ccom', None)
    else:
        request.session.pop('ins_art_righe', None)
        request.session.pop('ins_art_ccom', None)
    return render(request, "ins_articoli/index.html", {
        "righe": righe,
        "troppo_lunghe": troppo_lunghe,
        "articoli":articoli_ok,
        "barcode_rotti": barcode_rotti,
        "testata": testata,
        "intestazioni": [c["nome"] for c in TRACCIATO],
    })

def download(request):
    """Scarica il CSV generato nell'ultima elaborazione.

    Arriva in GET (è un link), quindi le righe vengono rilette dalla sessione
    dove le ha salvate la view index. Il file è scritto con separatore ';'
    ed encoding cp1252, come il tracciato che Gold accetta.
    """
    # Righe già generate da index; lista vuota se l'utente non ha ancora elaborato
    righe = request.session.get('ins_art_righe', [])
    ccom = request.session.get('ins_art_ccom', 'articoli')

    if not righe:
        return HttpResponse("Nessun dato da scaricare. Genera prima le righe.", status=400)

    # "File finto" in memoria: il modulo csv ci scrive come farebbe su disco
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')

    # Intestazione: gli 80 nomi presi dal tracciato, nell'ordine esatto
    writer.writerow([c["nome"] for c in TRACCIATO])
    writer.writerows(righe)

    # Gold vuole ISO-8859-1 (cp1252), non UTF-8: le accentate uscirebbero
    # sbagliate. errors='replace' evita il crash se arriva un carattere
    # non rappresentabile (es. incollato da Word) e lo sostituisce con '?'
    contenuto = buffer.getvalue().encode('cp1252', errors='replace')

    response = HttpResponse(contenuto, content_type='text/csv; charset=ISO-8859-1')
    # Il nome del file è il contratto commerciale, come fanno già a mano
    response['Content-Disposition'] = f'attachment; filename="{ccom}.csv"'
    return response