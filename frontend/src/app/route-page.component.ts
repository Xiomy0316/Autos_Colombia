import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { NavigationService, type AppView } from './navigation.service';

/** Componente vacío: traduce la ruta activa a la vista del componente raíz. */
@Component({ selector: 'app-route-page', template: '' })
export class RoutePageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly nav = inject(NavigationService);

  ngOnInit(): void {
    const view = this.route.snapshot.data['page'] as AppView | undefined;
    if (view) this.nav.setView(view);
  }
}
