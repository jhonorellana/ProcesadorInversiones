# -*- coding: utf-8 -*-
"""
Extractor de datos de PDFs de la Bolsa de Valores de Quito (BVQ).
Reemplaza PDFExtractor_Gemini.py para documentos BVQ -- sin API externa.

PROBLEMA CONOCIDO DEL PDF BVQ
==============================
Ciertas secciones del PDF tienen caracteres duplicados por superposicion
de capas de fuente (ej. 'BBOOLLSSAA' en lugar de 'BOLSA', '443322,,7744'
en lugar de '432,74'). Este modulo los detecta y corrige antes de aplicar
los patrones de extraccion.

El criterio de deteccion: si >= 70% de los pares en posicion par son
iguales, la cadena es "doblada" y se toma cada segundo caracter (s[::2]).
Esto es seguro frente a cadenas con '00' naturales como RUCs o codigos.
"""

import pdfplumber
import re
import os
import csv
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# Utilidades de limpieza
# =============================================================================

def _is_doubled_string(s: str) -> bool:
    """
    Retorna True si la cadena sigue el patron de caracteres duplicados.
    Compara pares en posiciones pares: s[0]==s[1], s[2]==s[3], ...
    Umbral: >= 70% de los pares deben ser iguales.

    Ejemplos:
        'BBOOLLSSAA'     -> True  (5/5 = 100%)
        '11,,7722'       -> True  (4/4 = 100%)
        '443322,,7744'   -> True  (6/6 = 100%)
        '95,00000000'    -> False (0/5 =   0%, el 9 y 5 no son par)
        '1791961021001'  -> False (0/6 =   0%)
        '0,00'           -> False (0/2 =   0%)
    """
    if not s or len(s) < 2:
        return False
    s_low = s.lower()
    total_pairs = len(s_low) // 2
    if total_pairs == 0:
        return False
    matched = sum(1 for i in range(0, len(s_low) - 1, 2)
                  if s_low[i] == s_low[i + 1])
    return matched / total_pairs >= 0.70


def _fix_doubled(s: str) -> str:
    """
    Corrige caracteres duplicados tomando cada segundo caracter (s[::2]).
    Solo actua cuando _is_doubled_string retorna True.

    'BBOOLLSSAA'   -> 'BOLSA'
    '11,,7722'     -> '1,72'
    '443322,,7744' -> '432,74'
    '0,00'         -> '0,00'   (sin cambio)
    '95,00000000'  -> '95,00000000' (sin cambio)
    """
    if _is_doubled_string(s):
        return s[::2]
    return s


def _dedup_text(text: str) -> str:
    """
    Aplica _fix_doubled token a token (separados por espacio) para limpiar
    el texto completo sin corromper cadenas no duplicadas.
    Preserva la estructura de lineas.
    """
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        tokens = line.split(' ')
        fixed_lines.append(' '.join(_fix_doubled(t) for t in tokens))
    return '\n'.join(fixed_lines)


def _norm_num(s: str) -> str:
    """
    Normaliza un numero en formato europeo (coma=decimal) a punto decimal.
    Retorna cadena vacia si el valor es un guion o vacio.

    '453,71'   -> '453.71'
    '1,72'     -> '1.72'
    '0,00'     -> '0.00'
    '-'        -> ''
    """
    if not s:
        return ''
    s = s.strip().replace(' ', '')
    if s in ('-', '\u2013', '\u2014', ''):
        return ''
    s = s.rstrip('%')
    # Determinar separador decimal segun cual aparece ultimo
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # coma es decimal (europeo): quitar puntos de miles
            s = s.replace('.', '').replace(',', '.')
        else:
            # punto es decimal (americano): quitar comas de miles
            s = s.replace(',', '')
    elif ',' in s:
        # Solo coma: es separador decimal
        s = s.replace(',', '.')
    # Validar que sea un numero
    try:
        float(s)
        return s
    except ValueError:
        return s


