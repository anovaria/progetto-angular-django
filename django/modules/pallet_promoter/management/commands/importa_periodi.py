"""
Management command per importare periodi promozionali da Excel CED.

Uso:
    python manage.py importa_periodi percorso/file.xlsx
    python manage.py importa_periodi percorso/file.xlsx --dry-run
    python manage.py importa_periodi percorso/file.xlsx --tutti  (importa anche Q, S, T, W)
"""

import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from modules.pallet_promoter.models import Periodo


class Command(BaseCommand):
    help = 'Importa periodi promozionali da file Excel CED'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Percorso del file Excel')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula importazione senza salvare',
        )
        parser.add_argument(
            '--tutti',
            action='store_true',
            help='Importa tutti i tipi (P, Q, S, T, W), non solo P-*',
        )
        parser.add_argument(
            '--anno',
            type=int,
            help='Filtra solo periodi di un anno specifico',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        importa_tutti = options['tutti']
        anno_filtro = options.get('anno')

        # Verifica file esiste
        if not os.path.exists(file_path):
            raise CommandError(f'File non trovato: {file_path}')

        # Importa pandas/openpyxl
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('Installa pandas: pip install pandas openpyxl')

        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('IMPORTAZIONE PERIODI PROMOZIONALI'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(f'File: {file_path}')
        self.stdout.write(f'Dry run: {"Sì" if dry_run else "No"}')
        self.stdout.write(f'Filtro: {"Tutti i tipi" if importa_tutti else "Solo P-* (Pallet)"}')
        if anno_filtro:
            self.stdout.write(f'Anno: {anno_filtro}')
        self.stdout.write('=' * 60)

        # Leggi Excel
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise CommandError(f'Errore lettura Excel: {e}')

        self.stdout.write(f'\nRighe nel file: {len(df)}')

        # Verifica colonne
        colonne_richieste = ['Promozione', 'Cod.Est.Promo', 'Descrizione', 'Iniz.vend.', 'Fine vend.']
        colonne_mancanti = [c for c in colonne_richieste if c not in df.columns]
        if colonne_mancanti:
            raise CommandError(f'Colonne mancanti: {colonne_mancanti}')

        # Filtra solo P-* se non --tutti
        if not importa_tutti:
            df = df[df['Cod.Est.Promo'].str.startswith('P-', na=False)]
            self.stdout.write(f'Righe dopo filtro P-*: {len(df)}')

        # Contatori
        creati = 0
        aggiornati = 0
        errori = 0

        for idx, row in df.iterrows():
            try:
                codice = str(row['Cod.Est.Promo']).strip()
                codice_promozione = int(row['Promozione'])
                descrizione = str(row['Descrizione']).strip()
                
                # Parse date
                data_inizio = pd.to_datetime(row['Iniz.vend.']).date()
                data_fine = pd.to_datetime(row['Fine vend.']).date()
                
                # Calcola anno dalla data inizio
                anno = data_inizio.year
                
                # Filtra per anno se specificato
                if anno_filtro and anno != anno_filtro:
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [DRY-RUN] {codice} | {descrizione[:40]} | '
                        f'{data_inizio} - {data_fine} | Anno {anno}'
                    )
                    creati += 1
                else:
                    # Crea o aggiorna
                    periodo, created = Periodo.objects.update_or_create(
                        codice=codice,
                        defaults={
                            'codice_promozione': codice_promozione,
                            'descrizione': descrizione,
                            'data_inizio': data_inizio,
                            'data_fine': data_fine,
                            'anno': anno,
                            'num_hostess': 8,
                        }
                    )
                    if created:
                        creati += 1
                        self.stdout.write(self.style.SUCCESS(f'  ✅ CREATO: {codice}'))
                    else:
                        aggiornati += 1
                        self.stdout.write(f'  🔄 Aggiornato: {codice}')

            except Exception as e:
                errori += 1
                self.stdout.write(self.style.ERROR(f'  ❌ Errore riga {idx}: {e}'))

        # Riepilogo
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'COMPLETATO!'))
        self.stdout.write(f'  Creati: {creati}')
        self.stdout.write(f'  Aggiornati: {aggiornati}')
        if errori:
            self.stdout.write(self.style.ERROR(f'  Errori: {errori}'))
        self.stdout.write('=' * 60)
