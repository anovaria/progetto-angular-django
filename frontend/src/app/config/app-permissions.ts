// src/app/config/app-permissions.ts

export interface AppConfig {
    path: string;
    label: string;
    icon: string;
    groups: string[];
    users?: string[];
    children?: AppConfig[];
    isExternal?: boolean;  // Per link esterni come Django Admin
}

export const APP_PERMISSIONS: AppConfig[] = [

    {
        path: '/plu',
        label: 'PLU',
        icon: 'qr_code_scanner',
        groups: ['freschi', 'itd'],
    },
    {
        path: '/django/importelab',
        label: 'Rossetto',
        icon: 'sync',
        groups: ['itd'],
        users: ['loredana.gobbo'],
    },
    {
        path: '/django/pallet-promoter',
        label: 'Pallet-Promoter',
        icon: 'inventory_2',
        groups: ['acquisti', 'centralino', 'ufficio qualita', 'itd'],
        children: [
            { path: '/django/pallet-promoter', label: 'Dashboard', icon: 'dashboard', groups: [] },
            { path: '/django/pallet-promoter-pallet', label: 'Gestione Pallet', icon: 'grid_view', groups: [] },
            { path: '/django/pallet-promoter-testate', label: 'Gestione Testate', icon: 'view_column', groups: [] },
            { path: '/django/pallet-promoter-scelta-fornitore', label: 'Scelta Fornitore', icon: 'grid_on', groups: [] },
        ]
    },
    {
        path: '/django/merchandiser',
        label: 'Merchandiser',
        icon: 'store',
        groups: ['centralino', 'ufficio qualita', 'itd'],
        children: [
            { path: '/django/merchandiser', label: 'Dashboard', icon: 'dashboard', groups: [] },
            { path: '/django/merchandiser-slot', label: 'Gestione Slot', icon: 'event_available', groups: [] },
            { path: '/django/merchandiser-anagrafiche', label: 'Anagrafiche', icon: 'people', groups: [] },
            { path: '/django/merchandiser-attivita', label: 'Gestione Attività', icon: 'assignment', groups: [] },
        ]
    },
    {
        path: '/django/merchandiser-agenzie',
        label: 'Gestione Agenzie',
        icon: 'business',
        groups: ['ufficio qualita', 'centralino', 'itd'],
    },
    {
        path: '/django/alloca-hostess',
        label: 'Hostess',
        icon: 'people',
        groups: ['centralino', 'ufficio qualita', 'itd'],
        children: [
            { path: '/django/alloca-hostess', label: 'Dashboard', icon: 'dashboard', groups: [] },
            { path: '/django/alloca-hostess-individuazione', label: 'Gestione Slot', icon: 'person_search', groups: [] },
            { path: '/django/alloca-hostess-hostess', label: 'Lista Hostess', icon: 'badge', groups: [] },
            { path: '/django/merchandiser-hostess', label: 'Anagrafica Hostess', icon: 'people', groups: [] },
        ]
    },
    {
        path: '/django/punto-info',
        label: 'Orari Merchandiser',
        icon: 'schedule',
        groups: ['pinfo', 'ufficio qualita', 'itd'],
    },
    {
        path: '/django/alloca-hostess-orari',
        label: 'Orari Hostess',
        icon: 'schedule',
        groups: ['pinfo', 'ufficio qualita', 'itd'],
    },
    {
        path: '/django/welfare',
        label: 'Welfare',
        icon: 'card_giftcard',
        groups: ['ufficio cassa', 'itd'],
        children: [
            { path: '/django/welfare', label: 'Dashboard', icon: 'dashboard', groups: [] },
            { path: '/django/welfare-ricerca', label: 'Ricerca Voucher', icon: 'search', groups: [] },
            { path: '/django/welfare-cassa', label: 'Cassa', icon: 'point_of_sale', groups: [] },
            { path: '/django/welfare-consegne', label: 'Da Consegnare', icon: 'inventory', groups: ['pinfo'] },
            { path: '/django/welfare-storico', label: 'Storico Consegne', icon: 'history', groups: ['pinfo'] },
            { path: '/django/welfare-contabilita', label: 'Contabilità', icon: 'analytics', groups: [] },
            { path: '/django/welfare-import', label: 'Import Email', icon: 'email', groups: [] },
        ]
    },
    {
        path: '/django/assortimenti',
        label: 'AssoArticoli',
        icon: 'inventory_2',
        groups: ['gruppoced', 'itd'],
    },
    {
        path: '/admin',
        label: 'Django Admin',
        icon: 'admin_panel_settings',
        groups: ['itd'],
        isExternal: true,
    },
    {
        path: 'active-users',
        label: 'Utenti Online',
        icon: 'people',
        groups: ['itd'],
    },
];

/**
 * Verifica se un utente può vedere un'app
 */
export function canAccessApp(
    app: AppConfig,
    userGroups: string[],
    username: string
): boolean {
    if (app.users?.map(u => u.toLowerCase()).includes(username.toLowerCase())) {
        return true;
    }
    const normalizedUserGroups = userGroups.map(g => g.toLowerCase());
    return app.groups.some(g => normalizedUserGroups.includes(g.toLowerCase()));
}

/**
 * Verifica se un utente può vedere un child specifico
 */
export function canAccessChild(
    parent: AppConfig,
    child: AppConfig,
    userGroups: string[],
    username: string
): boolean {
    if (!child.groups || child.groups.length === 0) {
        return canAccessApp(parent, userGroups, username);
    }
    const normalizedUserGroups = userGroups.map(g => g.toLowerCase());
    const hasChildAccess = child.groups.some(g => normalizedUserGroups.includes(g.toLowerCase()));
    return canAccessApp(parent, userGroups, username) || hasChildAccess;
}

/**
 * Filtra le app visibili per un utente
 */
export function getVisibleApps(
    userGroups: string[],
    username: string
): AppConfig[] {
    return APP_PERMISSIONS.filter(app => canAccessApp(app, userGroups, username));
}