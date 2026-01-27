import { Routes } from '@angular/router';
export const DJANGO_EMBED_ROUTES: Routes = [
  {
    path: 'importelab',
    loadComponent: () => import('./pages/importelab').then(m => m.ImportelabPageComponent),
    data: {
      groups: ['itd', 'Commerciale'],
      menu: { label: 'Rossetto', icon: 'sync' }
    }
  },
  {
    path: 'merchandiser',
    loadComponent: () => import('./pages/merchandiser').then(m => m.MerchandiserPageComponent),
    data: {
      groups: ['itd', 'Ufficio Qualità', 'Centralino', 'Pinfo'],
      menu: { label: 'Merchandiser', icon: 'store' }
    }
  },
  {
    path: 'pallet-promoter',
    loadComponent: () => import('./pages/pallet-promoter').then(m => m.PalletPageComponent),
    data: {
      groups: ['itd', 'Commerciale'],
      menu: { label: 'Pallet-Promoter', icon: 'inventory_2' }
    }
  },
  {
    path: 'alloca-hostess',
    loadComponent: () => import('./pages/alloca-hostess').then(m => m.AllocaHostessPageComponent),
    data: {
      groups: ['itd', 'Centralino', 'Ufficio Qualità'],
      menu: { label: 'Alloca Hostess', icon: 'people' }
    }
  },
  {
    path: 'punto-info',
    loadComponent: () => import('./pages/punto-info').then(m => m.PuntoInfoPageComponent),
    data: {
      groups: ['itd', 'Pinfo', 'Ufficio Qualità'],
      menu: { label: 'Registrazione Orari', icon: 'schedule' }
    }
  },
  {
    path: 'assortimenti',
    loadComponent: () => import('./pages/assortimenti').then(m => m.AssortimentiComponent),
    data: {
      groups: ['itd', 'GruppoCED'],
      menu: { label: 'Assortimenti', icon: 'inventory_2' }
    }
  },
  // Welfare - sottopagine
  {
    path: 'welfare',
    loadComponent: () => import('./pages/welfare').then(m => m.WelfarePageComponent),
    data: { groups: ['itd', 'ufficio cassa'] }
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
    data: { groups: ['itd', 'ufficio cassa'] }
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
];