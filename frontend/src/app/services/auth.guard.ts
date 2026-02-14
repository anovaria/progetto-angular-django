import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, Router } from '@angular/router';
import { AuthService } from './auth';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) { }

  canActivate(route: ActivatedRouteSnapshot): boolean {
    // Verifica autenticazione
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/login']);
      return false;
    }

    // Verifica permessi app (se specificati)
    const requiredApps = route.data['apps'] as string[];
    if (requiredApps && requiredApps.length > 0) {
      if (!this.auth.hasAnyApp(requiredApps)) {
        // Utente autenticato ma senza permessi per questa app
        this.router.navigate(['/unauthorized']);
        return false;
      }
    }

    // Verifica gruppi/OU (fallback per compatibilità)
    const requiredGroups = route.data['groups'] as string[];
    if (requiredGroups && requiredGroups.length > 0) {
      const hasGroup = requiredGroups.some(g => this.auth.hasGroup(g));
      if (!hasGroup) {
        this.router.navigate(['/unauthorized']);
        return false;
      }
    }

    return true;
  }
}