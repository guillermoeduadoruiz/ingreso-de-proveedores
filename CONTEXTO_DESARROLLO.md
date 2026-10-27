# CONTEXTO_DESARROLLO

Snapshot de conocimiento del desarrollo para retomarlo con opencode (o cualquier entorno) sin perder contexto. **Leer este archivo completo al retomar el proyecto.**

Actualizado: 2026-09-17

---

## 1. Qué es el proyecto

Aplicación de escritorio **Windows-only** en **PyQt5** (UI en español) que registra las recepciones de mercadería / ingresos de proveedores en un depósito y genera documentos:

- **Remito** (A4 con preimpreso: se **superpone** texto sobre un formulario preimpreso escaneado; coordenadas en mm medidas a 300 dpi).
- **Etiquetas** (hoja de etiquetas con dimensiones configurables) con QR de trazabilidad.
- Dos apps en un paquete:
  - `ingresos_proveedores/` → app principal. Entrypoint `ingresos_proveedores/main.py` (login → `VentanaPrincipal`).
  - `configurador/main.py` → herramienta de setup independiente que reutiliza el paquete (DB, impresoras, etiquetas).

No hay web framework, ni tests, ni CI, ni linter configurado. Python 3.13 en `.venv`.

## 2. Arquitectura / capas

```
config/   → ConfigManager (config_setup.json, secretos cifrados)
database/ → conexiones (dataclasses SQLServer/MySQL/impresoras), clientes MySQL y SQL Server
modelos/  → dataclasses (Ingreso, Remito, RecepcionPrevista, Proveedor)
servicios/ → lógica de negocio (ingreso_svc, recepcion_svc, impresion_svc, pdf_generator)
ui/       → ventanas y diálogos PyQt5 (ventana_principal, registro_ingreso, consulta_*, etc.)
```

Flujo principal (3 pasos): Seleccionar Recepciones → Ingresar Remitos → Confirmar y Registrar.
Al confirmar, `RegistroIngresoWidget._confirmar` llama `impresion_svc.imprimir_documentos(ingreso)`, que por cada **destino** agrupado genera remito + etiquetas: PDF en `pdfs/remitos/<id>_<suc>.pdf` y `pdfs/etiquetas/<id>_<suc>_etiquetas.pdf`, y luego imprime (o abre con `os.startfile` si no hay impresora).

## 3. Ejecutar (desde la raíz del repo)

```
.venv\Scripts\python.exe ingresos_proveedores\main.py
.venv\Scripts\python.exe configurador\main.py
```

Importantes:
- Ambos entrypoints insertan `ingresos_proveedores/` en `sys.path` → los imports son planos (`from config.config_manager import ...`). **No ejecutar módulos sueltos desde dentro de `ingresos_proveedores/`** (rompe los imports relativos).
- `configurador/main.py` debe correrse SIEMPRE desde la raíz (calcula `BASE_DIR` desde su propia ubicación).

## 4. Configuración y secretos

- `config_setup.json` en la raíz (ruta resuelta por `utils/paths.py`). Contiene **credenciales reales de servidores internos**: no exponer en commits.
- Passwords de DB están con prefijo `$ENC$` (cifrado con key derivada de la máquina, PBKDF2; salt en `%APPDATA%\IngresosProveedores\.salt`). No editar a mano un password cifrado en el JSON: usar `utils.crypto.encrypt_password`.
- Hash del password de desbloqueo: `%APPDATA%\IngresosProveedores\.config_pass`.
- Config de impresoras: hay **múltiples configs** en `impresoras.configs` (p.ej. `WorkConfig` y `desarrollo`), con una activa (`impresoras.activa`). Actualmente activa: `desarrollo` (impresoras = "Microsoft Print to PDF").

## 5. Bases de datos

Hay DOS bases y la app necesita AMBAS alcanzables:

- **SQL Server** (pyodbc): recepciones previstas y datos de clientes/proveedores. Requiere ODBC Driver 17/18 instalado (auto-resuelto por `DRIVER_PRIORITY` en `database/conexiones.py`).
- **MySQL** (pymysql): persiste ingresos, remitos, recepciones y `ingresoscd_remitos_generados` (numeración + estado de remitos generados).

