# NetPlotBrain GUI — v9.0

Interfaz gráfica (tkinter) para la librería [netplotbrain](https://github.com/wiheto/netplotbrain),
para visualizar redes cerebrales en 3D sin escribir código.

## Novedades de la v9

- **Render en la nube (opcional), con tu propio servidor en Hugging Face Spaces.**
  La carpeta `nube/` contiene un pequeño servidor (FastAPI + Docker) que recibe los
  parámetros del render y devuelve la imagen. Se despliega gratis en un Space de
  Hugging Face (CPU Basic: 2 vCPU y 16 GB de RAM) y tiene una URL fija, así que no hay
  que copiar nada cada sesión. Se configura con el botón **Nube** de la cabecera:
  - **Automático:** cuando el estimador marca el render como pesado para tu equipo y hay
    un servidor configurado, el aviso te ofrece «Renderizar en la nube». Si la nube
    falla, te pregunta si quieres hacerlo en tu equipo.
  - **Siempre local / Siempre en la nube:** para forzar una u otra.
  - Si tu Space es privado, escribe tu token de Hugging Face (permiso de lectura). El
    token solo vive en memoria durante la sesión; no se guarda en disco (también puede
    leerse de la variable de entorno `NETPLOTBRAIN_NUBE_TOKEN`).
  - **Límites de la nube:** solo nodos desde la tabla de nodos (no NIfTI ni atlas),
    solo templates de TemplateFlow por nombre (no un NIfTI propio), máx. 500 nodos y
    20,000 aristas, y la imagen llega como PNG a 150 dpi (sin vista interactiva ni
    SVG/PDF; para eso, renderiza en tu equipo).
  - **Privacidad:** los datos de tus nodos viajan a tu servidor en Hugging Face. No
    envíes información sensible de personas.
  - Se descartó usar Google Colab con un túnel (ngrok/Cloudflare): las reglas de Colab
    gratuito prohíben interactuar con un notebook por una interfaz web externa y hay
    reportes de cuentas bloqueadas por hacerlo.

- **Entorno virtual aislado.** `setup.py` ahora crea un `.venv` propio con
  `--system-site-packages`: reutiliza lo que ya tienes instalado globalmente
  cuando coincide, pero instala las versiones exactas que netplotbrain
  necesita solo dentro de ese entorno, sin tocar ni desinstalar nada de tus
  otros proyectos (por ejemplo, si usas `numpy`/`pandas` más recientes para
  otra cosa, como `vectorbt`, no se ven afectados).
- **Vista previa con cortes reales (opcional).** `generar_vista_previa.py`
  descarga un template ligero (`MNI152NLin2009cAsym`, 2mm, solo cerebro) y
  genera tres imágenes reales (sagital/coronal/transversal) que la vista
  previa usa como fondo en vez del dibujo esquemático, si están presentes.
  `setup.py` intenta generarlas automáticamente; si no hay internet o algo
  falla, la GUI simplemente sigue con el dibujo esquemático — no es un
  requisito para que el programa funcione.
- **Estimador de costo antes de renderizar.** Además de revisar la RAM del
  equipo, la GUI ahora clasifica la combinación de estilo + voxel size +
  vista elegida como ligera/moderada/pesada (con base en mediciones reales:
  `filled` resultó ~350 veces más lento que `surface` incluso en su ajuste
  más suave), y solo avisa cuando la tarea concreta lo amerita — no por un
  umbral genérico de "tu computadora es lenta".
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
- **Librerías congeladas** en `requirements_v9.txt`, generadas con `pip freeze` desde un entorno donde
  el programa fue probado, para reducir problemas de compatibilidad entre versiones.

## Instalación

```
pip install -r requirements_v9.txt
python netplotbrain_gui_v9.py
```

En Windows también puedes correr `python setup_v9.py`, que instala las dependencias y crea un acceso
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
