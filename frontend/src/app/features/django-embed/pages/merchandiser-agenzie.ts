import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-agenzie',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `<app-iframe-wrapper [djangoPath]="'/app/merchandiser/agenzie/'"></app-iframe-wrapper>`
})
export class MerchandiserAgenzieComponent { }