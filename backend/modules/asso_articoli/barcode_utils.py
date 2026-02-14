"""
Utility per generazione barcode EAN13
Supporta output SVG (inline HTML) e PNG (per Excel export)
"""
import barcode
from barcode.writer import SVGWriter, ImageWriter
from io import BytesIO
import base64


def generate_ean13_svg(ean_code, add_checksum=True):
    """
    Genera barcode EAN13 come SVG inline
    
    Args:
        ean_code: Codice EAN (12 cifre, la 13a viene calcolata automaticamente)
        add_checksum: Se True, calcola automaticamente il checksum digit
    
    Returns:
        str: SVG come stringa (può essere embedded direttamente in HTML)
    """
    if not ean_code or len(str(ean_code)) < 12:
        return None
    
    try:
        # Prendi i primi 12 caratteri
        ean_12 = str(ean_code)[:12]
        
        # Genera il barcode EAN13
        ean = barcode.get('ean13', ean_12, writer=SVGWriter())
        
        # Genera SVG in memoria
        buffer = BytesIO()
        ean.write(buffer, options={
            'module_width': 0.2,
            'module_height': 10.0,
            'quiet_zone': 2.0,
            'font_size': 8,
            'text_distance': 5.0,  # era 2.0, aumentato per staccare i numeri
        })
        
        svg_content = buffer.getvalue().decode('utf-8')
        return svg_content
    except Exception as e:
        print(f"Errore generazione barcode per {ean_code}: {e}")
        return None


def generate_ean13_png(ean_code, add_checksum=True):
    """
    Genera barcode EAN13 come immagine PNG (senza numeri, per Excel)
    """
    if not ean_code or len(str(ean_code)) < 12:
        return None
    
    try:
        ean_12 = str(ean_code)[:12]
        ean = barcode.get('ean13', ean_12, writer=ImageWriter())
        
        buffer = BytesIO()
        ean.write(buffer, options={
            'module_width': 0.4,      # più largo
            'module_height': 15.0,    # più alto
            'quiet_zone': 2.0,
            'write_text': False,      # NIENTE NUMERI
        })
        
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Errore generazione barcode PNG per {ean_code}: {e}")
        return None


def generate_ean13_base64(ean_code):
    """
    Genera barcode EAN13 come base64 (per data URI)
    
    Args:
        ean_code: Codice EAN (12 cifre)
    
    Returns:
        str: Immagine PNG codificata in base64
    """
    png_buffer = generate_ean13_png(ean_code)
    if png_buffer:
        png_data = png_buffer.getvalue()
        base64_data = base64.b64encode(png_data).decode('utf-8')
        return base64_data
    return None


def validate_ean13(ean_code):
    """
    Valida un codice EAN13 (verifica checksum)
    
    Args:
        ean_code: Codice EAN completo (13 cifre)
    
    Returns:
        bool: True se valido, False altrimenti
    """
    if not ean_code or len(str(ean_code)) != 13:
        return False
    
    try:
        ean_str = str(ean_code)
        
        # Calcola checksum
        odd_sum = sum(int(ean_str[i]) for i in range(0, 12, 2))
        even_sum = sum(int(ean_str[i]) for i in range(1, 12, 2))
        
        checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
        
        return int(ean_str[12]) == checksum
    except:
        return False


def normalize_ean_for_barcode(ean_code, tipo_ean=None):
    """
    Normalizza il codice EAN secondo il tipo (come nella logica Access)
    
    Args:
        ean_code: Codice EAN grezzo
        tipo_ean: Tipo EAN (6, 7, o None per default)
    
    Returns:
        str: EAN normalizzato a 12 cifre per generazione barcode
    """
    if not ean_code:
        return None
    
    ean_str = str(ean_code).strip()
    
    # Logica Access: IIf([tipo]=6, "00000" & Mid([EAN],1,7), 
    #                    IIf([tipo]=7, "0" & Mid([EAN],1,11), 
    #                        Mid([EAN],1,12)))
    
    if tipo_ean == 6:
        # Tipo 6: padding con 5 zeri + primi 7 caratteri
        return ('00000' + ean_str[:7])[:12]
    elif tipo_ean == 7:
        # Tipo 7: padding con 1 zero + primi 11 caratteri
        return ('0' + ean_str[:11])[:12]
    else:
        # Default: primi 12 caratteri
        return ean_str[:12]
