// src/app/features/plu/plu-list.component.ts
import { Component, OnInit, ViewChild, AfterViewInit, inject, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import JsBarcode from 'jsbarcode';
import {
  PLUService,
  PLUArticolo,
  Reparto,
  Banco,
  Fornitore,
  Stats
} from './plu';

@Component({
  selector: 'app-plu-list',
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatChipsModule,
    MatProgressBarModule,
    MatMenuModule,
    MatTooltipModule,
    MatSnackBarModule
  ],
  templateUrl: './plu-list.html',
  styleUrl: './plu-list.css'
})
export class PluListComponent implements OnInit, AfterViewInit {
  // Dependency injection
  private pluService = inject(PLUService);
  private snackBar = inject(MatSnackBar);
  // Colonne tabella
  displayedColumns = [
    'plu', 'codArticolo', 'descrizione', 'ean_formatted',
    'reparto_nome', 'bancobilancia', 'descrccom', 'barcode', 'actions'
  ];

  // Datasource
  dataSource = new MatTableDataSource<PLUArticolo>();

  // ViewChild
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('printTemplate') printTemplate!: ElementRef;

  // Dati per filtri
  reparti: Reparto[] = [];
  banchi: Banco[] = [];
  fornitori: Fornitore[] = [];

  // Filtri
  filtroReparto: string = '';
  filtroBanco: string = '';
  filtroFornitore: string = '';
  filtroRicerca = '';

  // Stats
  stats: Stats | null = null;

  // Loading
  loading = false;
  loadingExport = false;

  // Flags per UX
  isInitialLoad = true;

  // Dati per template stampa
  currentPrintArticolo: PLUArticolo | null = null;
  currentPrintBarcode: string = '';

  // No more constructor needed - usando inject()

  async ngOnInit() {
    await this.initialize();
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

    // Filtro custom per ricerca
    this.dataSource.filterPredicate = (data: PLUArticolo, filter: string) => {
      const searchStr = filter.toLowerCase();
      return (
        (data.plu?.toLowerCase() || '').includes(searchStr) ||
        (data.descrizione?.toLowerCase() || '').includes(searchStr) ||
        (data.ean_formatted?.toLowerCase() || '').includes(searchStr) ||
        (data.codArticolo?.toLowerCase() || '').includes(searchStr) ||
        (data.descrccom?.toLowerCase() || '').includes(searchStr)
      );
    };
  }

  /**
   * Inizializzazione completa del componente
   */
  async initialize() {
    this.loading = true;

    try {
      // Carica tutto in parallelo per performance
      await Promise.all([
        this.loadFilters(),
        this.loadStats(),
        this.loadData()
      ]);

      this.isInitialLoad = false;

      // Notifica successo
      this.showSnackbar(
        `✅ Caricati ${this.dataSource.data.length} articoli`,
        'success'
      );

    } catch (error) {
      console.error('Errore inizializzazione:', error);
      this.showSnackbar(
        '❌ Errore caricamento dati. Riprova più tardi.',
        'error'
      );
    } finally {
      this.loading = false;
    }
  }

  /**
   * Carica filtri (reparti, banchi, fornitori)
   */
  async loadFilters() {
    try {
      [this.reparti, this.banchi, this.fornitori] = await Promise.all([
        this.pluService.getReparti().toPromise(),
        this.pluService.getBanchi().toPromise(),
        this.pluService.getFornitori().toPromise()
      ]) as [Reparto[], Banco[], Fornitore[]];

      console.log(`📊 Caricati ${this.reparti.length} reparti, ${this.banchi.length} banchi, ${this.fornitori.length} fornitori`);

    } catch (error) {
      console.error('Errore caricamento filtri:', error);
      this.reparti = [];
      this.banchi = [];
      this.fornitori = [];
    }
  }

  /**
   * Carica statistiche
   */
  async loadStats() {
    try {
      this.stats = await this.pluService.getStats().toPromise() || null;
      console.log('📈 Statistiche caricate:', this.stats);
    } catch (error) {
      console.error('Errore caricamento stats:', error);
      this.stats = null;
    }
  }

