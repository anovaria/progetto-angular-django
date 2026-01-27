import { Component } from '@angular/core';
import { SharedModule } from '../../shared/modules';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [SharedModule],
  templateUrl: './admin.html',
  styleUrls: ['./admin.css']
})
export class Admin {}
