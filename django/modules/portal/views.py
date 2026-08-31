from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from modules.auth.backends import LDAPBackend
from modules.auth.models import UserAppPermission

"""
Modulo views del portale principale.

Gestisce le viste di login/logout, la homepage, la pagina degli utenti online,
l'amministrazione dei messaggi di sistema e la gestione dei permessi per app.
La configurazione del menu viene costruita staticamente in MENU_CONFIG e filtrata
in base ai gruppi LDAP e ai permessi individuali dell'utente.
"""

# Configurazione menu - allineata con Angular APP_PERMISSIONS
# Ogni voce definisce: percorso, etichetta, icona Bootstrap Icons,
# gruppi autorizzati e nome app per i permessi individuali.
# Il campo 'desc' alimenta il tooltip (attributo title) mostrato sulla voce di menu.
# Le voci con 'children' generano sottomenu espandibili nella sidebar.
MENU_CONFIG = [
    {
        'path': '/app/masterdata/',
        'label': 'Assortimento',
        'icon': 'basket',
        'desc': 'Consultazione ed esportazione del catalogo articoli (masterdata)',
        'groups': ['acquisti', 'itd', 'gruppoced'],
        'app_name': 'masterdata',
    },
    {
        'path': '/app/masterdatacategory/',
        'label': 'MD Category',
        'icon': 'grid-3x3-gap',
        'desc': 'Gestione delle categorie merceologiche del masterdata',
        'groups': ['itd'],
        'app_name': 'masterdatacategory',
    },
    {
        'path': '/app/ricette/',
        'label': 'Ricette',
        'icon': 'journal-richtext',
        'desc': 'Gestione delle ricette degli articoli (ingredienti e imballi)',
        'groups': ['itd'],
        'app_name': 'ricette',
    },
    {
        'path': '/app/plu/',
        'label': 'PLU',
        'icon': 'upc-scan',
        'desc': 'Gestione e stampa dei codici PLU per le bilance',
        'groups': ['acquisti', 'freschi', 'itd' ,'gruppoced'],
        'app_name': 'plu',
    },
    {
        'path': '/app/stampaoffertefuture/',
        'label': 'Offerte Future',
        'icon': 'tag',
        'desc': 'Consultazione ed esportazione delle offerte promozionali future',
        'groups': ['comunicazione', 'itd', 'gruppoced'],
        'app_name': 'stampaoffertefuture',
    },
    {
        'path': '/app/offerte-future-pdv/',
        'label': 'Offerte Future PDV',
        'icon': 'file-earmark-image',
        'desc': 'Griglia articoli in promo futura per il PDV (CCOM, giacenze, data consegna)',
        'groups': ['itd', 'resp.vendita'],
        'app_name': 'offerte_future_pdv',
    },
    {
        'path': '/app/importelab/',
        'label': 'Rossetto',
        'icon': 'arrow-repeat',
        'desc': 'Importazione ed elaborazione degli ordini collio (flusso Rossetto)',
        'groups': ['itd','acquisti'],
        'app_name': 'importelab',
    },
    {
        'path': '/app/master-ordini/',
        'label': 'Master Ordini',
        'icon': 'file-earmark-excel',
        'desc': 'Consultazione ed esportazione degli ordini fornitori',
        'groups': ['itd','acquisti'],
        'app_name': 'master-ordini',
    },
    {
        'path': '#',
        'label': 'Bidone',
        'icon': 'clipboard2-check',
        'desc': 'Controlli qualità dati acquisti (ex fogli Excel "lista controlli vari")',
        'groups': ['itd','gruppoced'],
        'app_name': 'bidone',
        'children': [
            {'path': '/app/ordini-bloccati/',     'label': 'Ordini Bloccati',         'icon': 'exclamation-triangle', 'desc': 'Ordini fornitore non trasmessi a Gold per errore',          'groups': []},
            {'path': '/app/art-stato-ord-aperta/','label': 'Art. Stato E Ord. Aperta', 'icon': 'box-seam',             'desc': 'Articoli eliminati con ordine fornitore ancora aperto',   'groups': []},
            {'path': '/app/promo-doppie/',        'label': 'Promo Doppie',             'icon': 'tags',                 'desc': 'Articoli con due promozioni sovrapposte attive oggi',       'groups': []},
            {'path': '/app/promo-doppie-domani/', 'label': 'Promo Doppie Domani',      'icon': 'calendar-event',       'desc': 'Articoli con promozioni sovrapposte che iniziano domani',  'groups': []},
            {'path': '/app/giac-negative/',       'label': 'Giacenze Negative',        'icon': 'arrow-down-circle',    'desc': 'Articoli con giacenza PDV negativa (escluso sett. 2)',     'groups': []},
            {'path': '/app/art-no-ean/',          'label': 'Articoli senza EAN',       'icon': 'upc-scan',             'desc': 'Articoli attivi sprovvisti di codice EAN',                 'groups': []},
            {'path': '/app/stesso-prezzo/',       'label': 'Promo Stesso Prezzo',      'icon': 'tag',                  'desc': 'Promo con prezzo offerta uguale al prezzo di vendita',     'groups': []},
            {'path': '/app/prezzo-promo-alto/',   'label': 'Prezzo Promo Alto',        'icon': 'exclamation-circle',   'desc': 'Promo con prezzo offerta superiore al prezzo di vendita',  'groups': []},
            {'path': '/app/controllo-legami/',    'label': 'Controllo Legami Kit',     'icon': 'diagram-3',            'desc': 'Verifica coerenza prezzi componenti vs kit (V_QC110)',     'groups': []},
        ],
    },
    {
        'path': '/app/rio-fornitori/',
        'label': 'Riordino Fornitori srviis',
        'icon': 'truck',
        'desc': 'Riordino fornitori - versione legacy su srviis (fallback, solo ITD)',
        'groups': ['itd'],
        'app_name': 'rio-fornitori',
    },
    {
        'path': '/app/rio-fornitori-new/',
        'label': 'Riordino Fornitori',
        'icon': 'truck',
        'desc': 'Riordino fornitori per codice con trasferimento a Gold',
        'groups': ['acquisti', 'itd'],
        'app_name': 'rio-fornitori-new',
    },
    {
        'path': '/app/pallet-promoter/',
        'label': 'Pallet Buyer',
        'icon': 'box-seam',
        'desc': 'Assegnazione di pallet e testate promozionali e planning hostess',
        'groups': ['acquisti', 'agenzie', 'itd'],
        'app_name': 'pallet-promoter',
        'children': [
            {'path': '/app/pallet-promoter/', 'label': 'Dashboard', 'icon': 'speedometer2', 'groups': []},
            {'path': '/app/pallet-promoter/pallet/', 'label': 'Gestione Pallet', 'icon': 'grid', 'groups': []},
            {'path': '/app/pallet-promoter/testate/', 'label': 'Gestione Testate', 'icon': 'layout-three-columns', 'groups': []},
            {'path': '/app/pallet-promoter/hostess/scelta-fornitore/', 'label': 'Scelta Fornitore', 'icon': 'table', 'groups': []},
        ],
    },
    {
        'path': '/app/merchandiser/',
        'label': 'Merchandiser Agenzie',
        'icon': 'shop',
        'desc': 'Gestione slot, anagrafica e timbrature dei merchandiser delle agenzie',
        'groups': ['agenzie', 'itd'],
        'app_name': 'merchandiser',
        'children': [
            {'path': '/app/merchandiser/', 'label': 'Dashboard', 'icon': 'speedometer2', 'groups': []},
            {'path': '/app/merchandiser/slot/', 'label': 'Gestione Slot', 'icon': 'calendar2-check', 'groups': []},
            {'path': '/app/merchandiser/merchandiser/', 'label': 'Anagrafica Merchandiser', 'icon': 'people', 'groups': []},
        ],
    },
    {
        'path': '/app/alloca-hostess/',
        'label': 'Hostess Agenzie',
        'icon': 'people',
        'desc': 'Allocazione hostess negli slot e registrazione di presenze e orari',
        'groups': ['agenzie', 'itd'],
        'app_name': 'alloca-hostess',
        'children': [
            {'path': '/app/alloca-hostess/', 'label': 'Dashboard', 'icon': 'speedometer2', 'groups': []},
            {'path': '/app/alloca-hostess/individuazione/', 'label': 'Gestione Slot', 'icon': 'person-bounding-box', 'groups': []},
            {'path': '/app/alloca-hostess/hostess/', 'label': 'Lista Hostess', 'icon': 'person-badge', 'groups': []},
            {'path': '/app/merchandiser/hostess/', 'label': 'Anagrafica Hostess', 'icon': 'people', 'groups': []},
        ],
    },
    {
        'path': '/app/merchandiser/agenzie/',
        'label': 'Gestione Agenzie',
        'icon': 'building',
        'desc': 'Anagrafica e gestione delle agenzie esterne',
        'groups': ['agenzie', 'itd'],
        'app_name': 'agenzie',
    },
    {
        'path': '/app/merchandiser/solo-orari/',
        'label': 'Orari Merchandiser Pinfo',
        'icon': 'clock',
        'desc': 'Consultazione degli orari dei merchandiser (vista Pinfo)',
        'groups': ['pinfo', 'agenzie', 'itd'],
        'app_name': 'solo-orari',
    },
    {
        'path': '/app/alloca-hostess/orari-hostess/',
        'label': 'Orari Hostess Pinfo',
        'icon': 'clock',
        'desc': 'Consultazione degli orari delle hostess (vista Pinfo)',
        'groups': ['pinfo', 'agenzie', 'itd'],
        'app_name': 'orari-hostess',
    },
    {
        'path': '/app/alloca-hostess/attivita-non-previste/',
        'label': 'Attività non previste Pinfo',
        'icon': 'person-lines-fill',
        'desc': 'Registrazione delle attività hostess non previste (Pinfo)',
        'groups': ['pinfo', 'agenzie', 'itd'],
        'app_name': 'attivita-non-previste',
    },
    {
        'path': '/app/cursori/',
        'label': 'Cursori Terminali',
        'icon': 'upc-scan',
        'desc': 'Funzioni del terminale palmare: dettaglio articolo da scansione EAN',
        'groups': ['itd','resp.vendita'],
        'app_name': 'cursori',
    },
    {
        'path': '/app/entrata-merci/',
        'label': 'Entrata Merci',
        'icon': 'box-arrow-in-down',
        'desc': 'Consultazione ed esportazione delle merci in entrata per PDV e Magazzino',
        'groups': ['itd','resp.vendita'],
        'app_name': 'entrata-merci',
    },
    {
        'path': '/app/welfare/',
        'label': 'Welfare',
        'icon': 'gift',
        'desc': 'Gestione dei buoni welfare aziendali (contabilità e consegne)',
        'groups': ['ufficio cassa', 'pinfo', 'itd'],
        'app_name': 'welfare',
        'children': [
            {'path': '/app/welfare/', 'label': 'Dashboard', 'icon': 'speedometer2', 'groups': ['ufficio cassa', 'itd']},
            {'path': '/app/welfare/contabilita/', 'label': 'Contabilità', 'icon': 'bar-chart-line', 'groups': ['ufficio cassa', 'itd']},
            {'path': '/app/welfare/da-consegnare/', 'label': 'Da Consegnare', 'icon': 'inbox', 'groups': ['ufficio cassa', 'pinfo', 'itd']},
            {'path': '/app/welfare/storico/', 'label': 'Storico Consegne', 'icon': 'clock-history', 'groups': ['ufficio cassa', 'pinfo', 'itd']},
            {'path': '/app/welfare/import/', 'label': 'Import Email', 'icon': 'envelope', 'groups': ['ufficio cassa', 'itd']},
        ],
    },
    {
        'path': '/app/asso-articoli/',
        'label': 'AssoArticoli',
        'icon': 'box-seam',
        'desc': 'Consultazione e filtro degli articoli dell\'assortimento (GoldReport)',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'asso-articoli',
    },
    {
        'path': '/app/scaricopromo/attributi/',
        'label': 'Attributi',
        'icon': 'tags',
        'desc': 'Creazione del file attributi da importare su Gold',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'scaricopromo',
    },
    {
        'path': '/app/scaricopromo/',
        'label': 'Scaricopromo',
        'icon': 'card-checklist',
        'desc': 'Gestione promozioni: tabelle "Mettere in" ed export CSV',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'scaricopromo',
    },
    {
        'path': '/app/caricopromo-reparto/',
        'label': 'Caricopromo',
        'icon': 'card-heading',
        'desc': 'Caricamento promozioni di reparto (selezione CCOM e articoli)',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'caricopromo-reparto',
    },
    {
        'path': '/app/caricopromo-abbig/',
        'label': 'Caricopromo Abbig.',
        'icon': 'card-heading',
        'desc': 'Caricamento promozioni per il reparto abbigliamento',
        'groups': ['abbigliamento', 'itd'],
        'app_name': 'caricopromo-abbig',
    },
    {
        'path': '/app/assortimento-abbig/',
        'label': 'Assortimento Abbig.',
        'icon': 'handbag',
        'desc': 'Assortimento abbigliamento con filtri Reparto/Fornitore/CCOM',
        'groups': ['abbigliamento', 'itd'],
        'app_name': 'assortimento-abbig',
    },
    {
        'path': '/app/invenduti/',
        'label': 'Invenduti',
        'icon': 'archive',
        'desc': 'Consultazione ed esportazione degli articoli invenduti',
        'groups': ['itd', 'resp.vendita'],
        'app_name': 'invenduti',
    },
        {
        'path': '/app/giacenze-negative/',
        'label': 'Giacenze Negative',
        'icon': 'archive',
        'desc': 'Consultazione delle giacenze negative',
        'groups': ['itd', 'resp.vendita'],
        'app_name': 'giacenze-negative',
    },
    {
        'path': '/app/stock-picking/',
        'label': 'Stock Picking',
        'icon': 'box-arrow-in-down',
        'desc': 'Consultazione ed esportazione dello stock picking articoli',
        'groups': ['itd', 'depositi'],
        'app_name': 'stock-picking',
    },
    {
        'path': '/app/picking-negativi/',
        'label': 'Picking Negativi',
        'icon': 'exclamation-triangle',
        'desc': 'Visualizzazione ed esportazione dei picking con quantità negative',
        'groups': ['itd', 'depositi'],
        'app_name': 'picking-negativi',
    },
    {
        'path': '/app/piano-promo/',
        'label': 'Piano Promo',
        'icon': 'calendar2-check',
        'desc': 'Creazione e gestione delle sessioni di piano promo (Gold)',
        'groups': ['itd','depositi'],
        'app_name': 'piano-promo',
    },
    {
        'path': '/app/edicola/',
        'label': 'Edicola',
        'icon': 'journal-text',
        'desc': 'Gestione degli articoli e dei movimenti dell\'edicola',
        'groups': ['edicola', 'itd'],
        'app_name': 'edicola',
    },
    {
        'path': '/app/scarti-gettati/',
        'label': 'Scarti Gettati',
        'icon': 'trash3',
        'desc': 'Registrazione degli scarti gettati al banco taglio',
        'groups': ['itd'],
        'app_name': 'scarti-gettati',
    },
    {
        'path': '/app/ricerca_gold/',
        'label': 'Ricerca EAN / Cod. Gold / Cod. Fornitore',
        'icon': 'search',
        'desc': 'Sostituisce il file Excel Ricerca_Ean_CodGold_CodFor',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'ricerca_gold',
    },
    {
        'path': '/app/ins-articoli/',
        'label': 'Ins. Art. 10001',
        'icon': 'search',
        'desc': 'Sostituisce il file Excel Inser_Articoli_10001',
        'groups': ['itd'],
        'app_name': 'Ins. Art. 10001',
    },
    {
        'path': '/app/preventivi/',
        'label': 'Preventivi',
        'icon': 'journal-text',
        'desc': 'Sostituisce il file Excel',
        'groups': ['gruppoced', 'itd'],
        'app_name': 'Preventivi',
    },
    {
        'path': '/app/ortofrutta/',
        'label': 'Scarico Frescheria',
        'icon': 'journal-text',
        'desc': 'Sostituisce il file Excel',
        'groups': ['ortofrutta', 'itd'],
        'app_name': 'Scarico Frescheria',
    },
    {
        'path': '/portal/utenti-online/',
        'label': 'Utenti Online',
        'icon': 'people',
        'desc': 'Elenco degli utenti attualmente collegati al portale',
        'groups': ['itd'],
    },
    {
        'path': '/portal/admin-msg/',
        'label': 'Messaggi Portale',
        'icon': 'megaphone',
        'desc': 'Pubblicazione degli avvisi di sistema mostrati nel portale',
        'groups': ['itd'],
    },
    {
        'path': '/portal/admin-permessi/',
        'label': 'Gestione Permessi',
        'icon': 'shield-check',
        'desc': 'Assegnazione dei permessi individuali alle app del portale',
        'groups': ['itd'],
    },
    {
        'path': '/admin/',
        'label': 'Django Admin',
        'icon': 'shield-lock',
        'desc': 'Pannello di amministrazione Django (si apre in una nuova scheda)',
        'groups': ['itd'],
        'is_external': True,
    },
]

