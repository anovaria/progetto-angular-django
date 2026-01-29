import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-pallet',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/pallet/"
      title="Caricamento Gestione Pallet...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterPalletComponent { }
