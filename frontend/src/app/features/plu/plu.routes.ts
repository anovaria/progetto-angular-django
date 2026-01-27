import { Routes } from '@angular/router';

// features/plu/plu.routes.ts
export const PLU_ROUTES: Routes = [
    {
        path: '',
        pathMatch: 'full', // <--- Fondamentale quando il path è stringa vuota
        loadComponent: () =>
            import('./plu-list').then(m => m.PluListComponent),
        data: { groups: ['ITD', 'Freschi'] }
    }
];