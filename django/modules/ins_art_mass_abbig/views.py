from django.shortcuts import render
from datetime import date
from .config import tracciato, VARIANTI
import csv
import io
from django.http import HttpResponse

# Le colonne che l'utente incolla, una per box, uguali per tutte e 4 le varianti.
# Fornitore e Contratto commerciale sono per-riga (non c'è più un unico valore
# per infornata: possono cambiare articolo per articolo).
# La tupla è (nome del campo, etichetta mostrata a schermo).
COLONNE = [
    ("fornitore",   "Codice fornitore"),
    ("ccom",        "Contratto commerciale"),
    ("barcode",     "Barcode"),
    ("descrizione", "Descrizione principale"),
    ("struttura",   "Struttura merceologica"),
    ("costo",       "Costo lordo"),
    ("prezzo",      "Prezzo di vendita base"),
    ("referenza",   "Referenza fornitore"),
    ("codgold",     "Codice articolo Gold"),
]


def _parse_input(valori):
    """Accoppia per posizione le colonne incollate in box separati.

    valori: dizionario {campo: testo della textarea}

    La riga N di ogni box appartiene allo stesso articolo, quindi tutte le
    liste devono avere lo stesso numero di righe. Se non è così restituisce
    un errore invece degli articoli: meglio fermarsi che generare righe sfasate.
    """
    liste = {
        campo: [r.strip() for r in valori.get(campo, "").split("\n") if r.strip()]
        for campo, _label in COLONNE
    }

    conteggi = {campo: len(v) for campo, v in liste.items()}
    n = max(conteggi.values()) if conteggi else 0

    if n == 0:
        return [], "Non hai incollato nessun dato."

    diverse = [f"{label}: {conteggi[campo]}"
               for campo, label in COLONNE if conteggi[campo] != n]
    if diverse:
        return [], (f"Le colonne hanno un numero di righe diverso (attese {n}). "
                    f"Controlla — {' · '.join(diverse)}")

    articoli = [
        {campo: liste[campo][i] for campo, _label in COLONNE}
        for i in range(n)
    ]
    return articoli, None


def _valida(articoli):
    """Stessi controlli di ins_articoli: descrizioni troppo lunghe, barcode
    finiti in notazione scientifica."""
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
    return troppo_lunghe, barcode_rotti


def _genera_righe(articoli, variante):
    """Costruisce le righe del CSV: una per articolo, 80 valori ciascuna."""
    oggi = date.today().strftime("%d/%m/%Y")
    fine = "31/12/2049"
    righe = []
    for art in articoli:
        riga = []
        for col in tracciato(variante):
            tipo = col["tipo"]
            if tipo == "articolo":
                valore = art.get(col["campo"], "")
                # Costo e prezzo: Gold vuole la virgola come separatore decimale
                if col["campo"] in ("costo", "prezzo"):
                    valore = valore.replace(".", ",")
            elif tipo == "costante":
                valore = col["valore"]
            elif tipo == "oggi":
                valore = oggi
            elif tipo == "fine":
                valore = fine
            elif tipo == "desc20":
                valore = art.get("descrizione", "")[:20]
            else:
                valore = ""
            riga.append(valore)
        righe.append(riga)
    return righe


def _tab_vuota(slug, meta):
    return {
        "slug": slug,
        "label": meta["label"],
        "valori": {campo: "" for campo, _label in COLONNE},
        "articoli": None,
        "errore": None,
        "troppo_lunghe": [], "barcode_rotti": [],
        "pronta": False,
    }


def index(request):
    tabs = {slug: _tab_vuota(slug, meta) for slug, meta in VARIANTI.items()}
    attiva = request.POST.get("variante", "for-normale")
    if attiva not in VARIANTI:
        attiva = "for-normale"

    if request.method == "POST":
        t = tabs[attiva]
        t["valori"] = {campo: request.POST.get(campo, "") for campo, _label in COLONNE}

        articoli, errore = _parse_input(t["valori"])
        t["errore"] = errore

        if not errore:
            troppo_lunghe, barcode_rotti = _valida(articoli)
            t["troppo_lunghe"] = troppo_lunghe
            t["barcode_rotti"] = barcode_rotti

            if not any([troppo_lunghe, barcode_rotti]):
                righe = _genera_righe(articoli, attiva)

                sessione_righe = request.session.get('ins_art_mass_righe', {})
                sessione_ccom = request.session.get('ins_art_mass_ccom', {})
                sessione_righe[attiva] = righe
                sessione_ccom[attiva] = articoli[0]["ccom"] or "articoli"
                request.session['ins_art_mass_righe'] = sessione_righe
                request.session['ins_art_mass_ccom'] = sessione_ccom

                t["articoli"] = articoli
                t["pronta"] = True

    for t in tabs.values():
        t["colonne"] = [
            {"campo": c, "label": l, "valore": t["valori"].get(c, "")}
            for c, l in COLONNE
        ]

    return render(request, "ins_art_mass_abbig/index.html", {
        "tabs": tabs,
        "attiva": attiva,
    })


def download(request):
    """Scarica il CSV generato per la variante indicata in ?v=.

    Arriva in GET (è un link), quindi le righe vengono rilette dalla sessione
    dove le ha salvate la view index, tenute separate per variante.
    """
    variante = request.GET.get('v', '')
    sessione_righe = request.session.get('ins_art_mass_righe', {})
    sessione_ccom = request.session.get('ins_art_mass_ccom', {})
    righe = sessione_righe.get(variante, [])
    ccom = sessione_ccom.get(variante, 'articoli')

    if variante not in VARIANTI or not righe:
        return HttpResponse("Nessun dato da scaricare. Genera prima le righe.", status=400)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow([c["nome"] for c in tracciato(variante)])
    writer.writerows(righe)

    # Gold vuole ISO-8859-1 (cp1252), non UTF-8: le accentate uscirebbero
    # sbagliate. errors='replace' evita il crash su caratteri non rappresentabili.
    contenuto = buffer.getvalue().encode('cp1252', errors='replace')

    response = HttpResponse(contenuto, content_type='text/csv; charset=ISO-8859-1')
    response['Content-Disposition'] = f'attachment; filename="{ccom}-{variante}.csv"'
    return response
