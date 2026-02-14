import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

// --- UTILITY PER LEGGERE IL COOKIE CSRF ---
const getCsrfCookie = (name: string = 'csrftoken'): string | null => {
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Controlla se il cookie inizia con il nome corretto
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
  }
  return null;
};

// --- INTERCEPTOR PRINCIPALE (JWT + CSRF) ---
export const AuthInterceptor: HttpInterceptorFn = (
  req: HttpRequest<any>,
  next: HttpHandlerFn
): Observable<HttpEvent<any>> => {

  const isLoginRequest = req.url.includes('/auth/login-ldap/');
  let headers: { [name: string]: string | string[] } = {};
  let currentReq = req;

  // ==========================================================
  // 1. GESTIONE CSRF (SICUREZZA PER TUTTE LE RICHIESTE NON-GET)
  // ==========================================================
  const csrfToken = getCsrfCookie();

  // Aggiungi CSRF a tutte le richieste non-GET (inclusa la login)
  if (req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'OPTIONS' && csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }

  // ==========================================================
  // 2. GESTIONE JWT (AUTENTICAZIONE, ESCLUSA LA LOGIN)
  // ==========================================================

  if (!isLoginRequest) {
    const session = localStorage.getItem('session');
    console.log('INTERCEPTOR - session:', session);
    let token = null;

    if (session) {
      try {
        const parsed = JSON.parse(session);
        token = parsed.access || null;
        console.log('INTERCEPTOR - parsed.username:', parsed.username);

        if (parsed.username) {
          headers['X-Auth-User'] = parsed.username;
        }
      } catch { }
    }

    // Se il token JWT è presente, aggiungilo
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  // ==========================================================
  // 3. APPLICA GLI HEADER
  // ==========================================================

  // Clona la request solo se ci sono header da aggiungere
  if (Object.keys(headers).length > 0) {
    currentReq = req.clone({
      setHeaders: headers
    });
  }

  return next(currentReq);
};