# NetPlotBrain GUI

**Interfaz gráfica para [netplotbrain](https://github.com/wiheto/netplotbrain): visualiza redes cerebrales en 3D sin escribir código.**

Desarrollada en un instituto de investigación en neurociencias para que
neurofisiólogos y clínicos exploren conectividad cerebral directamente, sin
programar en Python.

Toda la interfaz está en español.

---

## Instalación

```bash
git clone https://github.com/Prometeo04/NetPlotBrainGUI.git
cd NetPlotBrainGUI
python setup.py
```

El instalador se encarga de todo:

1. **Busca un Python compatible (3.9–3.12).** Si el tuyo no sirve —por ejemplo
   si tienes 3.13— **descarga un Python 3.12 solo para esta aplicación**. Tu
   Python del sistema no se toca.
2. **Crea un entorno virtual aislado** (`.venv`) dentro de la carpeta.
3. **Instala las librerías con versiones fijas y probadas**, empezando por
   numpy<2.0.
4. Comprueba que `tkinter` funcione y, si falta, dice cómo instalarlo.
5. Genera las imágenes de vista previa a partir de un template real.
6. Descarga los templates de TemplateFlow (opcional, te pregunta).
7. Crea un acceso directo en el escritorio (Windows).

### Por qué el entorno aislado importa

netplotbrain necesita **numpy<2.0**. Si instalaras eso en tu Python global,
romperías cualquier otro proyecto que use numpy 2.x (vectorbt, por ejemplo).
El `.venv` evita exactamente eso: las versiones que necesita esta aplicación
viven dentro de su carpeta y no salen de ahí.

El aislamiento es **completo**: el instalador no usa `--system-site-packages`.
Si lo usara, pip se saltaría la instalación dentro del `.venv` de cualquier
librería que ya estuviera en tu Python global con la versión exacta, y la
aplicación acabaría dependiendo de esa copia externa. El día que la cambiaras,
se rompería. Al terminar, el instalador verifica que numpy, pandas,
matplotlib y netplotbrain estén efectivamente dentro del `.venv` y avisa si
alguna no lo está.

### Si ya tenías una versión anterior instalada

No hay conflicto. El instalador detecta el `.venv` viejo y, si se creó con la
configuración antigua (la que dejaba entrar librerías del sistema) o con una
versión de Python incompatible, lo **borra y lo vuelve a crear** aislado. Tus
datos, tu configuración (`~/.netplotbrain_gui.json`) y los templates ya
descargados se conservan.

### Si algo falla

Los errores se guardan en `~/.netplotbrain_gui.log` con la fecha, la versión,
el sistema operativo y los ajustes del render. El diálogo de error te dice la
ruta del archivo. Hace falta porque el acceso directo abre la aplicación con
`pythonw.exe`, que no tiene consola: sin ese registro, un fallo no dejaría
rastro en ningún lado.

El registro guarda **los ajustes, no los datos**: estilo, vista, tipo de nodo y
el número de filas de cada tabla, nunca las coordenadas. Puedes adjuntarlo a un
reporte de error sin exponer información del estudio.

### Requisitos

- Windows 10/11, Linux o macOS
- Cualquier Python 3.9 o posterior para arrancar el instalador
  ([descargar](https://www.python.org/downloads/)). No tiene que ser una
  versión compatible: el instalador resuelve eso.
- En Windows, marca **«Add Python to PATH»** al instalar Python.
- En Linux puede faltar `tkinter`: `sudo apt install python3-tk`
  (el instalador lo detecta y te lo dice).

---

## Qué puede hacer

### Datos de entrada

| Fuente | Formatos |
|---|---|
| Tabla de nodos | Edición directa, o importar CSV, TSV, XLS, XLSX |
| Tabla de aristas | Edición directa, o importar CSV, TSV, XLS, XLSX |
| Matriz de adyacencia | CSV, XLS, XLSX, NumPy `.npy` |
| Parcelación | Archivo NIfTI propio (`.nii`, `.nii.gz`) |
| Atlas | TemplateFlow (Schaefer 100/200/400) |

Todo se puede exportar a CSV.

### Formato de los datos

**Nodos** — `x`, `y`, `z` son obligatorias y van en milímetros (espacio MNI):

```csv
x,y,z,comunidad,centralidad
30,-20,20,1,0.9
-30,-20,20,1,0.7
10,40,10,2,0.5
-10,40,10,2,0.4
```

- `comunidad` (opcional): agrupa nodos por color.
- `centralidad` (opcional): si está, controla el tamaño de cada nodo.

**Aristas** — `i` y `j` son índices de fila de la tabla de nodos, empezando en 0:

```csv
i,j,peso
0,1,0.9
1,2,0.5
2,3,0.7
```

- `peso` (opcional): controla el grosor de la línea y permite filtrar por umbral.

### Vista previa en tiempo real

Mientras escribes coordenadas, tres cortes (sagital, coronal y transversal)
muestran dónde va cayendo cada nodo, sobre cortes de un cerebro real. Así se
detecta un signo invertido o una coordenada mal escrita antes de gastar minutos
en un render.

### Controles

- **Estilo del template:** `surface`, `cloudy`, `glass`, `filled`
- **Tipo de nodo:** círculos, esferas, o `parcels` (solo con atlas o NIfTI)
- **Vistas:** L, R, S, I, A, P, preset-4, preset-6, 360° con número de cuadros
- **Voxel size:** compromiso entre detalle y velocidad
- **Escalas y opacidad** de nodos, aristas y template
- **Selector de hemisferio**
- **Exportar** a PNG o SVG

Los tamaños de esferas y círculos están calibrados para verse iguales:
netplotbrain mide las esferas en radio de vóxeles y los círculos en área de
puntos², que son escalas distintas.

### Análisis de recursos y renderizado en la nube

La aplicación mide la RAM y la GPU del equipo y clasifica cada configuración
como ligera, moderada o pesada. Si una configuración no va a caber, avisa
**antes** de empezar y ofrece tres salidas: ajustar los parámetros, renderizar
de todos modos, o mandarlo a un servidor.

El servidor es opcional y está en la carpeta [`nube/`](nube/), con tres
opciones de alojamiento y una nota importante sobre privacidad si trabajas con
datos de pacientes. **Para datos de pacientes, la opción recomendada es
levantar el servidor en un equipo de tu propia red local**, donde los datos
nunca salen de la institución.

### Cancelar un render

Mientras se genera la figura hay un botón **Cancelar**. Es útil sobre todo con
`filled` y con `parcels`, que pueden tardar varios minutos.

(Nota técnica: matplotlib no se puede interrumpir a media operación, así que al
cancelar la aplicación deja de esperar el resultado y te devuelve el control,
pero el cálculo en curso termina por su cuenta en segundo plano.)

### Validación

- Verifica que las aristas apunten a nodos que existen, y ofrece limpiar las rotas
- Detecta lazos sobre el mismo nodo, matrices no cuadradas y NIfTI 4D
- Comprueba que un NIfTI propio siga existiendo antes de renderizar (si se
  movió, netplotbrain confundiría la ruta con el nombre de un template)
- Impide combinaciones que no funcionan, como `parcels` con datos de tabla
- Mensajes de error en español, con la solución cuando la hay

---

## Uso rápido

1. Abre la aplicación (doble clic en el acceso directo, o
   `.venv/bin/python netplotbrain_gui_v9.py`).
2. Vienen datos de ejemplo cargados: pulsa **Generar figura**.
3. Prueba el generador aleatorio para ver una red más grande.
4. Recorre las pestañas: Nodos, Aristas, Archivo, Matriz.

---

## Estructura del proyecto

```
NetPlotBrainGUI/
├── netplotbrain_gui_v9.py    # Aplicación principal
├── setup.py                  # Instalador
├── generar_vista_previa.py   # Genera los cortes de fondo de la vista previa
├── requirements.txt          # Versiones fijas y probadas
├── netplotbrain_gui.ico      # Icono
├── ejemplos/
│   ├── nodos.csv             # Datos de ejemplo
│   └── aristas.csv
├── nube/                     # Servidor de renderizado (opcional)
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md             # Opciones de alojamiento y privacidad
├── assets/                   # Imágenes de vista previa (las crea el setup)
├── LICENSE
└── README.md
```

---

## Limitaciones conocidas

- **numpy<2.0 es obligatorio.** netplotbrain usa APIs que NumPy 2.x eliminó.
  De ahí el entorno aislado.
- **El estilo `filled` es muy lento.** En nuestras mediciones tardó unos 100
  segundos incluso con voxel size 4, cerca de 350 veces más que `surface`. La
  aplicación avisa antes de usarlo.
- **`parcels` es lento y necesita un atlas.** Pinta cada región en 3D y puede
  tardar varios minutos. No funciona con datos de tabla, porque necesita un
  volumen de parcelación; la aplicación lo oculta en ese modo.
- **La primera vez es lenta:** TemplateFlow descarga el template. El instalador
  puede adelantarse a eso.
- **Las edades de las cohortes MNIInfant no están verificadas** contra la
  documentación de TemplateFlow. Si tu trabajo depende de la edad exacta de una
  cohorte, confírmala en [templateflow.org](https://www.templateflow.org) antes
  de publicar.

---

## Tecnologías

- [netplotbrain](https://github.com/wiheto/netplotbrain) — visualización 3D de redes cerebrales
- [TemplateFlow](https://www.templateflow.org) — repositorio de templates
- [tkinter](https://docs.python.org/3/library/tkinter.html) — interfaz gráfica
- [nibabel](https://nipy.org/nibabel/) — lectura de NIfTI
- [pandas](https://pandas.pydata.org/) — datos tabulares
- [uv](https://github.com/astral-sh/uv) — lo usa el instalador para descargar Python cuando hace falta

## Cita

Si usas esta herramienta en un contexto académico, cita la librería que hace el
trabajo de fondo:

> Fanton, S., & Thompson, W. H. (2023). NetPlotBrain: A Python package for
> visualising networks and brains. *Network Neuroscience*, 7(2), 461–481.

## Autor

**Jesús Manuel Segobia Luna** ([@Prometeo04](https://github.com/Prometeo04))

## Licencia

MIT — ver [LICENSE](LICENSE).
