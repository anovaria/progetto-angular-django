// Path: src/app/pages/merchandiser-hostess.ts

import { Component } from '@angular/core';
import { IframeWrapperComponent } from '../iframe-wrapper';

@Component({
    selector: 'app-merchandiser-hostess',
    standalone: true,
    imports: [IframeWrapperComponent],
    template: `<app-iframe-wrapper [djangoPath]="'/app/merchandiser/hostess/'"></app-iframe-wrapper>`
})
export class MerchandiserHostessComponent { }