def can_access(app, user_groups, username, user_app_permissions=None):
    """
    Verifica se l'utente può vedere un'app (voce padre del menu).

    Controlla prima i permessi individuali salvati nel database (UserAppPermission),
    poi verifica se uno dei gruppi LDAP dell'utente è tra quelli autorizzati per l'app.
    """
    # Controlla permessi individuali dal database
    app_name = app.get('app_name')
    if app_name and user_app_permissions and app_name in user_app_permissions:
        return True
    # Confronto case-insensitive tra i gruppi dell'utente e quelli richiesti dall'app
    user_groups_lower = [g.lower() for g in user_groups]
    return any(g.lower() in user_groups_lower for g in app.get('groups', []))

def can_access_child(parent, child, user_groups, username, user_app_permissions=None):
    """
    Verifica se l'utente può vedere un elemento figlio del menu (child).

    Logica di accesso a cascata:
    1. Se il child ha una lista 'users', controlla se l'username corrente vi appartiene.
    2. Se l'utente ha un permesso individuale sul padre, può vedere tutti i figli.
    3. Se il child ha gruppi propri non vuoti, controlla quelli.
    4. Se child.groups è vuoto [], eredita i permessi dal padre.
    """
    child_users = child.get('users', [])
    # Accesso per username specifico configurato direttamente sul child
    if child_users and username.lower() in [u.lower() for u in child_users]:
        return True
    # Permesso individuale sul padre → accesso a tutti i children
    parent_app = parent.get('app_name')
    if parent_app and user_app_permissions and parent_app in user_app_permissions:
        return True
    child_groups = child.get('groups', [])
    if child_groups:
        # Il child ha gruppi propri: verifica l'appartenenza dell'utente
        user_groups_lower = [g.lower() for g in user_groups]
        return any(g.lower() in user_groups_lower for g in child_groups)
    # Nessun gruppo sul child: delega al controllo del padre
    return can_access(parent, user_groups, username, user_app_permissions)

