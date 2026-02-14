import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface LoginResponse {
  username: string;
  groups?: string[];  // OU (deprecato, per compatibilità)
  ous?: string[];     // OU da AD
  apps?: string[];    // App autorizzate da DB
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) { }

  login(username: string, password: string) {
    return this.http.post<LoginResponse>(
      `${environment.apiBase}/auth/login-ldap/`,
      { username, password },
      { withCredentials: true }
    );
  }

  testLogin(username: string, password: string) {
    return this.http.post<LoginResponse>(
      `${environment.apiBase}/auth/login-ldap-test/`,
      { username, password },
      { withCredentials: true }
    );
  }
}