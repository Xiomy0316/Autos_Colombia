import type { CanActivateFn } from '@angular/router';
import { inject } from '@angular/core';

import { AuthService, type Permission } from './auth.service';
import { NavigationService, type AppView } from './navigation.service';

/** Exige sesión vigente. Si hay contraseña temporal, fuerza el cambio. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const nav = inject(NavigationService);
  if (!auth.isAuthenticated()) {
    nav.setView('login');
    return false;
  }
  if (auth.mustChangePassword()) {
    nav.setView('change-password');
    return false;
  }
  return true;
};

/** Exige sesión + el permiso atómico de la página solicitada. */
export const pageGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const nav = inject(NavigationService);
  if (!auth.isAuthenticated()) {
    nav.setView('login');
    return false;
  }
  if (auth.mustChangePassword()) {
    nav.setView('change-password');
    return false;
  }
  const permission = route.data['permission'] as Permission | undefined;
  const view = route.data['page'] as AppView;
  if (permission && !auth.has(permission)) {
    // Sin permiso: no se muestra la vista ni se expone su URL.
    nav.setView('dashboard');
    return false;
  }
  nav.setView(view);
  return true;
};

/** Puerta de entrada al login: session activa => panel, si no, login. */
export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const nav = inject(NavigationService);
  if (auth.isAuthenticated() && !auth.mustChangePassword()) {
    nav.setView('dashboard');
    return false;
  }
  nav.setView('login');
  return true;
};
