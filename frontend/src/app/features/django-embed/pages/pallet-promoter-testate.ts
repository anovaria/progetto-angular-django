import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-testate',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/testate/"
      title="Caricamento Gestione Testate...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterTestateComponent { }