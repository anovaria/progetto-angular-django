import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private groups: string[] = [];

  setTokens(access: string | null, refresh: string | null) {
    this.accessToken = access;
    this.refreshToken = refresh;
  }

  setGroups(groups: string[]) {
    this.groups = groups || [];
  }

  getAccessToken() {
    return this.accessToken;
  }

  getRefreshToken() {
    return this.refreshToken;
  }

  getGroups() {
    return this.groups;
  }

  clear() {
    this.accessToken = null;
    this.refreshToken = null;
    this.groups = [];
  }
}
