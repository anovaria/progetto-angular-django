import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-assortimenti-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/asso_articoli/"
      title="Caricamento asso_articoli...">
    </app-iframe-wrapper>
  `
})
export class AssortimentiComponent { }