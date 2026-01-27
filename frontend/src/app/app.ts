import { Component, signal } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { AuthService } from './services/auth';
import { Observable } from 'rxjs';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, MatButtonModule, MatIconModule],
  templateUrl: './app.html',
  styleUrls: ['./app.scss']
})
export class App {
  username$: Observable<string | null>;
  protected readonly title = signal('frontend');

  constructor(private authService: AuthService, private router: Router) {
    this.username$ = this.authService.username$;
  }

  logout() {
    this.authService.clear();
    this.router.navigate(['/login']);
  }
}