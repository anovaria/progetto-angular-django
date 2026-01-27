import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'punto-info-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/merchandiser/solo-orari/"
      title="Caricamento Registrazione Orari...">
    </app-iframe-wrapper>
  `
})
export class PuntoInfoPageComponent { }