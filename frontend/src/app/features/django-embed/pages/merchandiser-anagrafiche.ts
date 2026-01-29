import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-anagrafiche',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/merchandiser/merchandiser/"
      title="Caricamento Anagrafiche Merchandiser...">
    </app-iframe-wrapper>
  `
})
export class MerchandiserAnagraficheComponent { }