def _norm_date(s: str) -> str:
    """
    Convierte DD-MM-YYYY [HH:MM:SS] a YYYY-MM-DD [HH:MM:SS].
    Aplica _fix_doubled al valor captado (puede venir doblado del PDF).

    '29-04-2026 13:00:17' -> '2026-04-29 13:00:17'
    '2299--0044--22002266 1133::0000::1177' -> '2026-04-29 13:00:17'
    """
    if not s:
        return ''
    s = _fix_doubled(s.strip())
    s = re.sub(r'-{2,}', '-', s)
    s = re.sub(r':{2,}', ':', s)
    s = s.strip()
    m = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})(\s+\d{2}:\d{2}:\d{2})?$', s)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        hora = m.group(4) or ''
        return f'{year}-{month.zfill(2)}-{day.zfill(2)}{hora}'
    return s


def _safe(tokens: list, idx: int, default: str = '') -> str:
    """Acceso seguro a lista: retorna default si idx fuera de rango."""
    try:
        return tokens[idx]
    except IndexError:
        return default


# =============================================================================
# Clase principal -- interfaz compatible con PDFExtractor_Gemini
# =============================================================================

class PDFExtractor:
    """
    Extractor de liquidaciones de la Bolsa de Valores de Quito (BVQ).
    Expone la misma interfaz publica que PDFExtractor_Gemini.PDFExtractor
    para que MainProcesador.py funcione sin cambios en la logica de negocio.
    """

    # -------------------------------------------------------------------------
    # Metodos de compatibilidad con interfaz Gemini
    # -------------------------------------------------------------------------

    def limpiar_valor_numerico(self, valor: str) -> str:
        return _norm_num(valor)

    def formatear_fecha_yyyy_mm_dd(self, fecha_str: str) -> str:
        return _norm_date(fecha_str)

    def identificar_tipo_documento(self, texto: str) -> str:
        t = texto.upper()
        if 'BONO' in t and 'ESTADO' in t:
            return 'BONO_ESTADO'
        if 'NOTA' in t and 'CREDITO' in t:
            return 'NOTA_CREDITO'
        if 'PAPEL' in t and 'COMERCIAL' in t:
            return 'NOTA_CREDITO'
        return 'DESCONOCIDO'

    def extraer_tipo_operacion(self, texto: str) -> str:
        m = re.search(r'\b(Compra|Venta)\b', texto, re.IGNORECASE)
        return m.group(1).upper() if m else ''

    def extraer_propietario(self, texto: str) -> str:
        """Las liquidaciones BVQ no incluyen nombre del propietario."""
        return ''

    # -------------------------------------------------------------------------
    # Extraccion de texto del PDF
    # -------------------------------------------------------------------------

    def _extraer_texto(self, ruta: str) -> Optional[str]:
        """Extrae el texto completo del PDF usando pdfplumber."""
        try:
            partes = []
            with pdfplumber.open(ruta) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        partes.append(t)
            return '\n'.join(partes) if partes else None
        except Exception as e:
            logger.error(f'Error extrayendo texto de {ruta}: {e}')
            return None

    # -------------------------------------------------------------------------
    # Motor de extraccion de campos
    # -------------------------------------------------------------------------

    def _extraer_campos(self, texto_raw: str) -> Dict[str, Any]:
        """
        Extrae todos los campos del texto crudo del PDF.

        Estrategia:
        1. Ciertos campos (RUC, RMV, operacion_no) se extraen del texto RAW
           porque estan en secciones no duplicadas con numeros exactos.
        2. El resto del texto se limpia token a token (_dedup_text) para
           normalizar las secciones con caracteres duplicados, y luego se
           aplican los patrones regex.
        """
        d: Dict[str, Any] = {}

        # ── PRE-EXTRACCION EN TEXTO CRUDO (seccion no duplicada) ─────────────

        # Tipo de operacion y numero de operacion
        # "Compra N0. 12089 - VRF79"  (esta linea NO esta duplicada)
        op_m = re.search(r'\b(Compra|Venta)\s+N0?\.\s*(\d+)', texto_raw, re.IGNORECASE)
        if op_m:
            d['tipo_operacion'] = op_m.group(1).upper()
            d['operacion_no'] = op_m.group(2)

        # RUC de la casa de valores (13 digitos exactos, en seccion no duplicada)
        ruc_m = re.search(r'\b(\d{13})\b', texto_raw)
        if ruc_m:
            d['ruc_casa_valores'] = ruc_m.group(1)

        # Registro RMV (formato NNNN.N.NN.NNNNN, en seccion no duplicada)
        rmv_m = re.search(r'\b(\d{4}\.\d+\.\d+\.\d+)\b', texto_raw)
        if rmv_m:
            d['registro_rmv'] = rmv_m.group(1)

        # ── LIMPIEZA DE TEXTO DUPLICADO ───────────────────────────────────────

        texto = _dedup_text(texto_raw)

        # ── FECHAS DE CABECERA (en seccion duplicada, ya limpias tras dedup) ──

        m = re.search(r'hora\s+consulta:\s*([\d][\d-]+\s+[\d:]+)', texto, re.IGNORECASE)
        if m:
            d['fecha_consulta'] = _norm_date(m.group(1))

        m = re.search(r'hora\s+de\s+cierre:\s*([\d][\d-]+\s+[\d:]+)', texto, re.IGNORECASE)
        if m:
            d['fecha_cierre'] = _norm_date(m.group(1))

        # ── INTERMEDIARIO ─────────────────────────────────────────────────────

        # Linea de datos despues del header "Casa de valores ... Operador de valores"
        cv_hdr_m = re.search(
            r'Casa\s+de\s+valores\s+.{0,60}?Operador\s+de\s+valores\s*\n\s*(.+)',
            texto, re.IGNORECASE
        )
        if cv_hdr_m:
            data_line = cv_hdr_m.group(1).strip()
            addr_m = re.search(r'\b(?:Av\.|Calle|Jr\.|Urb\.|Edif\.?|Km\.?|Plaza|N\d{1,2}-)', data_line)
            if addr_m:
                d['casa_valores'] = data_line[:addr_m.start()].strip()
                if 'ruc_casa_valores' in d:
                    ruc_pos = data_line.find(d['ruc_casa_valores'])
                    if ruc_pos > addr_m.start():
                        d['direccion_casa_valores'] = data_line[addr_m.start():ruc_pos].strip()
            else:
                # Sin direccion reconocible: todo antes del RUC es el nombre
                if 'ruc_casa_valores' in d:
                    ruc_pos = data_line.find(d['ruc_casa_valores'])
                    if ruc_pos > 0:
                        d['casa_valores'] = data_line[:ruc_pos].strip()

        # Operador de valores: texto despues del RUC en la misma linea
        if 'ruc_casa_valores' in d:
            op_val_m = re.search(
                re.escape(d['ruc_casa_valores']) + r'\s+(.+?)(?:\n|$)',
                texto
            )
            if op_val_m:
                d['operador_valores'] = op_val_m.group(1).strip()

        # ── DATOS DEL VALOR ───────────────────────────────────────────────────

        val_hdr_m = re.search(
            r'Val\.\s*Nom\.\s*actual\s+Val\.\s*Nom\.\s*original\s+Valor\s+efectivo\s*\(A\)\s*\n',
            texto, re.IGNORECASE
        )
        if val_hdr_m:
            rest = texto[val_hdr_m.end():]
            lines = rest.split('\n')
            data_line1 = lines[0].strip() if lines else ''
            data_line2 = lines[1].strip() if len(lines) > 1 else ''

            # Numeros al final de la linea
            nums = re.findall(r'([\d]+(?:[,\.][\d]+)*)', data_line1)
            if len(nums) >= 3:
                d['valor_nominal'] = _norm_num(nums[0])
                # nums[1] = val nom original (igual al actual normalmente)
                d['valor_efectivo'] = _norm_num(nums[2])
            elif len(nums) == 2:
                d['valor_nominal'] = _norm_num(nums[0])
                d['valor_efectivo'] = _norm_num(nums[1])
            elif len(nums) == 1:
                d['valor_nominal'] = _norm_num(nums[0])

            # Titulo y emisor: texto antes de los numeros
            text_part = re.sub(r'[\d]+(?:[,\.][\d]+)*', '', data_line1).strip()

            titulos_conocidos = [
                r'NOTAS?\s+DE\s+CR[EÉe]DITO',
                r'BONOS?\s+DEL?\s+ESTADO',
                r'PAPEL\s+COMERCIAL',
                r'CERTIFICADOS?\s+DE\s+DEP[OÓo]SITO',
                r'OBLIGACIONES?',
            ]
            for patron in titulos_conocidos:
                tm = re.search(patron, text_part, re.IGNORECASE)
                if tm:
                    d['titulo_valor'] = tm.group(0).strip()
                    emisor_part = text_part[tm.end():].strip()
                    # El emisor puede continuar en la segunda linea
                    if (data_line2
                            and re.match(r'^[A-Z][A-Z\s]+$', data_line2)
                            and not re.search(r'[\d]', data_line2)
                            and len(data_line2) < 60):
                        emisor_part = (emisor_part + ' ' + data_line2).strip()
                    d['emisor'] = emisor_part
                    break

            if 'titulo_valor' not in d and text_part:
                # Fallback: primeras 3 palabras como titulo
                words = text_part.split()
                d['titulo_valor'] = ' '.join(words[:3])
                d['emisor'] = ' '.join(words[3:])

        # ── CUPON / FECHAS ────────────────────────────────────────────────────

        cupon_hdr_m = re.search(
            r'Cup[o\?]\w*\s+actual\s+Cup[o\?]\w*\s+anterior'
            r'\s+Fecha\s+valor\s+Fecha\s+emisi\S+\s+Fecha\s+vencimiento\s*\n\s*(.+)',
            texto, re.IGNORECASE
        )
        if cupon_hdr_m:
            tokens = cupon_hdr_m.group(1).strip().split()
            d['cupon_actual'] = _safe(tokens, 0) if _safe(tokens, 0) != '-' else ''
            d['cupon_anterior'] = _safe(tokens, 1) if _safe(tokens, 1) != '-' else ''
            fv = _safe(tokens, 2)
            fe = _safe(tokens, 3)
            fvc = _safe(tokens, 4)
            d['fecha_valor'] = _norm_date(fv) if fv and fv != '-' else ''
            d['fecha_emision'] = _norm_date(fe) if fe and fe != '-' else ''
            d['fecha_vencimiento'] = _norm_date(fvc) if fvc and fvc != '-' else ''

        # ── RENDIMIENTOS / TASAS ──────────────────────────────────────────────

        # "RDTO. Nominal (%) Precio (%) Interes Nominal (%) TIR / TEA (%) Precio Neto (%)"
        # "- % 95,00000000 % - - 95,37810496 %"
        tasas_hdr_m = re.search(
            r'RDTO\.\s*Nominal.*?Precio\s*Neto\s*\(%\)\s*\n\s*(.+)',
            texto, re.IGNORECASE
        )
        if tasas_hdr_m:
            # Quitar tokens '%' sueltos para quedar con los 5 valores
            tokens = [t for t in tasas_hdr_m.group(1).strip().split() if t != '%']
            claves = ['rendimiento_nominal', 'precio', 'interes_nominal', 'tir_tea', 'precio_neto']
            for i, clave in enumerate(claves):
                v = _safe(tokens, i)
                d[clave] = _norm_num(v) if v and v != '-' else ''

        # ── DIAS DE INTERES / BASE / PLAZO ────────────────────────────────────

        dias_hdr_m = re.search(
            r'D[i\?\w]+\s+de\s+inter[e\?\w]+\s+Base\s+D[i\?\w]+\s+Plazo\s+por\s+vencer\s*\n\s*(.+)',
            texto, re.IGNORECASE
        )
        if dias_hdr_m:
            tokens = dias_hdr_m.group(1).strip().split()
            d['dias_interes'] = _safe(tokens, 0) if _safe(tokens, 0) != '-' else ''
            d['base_dias'] = _safe(tokens, 1) if _safe(tokens, 1) != '-' else ''
            d['plazo_por_vencer'] = _safe(tokens, 2) if _safe(tokens, 2) != '-' else ''

        # ── DATOS DE TRANSACCION ──────────────────────────────────────────────

        trans_hdr_m = re.search(
            r'Desmaterializado\s+Cam\.?compensaci\S+\s+Moneda\s+Mercado\s+Postura\s*\n\s*(.+)',
            texto, re.IGNORECASE
        )
        if trans_hdr_m:
            tokens = trans_hdr_m.group(1).strip().split()
            d['desmaterializado'] = _safe(tokens, 0)
            d['camara_compensacion'] = _safe(tokens, 1)
            d['moneda'] = _safe(tokens, 2)
            d['mercado'] = _safe(tokens, 3)
            d['postura'] = _safe(tokens, 4)

        # ── TIPO OPERACION DETALLE / SALDO / PRECIO SUCIO ─────────────────────

        # "Valor minimo Cupon  Tipo de operacion  Saldo por amortizar  Precio sucio (%)"
        # "(%)                                                                          "
        # "453,71           -  CONTADO            -                                     "
        tipo_op_blk = re.search(
            r'Tipo\s+de\s+operaci\S+\s+Saldo\s+por\s+amortizar.+?\n'
            r'(?:[^\n]+\n)?\s*[\d,\.]+\s+(-|\S+)\s+(\S+)\s+(-|\S+)',
            texto, re.IGNORECASE
        )
        if tipo_op_blk:
            d['tipo_operacion_detalle'] = tipo_op_blk.group(2) if tipo_op_blk.group(2) != '-' else ''
            d['saldo_por_amortizar'] = _norm_num(tipo_op_blk.group(3)) if tipo_op_blk.group(3) != '-' else ''

        # ── CALIFICACION Y CODIGO VECTOR ──────────────────────────────────────

        # Linea: "Calificadora de  Calificacion  Ultima calificacion  Codigo vector  Registro RMV"
        # Cont.:  "riesgos"
        # Datos:  "NO APLICA  NO APLICA  -  2000.1.02.00381"
        # Datos2: "NO APLICA"
        cal_hdr_m = re.search(
            r'C[o\?\w]+digo\s+vector\s+Registro\s+RMV\s*\n'
            r'(?:[^\n]+\n)?'          # linea opcional ('riesgos')
            r'\s*([^\n]+)',
            texto, re.IGNORECASE
        )
        if cal_hdr_m:
            tokens = cal_hdr_m.group(1).strip().split()
            # El penultimo token es codigo_vector, el ultimo es registro_rmv
            if len(tokens) >= 2:
                cv = _safe(tokens, -2)
                d['codigo_vector'] = cv if cv and cv not in ('-', 'APLICA') else ''
                if 'registro_rmv' not in d:
                    d['registro_rmv'] = _safe(tokens, -1)

        # ── SECTOR ECONOMICO ──────────────────────────────────────────────────

        # Buscar el valor conocido directamente (mas robusto que parsear la tabla)
        sec_m = re.search(
            r'(GOBIERNO\s+CENTRAL'
            r'|SECTOR\s+P[UÚu]BLICO\s+(?:NO\s+)?FINANCIERO'
            r'|SECTOR\s+PRIVADO\s+(?:NO\s+)?FINANCIERO'
            r'|INSTITUCIONES\s+FINANCIERAS)',
            texto, re.IGNORECASE
        )
        if sec_m:
            d['sector_economico'] = sec_m.group(1).upper()
        else:
            # Fallback: data row despues del header de sector
            sec_hdr_m = re.search(
                r'Sector\s+econ\S+\s*\n(?:[^\n]*\n)?\s*(.+)',
                texto, re.IGNORECASE
            )
            if sec_hdr_m:
                meaningful = [t for t in sec_hdr_m.group(1).strip().split() if t != '-']
                if meaningful:
                    d['sector_economico'] = ' '.join(meaningful)

        # ── VALORES TOTALES ───────────────────────────────────────────────────

        # "Valor efectivo (A) - 431,02"  (en tabla de totales)
        ve_tot_m = re.search(
            r'Valor\s+efectivo\s*\(A\)\s+[-\u2013]\s+([\d,\.]+)',
            texto, re.IGNORECASE
        )
        if ve_tot_m and not d.get('valor_efectivo'):
            d['valor_efectivo'] = _norm_num(ve_tot_m.group(1))

        # "Bolsa(C) 0,02000 0,00"
        bolsa_m = re.search(r'Bolsa\s*\(C\)\s+([\d,\.]+)\s+([\d,\.]+)', texto, re.IGNORECASE)
        if bolsa_m:
            d['comision_bolsa'] = _norm_num(bolsa_m.group(2))

        # "Operador(D) 0,40000 1,72"
        oper_m = re.search(r'Operador\s*\(D\)\s+([\d,\.]+)\s+([\d,\.]+)', texto, re.IGNORECASE)
        if oper_m:
            d['comision_operador'] = _norm_num(oper_m.group(2))

        # Total comisiones: linea "Total X.XX  Y.YY" inmediatamente despues de Operador(D)
        tot_com_m = re.search(
            r'Operador\s*\(D\)[^\n]*\n\s*Total\s+([\d,\.]+)\s+([\d,\.]+)',
            texto, re.IGNORECASE
        )
        if tot_com_m:
            d['total_comisiones'] = _norm_num(tot_com_m.group(2))

        # "Monto interes(B) 0 0,00"
        int_m = re.search(
            r'Monto\s+inter[e\?]\w*\s*\(B\)\s+\S+\s+([\d,\.]+)',
            texto, re.IGNORECASE
        )
        if int_m:
            d['valor_interes'] = _norm_num(int_m.group(1))

        # "Total ( A+B+C+D ) 0 432,74"   -> total desembolso bruto
        desembolso_m = re.search(
            r'Total\s*\(\s*A\+B\+C\+D\s*\)\s+\S+\s+([\d,\.]+)',
            texto, re.IGNORECASE
        )
        if desembolso_m:
            d['total_desembolso'] = _norm_num(desembolso_m.group(1))

        # "Total comprador (A+B+C+D-RO-RB) 432,74"
        tot_comp_m = re.search(
            r'Total\s+comprador\s*\([^)]+\)\s+([\d,\.]+)',
            texto, re.IGNORECASE
        )
        if tot_comp_m:
            d['total_comprador'] = _norm_num(tot_comp_m.group(1))

        # ── FACTURA ASOCIADA ──────────────────────────────────────────────────

        fac_m = re.search(
            r'[Ll]iquidaci\S+\s+asociada\s+a\s+factura\s+N0?\.\s*\n?\s*([\d\-]+)',
            texto, re.IGNORECASE
        )
        if fac_m:
            d['factura_asociada_no'] = fac_m.group(1).strip()

        # ── TIPO DE DOCUMENTO ─────────────────────────────────────────────────

        d['tipo_documento'] = self.identificar_tipo_documento(texto)

        return d

    # -------------------------------------------------------------------------
    # API publica (compatible con PDFExtractor_Gemini)
    # -------------------------------------------------------------------------

    def extraer_datos_liquidacion(self, ruta_archivo: str) -> Optional[Dict[str, Any]]:
        """
        Extrae todos los campos de una liquidacion BVQ.
        Firma identica a PDFExtractor_Gemini.extraer_datos_liquidacion().
        """
        texto_raw = self._extraer_texto(ruta_archivo)
        if not texto_raw:
            logger.error(f'Sin texto: {ruta_archivo}')
            return None

        datos = self._extraer_campos(texto_raw)

        # Metadatos de procesamiento
        datos['archivo'] = os.path.basename(ruta_archivo)
        datos['ruta_completa'] = ruta_archivo
        datos['fecha_procesamiento'] = datetime.now().isoformat()
        datos['tamaño_archivo'] = os.path.getsize(ruta_archivo)
        datos['extractor_utilizado'] = 'PDFExtractor_BVQ (Python)'

        # Asegurar valor_nominal para la logica de renombrado
        if not datos.get('valor_nominal'):
            datos['valor_nominal'] = datos.get('valor_efectivo', '')

        logger.info(
            f'BVQ extraido: {os.path.basename(ruta_archivo)}'
            f' | op={datos.get("operacion_no", "?")} '
            f' | tipo={datos.get("tipo_documento", "?")}'
            f' | nom={datos.get("valor_nominal", "?")}'
        )
        return datos

    def guardar_resultados_csv(self, resultados: List[Dict[str, Any]], archivo_salida: str):
        """
        Guarda resultados en CSV.
        Firma identica a PDFExtractor_Gemini.guardar_resultados_csv().
        """
        try:
            filtrados = [r for r in resultados if r.get('tipo_documento') != 'DESCONOCIDO']
            if not filtrados:
                logger.warning('No hay registros validos para guardar (todos DESCONOCIDO)')
                return

            todos_campos: set = set()
            for r in filtrados:
                todos_campos.update(r.keys())

            campos_principales = [
                'tipo_operacion', 'propietario', 'tipo_documento',
                'fecha_consulta', 'fecha_cierre', 'operacion_no',
                'casa_valores', 'direccion_casa_valores', 'ruc_casa_valores',
                'operador_valores', 'titulo_valor', 'emisor',
                'valor_nominal', 'valor_efectivo',
                'cupon_actual', 'cupon_anterior',
                'fecha_valor', 'fecha_emision', 'fecha_vencimiento',
                'rendimiento_nominal', 'precio', 'interes_nominal',
                'tir_tea', 'precio_neto',
                'dias_interes', 'base_dias', 'plazo_por_vencer',
                'desmaterializado', 'camara_compensacion', 'moneda',
                'mercado', 'postura',
                'tipo_operacion_detalle', 'saldo_por_amortizar',
                'codigo_vector', 'registro_rmv',
                'sector_economico',
                'comision_bolsa', 'comision_operador', 'total_comisiones',
                'valor_interes', 'total_desembolso', 'total_comprador',
                'factura_asociada_no',
                'extractor_utilizado', 'archivo',
            ]
            extra = sorted(c for c in todos_campos if c not in campos_principales)
            encabezados = campos_principales + extra

            with open(archivo_salida, 'w', newline='', encoding='latin-1') as f:
                writer = csv.DictWriter(
                    f, fieldnames=encabezados, delimiter=';', extrasaction='ignore'
                )
                writer.writeheader()
                for r in filtrados:
                    writer.writerow({c: r.get(c, '') for c in encabezados})

            logger.info(f'CSV BVQ guardado: {archivo_salida} ({len(filtrados)} registros)')

        except Exception as e:
            logger.error(f'Error guardando CSV: {e}')


# =============================================================================
# Alias de compatibilidad con la clase original
# =============================================================================

class PDFExtractor_BVQ(PDFExtractor):
    """Alias mantenido por compatibilidad con imports existentes."""
    pass


# =============================================================================
# Prueba en linea de comandos
# =============================================================================

def main():
    """Modo standalone: extrae y muestra datos de un PDF BVQ."""
    import sys
    import pprint

    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = os.path.join('..', 'Entrada', '3. LIQUIDACION DE BOLSA_2.pdf')

    if not os.path.exists(ruta):
        print(f'[ERROR] Archivo no encontrado: {ruta}')
        return

    extractor = PDFExtractor()
    datos = extractor.extraer_datos_liquidacion(ruta)

    if datos:
        print(f'\n{"="*60}')
        print('DATOS EXTRAIDOS')
        print(f'{"="*60}')
        for k, v in sorted(datos.items()):
            if v and k not in ('ruta_completa',):
                print(f'  {k:<35} = {v}')
        print(f'{"="*60}')
    else:
        print('[ERROR] No se extrajeron datos.')


if __name__ == '__main__':
    main()
