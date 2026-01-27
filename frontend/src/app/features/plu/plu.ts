// src/app/features/plu/plu.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import * as ExcelJS from 'exceljs';

export interface PLUArticolo {
  codArticolo: string;
  descrizione: string;
  ccom: string;
  descrccom: string;
  rep: string;
  reparto_nome: string;
  bancobilancia: string;
  plu: string;
  plu_int: number;
  ean: string;
  ean_formatted: string;
}

export interface Reparto {
  reparto: string;
  reparto_nome: string;  // <-- aggiungi questo
  totale_articoli: number;
}

export interface Banco {
  banco: string;
  totale_articoli: number;
}

export interface Fornitore {
  codice: string;
  descrizione: string;
}

export interface Stats {
  totale_articoli: number;
  totale_reparti: number;
  totale_banchi: number;
  totale_fornitori: number;
  per_reparto: RepartoStats[];
}

export interface RepartoStats {
  reparto: string;
  totale_articoli: number;
  totale_plu: number;
  banchi: string[];
}

export interface DuplicatiResponse {
  trovati: number;
  duplicati: DuplicatoPLU[];
}

export interface DuplicatoPLU {
  plu: string;
  bancobilancia: string;
  count: number;
  articoli: PLUArticolo[];
}

@Injectable({
  providedIn: 'root'
})
export class PLUService {
  private apiUrl = `${environment.apiBase}/plu`;

  constructor(private http: HttpClient) { }

  getArticoli(filters?: {
    reparto?: string;
    banco?: string;
    fornitore?: string;
    search?: string;
    ordering?: string;
  }): Observable<PLUArticolo[]> {
    let params = new HttpParams();

    if (filters) {
      Object.keys(filters).forEach(key => {
        const value = (filters as any)[key];
        if (value !== null && value !== undefined && value !== '') {
          params = params.set(key, value.toString());
        }
      });
    }

    return this.http.get<PLUArticolo[]>(`${this.apiUrl}/`, { params });
  }

  getArticolo(codArticolo: string): Observable<PLUArticolo> {
    return this.http.get<PLUArticolo>(`${this.apiUrl}/${codArticolo}/`);
  }

  getReparti(): Observable<Reparto[]> {
    return this.http.get<Reparto[]>(`${this.apiUrl}/reparti/`);
  }

  getBanchi(): Observable<Banco[]> {
    return this.http.get<Banco[]>(`${this.apiUrl}/banchi/`);
  }

