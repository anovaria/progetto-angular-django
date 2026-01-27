// welfare-import.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
    selector: 'app-welfare-import-page',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/import/"
      title="Caricamento Import Email...">
    </app-iframe-wrapper>
  `
})
export class WelfareImportPageComponent { }