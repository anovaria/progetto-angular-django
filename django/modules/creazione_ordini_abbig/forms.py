import re
from django import forms
from .models import Ordine
from .services import valida_codice_ordine,parse_lista_testo,parse_lista_quantita

NOME_FILE_RE = re.compile(r'^[A-Za-z0-9_-]+$')

class OrdineForm(forms.ModelForm):
    nome_file = forms.CharField(max_length=100, required=True)
    lista_articoli = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 10}))
    lista_quantita = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 10}))
    class Meta:
        model = Ordine
        fields = ['codice_ordine', 'codice_fornitore', 'codice_commerciale']
        widgets = {
            'codice_ordine': forms.TextInput(attrs={'class': 'form-control'}),
            'codice_fornitore': forms.TextInput(attrs={'class': 'form-control'}),
            'codice_commerciale': forms.TextInput(attrs={'class': 'form-control'}),
        }

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

    def clean_lista_articoli(self):
        testo = self.cleaned_data['lista_articoli']
        return parse_lista_testo(testo)

    def clean_lista_quantita(self):
        testo = self.cleaned_data['lista_quantita']
        try:
            quantita = parse_lista_quantita(testo)
        except ValueError:
            raise forms.ValidationError("Ogni quantità deve essere un numero intero.")
        if any(q <= 0 for q in quantita):
            raise forms.ValidationError("Ogni quantità deve essere maggiore di zero.")
        return quantita
    
    def clean(self):
        cleaned_data = super().clean()
        articoli = cleaned_data.get('lista_articoli')
        quantita = cleaned_data.get('lista_quantita')
        if articoli is not None and quantita is not None:
            if len(articoli) != len(quantita):
                raise forms.ValidationError("Le due liste non sono allineate")
        return cleaned_data