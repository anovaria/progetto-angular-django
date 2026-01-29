// FILE: pallet-promoter-dashboard.ts
// -----------------------------------
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-dashboard',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/"
      title="Caricamento Dashboard...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterDashboardComponent { }