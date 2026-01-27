import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-importelab-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/importelab/"
      title="Caricamento...">
    </app-iframe-wrapper>
  `
})
export class ImportelabPageComponent { }