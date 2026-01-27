import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { Admin } from './admin.component';
import { MatCardModule } from '@angular/material/card';

const routes: Routes = [{ path: '', component: Admin }];

@NgModule({
  declarations: [],
  imports: [CommonModule, MatCardModule,Admin, RouterModule.forChild(routes)]
})
export class AdminModule {}
