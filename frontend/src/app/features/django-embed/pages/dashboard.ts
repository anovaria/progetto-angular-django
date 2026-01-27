import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [IframeWrapperComponent],
  template: `
    <app-iframe-wrapper
      djangoPath="/app/dashboard/"
      title="Caricamento Dashboard...">
    </app-iframe-wrapper>
  `
})
export class DashboardPageComponent { }