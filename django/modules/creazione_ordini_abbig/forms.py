import re
from django import forms
from .models import Ordine
from .services import valida_codice_ordine

NOME_FILE_RE = re.compile(r'^[A-Za-z0-9_-]+$')

class OrdineForm(forms.ModelForm):
    nome_file = forms.CharField(max_length=100, required=True)

    class Meta:
        model = Ordine
        fields = ['codice_ordine', 'codice_fornitore', 'codice_commerciale', 'codice_articolo', 'quantita_ordine']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['codice_ordine'].initial = 'ABB0000000000'

    def clean_codice_ordine(self):
        codice = self.cleaned_data['codice_ordine']
        valida_codice_ordine(codice)
        return codice

    def clean_nome_file(self):
        nome = self.cleaned_data['nome_file'].strip()
        if not nome:
            raise forms.ValidationError("Il nome del file è obbligatorio.")
        if not NOME_FILE_RE.match(nome):
            raise forms.ValidationError("Il nome del file può contenere solo lettere, numeri, trattini e underscore (niente spazi, punti o altri simboli).")
        return nome