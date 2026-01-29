import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-scelta-fornitore',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/hostess/scelta-fornitore/"
      title="Caricamento Scelta Fornitore...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterSceltaFornitoreComponent { }