// welfare-ricerca.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
    selector: 'app-welfare-ricerca-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/ricerca/"
      title="Caricamento Ricerca Voucher...">
    </app-iframe-wrapper>
  `
})
export class WelfareRicercaPageComponent { }