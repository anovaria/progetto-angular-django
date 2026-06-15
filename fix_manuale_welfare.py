from docx import Document
import sys
sys.stdout.reconfigure(encoding='utf-8')

PATH = r"Z:\Progetti IT\2026\Portale\Manuali-Utente\Manuale-Utente-Welfare.docx"

doc = Document(PATH)

VECCHIO = "Il modulo Welfare è integrato nel Portale Gros Cidac, basato su architettura Angular (frontend) e Django (backend). I dati sono memorizzati in un database Microsoft SQL Server."
NUOVO   = "Il modulo Welfare è integrato nel Portale Gros Cidac, basato su architettura Django (Python) con template server-side. I dati sono memorizzati in un database Microsoft SQL Server."

sostituzioni = 0
for p in doc.paragraphs:
    if "Angular" in p.text:
        # Sostituisce preservando la formattazione del primo run
        testo_nuovo = p.text.replace(
            "basato su architettura Angular (frontend) e Django (backend)",
            "basato su architettura Django (Python) con template server-side"
        )
        for run in p.runs:
            run.text = ""
        p.runs[0].text = testo_nuovo
        sostituzioni += 1
        print(f"Sostituito: {testo_nuovo[:80]}...")

if sostituzioni == 0:
    print("ATTENZIONE: nessuna occorrenza trovata, verificare il testo.")
else:
    doc.save(PATH)
    print(f"\nSalvato: {PATH}")
