import { AfterViewInit, Component, ViewChild, ChangeDetectorRef } from '@angular/core';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { AuthService } from '../../services/auth';
import { Observable } from 'rxjs';
import { Router, RouterOutlet, RouterLinkWithHref, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { environment } from '../../../environments/environment';
import { APP_PERMISSIONS, AppConfig, canAccessApp, canAccessChild } from '../../config/app-permissions';

@Component({
  selector: 'app-main-layout',
  templateUrl: './main-layout.html',
  styleUrls: ['./main-layout.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    MatToolbarModule,
    MatListModule,
    RouterOutlet,
    RouterLinkWithHref,
    RouterLinkActive
  ],
})
export class MainLayoutComponent implements AfterViewInit {
  @ViewChild('drawer') drawer!: MatSidenav;

  username$: Observable<string | null>;
  groups$: Observable<string[]>;

  opened = true;
  isCollapsed = false;
  isMobile = false;

  // Configurazione app centralizzata
  apps = APP_PERMISSIONS;
  expandedMenus: Set<string> = new Set();

  constructor(
    private authService: AuthService,
    private router: Router,
    private breakpointObserver: BreakpointObserver,
    private cdr: ChangeDetectorRef
  ) {
    this.username$ = this.authService.username$;
    this.groups$ = this.authService.groups$;

    this.breakpointObserver.observe([Breakpoints.Handset]).subscribe(result => {
      this.isMobile = result.matches;
      this.opened = !this.isMobile;
      this.isCollapsed = false;
    });

    this.expandMenuBasedOnUrl();
  }

  ngAfterViewInit() {
    this.drawer.openedChange.subscribe(() => {
      this.forceLayoutUpdate();
    });
  }

  /**
   * Espande automaticamente il menu in base all'URL corrente
   */
  private expandMenuBasedOnUrl() {
    const url = this.router.url;
    for (const app of this.apps) {
      if (app.children && url.startsWith(app.path)) {
        this.expandedMenus.add(app.path);
        break;
      }
    }
  }

  /**
   * Verifica se l'utente può vedere un'app
   */
  canAccess(app: AppConfig, groups: string[]): boolean {
    const username = this.authService.getUsername() || '';
    return canAccessApp(app, groups, username);
  }

  /**
   * Verifica se l'utente può vedere un child
   */
  canAccessChildItem(parent: AppConfig, child: AppConfig, groups: string[]): boolean {
    const username = this.authService.getUsername() || '';
    return canAccessChild(parent, child, groups, username);
  }

  /**
   * Toggle menu espandibile
   */
  toggleMenu(path: string) {
    if (!this.isCollapsed) {
      if (this.expandedMenus.has(path)) {
        this.expandedMenus.delete(path);
      } else {
        this.expandedMenus.add(path);
      }
    } else {
      this.router.navigate([path]);
    }
  }

  /**
   * Controlla se un menu è espanso
   */
  isExpanded(path: string): boolean {
    return this.expandedMenus.has(path);
  }

  toggleSidebar() {
    if (this.isMobile) {
      this.opened = !this.opened;
    } else {
      this.isCollapsed = !this.isCollapsed;
      if (this.isCollapsed) {
        this.expandedMenus.clear();
      }
    }
    this.forceLayoutUpdate();
  }

  private forceLayoutUpdate() {
    this.cdr.detectChanges();
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 0);
  }

  logout() {
    this.authService.clear();
    this.router.navigate(['/login']);
  }

  goToDjangoAdmin(event: Event) {
    event.preventDefault();
    window.open(environment.djangoAdminUrl, '_blank');
  }

  closeDrawerIfMobile() {
    if (this.isMobile) this.opened = false;
  }
}