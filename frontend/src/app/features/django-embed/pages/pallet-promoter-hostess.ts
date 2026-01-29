import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-pallet-promoter-hostess',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/pallet-promoter/hostess/"
      title="Caricamento Individuazione Hostess...">
    </app-iframe-wrapper>
  `
})
export class PalletPromoterHostessComponent { }