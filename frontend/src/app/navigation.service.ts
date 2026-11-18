import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type Page =
  | 'dashboard'
  | 'vehicles'
  | 'customers'
  | 'cells'
  | 'history'
  | 'payments'
  | 'payments-register'
  | 'novelties'
  | 'settings'
  | 'entry'
  | 'exit'
  | 'parking-lots'
  | 'employees'
  | 'users'
  | 'users-form'
  | 'reports'
  | 'tariffs';

export type AppView = Page | 'login' | 'change-password';

/** Puente entre el Router (URLs reales) y el componente raíz que renderiza las vistas. */
@Injectable({ providedIn: 'root' })
export class NavigationService {
  readonly view$ = new BehaviorSubject<AppView>('login');
  setView(view: AppView): void { this.view$.next(view); }
}
