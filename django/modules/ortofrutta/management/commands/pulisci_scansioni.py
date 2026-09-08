import datetime
from django.core.management.base import BaseCommand
from modules.ortofrutta.models import ScansioneOrtofrutta,ListinoGiorno


class Command(BaseCommand):
    help = 'Cancella le scansioni ortofrutta dei giorni precedenti'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe cancellato senza cancellare nulla',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        oggi = datetime.date.today()

        vecchie = ScansioneOrtofrutta.objects.filter(creato_il__date__lt=oggi)
        quante = vecchie.count()

        listini_vecchi = ListinoGiorno.objects.filter(data_competenza__lt=oggi)
        quanti_listini = listini_vecchi.count()

        if dry_run:
            self.stdout.write(f'[DRY RUN] Verrebbero cancellate {quante} scansioni e {quanti_listini} righe di listino precedenti al {oggi}')
            return

        vecchie.delete()
        listini_vecchi.delete()
        self.stdout.write(f'Cancellate {quante} scansioni precedenti al {oggi}')
        self.stdout.write(f'Cancellate {quanti_listini} righe di listino precedenti al {oggi}')