def get_visible_menu(user_groups, username, user_app_permissions=None):
    """
    Restituisce la lista di voci di menu visibili per l'utente corrente.

    Itera su MENU_CONFIG, esclude le voci non accessibili e, per le voci
    con sottomenu, filtra anche i children non accessibili.
    """
    visible = []
    for app in MENU_CONFIG:
        # Salta le voci padre non accessibili
        if not can_access(app, user_groups, username, user_app_permissions):
            continue
        item = dict(app)
        if 'children' in app:
            # Filtra i children: include solo quelli visibili per questo utente
            visible_children = [
                child for child in app['children']
                if can_access_child(app, child, user_groups, username, user_app_permissions)
            ]
            item = dict(app, children=visible_children)
        visible.append(item)
    return visible

def login_view(request):
    """
    Vista di login tramite autenticazione LDAP.

    Se l'utente è già autenticato (sessione attiva), viene reindirizzato alla home.
    In caso di POST, autentica le credenziali tramite LDAPBackend e, se valide,
    salva nella sessione username, gruppi (OU + gruppi AD) e app autorizzate.
    """
    if request.session.get('user'):
        return redirect('portal:home')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if username and password:
            backend = LDAPBackend()
            user = backend.authenticate(request, username=username, password=password)

            if user:
                # Unisce le OU e i gruppi AD in un'unica lista senza duplicati
                ldap_ous = getattr(user, 'ldap_ous', [])
                ldap_groups = getattr(user, 'ldap_groups', [])
                all_groups = list(set(ldap_ous + ldap_groups))

                # Recupera le app con permesso individuale per questo utente
                user_apps = list(
                    UserAppPermission.objects
                    .filter(username=user.username.lower())
                    .values_list('app_name', flat=True)
                )

                # Salva i dati utente in sessione per l'accesso nelle view successive
                request.session['user'] = {
                    'username': user.username,
                    'groups': all_groups,
                    'apps': user_apps,
                }

                return redirect('portal:home')
            else:
                error = 'Credenziali non valide'
        else:
            error = 'Inserisci username e password'

    return render(request, 'portal/login.html', {'error': error})


