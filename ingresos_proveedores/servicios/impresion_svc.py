import os

from config.config_manager import ConfigManager
from modelos.ingreso import Ingreso
from modelos.remito import Remito
from servicios.ingreso_svc import IngresoService
from servicios.pdf_generator import generar_remito as pdf_remito, generar_etiquetas as pdf_etiquetas, generar_pdf_etiquetas_mateti
from servicios.dp_generator import imprimir_etiquetas_dp
from database.conexiones import ConfigImpresoras


class ImpresionService:
    def __init__(self, config_manager: ConfigManager, ingreso_svc: IngresoService | None = None):
        self._cm = config_manager
        self._ingreso_svc = ingreso_svc

    def _sucursales_excluidas(self) -> set[str]:
        raw = self._cm.impresion.sucursales_excluidas
        return {s.strip() for s in raw.split('\n') if s.strip()}

    def _agrupar_por_destino(self, ingreso: Ingreso) -> list[dict]:
        excluidas = self._sucursales_excluidas()
        destinos: dict[str, dict] = {}
        for remito in ingreso.remitos:
            for recepcion in remito.recepciones:
                clave = recepcion.sucursal_destino
                if clave in excluidas:
                    continue
                if clave not in destinos:
                    destinos[clave] = {
                        'destino': recepcion.nombre_destino,
                        'sucursal': clave,
                        'total_bultos': 0,
                        'remitos': [],
                    }
                if remito not in destinos[clave]['remitos']:
                    destinos[clave]['remitos'].append(remito)
                    destinos[clave]['total_bultos'] += remito.cantidad_bultos
        return list(destinos.values())

    def _tiene_destino_no_excluido(self, remito: Remito, excluidas: set[str]) -> bool:
        return any(rp.sucursal_destino not in excluidas for rp in remito.recepciones)

    def _total_bultos(self, ingreso: Ingreso) -> int:
        excluidas = self._sucursales_excluidas()
        return sum(
            r.cantidad_bultos for r in ingreso.remitos
            if self._tiene_destino_no_excluido(r, excluidas)
        )

    def _prox_num_remito(self) -> tuple[str, int]:
        cfg = self._cm.impresion
        num = cfg.prox_numero_remito
        pv = ''.join(ch for ch in (cfg.punto_venta or '') if ch.isdigit()).zfill(5)
        if pv:
            return f'{pv} - {num:08d}', num
        return f'{num:08d}', num

    def _incrementar_num_remito(self):
        cfg = self._cm.impresion
        cfg.prox_numero_remito += 1
        self._cm.save_impresion_config(cfg)

    def _obtener_o_generar_num_remito(self, ingreso: Ingreso, destino: dict,
                                      reimprimir: bool = False) -> str:
        """Asigna y registra el número del remito generado.

        La numeración es exclusiva de esta aplicación: punto de venta
        propio + secuencia. En reimpresión se reutiliza el número ya
        asignado para ese ingreso y destino.
        """
        clave = destino.get('sucursal', '') or destino.get('destino', '')
        if not self._ingreso_svc:
            return ''
        try:
            existente = self._ingreso_svc.obtener_remito_generado(
                ingreso.id_ingreso, clave
            )
            if existente:
                return existente
        except Exception:
            pass
        if reimprimir:
            return ''
        num_str, _ = self._prox_num_remito()
        try:
            self._ingreso_svc.guardar_remito_generado(
                ingreso.id_ingreso, num_str, clave
            )
        except Exception:
            return ''
        self._incrementar_num_remito()
        return num_str

    def _abrir_pdf(self, filepath: str):
        if os.path.exists(filepath):
            os.startfile(filepath)

    def _imprimir_pdf_qt(self, filepath: str, printer_name: str) -> bool:
        """Imprime el PDF sin depender del visor de PDF instalado en el equipo.

        Renderiza cada página con PyMuPDF y la envía a la impresora vía QPrinter.
        """
        import pymupdf
        from PyQt5.QtCore import Qt, QRect
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtPrintSupport import QPrinter, QPrinterInfo

        info = next(
            (p for p in QPrinterInfo.availablePrinters() if p.printerName() == printer_name),
            None,
        )
        if info is None:
            return False

        printer = QPrinter(info, QPrinter.HighResolution)
        printer.setFullPage(True)
        printer.setDocName(os.path.basename(filepath))

        dpi = 300
        with pymupdf.open(filepath) as doc:
            if doc.page_count == 0:
                return False
            painter = QPainter()
            if not painter.begin(printer):
                return False
            try:
                for i, page in enumerate(doc):
                    if i > 0:
                        printer.newPage()
                    pix = page.get_pixmap(dpi=dpi, alpha=False)
                    img = QImage(pix.samples, pix.width, pix.height,
                                 pix.stride, QImage.Format_RGB888).copy()
                    area = painter.viewport()
                    size = img.size().scaled(area.size(), Qt.KeepAspectRatio)
                    painter.drawImage(QRect(area.x(), area.y(), size.width(), size.height()), img)
            finally:
                painter.end()
        return True

    def _imprimir_pdf(self, filepath: str, printer_name: str):
        try:
            if self._imprimir_pdf_qt(filepath, printer_name):
                return
        except Exception:
            pass
        try:
            import win32api
            win32api.ShellExecute(
                0, "printto", filepath,
                f'"{printer_name}"', None, 0,
            )
        except Exception:
            self._abrir_pdf(filepath)

    def _procesar_pdf(self, filepath: str, printer_name: str):
        if not printer_name:
            self._abrir_pdf(filepath)
        else:
            self._imprimir_pdf(filepath, printer_name)

    def generar_remito(self, ingreso: Ingreso, destino: dict, impresora_override: str = '',
                       reimprimir: bool = False) -> str | None:
        cfg = self._cm.impresoras
        printer = impresora_override or cfg.impresora_remitos
        if not printer:
            return None
        try:
            remito_str = self._obtener_o_generar_num_remito(
                ingreso, destino, reimprimir
            )
            filepath = pdf_remito(
                ingreso, destino,
                self._cm.impresion, cfg,
                remito_str,
            )
            copias = cfg.copias_remitos or 1
            for _ in range(copias):
                self._procesar_pdf(filepath, printer)
            return filepath
        except Exception:
            return None

    def _usar_direct_protocol(self, printer: str) -> bool:
        """La Honeywell PC42t habla Direct Protocol (DP): etiqueta por comandos."""
        low = (printer or '').lower()
        return 'honeywell' in low or 'pc42' in low

    def generar_etiquetas(self, ingreso: Ingreso, destino: dict, impresora_override: str = '',
                          reimprimir: bool = False) -> str | None:
        cfg = self._cm.impresoras
        printer = impresora_override or cfg.impresora_etiquetas
        if not printer:
            return None
        try:
            num_remito = self._obtener_o_generar_num_remito(
                ingreso, destino, reimprimir
            )
            if self._usar_direct_protocol(printer):
                cant = imprimir_etiquetas_dp(
                    ingreso, destino, cfg, self._cm.impresion, printer, num_remito
                )
                return f'DP:{printer}:{cant}'
            filepath = pdf_etiquetas(ingreso, destino, cfg, self._cm.impresion, num_remito)
            self._procesar_pdf(filepath, printer)
            return filepath
        except Exception:
            return None

    def imprimir_documentos(self, ingreso: Ingreso) -> tuple[list[str], list[str]]:
        exitos = []
        errores = []

        destinos = self._agrupar_por_destino(ingreso)
        for destino in destinos:
            r = self.generar_remito(ingreso, destino)
            if r:
                exitos.append(f'Remito → {destino["destino"]}')
            else:
                errores.append(f'Remito → {destino["destino"]}')

            e = self.generar_etiquetas(ingreso, destino)
            if e:
                exitos.append(f'Etiquetas → {destino["destino"]} ({destino["total_bultos"]} bultos)')
            else:
                errores.append(f'Etiquetas → {destino["destino"]}')

        return exitos, errores

    def imprimir_remitos(self, ingreso: Ingreso, impresora_override: str = '',
                         reimprimir: bool = False) -> tuple[list[str], list[str]]:
        exitos = []
        errores = []
        destinos = self._agrupar_por_destino(ingreso)
        for destino in destinos:
            r = self.generar_remito(ingreso, destino, impresora_override, reimprimir)
            if r:
                exitos.append(f'Remito → {destino["destino"]}')
            else:
                errores.append(f'Remito → {destino["destino"]}')
        return exitos, errores

    def imprimir_etiquetas(self, ingreso: Ingreso, impresora_override: str = '',
                           reimprimir: bool = False) -> tuple[list[str], list[str]]:
        exitos = []
        errores = []
        destinos = self._agrupar_por_destino(ingreso)
        for destino in destinos:
            e = self.generar_etiquetas(ingreso, destino, impresora_override, reimprimir)
            if e:
                exitos.append(f'Etiquetas → {destino["destino"]} ({destino["total_bultos"]} bultos)')
            else:
                errores.append(f'Etiquetas → {destino["destino"]}')
        return exitos, errores

    def imprimir_etiquetas_mateti(self, materiales: list[dict]) -> str | None:
        cfg = self._cm.impresoras
        filepath = generar_pdf_etiquetas_mateti(materiales, cfg)
        if not filepath:
            return None
        printer = cfg.impresora_etiquetas_mateti or cfg.impresora_etiquetas
        self._procesar_pdf(filepath, printer)
        return filepath
