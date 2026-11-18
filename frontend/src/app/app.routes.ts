import { Routes } from '@angular/router';

import { authGuard, loginGuard, pageGuard } from './auth.guard';
import { RoutePageComponent } from './route-page.component';

/**
 * Rutas reales con guards. `data.permission` replica la matriz del backend;
 * el guard de Angular no sustituye la validación de FastAPI.
 */
const page = (path: string, permission: string, view = path): Routes => [{
  path,
  component: RoutePageComponent,
  canActivate: [pageGuard],
  data: { page: view, permission },
}];

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: 'login', component: RoutePageComponent, canActivate: [loginGuard], data: { page: 'login' } },
  {
    path: 'change-password',
    component: RoutePageComponent,
    canActivate: [authGuard],
    data: { page: 'change-password' },
  },
  ...page('dashboard', 'OPERATE'),
  ...page('cells', 'VIEW_AVAILABILITY'),
  ...page('entry', 'OPERATE'),
  ...page('exit', 'OPERATE'),
  ...page('customers', 'OPERATE'),
  ...page('vehicles', 'VIEW_AVAILABILITY'),
  ...page('payments', 'OPERATE'),
  ...page('payments-register', 'OPERATE'),
  ...page('novelties', 'OPERATE'),
  ...page('history', 'VIEW_HISTORY'),
  ...page('parking-lots', 'MANAGE_STRUCTURE'),
  ...page('employees', 'MANAGE_STRUCTURE'),
  ...page('users', 'MANAGE_ACCOUNTS'),
  ...page('users-form', 'MANAGE_ACCOUNTS'),
  ...page('reports', 'VIEW_ACTIVITY'),
  ...page('settings', 'MANAGE_STRUCTURE'),
  ...page('tariffs', 'MANAGE_STRUCTURE'),
  { path: '**', redirectTo: 'dashboard' },
];
