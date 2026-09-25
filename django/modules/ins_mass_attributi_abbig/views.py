import re,io,csv

from django.http import HttpResponse
from django.shortcuts import render
from .config import BLOCCHI,COLONNE_INPUT,CAMPI_OBBLIGATORI, TRACCIATO

def _valore_campo(definizione, art):
    if definizione["tipo"] == "manuale":
        valore=art.get(definizione["campo"])
    elif definizione["tipo"] == "costante":   
        valore=definizione["valore"]
    elif definizione["tipo"] == "calcolato":
        valore=definizione["funzione"](art)
    elif definizione["tipo"] == "manuale_con_default":
        valore = art.get(definizione["campo"], "") or definizione["default"]

    return valore

def _riga_blocco(blocco, art):
    colonne = BLOCCHI[blocco]
    lista=[]
    for c, v in colonne.items():
        lista.append(_valore_campo(v, art))
    return lista

def _righe_blocco(blocco, articoli):
    riga=[]
    for a in articoli:
        riga.append(_riga_blocco(blocco,a))
    return riga

def _genera_righe(articoli):
    righe={}
    for b in BLOCCHI:
        righe[b]= _righe_blocco(b,articoli)
    return righe

def _parsing(valori):
    liste = {}
    for campo, _label in COLONNE_INPUT:
        righe_grezze = valori.get(campo, "").split("\n")
        if campo == "noscorep_data_fine":
            liste[campo] = [r.strip() for r in righe_grezze]
        else:
            liste[campo] = [r.strip() for r in righe_grezze if r.strip()]

    conteggi = {campo: len(liste[campo]) for campo in liste}
    n = len(liste["codice_articolo"])
    if n == 0:
        return [], "Non hai incollato nessun dato."
    
    diverse = [f"{campo}: {conteggi[campo]}"
           for campo in CAMPI_OBBLIGATORI if conteggi[campo] != n]
    if diverse:
        return [], (f"Le colonne hanno un numero di righe diverso (attese {n}). "
                f"Controlla — {' · '.join(diverse)}")
    
    codici = liste["codice_articolo"]
    if len(codici) != len(set(codici)):
        return [], "Ci sono Codici articolo duplicati."
    
    articoli = []
    righe_noscorep = liste["noscorep_data_fine"]
    for i in range(n):
        valore_noscorep = righe_noscorep[i] if i < len(righe_noscorep) else ""
        art = {
            "codice_articolo": liste["codice_articolo"][i],
            "ccom": liste["ccom"][i],
            "linea": liste["linea"][i],
            "tcol_attributo": liste["tcol_attributo"][i],
            "tcol_alfa": liste["tcol_alfa"][i],
            "sargc_attributo": liste["sargc_attributo"][i],
            "noscorep_data_fine": valore_noscorep,
        }
        articoli.append(art)

    return articoli, None

def _valida(articoli):
    cod_err = [
        {"riga": i, "codice_articolo": a["codice_articolo"], "lunghezza": len(a["codice_articolo"])}
        for i, a in enumerate(articoli, start=1)
        if len(a["codice_articolo"]) != 6
    ]
    return cod_err

def index(request):
    righe = None
    errore = None
    valori = {campo: "" for campo, _label in COLONNE_INPUT}
    codici_non_validi = []
    pronta = False
    if request.method == "POST":
        valori = {campo: request.POST.get(campo, "") for campo, _label in COLONNE_INPUT}
        articoli, errore = _parsing(valori)
        
        if not errore:
            codici_non_validi = _valida(articoli)
            if not codici_non_validi: 
                righe = _genera_righe(articoli)
                nome_file = request.POST.get('nome_file', '').strip()
                request.session['ins_attr_righe'] = righe
                request.session['ins_attr_nome'] = nome_file
                pronta = True
    colonne = [
        {"campo": campo, "label": _label, "valore": valori.get(campo, "")}
        for campo, _label in COLONNE_INPUT
    ]
    blocchi = list(BLOCCHI.keys())

    return render(request, "ins_mass_attributi_abbig/index.html", {
    "colonne": colonne,
    "errore": errore,
    "codici_non_validi": codici_non_validi,
    "pronta": pronta,
    "righe": righe,
    "blocchi": blocchi,
})

def download(request):
    blocco = request.GET.get('b', '')
    righe_sessione = request.session.get('ins_attr_righe',{})
    nome_base = request.session.get('ins_attr_nome','')
    righe = righe_sessione.get(blocco)
    if blocco not in BLOCCHI or not righe:
        return HttpResponse("Nessun dato da scaricare. Genera prima le righe.", status=400)
    if not nome_base:
        nome_base = "attributi_abbig"
    nome_file = f"{nome_base}_{blocco}"
    if nome_file.lower().endswith('.csv'):
        nome_file = nome_file[:-4]
    nome_file = re.sub(r'[\\/:*?"<>|\r\n]', '_', nome_file)

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(TRACCIATO)
    writer.writerows(righe)
    contenuto = buffer.getvalue().encode('cp1252', errors='replace')
    response = HttpResponse(contenuto, content_type='text/csv; charset=ISO-8859-1')
    response['Content-Disposition'] = f'attachment; filename="{nome_file}.csv"'
    return response