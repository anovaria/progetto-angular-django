import { Component } from '@angular/core';

@Component({
  selector: 'app-access-denied',
  template: `<div class="access-denied">
               <h2>Accesso negato</h2>
               <p>Non hai i permessi necessari per visualizzare questa pagina.</p>
             </div>`,
  styles: [`.access-denied { text-align: center; margin-top: 50px; }`]
})
export class AccessDeniedComponent {}
