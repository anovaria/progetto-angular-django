import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-alloca-hostess-dashboard',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/alloca-hostess/"
      title="Caricamento Dashboard...">
    </app-iframe-wrapper>
  `
})
export class AllocaHostessDashboardComponent { }