def logout_view(request):
    """
    Vista di logout: distrugge completamente la sessione corrente
    e reindirizza alla pagina di login.
    """
    request.session.flush()
    return redirect('portal:login')


def home_view(request):
    """
    Homepage del portale.

    Richiede autenticazione: se la sessione non contiene l'utente,
    reindirizza al login. Altrimenti mostra la pagina principale.
    """
    session_user = request.session.get('user')
    if not session_user:
        return redirect('portal:login')
    return render(request, 'portal/home.html')


def utenti_online_view(request):
    """
    Pagina di monitoraggio degli utenti online - accessibile solo al gruppo ITD.

    Recupera le attività utente dal modello UserActivity e le suddivide in tre categorie:
    - online: attivi negli ultimi 5 minuti
    - recenti: attivi tra 5 minuti e 24 ore fa
    - storico: attività più vecchie di 24 ore

    Filtra per ambiente (dev/prod) letto dalla configurazione di Django.
    """
    session_user = request.session.get('user')
    if not session_user:
        return redirect('portal:login')

    from django.conf import settings
    from modules.active_users.models import UserActivity

    # Legge l'ambiente corrente (dev/prod) dalla configurazione Django
    env = getattr(settings, 'PORTAL_ENVIRONMENT', 'dev')
    now = timezone.now()

    # Soglie temporali per classificare l'attività degli utenti
    threshold_online = now - timedelta(minutes=5)
    threshold_today = now - timedelta(hours=24)

    # Utenti attivi negli ultimi 5 minuti (considerati "online")
    qs_online = (
        UserActivity.objects
        .filter(environment=env, last_activity__gte=threshold_online)
        .order_by('-last_activity')
    )
    # Utenti attivi nelle ultime 24 ore ma non negli ultimi 5 minuti
    qs_recenti = (
        UserActivity.objects
        .filter(environment=env, last_activity__gte=threshold_today, last_activity__lt=threshold_online)
        .order_by('-last_activity')
    )
    # Utenti con ultima attività oltre le 24 ore (storico, senza filtro ambiente)
    qs_storico = (
        UserActivity.objects
        .filter(last_activity__lt=threshold_today)
        .order_by('-last_activity')
    )

    def enrich(ua):
        """Arricchisce un record UserActivity con il tempo di inattività calcolato."""
        idle = (now - ua.last_activity).total_seconds()
        return {
            'username': ua.username,
            'display_name': ua.display_name or ua.username,
            'last_activity': ua.last_activity,
            'last_path': ua.last_path,
            'ip_address': ua.ip_address,
            'idle_seconds': round(idle),
            'idle_label': _idle_label(round(idle)),
            'environment': ua.environment,
        }

    online = [enrich(u) for u in qs_online]
    recenti = [enrich(u) for u in qs_recenti]
    storico = [enrich(u) for u in qs_storico]

    return render(request, 'portal/utenti_online.html', {
        'online': online,
        'recenti': recenti,
        'storico': storico,
        'environment': env,
        'now': now,
        'kicked': request.GET.get('kicked'),
        'kicked_n': request.GET.get('n', '0'),
    })


