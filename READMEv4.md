# NetPlotBrain GUI

Interfaz gráfica de escritorio para visualizar redes neuronales sobre templates cerebrales usando [netplotbrain](https://www.netplotbrain.org/).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Características

- **Editor de nodos** — Tabla editable con coordenadas MNI (x, y, z), comunidad y centralidad
- **Editor de edges** — Define conexiones entre nodos con peso configurable
- **Configuración visual** — Template cerebral, vista, estilo, tipo de nodo, escala
- **Import/Export CSV** — Carga y guarda tus datos de nodos y edges
- **Plot directo** — Genera la visualización con un clic, sin escribir código
- **Guardar resultado** — Exporta como PNG, SVG o PDF

---

## Instalación desde cero (computadora nueva)

### 0. Requisitos previos

Si tu computadora **no tiene Python** instalado:

1. Descárgalo de [python.org/downloads](https://www.python.org/downloads/)
2. **IMPORTANTE:** durante la instalación, marca la casilla **☑ "Add Python to PATH"** (si no la marcas, nada va a funcionar desde la terminal)
3. Verifica que quedó bien abriendo una terminal (CMD o PowerShell) y escribiendo:

```bash
python --version
```

Si responde con `Python 3.x.x`, estás listo.

### 1. Descarga este proyecto

**Opción A — Con Git:**

```bash
git clone https://github.com/Prometeo04/netplotbrain-gui.git
cd netplotbrain-gui
```

**Opción B — Sin Git (descarga ZIP):**

1. En esta página de GitHub, haz clic en el botón verde **"<> Code"**
2. Selecciona **"Download ZIP"**
3. Descomprime el ZIP y abre la carpeta en una terminal

### 2. Instala las dependencias

```bash
pip install -r requirements.txt
```

Esto instala automáticamente: netplotbrain, numpy, pandas, matplotlib, scipy, nibabel, templateflow. No necesitas instalar nada más.

### 3. Ejecuta la GUI

```bash
python netplotbrain_gui_v2.py
```

> La primera vez que ploteas, TemplateFlow descarga el template cerebral (~100 MB). Necesitas conexión a internet solo para eso. Después es instantáneo.

---

## Uso

1. **Pestaña Nodos** — Agrega nodos manualmente, genera aleatorios o importa un CSV con columnas `x, y, z, comunidad, centralidad`
2. **Pestaña Edges** — Define conexiones con columnas `i, j, weight` donde `i` y `j` son índices de nodos (empezando desde 0)
3. **Configuración** — Selecciona template, vista, estilo y tipo de nodo
4. **▶ PLOT** — Genera la visualización sobre el cerebro
5. **Guardar PNG** — Exporta el resultado

## Formato de archivos

### nodos.csv
```
x,y,z,comunidad,centralidad
-42,20,35,Default,0.82
38,-15,50,Visual,0.65
```

### edges.csv
```
i,j,weight
0,7,1.63
4,2,0.95
```

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `'python' no se reconoce como comando` | Reinstala Python marcando "Add to PATH" |
| `ModuleNotFoundError` | Corre `pip install -r requirements.txt` otra vez |
| `Calling nonzero on 0d arrays` | Asegúrate de tener `numpy==1.26.4` (`pip install numpy==1.26.4`) |
| El plot tarda mucho la primera vez | Normal — está descargando el template cerebral (~100 MB) |

## Requisitos del sistema

- Python 3.10 o superior
- Windows, macOS o Linux
- Conexión a internet (solo la primera vez)

## Autor

Jesús Manuel Segovia Luna — [@Prometeo04](https://github.com/Prometeo04)
