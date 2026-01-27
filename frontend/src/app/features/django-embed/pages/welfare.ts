// welfare.ts - Dashboard
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
  selector: 'app-welfare-page',
  standalone: true,
  imports: [IframeWrapperComponent],
  template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/"
      title="Caricamento Welfare...">
    </app-iframe-wrapper>
  `
})
export class WelfarePageComponent { }