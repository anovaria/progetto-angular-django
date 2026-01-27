// welfare-consegne.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
    selector: 'app-welfare-consegne-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/da-consegnare/"
      title="Caricamento Da Consegnare...">
    </app-iframe-wrapper>
  `
})
export class WelfareConsegnePageComponent { }