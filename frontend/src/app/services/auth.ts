// auth.service.ts - Versione con permessi app
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

interface SessionData {
  username: string;
  groups: string[];  // OU da AD (per compatibilità)
  apps: string[];    // App autorizzate da DB
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private usernameSubject = new BehaviorSubject<string | null>(null);
  username$ = this.usernameSubject.asObservable();

  private groupsSubject = new BehaviorSubject<string[]>([]);
  groups$ = this.groupsSubject.asObservable();

  private appsSubject = new BehaviorSubject<string[]>([]);
  apps$ = this.appsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadFromLocalStorage();
  }

  /**
   * Carica da localStorage
   */
  private loadFromLocalStorage() {
    const session = localStorage.getItem('session');
    if (session) {
      try {
        const { username, groups, apps } = JSON.parse(session) as SessionData;
        this.usernameSubject.next(username);
        this.groupsSubject.next(groups || []);
        this.appsSubject.next(apps || []);
      } catch {
        this.clear();
      }
    }
  }

  /**
   * Salva in localStorage
   */
  private saveToLocalStorage(username: string, groups: string[], apps: string[]) {
    localStorage.setItem('session', JSON.stringify({ username, groups, apps }));
  }

  /**
   * Imposta sessione
   */
  setSession(username: string, groups: string[], apps: string[] = []) {
    //console.log('[AUTH] setSession chiamato:', { username, groups, apps });
    const normalizedGroups = groups.map(g => g.toLowerCase());
    const normalizedApps = apps.map(a => a.toLowerCase());
    //console.log('[AUTH] Salvo in localStorage:', { username, normalizedGroups, normalizedApps });
    this.saveToLocalStorage(username, normalizedGroups, normalizedApps);
    //console.log('[AUTH] Verifica localStorage:', localStorage.getItem('session'));
    this.usernameSubject.next(username);
    this.groupsSubject.next(normalizedGroups);
    this.appsSubject.next(normalizedApps);
  }

  /**
   * Clear session
   */
  clear() {
    localStorage.removeItem('session');
    this.usernameSubject.next(null);
    this.groupsSubject.next([]);
    this.appsSubject.next([]);
  }

  /**
   * Verifica se autenticato
   */
  isAuthenticated(): boolean {
    return !!this.usernameSubject.value;
  }

  /**
   * Verifica appartenenza a gruppo (OU)
   */
  hasGroup(group: string): boolean {
    return this.groupsSubject.value.includes(group.toLowerCase());
  }

  /**
   * Verifica accesso a app
   */
  hasApp(app: string): boolean {
    return this.appsSubject.value.includes(app.toLowerCase());
  }

  /**
   * Verifica accesso a una delle app
   */
  hasAnyApp(apps: string[]): boolean {
    const userApps = this.appsSubject.value;
    return apps.some(app => userApps.includes(app.toLowerCase()));
  }

  /**
   * Get username corrente
   */
  getUsername(): string | null {
    return this.usernameSubject.value;
  }

  /**
   * Get apps autorizzate
   */
  getApps(): string[] {
    return this.appsSubject.value;
  }
}