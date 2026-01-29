import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-presenze',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/presenze/"
      title="Caricamento Presenze...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterPresenzeComponent { }