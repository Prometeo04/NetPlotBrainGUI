# NetPlotBrain GUI 🧠🕹️

**Interfaz gráfica arcade para [netplotbrain](https://github.com/wiheto/netplotbrain) — visualiza redes cerebrales en 3D sin escribir código.**

Desarrollado en un instituto de investigación en neurociencias para que neurofisiólogos y clínicos exploren conectividad cerebral directamente, sin programar en Python.

---

## Instalación (un solo comando)

```bash
git clone https://github.com/Prometeo04/NetPlotBrainGUI.git
cd NetPlotBrainGUI
python setup.py
```

El setup automáticamente:
- Instala todas las dependencias (numpy, netplotbrain, matplotlib, nibabel, templateflow)
- Detecta tu escritorio (soporta OneDrive)
- Crea un acceso directo con el icono del cerebro

Después solo haz doble clic en **NetPlotBrain GUI** en tu escritorio.

### Requisitos previos

- Windows 10/11
- Python 3.9–3.12 ([descargar aquí](https://www.python.org/downloads/))
- Marca **"Add Python to PATH"** durante la instalación de Python

---

## ¿Qué puede hacer?

### Templates cerebrales
- Templates adultos (MNI152, OASIS30ANTs)
- Templates infantiles/neonatales (MNIInfant cohortes 0–11, desde recién nacido hasta 24 meses)
- Templates animales (WHS para rata)
- Archivos NIfTI personalizados como template
- Archivero integrado que lista todos los templates de TemplateFlow con descarga en un clic

### Nodos (regiones cerebrales)
- Tabla editable con coordenadas x, y, z, comunidad y centralidad
- Carga de archivos NIfTI de parcelación (node_type parcels)
- Atlas de TemplateFlow (Schaefer 100/200/400 parcels)
- Generador aleatorio de redes con parámetros configurables

### Edges (conexiones)
- Tabla editable con índices i, j y peso
- Carga de matrices de adyacencia (CSV o NumPy .npy)
- Umbral configurable para filtrar conexiones débiles
- Importar/exportar CSV

### Controles visuales
- Escala de nodos y edges con sliders
- Opacidad del template
- Voxel size para velocidad de renderizado
- Tipo de nodo: círculos, esferas o parcels
- Estilo del template: glass, surface, filled, cloudy
- Vistas: L, R, S, I, A, P, preset-4, preset-6, 360°
- Selector de hemisferio
- Export como PNG o SVG

### Validación automática
- Detecta NumPy 2.0+ y avisa antes de arrancar
- Verifica que los edges referencien nodos válidos
- Ofrece limpiar edges rotos automáticamente
- Detecta self-loops, matrices no cuadradas, NIfTI 4D
- Mensajes de error claros y en español

---

## Uso rápido

1. Abre la app (doble clic en el acceso directo o `python netplotbrain_gui_v6.py`)
2. Los datos demo vienen precargados — haz clic en **▶ PLOTEAR RED**
3. Prueba el **🎲 GENERAR ALEATORIO** con 20 nodos y 4 comunidades
4. Explora las tabs: Nodos, Edges, NIfTI/Atlas, Matriz de adyacencia
5. Abre el **📂 ARCHIVERO TEMPLATES** para ver y descargar templates

### Templates infantiles

Para investigación neonatal, selecciona cualquiera de las cohortes MNIInfant:

| Cohorte | Edad |
|---------|------|
| 0 | Recién nacido |
| 1 | 2 semanas |
| 2 | 1 mes |
| 3 | 2 meses |
| 4 | 3 meses |
| 5 | 6 meses |
| 6–11 | 9–24 meses |

---

## Estructura del proyecto

```
NetPlotBrainGUI/
├── netplotbrain_gui_v6.py    # App principal (arcade edition)
├── setup.py                  # Instalador automático
├── netplotbrain_gui.ico      # Icono del cerebro pixel art
├── requirements.txt          # Dependencias
├── LICENSE                   # MIT
└── .gitignore
```

## Problemas conocidos

- **Primera vez lenta**: TemplateFlow descarga el template (~50-100MB). Las siguientes veces es instantáneo
- **"No responde" al plotear**: matplotlib renderiza en el hilo principal. Es normal, espera unos segundos
- **NumPy 2.0+**: la app lo detecta y te avisa. Solución: `pip install 'numpy>=1.24,<2.0'`

## Tecnologías

- [netplotbrain](https://github.com/wiheto/netplotbrain) — visualización 3D de redes cerebrales
- [TemplateFlow](https://www.templateflow.org) — repositorio de templates cerebrales
- [tkinter](https://docs.python.org/3/library/tkinter.html) — interfaz gráfica
- [nibabel](https://nipy.org/nibabel/) — lectura de archivos NIfTI
- [pandas](https://pandas.pydata.org/) — manejo de datos tabulares

## Cita

Si usas esta herramienta en un contexto académico:

> Fanton, S., & Thompson, W. H. (2023). NetPlotBrain: A Python package for visualising networks and brains. *Network Neuroscience*, 7(2), 461–481.

## Autor

**Jesús Manuel Segovia Luna** ([@Prometeo04](https://github.com/Prometeo04))

## Licencia

MIT — ver [LICENSE](LICENSE).