def _idle_label(seconds):
    """
    Converte un numero di secondi di inattività in una stringa leggibile.

    Esempi: 45 → '45s fa', 130 → '2m fa', 7200 → '2h fa'
    """
    if seconds < 60:
        return f"{seconds}s fa"
    if seconds < 3600:
        return f"{seconds // 60}m fa"
    return f"{seconds // 3600}h fa"

from django.core.cache import cache

def kick_user_view(request):
    session_user = request.session.get('user')
    if not session_user:
        return redirect('portal:login')
    groups = session_user.get('groups', [])
    if 'itd' not in [g.lower() for g in groups]:
        return redirect('portal:home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip().lower()
        eliminati = 0
        if username:
            from django.contrib.sessions.models import Session
            for s in Session.objects.filter(expire_date__gte=timezone.now()):
                data = s.get_decoded()
                if data.get('user', {}).get('username', '').lower() == username:
                    s.delete()
                    eliminati += 1
        return redirect(f'/portal/utenti-online/?kicked={username}&n={eliminati}')
    return redirect('portal:utenti_online')


def admin_msg_view(request):
    """
    Vista per la gestione dei messaggi popup del portale - solo ITD.

    Permette di inviare un messaggio urgente visibile a tutti gli utenti
    (o a utenti specifici) tramite la cache Django. Il messaggio viene
    memorizzato con chiave 'sitemsg_urgente' per una durata configurabile.

    Azioni POST supportate:
    - 'invia': salva il messaggio in cache con titolo, testo, destinatari e durata.
    - 'cancella': elimina il messaggio attivo dalla cache.
    """
    session_user = request.session.get('user')
    if not session_user:
        return redirect('portal:login')

    # Verifica che l'utente appartenga al gruppo ITD (case-insensitive)
    groups = session_user.get('groups', [])
    if 'itd' not in [g.lower() for g in groups]:
        return redirect('portal:home')

    # Legge il messaggio attualmente in cache (se presente)
    messaggio_attivo = cache.get('sitemsg_urgente')
    feedback = None

    if request.method == 'POST':
        azione = request.POST.get('azione')

        if azione == 'invia':
            titolo = request.POST.get('titolo', '').strip()
            testo = request.POST.get('testo', '').strip()
            destinatari_input = request.POST.get('destinatari', '').strip()
            durata = request.POST.get('durata', '60').strip()

            # Converte la lista di destinatari da stringa CSV a lista Python
            destinatari = [d.strip() for d in destinatari_input.split(',')] if destinatari_input else []
            # Converte la durata da minuti a secondi; fallback a 1 ora se non numerica
            durata_secondi = int(durata) * 60 if durata.isdigit() else 3600

            cache.set('sitemsg_urgente', {
                'titolo': titolo,
                'testo': testo,
                'destinatari': destinatari,
            }, timeout=durata_secondi)
            feedback = 'Messaggio inviato!'
            messaggio_attivo = cache.get('sitemsg_urgente')

        elif azione == 'cancella':
            cache.delete('sitemsg_urgente')
            feedback = 'Messaggio cancellato.'
            messaggio_attivo = None

    return render(request, 'portal/admin_msg.html', {
        'messaggio_attivo': messaggio_attivo,
        'feedback': feedback,
    })

def admin_permessi_view(request):
    """
    Vista per la gestione dei permessi individuali sulle app - solo ITD.

    Consente di assegnare o revocare l'accesso a singole app per utenti specifici,
    indipendentemente dai gruppi LDAP. I permessi sono salvati nel modello
    UserAppPermission.

    Azioni POST supportate:
    - 'aggiungi': crea un nuovo record UserAppPermission (get_or_create evita duplicati).
    - 'elimina': rimuove il permesso tramite il suo ID primario.
    """
    session_user = request.session.get('user')
    if not session_user:
        return redirect('portal:login')
    # Verifica appartenenza al gruppo ITD (case-insensitive)
    groups = session_user.get('groups', [])
    if 'itd' not in [g.lower() for g in groups]:
        return redirect('portal:home')
    if request.method == 'POST':
        azione = request.POST.get('azione')
        if azione == 'aggiungi':
            username  = request.POST.get('username', '').strip()
            app_name  = request.POST.get('app_name', '').strip()
            # get_or_create evita duplicati per la stessa coppia username/app
            UserAppPermission.objects.get_or_create(username=username.lower(), app_name = app_name)
        elif azione == 'elimina':
            id  = request.POST.get('id')
            UserAppPermission.objects.filter(id=id).delete()

    # Recupera tutti i permessi attivi, ordinati per chiarezza
    permessi = UserAppPermission.objects.all().order_by('username','app_name')
    # Costruisce la lista delle app disponibili da MENU_CONFIG (solo quelle con app_name)
    apps_disponibili = [
        (item['app_name'], item['label'])
        for item in MENU_CONFIG
        if 'app_name' in item
    ]

    return render(request, 'portal/admin_permessi.html', {
        'permessi': permessi,
        'apps_disponibili': apps_disponibili,
    })
