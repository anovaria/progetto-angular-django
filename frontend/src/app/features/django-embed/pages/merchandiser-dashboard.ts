import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-dashboard',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/merchandiser/"
      title="Caricamento Dashboard...">
    </app-iframe-wrapper>
  `
})
export class MerchandiserDashboardComponent { }