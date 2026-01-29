import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-slot',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/merchandiser/slot/"
      title="Caricamento Gestione Slot...">
    </app-iframe-wrapper>
  `
})
export class MerchandiserSlotComponent { }