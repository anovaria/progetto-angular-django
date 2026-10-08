from django import forms

from .models import Prenotazione
from .services import camera_occupata

class PrenotazioneForm(forms.ModelForm):

    class Meta:
        model = Prenotazione
        fields = ['camera', 'cognome', 'nome', 'azienda', 'data_arrivo', 'data_partenza', 'note']
        widgets = {
            'data_arrivo': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_partenza': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        camera = cleaned_data.get('camera')
        arrivo = cleaned_data.get('data_arrivo')
        partenza = cleaned_data.get('data_partenza')

        if not (camera and arrivo and partenza):
            return cleaned_data

        if partenza <= arrivo:
            raise forms.ValidationError('La data di partenza deve essere successiva alla data di arrivo.')

        if camera_occupata(camera, arrivo, partenza,escludi_pk=self.instance.pk):
            raise forms.ValidationError('La camera è già occupata in almeno una delle date scelte. Controlla il planning.')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.Select):
                campo.widget.attrs['class'] = 'form-select'
            else:
                campo.widget.attrs['class'] = 'form-control'

        self.fields['camera'].disabled = True
        if not self.instance.pk:
            self.fields['camera'].disabled = True