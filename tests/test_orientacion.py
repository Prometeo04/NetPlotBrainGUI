#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica que los cortes de generar_vista_previa.py queden bien orientados.

Para cada corte se construye un volumen sintético con un marcador brillante
colocado SOBRE el plano medio de ese corte (si estuviera fuera, el corte no lo
atravesaría) y asimétrico en los dos ejes que sí se ven. El volumen se guarda
en orientaciones deliberadamente distintas (RAS, LAS, PIR...) y se comprueba
que el marcador aparezca en el píxel que marca el contrato con la aplicación.

Si un eje estuviera espejeado o los ejes estuvieran intercambiados, estas
comprobaciones fallan.
"""

import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_vista_previa as gvp  # noqa: E402

FORMA = (60, 72, 50)
PASO = 2.0

# Para cada corte: eje que se fija, eje horizontal, eje vertical
EJES = {
    "Sagital": (0, 1, 2),
    "Coronal": (1, 0, 2),
    "Transversal": (2, 0, 1),
}

FALLOS = []


def comprobar(condicion, mensaje):
    if condicion:
        print(f"  ok    {mensaje}")
    else:
        print(f"  FALLA {mensaje}")
        FALLOS.append(mensaje)


def affine_ras():
    affine = np.eye(4)
    for eje in range(3):
        affine[eje, eje] = PASO
        affine[eje, 3] = -PASO * (FORMA[eje] - 1) / 2.0
    return affine


def volumen_con_marcador(marcador_mm, orientacion):
    """
    NIfTI con un cubo brillante en `marcador_mm`, guardado en `orientacion`.

    Se arma en RAS y luego se reordena. Al reordenar, nibabel cambia a la vez
    los datos y el affine, así que la posición en milímetros del marcador no
    cambia: es exactamente lo que se quiere poner a prueba.
    """
    datos = np.zeros(FORMA, dtype=np.float32)
    affine = affine_ras()
    datos[5:-5, 5:-5, 5:-5] = 0.3  # "cerebro" de fondo

    idx = [int(round((marcador_mm[e] - affine[e, 3]) / PASO)) for e in range(3)]
    datos[idx[0] - 1:idx[0] + 2, idx[1] - 1:idx[1] + 2, idx[2] - 1:idx[2] + 2] = 1.0

    img = nib.Nifti1Image(datos, affine)
    if orientacion != "RAS":
        transform = nib.orientations.ornt_transform(
            nib.orientations.io_orientation(affine),
            nib.orientations.axcodes2ornt(tuple(orientacion)))
        img = img.as_reoriented(transform)

    ruta = Path(tempfile.mkdtemp()) / f"m_{orientacion}.nii.gz"
    nib.save(img, ruta)
    return str(ruta)


def plano_medio_mm(eje):
    """Coordenada en mm del corte medio de un eje (el que toma el generador)."""
    affine = affine_ras()
    return affine[eje, 3] + PASO * (FORMA[eje] // 2)


def pixel_esperado(nombre, marcador_mm, meta, tamano):
    """Píxel (columna, fila) donde el contrato dice que debe caer el marcador."""
    _, eje_h, eje_v = EJES[nombre]
    m = meta[nombre]
    ancho, alto = tamano
    col = (marcador_mm[eje_h] - m["h_min"]) / (m["h_max"] - m["h_min"]) * ancho
    # La fila 0 es v_max: la fila crece a medida que baja el valor vertical.
    fila = (m["v_max"] - marcador_mm[eje_v]) / (m["v_max"] - m["v_min"]) * alto
    return col, fila


def probar_corte(nombre, orientacion, h_mm, v_mm):
    """Coloca el marcador en el plano medio de `nombre` y verifica ese corte."""
    from PIL import Image

    eje_fijo, eje_h, eje_v = EJES[nombre]
    marcador = [0.0, 0.0, 0.0]
    marcador[eje_fijo] = plano_medio_mm(eje_fijo)
    marcador[eje_h] = h_mm
    marcador[eje_v] = v_mm
    marcador = tuple(marcador)

    ruta = volumen_con_marcador(marcador, orientacion)
    assets_real = gvp.ASSETS
    gvp.ASSETS = Path(tempfile.mkdtemp()) / "assets"
    try:
        meta = gvp.generar(ruta)
        img = Image.open(gvp.ASSETS / gvp.NOMBRE_ARCHIVO[nombre])
        arr = np.asarray(img)

        # El marcador vale 1.0 y el fondo 0.3: el máximo debe ser claramente el marcador.
        if int(arr.max()) <= int(np.percentile(arr, 99)) // 2:
            comprobar(False, f"{orientacion} {nombre}: el marcador no destaca del fondo")
            return

        fila_max, col_max = np.unravel_index(int(np.argmax(arr)), arr.shape)
        col_esp, fila_esp = pixel_esperado(nombre, marcador, meta, img.size)
        dist = ((col_max - col_esp) ** 2 + (fila_max - fila_esp) ** 2) ** 0.5
        comprobar(dist <= 3.0,
                  f"{orientacion:4s} {nombre:12s} obtenido ({col_max:3d},{fila_max:3d})  "
                  f"esperado ({col_esp:5.1f},{fila_esp:5.1f})  error {dist:4.1f} px")
    finally:
        gvp.ASSETS = assets_real


def main():
    # Posiciones asimétricas en los dos ejes visibles: si un eje se espejea,
    # el marcador aparece en el lado contrario y la prueba falla.
    casos = [(30.0, 20.0), (-26.0, -18.0)]

    for orientacion in ("RAS", "LAS", "LPS", "PIR", "RAI"):
        print(f"\n--- Archivo guardado en orientación {orientacion} ---")
        for nombre in ("Sagital", "Coronal", "Transversal"):
            for h_mm, v_mm in casos:
                probar_corte(nombre, orientacion, h_mm, v_mm)

    print("\n" + "=" * 70)
    if FALLOS:
        print(f"{len(FALLOS)} comprobaciones fallaron:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("Todas las comprobaciones de orientación pasaron "
          f"({5 * 3 * len(casos)} combinaciones).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