## 6. Compilación / distribución

Dos scripts (ambos borran `build/` y `dist/` primero):
- `build_dist.bat` → copia portable de fuente con `.bat` lanzadores.
- `build_exe.bat` → PyInstaller desde `IngresosProveedores.spec` + `Configurador.spec`.

**Si se agrega un módulo nuevo hay que registrarlo en AMBOS**: lista `copy` de `build_dist.bat` Y `hiddenimports` del `.spec` correspondiente, o faltará en el build.

## 7. Generación de remitos y etiquetas — comportamiento actual (CRÍTICO)

- `_agrupar_por_destino` agrupa los remitos del ingreso por `sucursal_destino` de sus recepciones, **descartando las sucursales listadas en `impresion.sucursales_excluidas`** (separadas por nueva línea).
- Por cada destino no excluido se genera remito + etiquetas.
- **Comportamiento deliberado (2026-09-14):** si TODAS las recepciones caen en sucursales excluidas, `imprimir_documentos` no genera nada y **no muestra ninguna advertencia** (listas de éxito y error vacías). Se decidió no avisar; la exclusión es silenciosa a propósito.
- La exclusión actual es `CCU9999029` (depósito/central). Si en el futuro quieren que esa sucursal SÍ genere documentos, hay que sacarla de `sucursales_excluidas` (en `Configurador` o `config_impresion_dialog.py`).
- Numeración de remito: `"{punto_venta:05} - {seq:08}"` (ej: `00222 - 00000035`), guardada por `(id_ingreso, destino)` en `ingresoscd_remitos_generados`; se reutiliza en reimpresión. Siguiente número en `impresion.prox_numero_remito`.
- **Impresión (2026-09-15):** TODAS las configs imprimen por `ShellExecute("printto", pdf, printer)` (el visor de PDF de Windows/Edge renderiza y el **driver** convierte a PCL). No hay diálogo salvo que la impresora destino sea "Microsoft Print to PDF" (que por diseño pide guardar). ⚠️ **No usar spool RAW (`win32print` `WritePrinter` datatype `RAW`)**: los drivers v4 modernos (HP UPD PCL6 / class drivers) no aceptan jobs RAW y quedan **trabados en la cola sin imprimir** (probado con HP LaserJet MFP M630).
- **Etiquetas Honeywell PC42t (2026-09-17):** cuando la impresora de etiquetas es una **Honeywell PC42** (nombre contiene "honeywell"/"pc42"), la etiqueta se genera como stream **Direct Protocol (DP)** (`servicios/dp_generator.py`) y se envía por **RAW** a la cola de Windows (`WritePrinter`, datatype RAW) — decisión del usuario, a pesar de la advertencia de arriba (los drivers de Honeywell USB toleran RAW; si una job queda trabada en la cola, el driver no acepta passthrough y hay que replantear transporte TCP 9100). El resto de casos sigue por PDF. El contenido de la etiqueta replica el del PDF (mismo payload exacto del QR, con saltos de línea encodados como `CHR$(13)`), NASC 1252, fuentes `Swiss 721 BT`/`Swiss 721 Bold BT`, QR `BARSET "QRCODE",1,1,module(modelo 2),2,4`. El detalle del módulo del QR depende de la unidad de etiqueta (100x150 mm en WorkConfig). Si se agrega otro módulo de impresión, registrarlo en `build_dist.bat` y `IngresosProveedores.spec`.
- **Dos impresiones por etiqueta (2026-09-17):** cada etiqueta física se divide en dos impresiones idénticas apiladas (arriba/abajo) para poder cortar y conservar una copia. Constante `IMPRESIONES_POR_ETIQUETA = 2` en `pdf_generator.py` y `dp_generator.py`. En DP el layout se dibuja completo y se emite **un único `PF` por etiqueta física** (antes era uno por impresión); si se emitiera `PF` por impresión, cada mitad saldría en una etiqueta distinta. El PDF usa tipografía/espaciado compacto para que cada impresión entre en la mitad de alto (~75 mm en WorkConfig); en configs de etiqueta bajas (p.ej. `desarrollo` 60 mm) las dos impresiones no entran y el contenido se solapa.
- **Calibración cabezal PC42t (2026-09-22):** en impresión real, el cabezal de la Honeywell PC42t no arranca a imprimir en el borde físico izquierdo de la etiqueta; el texto quedaba cortado. Se subió `margen_izquierdo_etiquetas` de `WorkConfig` (`config_setup.json`) de 5 a 20 mm (y el fallback en `dp_generator.py` de `or 5.0` a `or 20.0`) para correr todo el contenido ~15 mm a la derecha. `_etiqueta_unica` ahora calcula el ancho útil como `ancho_mm - marg_l_mm - marg_r_mm` (antes el margen derecho ni se leía de `cfg` y la zona del QR se achicaba sola al subir el margen izquierdo); el título y la regla se centran/miden sobre ese ancho útil, y el contador `idx/total` usa `margen_derecho_etiquetas` en vez de reutilizar el izquierdo. Si en una próxima impresión el corte persiste o cambia de lado, ajustar `margen_izquierdo_etiquetas`/`margen_derecho_etiquetas` en `config_setup.json` (perfil `WorkConfig`) en vez de tocar las fórmulas.
- **Orden de campos en la etiqueta (2026-09-22):** por pedido del usuario, con el desplazamiento de 20 mm ya correcto, se reordenó el bloque: título `CUSPIDE SAU` → **todos los datos del destinatario** (Dest, Suc, Dom, CP/Ciudad, Distrito/Trans) → **nombre del proveedor** → resto del layout sin cambios. Aplicado a la vez en `pdf_generator.py` (`_draw_etiqueta`) y `dp_generator.py` (`_etiqueta_unica`) para mantener paridad de contenido.
- **Paridad de diseño PDF ↔ DP (2026-09-22):** por pedido del usuario, la etiqueta física (DP/Honeywell) debe repetir exactamente el diseño del PDF. Se alinearon en `dp_generator._etiqueta_unica`: el campo Distrito y Trans pasan a una sola línea (como en el PDF) y la lista de OC pasa de una columna a la **grilla monoespaciada del PDF** (etiqueta "OC:" como primera celda, columnas calculadas por ancho, truncado "+N mas"), usando la fuente residente **`Andale Mono`** (la PC42t no trae Courier; Andale Mono es su equivalente monoespaciada residente, confirmado en el datasheet/manual del usuario). Se hoisteó `text_w_mm` para reutilizar el ancho de la zona de texto en la grilla y en el QR. Bug fijado: el `for idx` de la grilla pisaba el `idx` del contador `idx/total` → renombrado a `i`.
- **⚠️ Pruéba real PC42t: `Andale Mono` NO va (2026-09-22).** Aunque el datasheet la lista como fuente residente, al usarla en el grid de OC el job DP/Raw falló en la impresora (LED de error). Se revirtió la grilla a **`Swiss 721 BT`** (Ya probada en la unidad); las columnas se alinean igual porque todos los códigos OC tienen el mismo largo. Si en el futuro se quiere monoespaciado, probar primero en la PC42t con una etiqueta de test.
- **✅ Eje vertical de `PP` invertido — CONFIRMADO en impresora real (2026-09-22/23).** El wrapper `_yp` de abajo funcionó: el usuario confirmó "el formato general está perfecto" tras probarlo. La hipótesis (fila de `PP` creciente hacia arriba, no hacia abajo, en esta PC42t) queda validada. Tras subir el margen izquierdo y bajar el superior, el usuario reportó dos veces que "CUSPIDE SAU" seguía saliendo **al pie de la etiqueta** en vez de arriba (pese a ser el primer elemento dibujado, con la y lógica más chica). Como un ajuste de `margen_superior_etiquetas` de pocos mm no explica un salto de "arriba" a "al pie", la hipótesis de trabajo es que la fila (segundo argumento de `PP x,y`) en esta PC42t crece **hacia arriba** en vez de hacia abajo (contrario a lo asumido/documentado en el punto anterior). Fix aplicado en `_etiqueta_unica`: toda la lógica interna se dejó igual (y lógica: 0 = arriba de la etiqueta, creciente = hacia abajo), y se agregó un wrapper `_yp(y_log) = alto_mm_en_dots - y_log` que se aplica recién al emitir cada comando `PP` (título, `_ptr`, grilla OC, QR, "Muelle:", contador `idx/total`). Esto preserva el orden relativo ya afinado (título primero, contador al final) sin tener que reescribir cada fórmula de posición. **Sin validar en impresora real todavía** — si tras esto el título sigue mal ubicado (o el resto del layout ahora queda invertido), la hipótesis es incorrecta y hay que revisar de nuevo con una etiqueta de test mínima (ver scripts `round_*_dp.py` en `%TEMP%\opencode`).
- **Desplazamientos finos de calibración (2026-09-22):** además del margen izquierdo (20 mm) y superior (3 mm) de `WorkConfig`, se agregaron dos constantes en `_etiqueta_unica`: `TEXT_SHIFT_MM = 7.0` (todo el texto, título incluido, se corre 7 mm a la izquierda respecto de `marg_l_mm`; bajado de un primer intento de 10 mm) y `QR_SHIFT_MM = 7.0` (el QR se corre 7 mm a la derecha respecto de su posición calculada). El QR usa `marg_l_mm` sin el `TEXT_SHIFT_MM`, así que estos dos desplazamientos son independientes entre sí.
- **Ajustes finos de layout post-validación (2026-09-23).** Con el formato general ya confirmado OK, 5 retoques en `_etiqueta_unica`: (1) **QR movido a la esquina inferior izquierda**, mismo tamaño (`qr_size_mm` sin cambios): `qx = x0` (alineado con el margen del texto) y `qy = alto_mm - 6mm - qr_size_mm` (colchón de 6 mm respecto del pie, el mismo que ya usaba la grilla de OC). Se eliminó `QR_SHIFT_MM` (quedó obsoleto, el QR ya no comparte referencia con el texto). (2) **"Muelle: ..." pasa a mostrarse ARRIBA del QR** (antes iba debajo): `my = qy - hueco - alto_de_línea`. (3)/(4) **bloque de "Proveedor" (+ fecha y remito) y bloque de "Remitente" bajados 15 mm cada uno** (dos `y += _dots(15.0)` insertados antes de cada sección; como el diseño fluye de arriba hacia abajo, todo lo que sigue después de cada bloque se corre en cadena, es el comportamiento esperado). (5) **Letra del destinatario** (Dest/Suc/Dom/CP-Ciudad/Distrito-Trans) subida de `FS` a `FS+1` (8→9pt). Efecto colateral corregido: como el QR ahora ocupa la misma columna izquierda que el texto (antes estaba a la derecha, en una zona separada), el cálculo de `qr_size_mm`/`qx`/`qy` se **adelantó (hoisteó) antes de la grilla de OC**, y el límite inferior de la grilla (`min_y`) ahora resta el alto del QR + el hueco de "Muelle:" cuando hay QR, para que la grilla de códigos OC no se dibuje encima del QR. Sin validar en impresora real todavía.
- **Segunda ronda de ajustes tras el QR en esquina inferior (2026-09-23).** (1) `TEXT_SHIFT_MM` subido de 7 a 12 mm (interpretado como ajuste incremental sobre el valor ya confirmado, no un reemplazo — a diferencia de la ronda anterior donde "7 mm" reemplazó a "10 mm" porque el valor previo *todavía no estaba confirmado*). (2) Pedido "bajar el QR 20 mm": con `qr_size_mm` (~33 mm) y el colchón de 6 mm que tenía respecto del pie, un corrimiento de 20 mm completo lo hubiera mandado ~14 mm fuera de la etiqueta (150 mm de alto) — se avisó al usuario y se aplicó solo un máximo seguro de 4 mm (`QR_DOWN_MM`), dejando 2 mm de colchón.
- **QR: posición exacta pedida por el usuario (2026-09-23).** Reemplaza el ajuste anterior (`QR_DOWN_MM`): el usuario pidió el borde inferior del QR a **exactamente 5 mm** del borde inferior físico de la etiqueta, manteniendo `qx = x0` (margen izquierdo sin cambios). Fórmula directa en `_etiqueta_unica`: `qy = _dots(alto_mm - 5.0 - qr_size_mm)` (el borde superior del QR, que tras `_yp` es `5 + qr_size_mm` mm físicos desde el pie; restando `qr_size_mm` da el borde inferior exacto en 5 mm). Verificado con un dump de coordenadas (`geo_real.py`-style, fuera de la impresora): borde inferior del QR en 5.0 mm, sin coordenadas fuera de 100×150 mm. Sin validar en impresora real todavía.
- **Paridad reimpresión ↔ impresión original (2026-09-22):** revisada la acción de reimprimir en `consulta_ingresos._reimprimir`. El único punto divergente era el número de remito de cross-docking: `imprimir_remitos(...)` ya pasaba `reimprimir=True` (reutiliza el número guardado, nunca crea uno nuevo), pero `imprimir_etiquetas(...)` NO lo pasaba → `_obtener_o_generar_num_remito` (con `reimprimir=False` por defecto) creaba un número NUEVO y avanzaba la secuencia si el guardado había fallado en la impresión original (issue del punto 9.4), saliendo las etiquetas reimpresas distintas a las originales. Se agregó el parámetro `reimprimir` a `ImpresionService.generar_etiquetas` e `imprimir_etiquetas`, y `_reimprimir('etiquetas')` ahora pasa `reimprimir=True`. Con esto ambos reprints usan exactamente la misma lógica: si hay número guardado lo reutilizan (idéntico al original); si no lo hay, imprimen sin número y sin avanzar la secuencia. La impresión original (registro) conserva `reimprimir=False`.
- **Tamaños de fuente DP ↔ PDF (2026-09-22):** en la impresión real el texto de la etiqueta DP salía visiblemente más grande que el PDF de referencia (ej. "Proveedor:" 13pt en DP vs 9pt en el PDF, "Dest:"/"Suc:" 11pt vs 7.5pt). Se agregó `FS = 8` en `_etiqueta_unica` (equivalente al `font_size = 7.5` del PDF, redondeado a entero) y todos los tamaños de campo se recalcularon en base a `FS` (`FS`, `FS±1`, etc.). Se dejaron sin tocar el título (18pt, ya coincidía) y las dos reglas separadoras (fijas en 9pt: es el combo 30 guiones@9pt verificado en la PC42t, no tocar).
- **Calibración fina post-impresión real (2026-09-22):** dos ajustes reportados tras imprimir en la PC42t con los cambios de arriba: (1) el título salía con un espacio en blanco arriba en vez de pegado al borde superior → se bajó `margen_superior_etiquetas` de `WorkConfig` de 10 a 3 mm (y el fallback en `dp_generator.py` de `or 10.0` a `or 3.0`); a confirmar en la próxima impresión si hace falta afinarlo más (subir o bajar). (2) el texto (no el QR) tenía que correrse 10 mm más a la izquierda → se agregó `TEXT_SHIFT_MM = 10.0` en `_etiqueta_unica`: `x0`/`x_centro` (arranque del texto y centrado del título) restan ese valor, pero `usable_w_mm`/`text_w_mm` (de los que depende la posición del QR) siguen calculados sobre el `marg_l_mm` original, así que el QR no se mueve.
- **⚠️ BLOCKER: job DP completo de etiquetas siempre termina en LED rojo (2026-09-22, sin resolver).** En impresión real en la Honeywell PC42t (driver RAW), el job completo de 3 etiquetas (≈70 comandos) **entra en modo error (LED rojo parpadeante) y no imprime**. Se aisló por eliminación de elementos (script por script de 2-4 líneas a la impresora): TODO elemento por separado imprime en verde (título, QR `BARSET/PB` corto y multilínea, reglas, contador, grilla, textos de 40+ chars, `AN 8` solo, `AN 9` solo). Lo que se confirmó rojo: cadenas PT de 44 chars (`44@7` y `44@9`; 42 OK), y `AN 8`+`AN 9` juntos en el mismo label (Q14: 4 campos → rojo; cada AN solo → verde). **Cambios aplicados en `dp_generator.py` (compilados, NO validadas end-to-end):** (1) `MAX_PT_LEN = 40` y `_ptr` trunca todo texto PT a ≤40; (2) reglas de separación 30 guiones a 9pt (era 44 a 7pt); (3) **eliminados `AN 8`/`AN 9`** → centrado/der.-alineado por cálculo con la nueva `_est_ancho_dots` (título, "Muelle:", contador); (4) eliminada `_pt_ajustado` (sin uso). Aun con todos esos cambios, el job de 3 etiquetas SIGUE dando rojo de entrada. Patrón observado: todo job con 1 etiqueta / ≤ ~12 comandos imprimió; todo job con 3 etiquetas / ~70 comandos falló (también 1 etiqueta completa ~22 campos nunca se testó aislada). Hipótesis pendiente: límite del firmware de la PC42t por **cantidad de campos/comandos por job o por formulario** (queda por testear job de 1 etiqueta completa: script `round_single_dp.py` en Temp). 🔁 **Al retomar:** probar ese script; si 1 etiqueta completa imprime, separar el envío en un job por etiqueta (o investigar límite de campos); si no, reducir campos del label o evaluar el camino PDF/driver Windows (la PC42t tiene driver instalado) en vez de DP. Recordatorio: cada job en rojo deja la impresora trabada hasta apagar ~5s; scripts de diagnóstico en `%TEMP%\opencode` (`round_q_dp.py`, `round_q2_dp.py`, `round_q3_dp.py`, `round_q4_dp.py`, `round_full_dp.py`, `round_single_dp.py`, `valida_cap.py`).
- **LED rojo antes de la 2ª etiqueta (2026-09-24):** reportado en reimpresión con varios bultos (la 1ª sale, antes de la 2ª la PC42t pasa a error) y la impresión original siguiente no emitió nada (la impresora queda trabada en error hasta apagarla, y los jobs que llegan mientras tanto no salen). Causa probable: en la PC42t el campo `PT` crece hacia arriba desde su `PP`; el título (18pt, `TITULO_Y_MM = 3`) quedaba con su caja hasta ~153,4 mm en una etiqueta de 150 mm → imagen más larga que la etiqueta → la impresora pierde el gap y falla al buscar la siguiente (explica también el blocker de "1 etiqueta OK / 3 etiquetas rojo"). Fix en `_render_dp`: cada `PP` de texto se limita para que la caja termine a `ETQ_TOPE_SUP_MM = 1.0` mm del borde (en la práctica, solo el título baja ~4,4 mm). Tope máximo verificado offline: 149,0 mm. **Sin validar en impresora real todavía.**
- **Transporte en línea propia (2026-09-24):** en el bloque destinatario, `Trans:` pasa a una línea nueva debajo de `Distrito:` (antes iban juntos separados por " - "). Cambio en `layout_etiqueta`, así que aplica a DP y PDF. El bloque termina a 40,9 mm, sin pisar "Proveedor" (50 mm).
- **LED rojo, 2ª prueba (2026-09-24):** con `ETQ_TOPE_SUP_MM = 1.0` (máx. 149 mm) una reimpresión de 3 etiquetas imprimió las 3, pero la impresora entró en error justo después de la 3/3. Se interpreta como desfase acumulado: la zona útil real es menor a 150 mm, así que cada etiqueta se pasa 1-2 mm y en la 3ª ya no encuentra el gap. Se subió `ETQ_TOPE_SUP_MM` a 5.0 (máx. 145 mm) y la regla bajo el título se bajó 1,5 mm para no tocar el título, que ahora queda más abajo. Si el error persiste (aunque sea más tarde), probar calibrar el medio en la PC42t o subir más el tope; si vuelve igual, descartar la hipótesis con un job de 3 etiquetas con un solo texto centrado.
- **MATETI: LED rojo tras 2-3 etiquetas (2026-10-27).** Mismo patrón que el anterior pero por driver Windows (PDF → QPrinter): cada página medía exactamente `alto_etiqueta_mateti` (25 mm), así que cualquier avance de más se acumulaba y la PC42t perdía el gap a las 2-3 filas (al azar). Fix en `generar_pdf_etiquetas_mateti`: la página ahora mide `alto_etiqueta_mateti - margen_inferior_etiquetas_mateti` (23 mm con WorkConfig) y la altura del código de barras se calcula para que el contenido entre en ese alto. Si el error persiste, subir `margen_inferior_etiquetas_mateti` (3-4 mm) y/o recalibrar el medio en la PC42t. **Sin validar en impresora real todavía.**

