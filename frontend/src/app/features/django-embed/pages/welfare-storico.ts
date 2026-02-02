// welfare-consegne.ts
import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';
@Component({
  selector: 'app-welfare-storico-page',
  standalone: true,
  imports: [IframeWrapperComponent],
  template: `
    <app-iframe-wrapper
      djangoPath="/app/welfare/storico/"
      title="Caricamento Storico richieste consegnate...">
    </app-iframe-wrapper>
  `
})
export class WelfareStoricoPageComponent { }