import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-alloca-hostess-hostess',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/alloca-hostess/hostess/"
      title="Caricamento Anagrafica Hostess...">
    </app-iframe-wrapper>
  `
})
export class AllocaHostessHostessComponent { }