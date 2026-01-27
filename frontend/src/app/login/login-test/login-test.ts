// src/app/login-test/login-test.component.ts
import { Component } from '@angular/core';
import { ApiService } from '../../services/api';
import { catchError, throwError } from 'rxjs';
import { CommonModule } from '@angular/common';
import { SharedModule } from '../../shared/modules';

@Component({
  selector: 'app-login-test',
  standalone: true,
  imports: [CommonModule, SharedModule],
  templateUrl: './login-test.html',
  styleUrls: ['./login-test.css']
})
export class LoginTestComponent {
  // 🔑 Modello per il binding del form
  credentials = {
    username: '',
    password: ''
  };

  // Messaggi di feedback per l'utente
  message: string = 'Inserisci le credenziali e testa l\'autenticazione LDAP.';
  isError: boolean = false;

  constructor(private apiService: ApiService) { }

  onLoginTest() {
    this.message = 'Invio richiesta POST...';
    this.isError = false;

    // Chiama il metodo di test nel servizio
    this.apiService.testLogin(this.credentials.username, this.credentials.password)
      .pipe(
        // Gestisce specificamente il 401 che potrebbe non essere intercettato altrove
        catchError(error => {
          this.isError = true;
          // Controlla se l'errore ha un dettaglio specifico dal backend (es. "Credenziali non valide")
          const detail = error.error?.detail || 'Errore di connessione o CORS/CSRF. Controlla la Console (F12).';
          this.message = `Login fallito: ${detail}`;
          return throwError(() => error);
        })
      )
      .subscribe({
        next: (response) => {
          // Successo: LDAP ha funzionato!
          this.isError = false;
          this.message = `✅ Login LDAP riuscito! Utente: ${response.username}. Gruppi: ${response.groups.join(', ')}`;
        },
        error: () => {
          // L'errore viene gestito nel catchError del pipe (evita di gestirlo due volte)
        }
      });
  }
}