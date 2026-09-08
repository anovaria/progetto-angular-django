from django import forms


class ElabUploadForm(forms.Form):
    file = forms.FileField(
        # Dal 2026 il formato del file può avere qualunque estensione (o nessuna).
        # Esempio: L030060.235
        label='File di testo (qualsiasi estensione)',
        widget=forms.ClearableFileInput(attrs={'accept': '*/*'})
    )


class OrderEmailForm(forms.Form):
    """Form vuota: il file .ext è determinato automaticamente dal sistema."""
    pass
