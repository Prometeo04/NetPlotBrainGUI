# NetPlotBrain GUI — v7.0

Interfaz gráfica (tkinter) para la librería [netplotbrain](https://github.com/wiheto/netplotbrain),
para visualizar redes cerebrales en 3D sin escribir código.

## Novedades de la v7

- **Interfaz sobria, completamente en español** (antes mezclaba inglés y español, con estética arcade).
- **Importar/exportar tablas en más formatos:** CSV, TSV, Excel (`.xlsx`, `.xlsm`, `.xls`) para nodos
  y aristas, con reconocimiento de nombres de columna en español o en inglés (`comunidad`/`community`,
  `peso`/`weight`, etc.) y aviso si el archivo no trae encabezados.
- **Vista previa esquemática en tiempo real:** tres paneles (sagital, coronal, transversal) que se
  actualizan mientras escribes coordenadas de un nodo. Es una ilustración aproximada, no el template real.
- **Esferas y círculos del mismo tamaño visual.** En la v6, una esfera con los mismos parámetros que un
  círculo se dibujaba mucho más grande; ahora se calibra el radio para que ambos tipos de nodo se vean
  equivalentes.
- **Indicador de progreso durante la descarga o el render.** La figura se genera en un hilo aparte, así
  que la ventana ya no se congela mientras se descarga un template o se calcula el plot.
- **Detección de recursos del equipo (RAM y GPU).** Si detecta poca memoria libre o una tarjeta gráfica
  integrada con un estilo exigente (`glass`, `filled`), avisa antes de renderizar y ofrece:
  - Ajustar automáticamente el estilo/voxel size a una combinación más liviana, o
  - Abrir **Google Colab** o **Binder** (ambos gratuitos) como alternativa en la nube.
  No se ofrece un servicio de nube propio: son enlaces a servicios públicos existentes.
- **Librerías congeladas** en `requirements_v7.txt`, generadas con `pip freeze` desde un entorno donde
  el programa fue probado, para reducir problemas de compatibilidad entre versiones.

## Instalación

```
pip install -r requirements_v7.txt
python netplotbrain_gui_v7.py
```

En Windows también puedes correr `python setup_v7.py`, que instala las dependencias y crea un acceso
directo en el escritorio.

Requiere Python 3.9–3.12. NumPy debe quedar por debajo de 2.0 (netplotbrain aún no es compatible con
NumPy 2.x); el setup y el requirements ya lo fijan así.

## Estructura de los datos

- **Nodos:** tabla con columnas `x, y, z` (coordenadas en milímetros, espacio MNI) y, opcionalmente,
  `comunidad` (para el color) y `centralidad` (para el tamaño). También puedes cargar un NIfTI de
  parcelación o un atlas de TemplateFlow.
- **Aristas:** tabla con columnas `i, j, peso` (índices de nodo y peso de la conexión), o una matriz de
  adyacencia cuadrada en CSV, Excel o `.npy`.
- **Template:** el cerebro de fondo. Puede ser un nombre de TemplateFlow (se descarga automáticamente la
  primera vez) o un archivo NIfTI propio.

## Pendientes conocidos

- Las edades de los cohortes `MNIInfant` de TemplateFlow no están confirmadas; revísalas contra la
  documentación oficial de TemplateFlow antes de usarlas en una figura para publicación.
- No se ha probado la detección de RAM/GPU en Windows (solo en Linux).
- El render con el estilo `glass` sigue siendo pesado sin GPU dedicada; el aviso de recursos lo
  advierte, pero la calidad final depende del equipo.

## Autor

Jesús Manuel Segovia Luna ([Prometeo04](https://github.com/Prometeo04))
