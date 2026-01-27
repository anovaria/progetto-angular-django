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
import { DJANGO_EMBED_ROUTES } from '../../features/django-embed/django-embed.routes';

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
  welfareExpanded = false;

  djangoRoutes = DJANGO_EMBED_ROUTES;

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

    // Espandi automaticamente Welfare se siamo su una sua pagina
    if (this.router.url.startsWith('/django/welfare')) {
      this.welfareExpanded = true;
    }
  }

  ngAfterViewInit() {
    this.drawer.openedChange.subscribe(() => {
      this.forceLayoutUpdate();
    });
  }

  toggleSidebar() {
    if (this.isMobile) {
      this.opened = !this.opened;
    } else {
      this.isCollapsed = !this.isCollapsed;
      if (this.isCollapsed) {
        this.welfareExpanded = false;
      }
    }
    this.forceLayoutUpdate();
  }

  toggleWelfareMenu() {
    if (!this.isCollapsed) {
      this.welfareExpanded = !this.welfareExpanded;
    } else {
      this.router.navigate(['/django/welfare']);
    }
  }

  private forceLayoutUpdate() {
    this.cdr.detectChanges();
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 0);
    setTimeout(() => {
      document.body.offsetHeight;
    }, 50);
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

  isAdmin(groups: string[]): boolean {
    return groups.includes('itd');
  }

  hasGroup(groups: string[], allowedGroups: string[]): boolean {
    if (groups.includes('itd')) return true;
    return allowedGroups.some(g => groups.includes(g.toLowerCase()));
  }
}