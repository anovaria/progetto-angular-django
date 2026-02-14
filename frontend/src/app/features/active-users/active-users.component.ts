import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActiveUsersService, ActiveUser } from './active-users.service';

@Component({
  selector: 'app-active-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="au-header">
      <div class="au-header-left">
        <h2>Utenti Attivi</h2>
        <span class="au-badge" [class.au-badge-green]="activeCount > 0">
          {{ activeCount }} online
        </span>
      </div>
      <div class="au-header-right">
        <label class="au-select-label">
          Finestra:
          <select [value]="thresholdMinutes" (change)="onMinutesChange($event)" class="au-select">
            <option value="2">2 min</option>
            <option value="5">5 min</option>
            <option value="10">10 min</option>
            <option value="30">30 min</option>
          </select>
        </label>
        <button (click)="toggleHistory()" class="au-btn" [class.au-btn-active]="showHistory">
          {{ showHistory ? 'Nascondi storico' : 'Storico oggi' }}
        </button>
        <span class="au-refresh-info" *ngIf="lastRefresh">
          Agg: {{ lastRefresh | date:'HH:mm:ss' }}
        </span>
      </div>
    </div>

    <div *ngIf="error" class="au-error">
      {{ error }}
      <button (click)="onMinutesChange(null)" class="au-btn au-btn-small">Riprova</button>
    </div>

    <div *ngIf="loading && users.length === 0" class="au-loading">
      Caricamento...
    </div>

    <div class="au-table-wrapper" *ngIf="users.length > 0">
      <table class="au-table">
        <thead>
          <tr>
            <th class="au-th-status"></th>
            <th>Utente</th>
            <th>Inattivo da</th>
            <th>Ultimo accesso</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let user of users; trackBy: trackByUser"
              [class.au-row-idle]="user.idle_seconds > 120">
            <td>
              <span class="au-dot"
                [class.au-dot-green]="user.idle_seconds <= 60"
                [class.au-dot-yellow]="user.idle_seconds > 60 && user.idle_seconds <= 180"
                [class.au-dot-red]="user.idle_seconds > 180">
              </span>
            </td>
            <td>
              <strong>{{ user.display_name || user.username }}</strong>
              <small class="au-username" *ngIf="user.display_name">{{ user.username }}</small>
            </td>
            <td>{{ formatIdle(user.idle_seconds) }}</td>
            <td>{{ user.last_activity | date:'HH:mm:ss' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div *ngIf="!loading && users.length === 0 && !error" class="au-empty">
      Nessun utente attivo negli ultimi {{ thresholdMinutes }} minuti.
    </div>

    <div *ngIf="showHistory" class="au-history">
      <h3>Storico accessi oggi ({{ historyUsers.length }} utenti)</h3>
      <div class="au-table-wrapper" *ngIf="historyUsers.length > 0">
        <table class="au-table">
          <thead>
            <tr>
              <th class="au-th-status"></th>
              <th>Utente</th>
              <th>Ultimo accesso</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let user of historyUsers; trackBy: trackByUser"
                [class.au-row-online]="user.is_online">
              <td>
                <span class="au-dot" [class.au-dot-green]="user.is_online" [class.au-dot-gray]="!user.is_online"></span>
              </td>
              <td>
                <strong>{{ user.display_name || user.username }}</strong>
                <small class="au-username" *ngIf="user.display_name">{{ user.username }}</small>
              </td>
              <td>{{ user.last_activity | date:'HH:mm:ss' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      padding: 20px;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .au-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .au-header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .au-header-left h2 {
      margin: 0;
      font-size: 1.4rem;
      color: #1a1a2e;
    }
    .au-header-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .au-badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 600;
      background: #e0e0e0;
      color: #666;
    }
    .au-badge-green {
      background: #e8f5e9;
      color: #2e7d32;
    }
    .au-select-label {
      font-size: 0.85rem;
      color: #555;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .au-select {
      padding: 4px 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 0.85rem;
    }
    .au-btn {
      padding: 6px 14px;
      border: 1px solid #1976D2;
      border-radius: 4px;
      background: white;
      color: #1976D2;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s;
    }
    .au-btn:hover { background: #e3f2fd; }
    .au-btn-active { background: #1976D2; color: white; }
    .au-btn-small { padding: 3px 10px; font-size: 0.8rem; }
    .au-refresh-info { font-size: 0.75rem; color: #999; }
    .au-error {
      padding: 12px 16px;
      background: #fff3e0;
      border-left: 4px solid #ff9800;
      border-radius: 4px;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .au-loading, .au-empty {
      padding: 40px;
      text-align: center;
      color: #999;
      font-size: 0.95rem;
    }
    .au-table-wrapper {
      overflow-x: auto;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .au-table {
      width: 100%;
      border-collapse: collapse;
      background: white;
    }
    .au-table th {
      padding: 10px 14px;
      text-align: left;
      font-size: 0.8rem;
      font-weight: 600;
      color: #555;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      background: #f5f5f5;
      border-bottom: 2px solid #e0e0e0;
    }
    .au-th-status { width: 30px; }
    .au-table td {
      padding: 10px 14px;
      border-bottom: 1px solid #f0f0f0;
      font-size: 0.9rem;
    }
    .au-table tbody tr:hover { background: #fafafa; }
    .au-row-idle { opacity: 0.75; }
    .au-row-online { background: #f1f8e9 !important; }
    .au-dot {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #ccc;
    }
    .au-dot-green {
      background: #4caf50;
      box-shadow: 0 0 6px rgba(76, 175, 80, 0.4);
    }
    .au-dot-yellow { background: #ff9800; }
    .au-dot-red { background: #f44336; }
    .au-dot-gray { background: #bdbdbd; }
    .au-username {
      display: block;
      color: #999;
      font-size: 0.75rem;
    }
    .au-history {
      margin-top: 30px;
      padding-top: 20px;
      border-top: 2px solid #e0e0e0;
    }
    .au-history h3 {
      margin: 0 0 16px 0;
      font-size: 1.1rem;
      color: #1a1a2e;
    }
  `]
})
export class ActiveUsersComponent implements OnInit, OnDestroy {
  users: ActiveUser[] = [];
  historyUsers: ActiveUser[] = [];
  activeCount = 0;
  thresholdMinutes = 5;
  showHistory = false;
  loading = true;
  error = '';
  lastRefresh: Date | null = null;

  private intervalId: any = null;

  constructor(
    private activeUsersService: ActiveUsersService,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit(): void {
    this.fetchData();
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  startPolling(): void {
    this.stopPolling();
    this.intervalId = setInterval(() => this.fetchData(), 15000);
  }

  stopPolling(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  onMinutesChange(event: Event | null): void {
    if (event) {
      const select = event.target as HTMLSelectElement;
      this.thresholdMinutes = +select.value;
    }
    this.loading = true;
    this.fetchData();
    this.startPolling();
    if (this.showHistory) {
      this.loadHistory();
    }
  }

  fetchData(): void {
    this.activeUsersService.getActiveUsers(this.thresholdMinutes).subscribe({
      next: (data) => {
        this.users = data.users;
        this.activeCount = data.count;
        this.lastRefresh = new Date();
        this.loading = false;
        this.error = '';
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = 'Errore nel recupero dati utenti attivi.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  toggleHistory(): void {
    this.showHistory = !this.showHistory;
    if (this.showHistory) {
      this.loadHistory();
    }
  }

  loadHistory(): void {
    this.activeUsersService.getHistory(24).subscribe({
      next: (data) => {
        this.historyUsers = data.users;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('History load error:', err);
      }
    });
  }

  formatIdle(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  }

  trackByUser(index: number, user: ActiveUser): string {
    return user.username;
  }
}