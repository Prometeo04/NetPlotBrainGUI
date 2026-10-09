#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera las imágenes de fondo de la vista previa esquemática
===========================================================

Descarga un template MNI ligero (unos 450 KB) y guarda tres cortes en
`assets/`, junto con un `preview_meta.json` que dice qué rango de milímetros
cubre cada imagen. La aplicación los usa como fondo para que, al escribir
coordenadas, se vean sobre un cerebro real y no sobre un dibujo aproximado.

Si algo falla, la aplicación sigue funcionando con su dibujo esquemático: este
script es una mejora opcional, nunca un requisito.

Convenio de ejes (el mismo que usa la aplicación):

    Sagital      horizontal = y (post -> ant)    vertical = z (inf -> sup)
    Coronal      horizontal = x (izq -> der)     vertical = z (inf -> sup)
    Transversal  horizontal = x (izq -> der)     vertical = y (post -> ant)

En las tres imágenes la fila 0 es el valor vertical MÁXIMO y la columna 0 es
el valor horizontal MÍNIMO, que es como la aplicación las dibuja.

Uso:
    python generar_vista_previa.py
"""

import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
ASSETS = RAIZ / "assets"

# Cada corte: (nombre, eje que se fija, eje horizontal, eje vertical)
# Los ejes se nombran por su índice en el volumen ya reorientado a RAS:
#   0 -> x (derecha),  1 -> y (anterior),  2 -> z (superior)
CORTES = [
    ("Sagital", 0, 1, 2),
    ("Coronal", 1, 0, 2),
    ("Transversal", 2, 0, 1),
]

NOMBRE_ARCHIVO = {
    "Sagital": "preview_sagital.png",
    "Coronal": "preview_coronal.png",
    "Transversal": "preview_transversal.png",
}


def descargar_template():
    """Devuelve la ruta del NIfTI del template, descargándolo si hace falta."""
    import templateflow.api as tf

    print("Descargando el template MNI152NLin2009cAsym (res-2, desc-brain, T1w)...")
    ruta = tf.get("MNI152NLin2009cAsym", resolution=2, desc="brain", suffix="T1w",
                  extension=".nii.gz")
    if isinstance(ruta, list):
        ruta = ruta[0]
    print(f"  {ruta}")
    return str(ruta)


def cargar_volumen(ruta):
    """
    Carga el NIfTI y lo reorienta a RAS.

    `as_closest_canonical` es la parte importante: distintos archivos guardan
    los ejes en distinto orden (LAS, RPI, etc.). Sin reorientar, los cortes
    saldrían espejeados o rotados según el archivo. Después de esto, el eje 0
    siempre crece hacia la derecha, el 1 hacia adelante y el 2 hacia arriba.
    """
    import nibabel as nib

    img = nib.as_closest_canonical(nib.load(ruta))
    datos = np.asarray(img.dataobj, dtype=np.float32)
    return datos, img.affine


def bordes_mm(affine, forma, eje):
    """
    Rango en milímetros que cubre un eje del volumen, de borde a borde.

    El affine da el centro de cada vóxel, así que se añade medio vóxel a cada
    extremo: la imagen que se genera cubre el volumen completo, no solo la
    línea que une los centros de los vóxeles de los extremos.
    """
    paso = affine[eje, eje]
    origen = affine[eje, 3]
    primero = origen
    ultimo = origen + paso * (forma[eje] - 1)
    bajo, alto = min(primero, ultimo), max(primero, ultimo)
    medio = abs(paso) / 2.0
    return bajo - medio, alto + medio


def recortar_corte(datos, eje_fijo, eje_h, eje_v):
    """
    Saca un corte 2D por la mitad del volumen y lo orienta para la pantalla:
    filas = eje vertical de mayor a menor, columnas = eje horizontal de menor
    a mayor.
    """
    indice = datos.shape[eje_fijo] // 2
    corte = np.take(datos, indice, axis=eje_fijo)

    # Tras np.take, los dos ejes que quedan conservan su orden relativo.
    ejes_restantes = [e for e in (0, 1, 2) if e != eje_fijo]
    pos_h = ejes_restantes.index(eje_h)
    pos_v = ejes_restantes.index(eje_v)

    # Se quiere (vertical, horizontal) para que las filas sean el eje vertical.
    corte = np.transpose(corte, (pos_v, pos_h))
    # La fila 0 debe ser el valor vertical máximo, y en el volumen el índice
    # crece hacia el valor positivo, así que se invierte.
    return np.flipud(corte)


def a_imagen(corte):
    """Normaliza el corte a una imagen en escala de grises de 8 bits."""
    from PIL import Image

    v = corte.astype(np.float32)
    bajo, alto = float(np.min(v)), float(np.max(v))
    if alto > bajo:
        v = (v - bajo) / (alto - bajo)
    else:
        v = np.zeros_like(v)
    # Se aclara un poco el fondo para que los nodos de color resalten encima.
    v = np.power(v, 0.85) * 215.0
    return Image.fromarray(v.astype(np.uint8), mode="L")


def generar(ruta_nifti=None):
    ASSETS.mkdir(exist_ok=True)
    ruta = ruta_nifti or descargar_template()
    datos, affine = cargar_volumen(ruta)
    print(f"Volumen reorientado a RAS: {datos.shape}")

    meta = {}
    for nombre, eje_fijo, eje_h, eje_v in CORTES:
        corte = recortar_corte(datos, eje_fijo, eje_h, eje_v)
        imagen = a_imagen(corte)
        destino = ASSETS / NOMBRE_ARCHIVO[nombre]
        imagen.save(destino, optimize=True)

        h_min, h_max = bordes_mm(affine, datos.shape, eje_h)
        v_min, v_max = bordes_mm(affine, datos.shape, eje_v)
        # Las claves van capitalizadas porque así las busca la aplicación.
        meta[nombre] = {
            "h_min": round(float(h_min), 2),
            "h_max": round(float(h_max), 2),
            "v_min": round(float(v_min), 2),
            "v_max": round(float(v_max), 2),
        }
        print(f"  {nombre:12s} {imagen.size[0]}x{imagen.size[1]} px   "
              f"h [{h_min:7.1f}, {h_max:7.1f}]   v [{v_min:7.1f}, {v_max:7.1f}]")

    (ASSETS / "preview_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nListo. Archivos en {ASSETS}")
    return meta


def main():
    try:
        generar(sys.argv[1] if len(sys.argv) > 1 else None)
        return 0
    except ImportError as e:
        print(f"Falta una librería: {e}", file=sys.stderr)
        print("Ejecuta primero el instalador: python setup.py", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"No se pudieron generar las imágenes: {type(e).__name__}: {e}",
              file=sys.stderr)
        print("La aplicación seguirá funcionando con su dibujo esquemático.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
