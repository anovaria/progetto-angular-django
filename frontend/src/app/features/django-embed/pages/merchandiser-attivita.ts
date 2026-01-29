import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-attivita',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/merchandiser/attivita/"
      title="Caricamento Gestione Attività...">
    </app-iframe-wrapper>
  `
})
export class MerchandiserAttivitaComponent { }