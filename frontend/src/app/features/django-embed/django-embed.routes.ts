import { Routes } from '@angular/router';

export const DJANGO_EMBED_ROUTES: Routes = [

  // ========================================
  // pallet-PROMOTER
  // ========================================
  {
    path: 'pallet-promoter',
    loadComponent: () => import('./pages/pallet-promoter-dashboard').then(m => m.PalletPromoterDashboardComponent),
    data: {
      groups: ['itd', 'Commerciale', 'pallet'],
      menu: { label: 'pallet-Promoter', icon: 'inventory_2' }
    }
  },
  {
    path: 'pallet-promoter-pallet',
    loadComponent: () => import('./pages/pallet-promoter-pallet').then(m => m.PalletPromoterPalletComponent),
    data: {
      menu: { label: 'Gestione pallet' },
      groups: ['itd', 'Commerciale', 'pallet']
    }
  },
  {
    path: 'pallet-promoter-testate',
    loadComponent: () => import('./pages/pallet-promoter-testate').then(m => m.PalletPromoterTestateComponent),
    data: {
      menu: { label: 'Gestione Testate' },
      groups: ['itd', 'Commerciale', 'pallet']
    }
  },
  {
    path: 'pallet-promoter-scelta-fornitore',
    loadComponent: () => import('./pages/pallet-promoter-scelta-fornitore').then(m => m.PalletPromoterSceltaFornitoreComponent),
    data: {
      menu: { label: 'Scelta Fornitore' },
      groups: ['itd', 'Commerciale', 'pallet']
    }
  },

  // ========================================
  // MERCHANDISER
  // ========================================
  {
    path: 'merchandiser',
    loadComponent: () => import('./pages/merchandiser-dashboard').then(m => m.MerchandiserDashboardComponent),
    data: {
      groups: ['itd', 'pallet', 'centralino', 'pinfo'],
      menu: { label: 'Merchandiser', icon: 'store' }
    }
  },
  {
    path: 'merchandiser-slot',
    loadComponent: () => import('./pages/merchandiser-slot').then(m => m.MerchandiserSlotComponent),
    data: { groups: ['itd', 'pallet'] }
  },
  {
    path: 'merchandiser-anagrafiche',
    loadComponent: () => import('./pages/merchandiser-anagrafiche').then(m => m.MerchandiserAnagraficheComponent),
    data: { groups: ['itd', 'pallet'] }
  },
  {
    path: 'merchandiser-agenzie',
    loadComponent: () => import('./pages/merchandiser-agenzie').then(m => m.MerchandiserAgenzieComponent),
    data: {
      menu: { label: 'Agenzie' },
      groups: ['itd', 'pallet']
    }
  },
  // ========================================
  // NUOVA ROUTE: Anagrafica Hostess
  // ========================================
  {
    path: 'merchandiser-hostess',
    loadComponent: () => import('./pages/merchandiser-hostess').then(m => m.MerchandiserHostessComponent),
    data: { groups: ['itd', 'pallet'] }
  },
  // ========================================
  {
    path: 'merchandiser-attivita',
    loadComponent: () => import('./pages/merchandiser-attivita').then(m => m.MerchandiserAttivitaComponent),
    data: { groups: ['itd', 'pallet'] }
  },

  // ========================================
  // ALLOCA-HOSTESS
  // ========================================
  {
    path: 'alloca-hostess',
    loadComponent: () => import('./pages/alloca-hostess-dashboard').then(m => m.AllocaHostessDashboardComponent),
    data: {
      groups: ['itd', 'centralino', 'pallet'],
      menu: { label: 'Alloca Hostess', icon: 'people' }
    }
  },
  {
    path: 'alloca-hostess-individuazione',
    loadComponent: () => import('./pages/alloca-hostess-individuazione').then(m => m.AllocaHostessIndividuazioneComponent),
    data: {
      menu: { label: 'Gestione Slot' },
      groups: ['itd', 'centralino', 'pallet']
    }
  },
  {
    path: 'alloca-hostess-hostess',
    loadComponent: () => import('./pages/alloca-hostess-hostess').then(m => m.AllocaHostessHostessComponent),
    data: { groups: ['itd', 'centralino', 'pallet'] }
  },
  {
    path: 'alloca-hostess-orari',
    loadComponent: () => import('./pages/alloca-hostess-orari').then(m => m.AllocaHostessOrariComponent),
    data: {
      menu: { label: 'Registrazione Orari' },
      groups: ['itd', 'pallet', 'centralino']
    }
  },

  // ========================================
  // ALTRE APP ESISTENTI
  // ========================================

  {
    path: 'importelab',
    loadComponent: () => import('./pages/importelab').then(m => m.ImportelabPageComponent),
    data: {
      groups: ['itd', 'segreteria'],
      menu: { label: 'Rossetto', icon: 'sync' }
    }
  },

  {
    path: 'punto-info',
    loadComponent: () => import('./pages/punto-info').then(m => m.PuntoInfoPageComponent),
    data: {
      groups: ['itd', 'pinfo', 'pallet'],
      menu: { label: 'Registrazione Orari', icon: 'schedule' }
    }
  },

  {
    path: 'assortimenti',
    loadComponent: () => import('./pages/assortimenti').then(m => m.AssortimentiComponent),
    data: {
      groups: ['itd', 'segreteria'],
      menu: { label: 'Assortimenti', icon: 'inventory_2' }
    }
  },

  // ========================================
  // WELFARE - sottopagine
  // ========================================
  {
    path: 'welfare',
    loadComponent: () => import('./pages/welfare').then(m => m.WelfarePageComponent),
    data: {
      groups: ['itd', 'ufficio cassa'],
      menu: { label: 'Welfare', icon: 'card_giftcard' }
    }
  },
  {
    path: 'welfare-ricerca',
    loadComponent: () => import('./pages/welfare-ricerca').then(m => m.WelfareRicercaPageComponent),
    data: { groups: ['itd', 'ufficio cassa'] }
  },
  {
    path: 'welfare-cassa',
    loadComponent: () => import('./pages/welfare-cassa').then(m => m.WelfareCassaPageComponent),
    data: { groups: ['itd', 'ufficio cassa'] }
  },
  {
    path: 'welfare-consegne',
    loadComponent: () => import('./pages/welfare-consegne').then(m => m.WelfareConsegnePageComponent),
    data: { groups: ['itd', 'ufficio cassa', 'pinfo'] }
  },
  {
    path: 'welfare-contabilita',
    loadComponent: () => import('./pages/welfare-contabilita').then(m => m.WelfareContabilitaPageComponent),
    data: { groups: ['itd', 'ufficio cassa'] }
  },
  {
    path: 'welfare-import',
    loadComponent: () => import('./pages/welfare-import').then(m => m.WelfareImportPageComponent),
    data: { groups: ['itd', 'ufficio cassa'] }
  },
  {
    path: 'welfare-storico',
    loadComponent: () => import('./pages/welfare-storico').then(m => m.WelfareStoricoPageComponent),
    data: { groups: ['itd', 'ufficio cassa', 'pinfo'] }
  },
];