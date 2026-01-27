// auth.service.ts - Versione senza SSO
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

interface SessionData {
  username: string;
  groups: string[];
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private usernameSubject = new BehaviorSubject<string | null>(null);
  username$ = this.usernameSubject.asObservable();

  private groupsSubject = new BehaviorSubject<string[]>([]);
  groups$ = this.groupsSubject.asObservable();

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
        const { username, groups } = JSON.parse(session) as SessionData;
        this.usernameSubject.next(username);
        this.groupsSubject.next(groups || []);
      } catch {
        this.clear();
      }
    }
  }

  /**
   * Salva in localStorage
   */
  private saveToLocalStorage(username: string, groups: string[]) {
    localStorage.setItem('session', JSON.stringify({ username, groups }));
  }

  /**
   * Imposta sessione
   */
  setSession(username: string, groups: string[]) {
    const normalizedGroups = groups.map(g => g.toLowerCase());
    this.saveToLocalStorage(username, normalizedGroups);
    this.usernameSubject.next(username);
    this.groupsSubject.next(normalizedGroups);
  }

  /**
   * Clear session
   */
  clear() {
    localStorage.removeItem('session');
    this.usernameSubject.next(null);
    this.groupsSubject.next([]);
  }

  /**
   * Verifica se autenticato
   */
  isAuthenticated(): boolean {
    return !!this.usernameSubject.value;
  }

  /**
   * Verifica appartenenza a gruppo
   */
  hasGroup(group: string): boolean {
    return this.groupsSubject.value.includes(group.toLowerCase());
  }

  /**
   * Get username corrente
   */
  getUsername(): string | null {
    return this.usernameSubject.value;
  }
}