  /**
   * Carica dati articoli con filtri
   */
  async loadData() {
    this.loading = true;

    try {
      const filters: any = {};
      if (this.filtroReparto) filters.reparto = this.filtroReparto;
      if (this.filtroBanco) filters.banco = this.filtroBanco;
      if (this.filtroFornitore) filters.fornitore = this.filtroFornitore;
      if (this.filtroRicerca) filters.search = this.filtroRicerca;

      const data = await this.pluService.getArticoli(filters).toPromise();
      this.dataSource.data = data || [];

      // Log solo se non è il caricamento iniziale
      if (!this.isInitialLoad) {
        const filterCount = Object.keys(filters).length;
        const message = filterCount > 0
          ? `🔍 Trovati ${this.dataSource.data.length} articoli (filtri attivi)`
          : `📦 Caricati ${this.dataSource.data.length} articoli`;
        console.log(message);
      }

    } catch (error) {
      console.error('Errore caricamento dati:', error);
      this.dataSource.data = [];
      this.showSnackbar('❌ Errore caricamento articoli', 'error');
    } finally {
      this.loading = false;
    }
  }

  /**
   * Applica filtro ricerca
   */
  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }

    // Feedback visivo
    if (filterValue && this.dataSource.filteredData.length === 0) {
      this.showSnackbar('Nessun risultato trovato', 'info');
    }
  }

  /**
   * Cancella filtro ricerca
   */
  clearSearchFilter() {
    this.filtroRicerca = '';
    this.dataSource.filter = '';

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  /**
   * Reset tutti i filtri
   */
  resetFilters() {
    this.filtroReparto = '';
    this.filtroBanco = '';
    this.filtroFornitore = '';
    this.filtroRicerca = '';
    this.dataSource.filter = '';

    this.loadData();
    this.showSnackbar('🔄 Filtri resettati', 'info');
  }

  /**
 * Export Excel con ExcelJS (lato client)
 */
  async exportExcel() {
    this.loadingExport = true;

    try {
      const articoli = this.dataSource.filteredData.length > 0
        ? this.dataSource.filteredData
        : this.dataSource.data;

      if (articoli.length === 0) {
        this.showSnackbar('⚠️ Nessun dato da esportare', 'warning');
        return;
      }

      // Prepara info filtri per statistiche (senza .nome)
      const filtriApplicati: any = {};
      if (this.filtroReparto) {
        filtriApplicati.reparto = this.filtroReparto;
      }
      if (this.filtroBanco) {
        filtriApplicati.banco = this.filtroBanco;
      }
      if (this.filtroFornitore) {
        const forn = this.fornitori.find(f => f.codice === this.filtroFornitore);
        filtriApplicati.fornitore = forn?.descrizione || this.filtroFornitore;
      }

      this.showSnackbar(`⏳ Generazione Excel in corso (${articoli.length} articoli)...`, 'info', 0);

      await this.pluService.exportExcelClient(articoli, filtriApplicati);

      this.showSnackbar(`✅ Excel generato con successo! (${articoli.length} articoli)`, 'success');
      console.log(`✅ Excel generato con ${articoli.length} articoli`);

    } catch (error) {
      console.error('Errore export Excel:', error);
      this.showSnackbar('❌ Errore durante la generazione del file Excel', 'error');
    } finally {
      this.loadingExport = false;
    }
  }
  /**
   * Genera barcode EAN-13
   */
  generateBarcode(ean: string): string {
    if (!ean) return '';

    try {
      const canvas = document.createElement('canvas');

      // Padding EAN a 13 cifre se necessario
      const eanPadded = ean.padStart(13, '0');

      JsBarcode(canvas, eanPadded, {
        format: 'EAN13',
        width: 1.5,
        height: 40,
        displayValue: false,
        margin: 2
      });

      return canvas.toDataURL('image/png');
    } catch (error) {
      console.error('Errore generazione barcode per EAN:', ean, error);
      return '';
    }
  }

  /**
   * Mostra dettagli articolo
   */
  viewDetails(articolo: PLUArticolo) {
    const details = `
🏷️ PLU: ${articolo.plu}
📦 Codice: ${articolo.codArticolo}
📝 Descrizione: ${articolo.descrizione}
🏪 Reparto: ${articolo.rep}
⚖️ Banco: ${articolo.bancobilancia}
📊 EAN: ${articolo.ean_formatted}
🏭 Fornitore: ${articolo.descrccom || 'N/A'}
    `.trim();

    alert(details);
    console.log('Dettagli articolo:', articolo);
  }

  /**
   * Stampa barcode usando template Angular
   */
  printBarcode(articolo: PLUArticolo) {
    if (!articolo.ean_formatted) {
      this.showSnackbar('⚠️ EAN non disponibile per questo articolo', 'warning');
      return;
    }

    // Genera barcode
    const barcodeUrl = this.generateBarcode(articolo.ean_formatted);

    if (!barcodeUrl) {
      this.showSnackbar('❌ Errore generazione barcode', 'error');
      return;
    }

    // Imposta dati per il template
    this.currentPrintArticolo = articolo;
    this.currentPrintBarcode = barcodeUrl;

    // Aspetta che Angular aggiorni il template
    setTimeout(() => {
      this.openPrintWindow();
    }, 100);
  }

  /**
   * Apre finestra di stampa con contenuto del template
   */
  private openPrintWindow() {
    const printWindow = window.open('', '_blank', 'width=400,height=600');

    if (!printWindow) {
      this.showSnackbar('❌ Impossibile aprire la finestra di stampa', 'error');
      return;
    }

    // Clona il contenuto del template
    const printContent = this.printTemplate.nativeElement.cloneNode(true) as HTMLElement;
    printContent.style.display = 'block';

    // Crea documento HTML per stampa
    const htmlContent = `
      <!DOCTYPE html>
      <html lang="it">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Barcode - PLU ${this.currentPrintArticolo?.plu}</title>
          <style>
            * {
              margin: 0;
              padding: 0;
              box-sizing: border-box;
            }
            
            body {
              font-family: Arial, sans-serif;
              padding: 20px;
              background: white;
            }
            
            .print-container {
              max-width: 300px;
              margin: 0 auto;
              border: 2px solid #333;
              padding: 20px;
              border-radius: 8px;
              text-align: center;
            }
            
            .print-barcode-img {
              max-width: 100%;
              margin: 20px 0;
            }
            
            .print-info {
              margin-top: 20px;
              font-size: 14px;
              line-height: 1.8;
              text-align: left;
            }
            
            .print-title {
              display: block;
              font-size: 16px;
              margin-bottom: 10px;
              text-align: center;
              color: #2E5090;
            }
            
            .print-detail {
              color: #333;
              margin: 8px 0;
              padding: 4px 0;
              border-bottom: 1px solid #eee;
            }
            
            .print-detail:last-child {
              border-bottom: none;
            }
            
            .btn-print {
              margin-top: 20px;
              padding: 12px 24px;
              background: #2E5090;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              font-size: 14px;
              transition: background 0.3s;
            }
            
            .btn-print:hover {
              background: #1a3d6b;
            }
            
            @media print {
              .btn-print { 
                display: none; 
              }
              .print-container { 
                border: none;
              }
              body {
                padding: 0;
              }
            }
          </style>
        </head>
        <body>
          ${printContent.innerHTML}
          <div style="text-align: center;">
            <button class="btn-print" onclick="window.print()">
              🖨️ Stampa
            </button>
          </div>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();

    this.showSnackbar('🖨️ Finestra di stampa aperta', 'info');

    // Reset dati dopo 500ms
    setTimeout(() => {
      this.currentPrintArticolo = null;
      this.currentPrintBarcode = '';
    }, 500);
  }

  /**
   * Copia EAN negli appunti
   */
  async copyEAN(ean: string) {
    if (!ean) {
      this.showSnackbar('⚠️ EAN non disponibile', 'warning');
      return;
    }

    try {
      await navigator.clipboard.writeText(ean);
      this.showSnackbar(`✅ EAN copiato: ${ean}`, 'success');
      console.log('EAN copiato:', ean);
    } catch (error) {
      console.error('Errore copia EAN:', error);

      // Fallback per browser che non supportano clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = ean;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        this.showSnackbar(`✅ EAN copiato: ${ean}`, 'success');
      } catch (err) {
        this.showSnackbar('❌ Impossibile copiare EAN', 'error');
      }
      document.body.removeChild(textArea);
    }
  }

  /**
   * Get color per chip reparto
   */
  getRepartoColor(rep: string): string {
    const repInt = parseInt(rep) || 0;

    if (repInt === 50) return 'primary'; // Pescheria
    if (repInt === 60 || repInt === 61) return 'accent'; // Salumeria/Gastronomia
    if (repInt >= 20 && repInt < 30) return 'warn'; // Macelleria
    if (repInt === 10) return 'primary'; // Ortofrutta

    return '';
  }

  /**
   * Mostra snackbar notification
   */
  private showSnackbar(
    message: string,
    type: 'success' | 'error' | 'warning' | 'info',
    duration: number = 3000
  ) {
    const panelClass = `snackbar-${type}`;

    this.snackBar.open(message, '✕', {
      duration: duration || 3000,
      horizontalPosition: 'end',
      verticalPosition: 'top',
      panelClass: [panelClass]
    });
  }
}