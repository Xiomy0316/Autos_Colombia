import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import type { Observable } from 'rxjs';
import { tap } from 'rxjs';

import { environment } from '../environments/environment';

export interface SessionUser {
  user_id: number;
  username: string;
  display_name: string;
  parking_lot_id: number;
  employee_id: number;
  role_codes: string[];
  permissions: string[];
  must_change_password: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_hours: number;
  user: SessionUser;
}

/** Permisos atómicos. Deben coincidir con `backend/app/rbac.py`. */
export const PERMISSIONS = {
  OPERATE: 'OPERATE',
  VIEW_AVAILABILITY: 'VIEW_AVAILABILITY',
  MANAGE_ACCOUNTS: 'MANAGE_ACCOUNTS',
  MANAGE_STRUCTURE: 'MANAGE_STRUCTURE',
  MANAGE_CELLS: 'MANAGE_CELLS',
  VIEW_ACTIVITY: 'VIEW_ACTIVITY',
  VIEW_HISTORY: 'VIEW_HISTORY',
} as const;

export type Permission = typeof PERMISSIONS[keyof typeof PERMISSIONS];

/** Página -> permiso. Espejo de `PAGE_PERMISSIONS` en el backend. */
export const PAGE_PERMISSIONS: Record<string, Permission> = {
  dashboard: PERMISSIONS.OPERATE,
  cells: PERMISSIONS.VIEW_AVAILABILITY,
  entry: PERMISSIONS.OPERATE,
  exit: PERMISSIONS.OPERATE,
  customers: PERMISSIONS.OPERATE,
  vehicles: PERMISSIONS.VIEW_AVAILABILITY,
  payments: PERMISSIONS.OPERATE,
  'payments-register': PERMISSIONS.OPERATE,
  novelties: PERMISSIONS.OPERATE,
  history: PERMISSIONS.VIEW_HISTORY,
  'parking-lots': PERMISSIONS.MANAGE_STRUCTURE,
  employees: PERMISSIONS.MANAGE_STRUCTURE,
  users: PERMISSIONS.MANAGE_ACCOUNTS,
  'users-form': PERMISSIONS.MANAGE_ACCOUNTS,
  reports: PERMISSIONS.VIEW_ACTIVITY,
  settings: PERMISSIONS.MANAGE_STRUCTURE,
  tariffs: PERMISSIONS.MANAGE_STRUCTURE,
};

const TOKEN_KEY = 'autoscolombia.session.token';
const USER_KEY = 'autoscolombia.session.user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  private readonly storedToken = sessionStorage.getItem(TOKEN_KEY) ?? '';
  private readonly storedUser = this.readStoredUser();

  readonly session = signal<SessionUser | null>(this.storedUser);
  readonly isAuthenticated = computed(() => !!this.session() && !!this.token);
  readonly mustChangePassword = computed(() => !!this.session()?.must_change_password);
  readonly displayName = computed(() => this.session()?.display_name ?? '');
  readonly roleLabel = computed(() => {
    const codes = this.session()?.role_codes ?? [];
    if (codes.includes('ADMINISTRADOR')) return 'Administrador';
    if (codes.includes('EMPLEADO')) return 'Empleado';
    return 'Sin rol';
  });

  get token(): string {
    return sessionStorage.getItem(TOKEN_KEY) ?? this.storedToken;
  }

  private readStoredUser(): SessionUser | null {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) as SessionUser : null;
    } catch {
      return null;
    }
  }

  private persist(token: string, user: SessionUser): void {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    this.session.set(user);
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.base}/auth/login`, { username, password }).pipe(
      tap((response) => this.persist(response.access_token, response.user)),
    );
  }

  /** Refresca el rol y los permisos vigentes al recargar la aplicación. */
  me(): Observable<SessionUser> {
    return this.http.get<SessionUser>(`${this.base}/auth/me`).pipe(
      tap((user) => this.persist(this.token, user)),
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<{ user: SessionUser }> {
    return this.http.post<{ user: SessionUser }>(`${this.base}/auth/change-password`, {
      current_password: currentPassword,
      new_password: newPassword,
    }).pipe(tap((response) => this.persist(this.token, response.user)));
  }

  logout(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    this.session.set(null);
  }

  has(permission: Permission | string): boolean {
    return !!this.session()?.permissions.includes(permission);
  }

  canPage(page: string): boolean {
    const permission = PAGE_PERMISSIONS[page];
    return permission ? this.has(permission) : false;
  }
}
