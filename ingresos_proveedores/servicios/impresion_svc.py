import os

from config.config_manager import ConfigManager
from modelos.ingreso import Ingreso
from modelos.remito import Remito
from servicios.pdf_generator import generar_remito as pdf_remito, generar_etiquetas as pdf_etiquetas
from database.conexiones import ConfigImpresoras


class ImpresionService:
    def __init__(self, config_manager: ConfigManager):
        self._cm = config_manager

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
        pref = cfg.prefijo_remito
        return f'{pref}{num:05d}', num

    def _incrementar_num_remito(self):
        cfg = self._cm.impresion
        cfg.prox_numero_remito += 1
        self._cm.save_impresion_config(cfg)

    def _abrir_pdf(self, filepath: str):
        if os.path.exists(filepath):
            os.startfile(filepath)

    def _imprimir_pdf(self, filepath: str, printer_name: str):
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

    def generar_remito(self, ingreso: Ingreso, destino: dict, impresora_override: str = '') -> str | None:
        cfg = self._cm.impresoras
        printer = impresora_override or cfg.impresora_remitos
        if not printer:
            return None
        try:
            remito_str, num = self._prox_num_remito()
            filepath = pdf_remito(
                ingreso, destino,
                self._cm.impresion, cfg,
                remito_str,
            )
            self._incrementar_num_remito()
            copias = self._cm.impresoras.copias_remitos or 1
            for _ in range(copias):
                self._procesar_pdf(filepath, printer)
            return filepath
        except Exception:
            return None

    def generar_etiquetas(self, ingreso: Ingreso, destino: dict, impresora_override: str = '') -> str | None:
        cfg = self._cm.impresoras
        printer = impresora_override or cfg.impresora_etiquetas
        if not printer:
            return None
        try:
            filepath = pdf_etiquetas(ingreso, destino, cfg, self._cm.impresion)
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

    def imprimir_remitos(self, ingreso: Ingreso, impresora_override: str = '') -> tuple[list[str], list[str]]:
        exitos = []
        errores = []
        destinos = self._agrupar_por_destino(ingreso)
        for destino in destinos:
            r = self.generar_remito(ingreso, destino, impresora_override)
            if r:
                exitos.append(f'Remito → {destino["destino"]}')
            else:
                errores.append(f'Remito → {destino["destino"]}')
        return exitos, errores

    def imprimir_etiquetas(self, ingreso: Ingreso, impresora_override: str = '') -> tuple[list[str], list[str]]:
        exitos = []
        errores = []
        destinos = self._agrupar_por_destino(ingreso)
        for destino in destinos:
            e = self.generar_etiquetas(ingreso, destino, impresora_override)
            if e:
                exitos.append(f'Etiquetas → {destino["destino"]} ({destino["total_bultos"]} bultos)')
            else:
                errores.append(f'Etiquetas → {destino["destino"]}')
        return exitos, errores