## 8. Estado actual del trabajo

- Un solo commit en git: `aff527c Primer commit: versión inicial del proyecto`.
- **Hay muchísimos archivos modificados y sin commitear** (todo el desarrollo de "preimpreso" de remitos, numeración, consulta de destinatarios, etc.). Ver `git status` antes de commitear; no hay `.gitignore`, así que `build/`, `dist/`, `pdfs/` y `__pycache__/` están trackeados. Stagear solo lo intencional.
- Archivos agregados sin commitear: `AGENTS.md`, `ui/consulta_destinatarios.py`, PDFs generados bajo `pdfs/`, etc.
- El desarrollo actual se basa en que el remito es un **formulario preimpreso** estilo factura: el PDF solo dibuja encima (fecha, cliente, proveedor, filas de remito, flete, QR). Las opciones de márgenes/orientación/tamaño de remito quedaron **decorativas** (no se usan).

## 9. Problemas conocidos / mejoras pendientes (identificados en investigación)

1. **Errores tragados:** `ImpresionService.generar_remito` / `generar_etiquetas` hacen `except Exception: return None` → el usuario ve un fallo genérico, nunca el traceback real. Ideal: devolver/loggear la excepción real.
2. **La generación requiere impresora:** si `impresora_remitos`/`impresora_etiquetas` está vacía, NO se genera el PDF (retorna None antes). Convendría generar el PDF siempre y solo imprimir si hay impresora.
3. **Reimpresión sin número guardado** genera remito sin número (y el QR sin `REM:`).
4. Si falla el guardado del número en MySQL se genera un remito sin numerar y la secuencia no avanza (aparece como éxito).
5. Bug de redondeo en `_fmtv` de `pdf_generator.py` (`round()` puede dar 100 → imprime `$10.100`). Raro pero posible.
6. UI se congela durante generación/impresión (corre en el hilo principal).
7. No hay `.gitignore`.
8. `consulta_ingresos.py` accede a `impresion_svc._cm` (atributo privado de otro objeto).

## 10. Comandos de verificación útiles

- Compilar sintaxis: `.venv\Scripts\python.exe -m py_compile <archivo>.py`
- Reproducción de generación sin imprimir (fijando impresoras vacías): construir un `Ingreso` dummy y llamar a `servicios/pdf_generator.generar_remito/generar_etiquetas` directamente; verifica que el PDF se crea.
- Probar flujo real: `ConfigManager().load_config()` + `MySQLConnection(cm.mysql)` + `IngresoService` + `ImpresionService(cm, ing_svc)` y llamar `imprimir_documentos(ingreso_real)` con un `obtener_ingreso_completo(id)`.

## 11. Cómo restaurar este backup

1. Descomprimir en una máquina/proyecto nuevo.
2. Asegurar `.venv` con Python 3.13 e instalar `requirements.txt`.
3. Configurar drivers ODBC 17/18 y alcanzabilidad de SQL Server + MySQL (editar `config_setup.json` con los mismos valores, respetando el cifrado `$ENC$`).
4. Verificar `Activa` de impresoras según la máquina destino.