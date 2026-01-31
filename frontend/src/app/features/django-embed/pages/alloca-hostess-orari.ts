import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-alloca-hostess-orari',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `<app-iframe-wrapper [djangoPath]="'/app/alloca-hostess/orari-hostess/'"></app-iframe-wrapper>`
})
export class AllocaHostessOrariComponent { }
