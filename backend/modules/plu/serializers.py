# modules/plu/serializers.py
from rest_framework import serializers
from .models import RepartoPlu, PluModifica, PluAlert


class RepartoPlUSerializer(serializers.ModelSerializer):
    """
    Serializer per RepartoPlu con campi calcolati
    """
    plu_int = serializers.IntegerField(read_only=True)
    ean_formatted = serializers.CharField(read_only=True)
    reparto_nome = serializers.CharField(read_only=True)
    banco_nome = serializers.CharField(read_only=True)
    
    class Meta:
        model = RepartoPlu
        fields = [
            'codArticolo',
            'descrizione',
            'ccom',
            'descrccom',
            'rep',
            'reparto_nome',
            'bancobilancia',
            'banco_nome',
            'plu',
            'plu_int',
            'ean',
            'ean_formatted',
        ]


class RepartoPlUDetailSerializer(RepartoPlUSerializer):
    """
    Serializer dettagliato con informazioni aggiuntive
    """
    modifiche_recenti = serializers.SerializerMethodField()
    
    class Meta(RepartoPlUSerializer.Meta):
        fields = RepartoPlUSerializer.Meta.fields + ['modifiche_recenti']
    
    def get_modifiche_recenti(self, obj):
        """Ultime 5 modifiche"""
        modifiche = PluModifica.objects.filter(
            cod_articolo=obj.codArticolo
        )[:5]
        return PluModificaSerializer(modifiche, many=True).data


class PluModificaSerializer(serializers.ModelSerializer):
    """
    Serializer per storico modifiche
    """
    utente_nome = serializers.CharField(source='utente.username', read_only=True)
    
    class Meta:
        model = PluModifica
        fields = [
            'id',
            'cod_articolo',
            'campo_modificato',
            'valore_precedente',
            'valore_nuovo',
            'utente',
            'utente_nome',
            'data_modifica',
            'note',
        ]
        read_only_fields = ['data_modifica']


class PluAlertSerializer(serializers.ModelSerializer):
    """
    Serializer per alerts
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    stato_display = serializers.CharField(source='get_stato_display', read_only=True)
    risolto_da_nome = serializers.CharField(source='risolto_da.username', read_only=True)
    
    class Meta:
        model = PluAlert
        fields = [
            'id',
            'tipo',
            'tipo_display',
            'cod_articolo',
            'descrizione',
            'stato',
            'stato_display',
            'data_creazione',
            'data_risoluzione',
            'risolto_da',
            'risolto_da_nome',
            'note_risoluzione',
        ]
        read_only_fields = ['data_creazione', 'data_risoluzione']


class RepartoStatsSerializer(serializers.Serializer):
    """
    Serializer per statistiche reparti
    """
    reparto = serializers.IntegerField()
    reparto_nome = serializers.CharField()
    totale_articoli = serializers.IntegerField()
    totale_plu = serializers.IntegerField()
    banchi = serializers.ListField()


class DuplicatoPluSerializer(serializers.Serializer):
    """
    Serializer per PLU duplicati
    """
    plu = serializers.CharField()
    bancobilancia = serializers.CharField()
    banco_nome = serializers.CharField()
    count = serializers.IntegerField()
    articoli = RepartoPlUSerializer(many=True)
