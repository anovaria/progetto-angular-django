import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface LoginResponse {
  username: string;
  groups: string[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) { }

  login(username: string, password: string) {
    return this.http.post<LoginResponse>(
      `${environment.apiBase}/auth/login-ldap/`,
      { username, password },
      { withCredentials: true } // utile se Django usa session cookie
    );
  }
  testLogin(username: string, password: string) {
    return this.http.post<LoginResponse>(
      // **ATTENZIONE:** Usa l'endpoint di test corretto!
      `${environment.apiBase}/auth/login-ldap-test/`,
      { username, password },
      { withCredentials: true }
    );
  }
}
