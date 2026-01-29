import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-alloca-hostess-individuazione',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `
    <app-iframe-wrapper
      djangoPath="/app/alloca-hostess/individuazione/"
      title="Caricamento Individuazione Hostess...">
    </app-iframe-wrapper>
  `
})
export class AllocaHostessIndividuazioneComponent { }