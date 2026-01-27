from django import forms

class ElabUploadForm(forms.Form):
    file = forms.FileField(
        label='File .elab',
        widget=forms.ClearableFileInput(attrs={'accept': '.elab'})
    )


class OrderEmailForm(forms.Form):
    """Form vuota: il file .ext è determinato automaticamente dal sistema."""
    pass
