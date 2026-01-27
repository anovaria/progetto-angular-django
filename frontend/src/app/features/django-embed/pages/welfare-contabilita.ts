// welfare-contabilita.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
    selector: 'app-welfare-contabilita-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/contabilita/"
      title="Caricamento Contabilità...">
    </app-iframe-wrapper>
  `
})
export class WelfareContabilitaPageComponent { }
