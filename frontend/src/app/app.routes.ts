import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layout/main-layout/main-layout';
import { LoginComponent } from './login/login';
import { AuthGuard } from './services/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [AuthGuard],
    data: { groups: ['ITD', 'Vendita'] },
    children: [
      {
        path: 'admin',
        loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES)
      },
      {
        path: 'plu',
        loadChildren: () => import('./features/plu/plu.routes').then(m => m.PLU_ROUTES)
      },
      {
        path: 'django',
        loadChildren: () => import('./features/django-embed/django-embed.routes').then(m => m.DJANGO_EMBED_ROUTES)
      }
    ]
  },
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: '**',
    redirectTo: ''
  }
];