  getFornitori(): Observable<Fornitore[]> {
    return this.http.get<Fornitore[]>(`${this.apiUrl}/fornitori/`);
  }

  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.apiUrl}/stats/`);
  }

  getDuplicati(): Observable<DuplicatiResponse> {
    return this.http.get<DuplicatiResponse>(`${this.apiUrl}/duplicati/`);
  }

  exportExcelBackend(filters?: {
    reparto?: string;
    banco?: string;
    fornitore?: string;
  }): Observable<Blob> {
    let params = new HttpParams();

    if (filters) {
      Object.keys(filters).forEach(key => {
        const value = (filters as any)[key];
        if (value !== null && value !== undefined && value !== '') {
          params = params.set(key, value.toString());
        }
      });
    }

    return this.http.get(`${this.apiUrl}/export_excel/`, {
      params,
      responseType: 'blob'
    });
  }

  /**
   * Genera Excel con barcode come TESTO (font barcode)
   * NO immagini - i filtri Excel funzionano correttamente
   */
  /**
 * Genera Excel con barcode come IMMAGINI
 */
  async exportExcelClient(
    articoli: PLUArticolo[],
    filtriApplicati?: {
      reparto?: string;
      banco?: string;
      fornitore?: string;
    }
  ): Promise<void> {
    try {
      const workbook = new ExcelJS.Workbook();

      workbook.creator = 'Portale Intranet';
      workbook.created = new Date();
      workbook.modified = new Date();
      workbook.lastModifiedBy = 'Sistema PLU';

      const worksheet = workbook.addWorksheet('PLU Articoli', {
        properties: { tabColor: { argb: 'FF2E5090' } },
        views: [{ state: 'frozen', xSplit: 0, ySplit: 1 }]
      });

      worksheet.columns = [
        { header: 'PLU', key: 'plu', width: 12 },
        { header: 'Cod. Articolo', key: 'codArticolo', width: 15 },
        { header: 'Descrizione', key: 'descrizione', width: 45 },
        { header: 'EAN', key: 'ean', width: 18 },
        { header: 'Barcode', key: 'barcode', width: 25 },
        { header: 'Reparto', key: 'reparto', width: 15 },
        { header: 'Banco', key: 'banco', width: 10 },
        { header: 'Cod. Fornitore', key: 'codFornitore', width: 15 },
        { header: 'Fornitore', key: 'fornitore', width: 35 },
      ];

      // Header style
      const headerRow = worksheet.getRow(1);
      headerRow.font = {
        bold: true,
        color: { argb: 'FFFFFFFF' },
        size: 11,
        name: 'Arial'
      };
      headerRow.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FF2E5090' }
      };
      headerRow.alignment = {
        vertical: 'middle',
        horizontal: 'center'
      };
      headerRow.height = 25;

      headerRow.eachCell((cell) => {
        cell.border = {
          top: { style: 'thin', color: { argb: 'FF000000' } },
          left: { style: 'thin', color: { argb: 'FF000000' } },
          bottom: { style: 'thin', color: { argb: 'FF000000' } },
          right: { style: 'thin', color: { argb: 'FF000000' } }
        };
      });

      // Import JsBarcode
      const JsBarcode = (await import('jsbarcode')).default;

      // Dati
      for (let index = 0; index < articoli.length; index++) {
        const art = articoli[index];
        const rowNumber = index + 2; // +2 perché riga 1 è header

        const row = worksheet.addRow({
          plu: art.plu || '',
          codArticolo: art.codArticolo || '',
          descrizione: art.descrizione || '',
          ean: art.ean_formatted || '',
          barcode: '', // Lascia vuoto, mettiamo l'immagine
          reparto: art.reparto_nome || art.rep || '',
          banco: art.bancobilancia || '',
          codFornitore: art.ccom || '',
          fornitore: art.descrccom || ''
        });

        row.height = 45;

        if (index % 2 === 0) {
          row.fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFF5F5F5' }
          };
        }

        row.eachCell((cell, colNumber) => {
          cell.font = { name: 'Arial', size: 10 };
          cell.alignment = {
            vertical: 'middle',
            horizontal: colNumber === 3 ? 'left' : 'center'
          };
          cell.border = {
            top: { style: 'thin', color: { argb: 'FFE0E0E0' } },
            left: { style: 'thin', color: { argb: 'FFE0E0E0' } },
            bottom: { style: 'thin', color: { argb: 'FFE0E0E0' } },
            right: { style: 'thin', color: { argb: 'FFE0E0E0' } }
          };
        });

        // PLU evidenziato
        const pluCell = row.getCell(1);
        pluCell.font = {
          bold: true,
          color: { argb: 'FF2E5090' },
          size: 11
        };

        // EAN come testo
        const eanCell = row.getCell(4);
        eanCell.numFmt = '@';

        // Genera barcode immagine
        const ean = art.ean_formatted || '';
        if (ean && ean.length === 13) {
          try {
            const canvas = document.createElement('canvas');
            JsBarcode(canvas, ean, {
              format: 'EAN13',
              width: 1.5,
              height: 40,
              displayValue: false,
              margin: 2
            });

            const base64 = canvas.toDataURL('image/png').split(',')[1];

            const imageId = workbook.addImage({
              base64: base64,
              extension: 'png',
            });

            worksheet.addImage(imageId, {
              tl: { col: 4.1, row: rowNumber - 0.9 },
              ext: { width: 120, height: 40 }
            });
          } catch (e) {
            console.error('Errore barcode per EAN:', ean, e);
          }
        }
      }

      // NO autofilter - le immagini non si spostano con i filtri
      // worksheet.autoFilter = { ... };

      // Fogli aggiuntivi
      this.addStatsSheet(workbook, articoli, filtriApplicati);

      // Download
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const filename = `PLU_Articoli_${timestamp}.xlsx`;
      this.downloadFile(blob, filename);

    } catch (error) {
      console.error('Errore generazione Excel:', error);
      throw error;
    }
  }

  private addStatsSheet(
    workbook: ExcelJS.Workbook,
    articoli: PLUArticolo[],
    filtri?: any
  ): void {
    const statsSheet = workbook.addWorksheet('Statistiche', {
      properties: { tabColor: { argb: 'FF4CAF50' } }
    });

    const titleRow = statsSheet.addRow(['STATISTICHE PLU ARTICOLI']);
    titleRow.font = { bold: true, size: 16, color: { argb: 'FF2E5090' } };
    titleRow.height = 30;
    statsSheet.mergeCells('A1:B1');

    statsSheet.addRow([]);

    const dateRow = statsSheet.addRow(['Data Generazione:', new Date().toLocaleString('it-IT')]);
    dateRow.getCell(1).font = { bold: true };

    statsSheet.addRow([]);

    if (filtri) {
      statsSheet.addRow(['FILTRI APPLICATI']).font = { bold: true, size: 12 };
      if (filtri.reparto) statsSheet.addRow(['Reparto:', filtri.reparto]);
      if (filtri.banco) statsSheet.addRow(['Banco:', filtri.banco]);
      if (filtri.fornitore) statsSheet.addRow(['Fornitore:', filtri.fornitore]);
      statsSheet.addRow([]);
    }

    statsSheet.addRow(['STATISTICHE GENERALI']).font = { bold: true, size: 12 };
    statsSheet.addRow(['Totale Articoli:', articoli.length]);

    const perReparto = this.groupBy(articoli, 'rep');
    statsSheet.addRow(['Reparti Distinti:', Object.keys(perReparto).length]);

    const perBanco = this.groupBy(articoli, 'bancobilancia');
    statsSheet.addRow(['Banchi Distinti:', Object.keys(perBanco).length]);

    statsSheet.addRow([]);

    statsSheet.addRow(['ARTICOLI PER REPARTO']).font = { bold: true, size: 12 };
    const headerReparto = statsSheet.addRow(['Reparto', 'Quantità']);
    headerReparto.font = { bold: true };
    headerReparto.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFE3F2FD' }
    };

    Object.entries(perReparto)
      .sort((a, b) => b[1].length - a[1].length)
      .forEach(([reparto, items]) => {
        statsSheet.addRow([reparto, items.length]);
      });

    statsSheet.columns = [
      { width: 30 },
      { width: 20 }
    ];
  }

  private addInstructionsSheet(workbook: ExcelJS.Workbook): void {
    const sheet = workbook.addWorksheet('Istruzioni', {
      properties: { tabColor: { argb: 'FFFF9800' } }
    });

    sheet.columns = [{ width: 80 }];

    const rows = [
      ['ISTRUZIONI PER VISUALIZZARE I BARCODE'],
      [''],
      ['Se la colonna "Barcode" mostra solo numeri invece del codice a barre:'],
      [''],
      ['1. Installa il font "Libre Barcode EAN13 Text" (file ean13.ttf fornito)'],
      ['   Doppio click sul file -> Installa'],
      [''],
      ['2. Dopo l\'installazione, chiudi e riapri Excel'],
      [''],
      ['3. I barcode saranno visibili automaticamente'],
      [''],
      ['NOTA: L\'installazione del font è necessaria solo una volta.'],
    ];

    rows.forEach((row, index) => {
      const excelRow = sheet.addRow(row);

      if (index === 0) {
        excelRow.font = { bold: true, size: 14, color: { argb: 'FF2E5090' } };
        excelRow.height = 25;
      } else {
        excelRow.font = { size: 11 };
      }
    });
  }

  private groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
    return array.reduce((result, item) => {
      const group = String(item[key] || 'N/A');
      if (!result[group]) {
        result[group] = [];
      }
      result[group].push(item);
      return result;
    }, {} as Record<string, T[]>);
  }

  downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
}