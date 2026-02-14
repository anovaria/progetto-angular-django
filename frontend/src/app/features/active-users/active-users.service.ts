import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ActiveUser {
  username: string;
  display_name: string;
  last_activity: string;
  last_path: string;
  ip_address: string;
  idle_seconds: number;
  is_online?: boolean;
}

export interface ActiveUsersResponse {
  count: number;
  threshold_minutes: number;
  server_time: string;
  users: ActiveUser[];
}

@Injectable({
  providedIn: 'root'
})
export class ActiveUsersService {

  private baseUrl = environment.apiBase;

  constructor(private http: HttpClient) { }

  getActiveUsers(minutes: number = 5): Observable<ActiveUsersResponse> {
    return this.http.get<ActiveUsersResponse>(
      `${this.baseUrl}/active-users/?minutes=${minutes}`
    );
  }

  getHistory(hours: number = 24): Observable<ActiveUsersResponse> {
    return this.http.get<ActiveUsersResponse>(
      `${this.baseUrl}/active-users/history/?hours=${hours}`
    );
  }
}