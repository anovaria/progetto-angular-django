// welfare-cassa.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
    selector: 'app-welfare-cassa-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/cassa/"
      title="Caricamento Cassa...">
    </app-iframe-wrapper>
  `
})
export class WelfareCassaPageComponent { }