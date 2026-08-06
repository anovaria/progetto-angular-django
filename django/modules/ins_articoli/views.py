from django.shortcuts import render
from datetime import date
from .config import TRACCIATO
import csv
import io
from django.http import HttpResponse

# Le colonne che l'utente incolla, una per box.
# La tupla è (nome del campo, etichetta mostrata a schermo).
# L'ordine qui decide solo l'ordine dei box a schermo: il CSV segue TRACCIATO.
COLONNE = [
    ("barcode",     "Barcode"),
    ("descrizione", "Descrizione principale"),
    ("struttura",   "Struttura merceologica"),
    ("iva",         "IVA acquisto"),
    ("pzxcrt",      "Pezzi per collo"),
    ("costo",       "Costo lordo"),
    ("prezzo",      "Prezzo di vendita base"),
    ("referenza",   "Referenza fornitore"),
    ("codgold",     "Codice articolo Gold"),
]


def _parse_input(valori):
    """Accoppia per posizione le sette colonne incollate in box separati.

    valori: dizionario {campo: testo della textarea}

    La riga N di ogni box appartiene allo stesso articolo, quindi tutte le
    liste devono avere lo stesso numero di righe. Se non è così restituisce
    un errore invece degli articoli: meglio fermarsi che generare righe sfasate.

    Restituisce la coppia (articoli, errore): errore è None se tutto ok.
    """
    # Ogni box diventa una lista di valori puliti, senza righe vuote
    liste = {
        campo: [r.strip() for r in valori.get(campo, "").split("\n") if r.strip()]
        for campo, _label in COLONNE
    }

    conteggi = {campo: len(v) for campo, v in liste.items()}
    n = max(conteggi.values())

    if n == 0:
        return [], "Non hai incollato nessun dato."

    # Colonne con un numero di righe diverso dal massimo: sono disallineate
    diverse = [f"{label}: {conteggi[campo]}"
               for campo, label in COLONNE if conteggi[campo] != n]
    if diverse:
        return [], (f"Le colonne hanno un numero di righe diverso (attese {n}). "
                    f"Controlla — {' · '.join(diverse)}")

    # Riga per riga, prende il valore corrispondente da ogni lista
    articoli = [
        {campo: liste[campo][i] for campo, _label in COLONNE}
        for i in range(n)
    ]
    return articoli, None

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
            if tipo == "articolo":
                valore = art.get(col["campo"], "")
                # Costo e prezzo: Gold vuole la virgola come separatore decimale
                if col["campo"] in ("costo", "prezzo"):
                    valore = valore.replace(".", ",")
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
    righe = None
    troppo_lunghe = []
    barcode_rotti = []
    iva_errate = []
    pezzi_errati = []
    errore = None
    articoli_ok = None
    testata = {"fornitore": "", "ccom": ""}
    valori = {campo: "" for campo, _label in COLONNE}

    if request.method == "POST":
        # Campi comuni a tutta l'infornata (la struttura non è più qui)
        testata = {
            "fornitore": request.POST.get("fornitore", "").strip(),
            "ccom": request.POST.get("ccom", "").strip(),
        }
        # Il contenuto dei sette box, riletto anche per ripopolarli dopo il Genera
        valori = {campo: request.POST.get(campo, "") for campo, _label in COLONNE}

        articoli, errore = _parse_input(valori)

        troppo_lunghe = [
            {"riga": i, "descrizione": a["descrizione"], "lunghezza": len(a["descrizione"])}
            for i, a in enumerate(articoli, start=1)
            if len(a["descrizione"]) > 50
        ]
        barcode_rotti = [
            {"riga": i, "barcode": a["barcode"]}
            for i, a in enumerate(articoli, start=1)
            if a["barcode"] and not a["barcode"].isdigit()
        ]

        # IVA: solo 22 (nazionale) o 222 (codice Gold per IVA estera)
        iva_errate = [
            {"riga": i, "iva": a["iva"]}
            for i, a in enumerate(articoli, start=1)
            if a["iva"] not in ("22", "222")
        ]

        # Pezzi per collo: deve essere un numero
        pezzi_errati = [
            {"riga": i, "pezzi": a["pzxcrt"]}
            for i, a in enumerate(articoli, start=1)
            if not a["pzxcrt"].isdigit()
        ]

        blocchi = [errore, troppo_lunghe, barcode_rotti, iva_errate, pezzi_errati]
        if not any(blocchi):
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
        "errore": errore,
        "troppo_lunghe": troppo_lunghe,
        "barcode_rotti": barcode_rotti,
        "iva_errate": iva_errate,
        "pezzi_errati": pezzi_errati,
        "articoli": articoli_ok,
        "testata": testata,
        "colonne": [{"campo": c, "label": l, "valore": valori.get(c, ""),
                     "peso": 3 if c == "descrizione" else 1}
                    for c, l in COLONNE],
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