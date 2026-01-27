import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'pallet-promoter-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/"
      title="Caricamento pallet_promoter...">
    </app-iframe-wrapper>
  `
})
export class PalletPageComponent { }