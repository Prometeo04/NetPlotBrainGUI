# NetPlotBrainGUI

Interfaz gráfica de escritorio para [netplotbrain](https://github.com/wiheto/netplotbrain) — visualiza redes cerebrales en 3D sin escribir una sola línea de código.

Desarrollado en un instituto de investigación en neurociencias para permitir que neurofisiólogos y clínicos exploren conectividad cerebral directamente, sin necesidad de programar en Python.

---

## ¿Qué hace?

- **Edita nodos y edges** en tablas interactivas (doble clic para editar celdas)
- **Soporta templates adultos e infantiles** (MNI152, MNIInfant cohortes 0–11, WHS para rata)
- **Carga archivos NIfTI personalizados** como template
- **Genera redes aleatorias** para exploración rápida
- **Valida datos automáticamente** antes de plotear (detecta edges rotos, nodos faltantes, self-loops)
- **Importa/exporta CSV** para nodos y edges
- **Controles visuales** para escala de nodos, escala de edges, tipo de nodo (círculos/esferas/parcels), estilo del template y vistas

## Capturas

> *Agrega aquí capturas de pantalla de la GUI y un plot generado.*
>
> Sugerencia: corre la app, genera nodos aleatorios, plotea, y toma screenshot.
> Guárdalas como `screenshots/gui.png` y `screenshots/plot.png`.

## Instalación

### Requisitos

- Python 3.9–3.12 (⚠️ Python 3.13+ puede tener problemas de compatibilidad)
- pip

### Pasos

```bash
git clone https://github.com/Prometeo04/NetPlotBrainGUI.git
cd NetPlotBrainGUI
pip install -r requirements.txt
python netplotbrain_gui.py
```

> **Nota para equipos con múltiples versiones de Python:** si tienes Python 3.14 y 3.12 instalados, usa `py -3.12` en lugar de `python` para todos los comandos.

### ¿Primera vez con Python?

1. Descarga Python 3.12 desde [python.org](https://www.python.org/downloads/)
2. **Marca la casilla "Add Python to PATH"** durante la instalación
3. Abre una terminal y sigue los pasos de arriba

## Uso rápido

1. Ejecuta `python netplotbrain_gui.py`
2. Los datos demo ya vienen cargados — haz clic en **📊 Plotear red** para verlo funcionar
3. Edita las tablas de nodos (x, y, z, comunidad, centralidad) y edges (i, j, weight)
4. O haz clic en **🎲 Generar nodos aleatorios** para crear una red nueva
5. Ajusta el template, vista, estilo y escalas en el panel izquierdo

### Templates infantiles

Para investigación neonatal/infantil, selecciona cualquiera de las cohortes `MNIInfant`:

| Cohorte | Edad aproximada |
|---------|----------------|
| 0       | Recién nacido  |
| 1       | 2 semanas      |
| 2       | 1 mes          |
| 3       | 2 meses        |
| ...     | ...            |
| 11      | 24 meses       |

### Template NIfTI personalizado

Selecciona "Archivo NIfTI personalizado..." en el menú de templates y carga tu archivo `.nii` o `.nii.gz`.

## Estructura del proyecto

```
NetPlotBrainGUI/
├── netplotbrain_gui.py   # Aplicación principal
├── requirements.txt      # Dependencias
├── README.md
├── LICENSE
└── .gitignore
```

## Problemas conocidos

- **NumPy 2.0+** causa errores de `nonzero on 0-d arrays`. La app detecta esto al arrancar y te avisa. Solución: `pip install 'numpy>=1.24,<2.0'`
- **Esferas muy grandes**: usa el slider de "Escala de nodos" para ajustar el tamaño
- **Template no carga**: requiere conexión a internet la primera vez (TemplateFlow descarga los archivos)

## Tecnologías

- [netplotbrain](https://github.com/wiheto/netplotbrain) — motor de visualización 3D
- [TemplateFlow](https://www.templateflow.org) — repositorio de templates cerebrales
- [tkinter](https://docs.python.org/3/library/tkinter.html) — interfaz gráfica
- [pandas](https://pandas.pydata.org/) — manejo de datos tabulares

## Cita

Si usas esta herramienta en un contexto académico, cita netplotbrain:

> Fanton, S., & Thompson, W. H. (2023). NetPlotBrain: A Python package for visualising networks and brains. *Network Neuroscience*, 7(2), 461–481.

## Licencia

MIT — ver [LICENSE](LICENSE).
