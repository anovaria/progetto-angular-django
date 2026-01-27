// src/app/login/login.component.ts - AGGIORNATO CON SSO
import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ApiService } from '../services/api';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth';
import { SharedModule } from '../shared/modules';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule
  ],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  username = '';
  password = '';
  errorMessage = '';

  constructor(private api: ApiService, private router: Router, private auth: AuthService) { }

  onLogin() {
    this.api.login(this.username, this.password).subscribe({
      next: res => {
        console.log("RISPOSTA LOGIN:", res);
        this.auth.setSession(res.username, res.groups || []);
        this.router.navigate(['/']);
      },
      error: err => {
        this.errorMessage = err.status === 0
          ? 'Server non raggiungibile.'
          : err.status === 401
            ? 'Credenziali non valide.'
            : `Errore sconosciuto (${err.status})`;
      }
    });
  }
}