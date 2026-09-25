from datetime import date

TRACCIATO = [
    "Codice articolo",
    "Classe attributo",
    "Codice attributo",
    "Valore numerico",
    "Valore alfanumerico",
    "Valore data",
    "Data inizio",
    "Data fine",
]
BLOCCHI = {
    "ACQ": {
        "Codice articolo":       {"tipo": "manuale", "campo": "codice_articolo"},
        "Classe attributo":      {"tipo": "costante", "valore": "ACQ"},
        "Codice attributo":      {"tipo": "calcolato", "funzione": lambda art: art["ccom"]+art["linea"].zfill(2)},
        "Valore numerico":       {"tipo": "costante", "valore": ""},
        "Valore alfanumerico":   {"tipo": "manuale", "campo": "ccom"},
        "Valore data":           {"tipo": "costante", "valore": ""},
        "Data inizio":           {"tipo": "calcolato", "funzione": lambda art: date.today().strftime("%d/%m/%Y")},
        "Data fine":             {"tipo": "costante", "valore": "31/12/2049"},
    },
    "TCOL": {
        "Codice articolo":       {"tipo": "manuale", "campo": "codice_articolo"},
        "Classe attributo":      {"tipo": "costante", "valore": "TCOL"},
        "Codice attributo":      {"tipo": "manuale", "campo": "tcol_attributo"},
        "Valore numerico":       {"tipo": "costante", "valore": ""},
        "Valore alfanumerico":   {"tipo": "manuale", "campo": "tcol_alfa"},
        "Valore data":           {"tipo": "costante", "valore": ""},
        "Data inizio":           {"tipo": "calcolato", "funzione": lambda art: date.today().strftime("%d/%m/%Y")},
        "Data fine":             {"tipo": "costante", "valore": "31/12/2049"},              
    },
    "TIPOFRON": {
        "Codice articolo":       {"tipo": "manuale", "campo": "codice_articolo"},
        "Classe attributo":      {"tipo": "costante", "valore": "TIPOFRON"},
        "Codice attributo":      {"tipo": "costante", "valore": "B"},
        "Valore numerico":       {"tipo": "costante", "valore": ""},
        "Valore alfanumerico":   {"tipo": "costante", "valore": ""},
        "Valore data":           {"tipo": "costante", "valore": ""},
        "Data inizio":           {"tipo": "calcolato", "funzione": lambda art: date.today().strftime("%d/%m/%Y")},
        "Data fine":             {"tipo": "costante", "valore": "31/12/2049"},
    },
    "NOSCOREP": {
        "Codice articolo":       {"tipo": "manuale", "campo": "codice_articolo"},
        "Classe attributo":      {"tipo": "costante", "valore": "NOSCOREP"},
        "Codice attributo":      {"tipo": "costante", "valore": "S"},
        "Valore numerico":       {"tipo": "costante", "valore": ""},
        "Valore alfanumerico":   {"tipo": "costante", "valore": ""},
        "Valore data":           {"tipo": "costante", "valore": ""},
        "Data inizio":           {"tipo": "calcolato", "funzione": lambda art: date.today().strftime("%d/%m/%Y")},
        "Data fine":             {"tipo": "manuale_con_default", "campo": "noscorep_data_fine", "default": "31/12/2049"},      
    },
    "SARGC": {
        "Codice articolo":       {"tipo": "manuale", "campo": "codice_articolo"},
        "Classe attributo":      {"tipo": "costante", "valore": "SARGC"},
        "Codice attributo":      {"tipo": "manuale", "campo": "sargc_attributo"},
        "Valore numerico":       {"tipo": "costante", "valore": ""},
        "Valore alfanumerico":   {"tipo": "costante", "valore": ""},
        "Valore data":           {"tipo": "costante", "valore": ""},
        "Data inizio":           {"tipo": "calcolato", "funzione": lambda art: date.today().strftime("%d/%m/%Y")},
        "Data fine":             {"tipo": "costante", "valore": "31/12/2049"},    
    }
}
COLONNE_INPUT = [
    ("codice_articolo", "Codice articolo"),
    ("ccom", "Codice CCOM"),
    ("linea", "Linea"),
    ("tcol_attributo", "Codice attributo TCOL"),
    ("tcol_alfa", "Valore alfanumerico TCOL"),
    ("sargc_attributo", "Codice attributo SARGC"),
    ("noscorep_data_fine", "Data Fine NOSCOREP")
]
CAMPI_OBBLIGATORI =  [campo for campo, _label in COLONNE_INPUT if campo != "noscorep_data_fine"]