import os

def create_outlook_mail_with_attachment(attachment_path: str, to: str, subject: str, body: str) -> None:
    """Crea una mail di Outlook in bozza (.Display) con allegato.

    Richiede: Windows + Microsoft Outlook installato e correttamente registrato.
    """
    if not os.path.exists(attachment_path):
        raise FileNotFoundError(f"File allegato non trovato: {attachment_path}")

    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pywin32 non disponibile. Installa con: pip install pywin32"
        ) from e

    try:
        pythoncom.CoInitialize()
    except Exception:
        pass

    out_app = None
    last_err = None
    for creator in ("Dispatch", "DispatchEx"):
        try:
            fn = getattr(win32com.client, creator)
            out_app = fn("Outlook.Application")
            break
        except Exception as e:
            last_err = e

    if out_app is None:
        raise RuntimeError(
            "Impossibile avviare Outlook via COM. "
            "Errore tipico: 'Invalid class string'. "
            "Verifica che Outlook sia installato e avviabile. "
            "Prova anche a eseguire da Start -> Esegui: outlook /regserver "
            f"(dettaglio: {last_err})"
        )

    out_mail = out_app.CreateItem(0)  # 0 = MailItem
    out_mail.To = to
    out_mail.Subject = subject
    out_mail.Body = body
    out_mail.Attachments.Add(os.path.abspath(attachment_path))
    out_mail.Display()
