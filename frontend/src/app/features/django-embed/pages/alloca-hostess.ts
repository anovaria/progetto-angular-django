import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'alloca-hostess-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/alloca-hostess/"
      title="Caricamento alloca-hostess...">
    </app-iframe-wrapper>
  `
})
export class AllocaHostessPageComponent { }