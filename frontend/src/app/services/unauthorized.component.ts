import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
    selector: 'app-unauthorized',
    standalone: true,
    imports: [CommonModule, RouterModule, MatButtonModule, MatIconModule],
    template: `
    <div class="unauthorized-container">
      <mat-icon class="icon">lock</mat-icon>
      <h1>Accesso non autorizzato</h1>
      <p>Non hai i permessi necessari per accedere a questa sezione.</p>
      <button mat-raised-button color="primary" routerLink="/">
        Torna alla Home
      </button>
    </div>
  `,
    styles: [`
    .unauthorized-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 80vh;
      text-align: center;
    }
    .icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #f44336;
      margin-bottom: 24px;
    }
    h1 {
      color: #333;
      margin-bottom: 16px;
    }
    p {
      color: #666;
      margin-bottom: 32px;
    }
  `]
})
export class UnauthorizedComponent { }