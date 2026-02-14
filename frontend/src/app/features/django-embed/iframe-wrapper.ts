import { Component, Input, AfterViewInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-iframe-wrapper',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './iframe-wrapper.html',
  styleUrls: ['./iframe-wrapper.scss']
})
export class IframeWrapperComponent implements AfterViewInit, OnDestroy {
  @Input() djangoPath: string = '/';
  @Input() title: string = 'Caricamento...';
  @Input() showLoader: boolean = true;

  iframeUrl: SafeResourceUrl | null = null;
  isLoading = true;
  hasError = false;

  constructor(
    private sanitizer: DomSanitizer,
    private cdr: ChangeDetectorRef
  ) { }

  ngAfterViewInit(): void {
    // Delay per evitare NG0100
    setTimeout(() => {
      this.buildIframeUrl();
    }, 0);
  }

  ngOnDestroy(): void { }

  private buildIframeUrl(): void {
    try {
      let baseUrl: string;

      if (environment.production) {
        baseUrl = '';
      } else {
        baseUrl = environment.apiBase.replace('/api', '');
      }

      // Aggiungi username per tracciamento attività
      const session = localStorage.getItem('session');
      let authParam = '';
      if (session) {
        try {
          const parsed = JSON.parse(session);
          if (parsed.username) {
            const separator = this.djangoPath.includes('?') ? '&' : '?';
            authParam = `${separator}_auth_user=${parsed.username}`;
          }
        } catch { }
      }

      const fullUrl = `${baseUrl}${this.djangoPath}${authParam}`;
      console.log('IframeWrapper: loading URL:', fullUrl);
      this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl);
      this.cdr.detectChanges();

    } catch (error) {
      console.error('Errore costruzione URL iframe:', error);
      this.hasError = true;
      this.isLoading = false;
      this.cdr.detectChanges();
    }
  }

  onIframeLoad(): void {
    console.log('IframeWrapper: iframe loaded');
    this.isLoading = false;
    this.cdr.detectChanges();
  }

  onIframeError(): void {
    console.error('IframeWrapper: iframe error');
    this.isLoading = false;
    this.hasError = true;
    this.cdr.detectChanges();
  }

  reload(): void {
    this.isLoading = true;
    this.hasError = false;
    this.iframeUrl = null;
    this.cdr.detectChanges();

    setTimeout(() => {
      this.buildIframeUrl();
    }, 100);
  }
}
