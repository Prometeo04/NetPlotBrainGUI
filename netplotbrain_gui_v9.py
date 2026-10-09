"""
NetPlotBrainGUI - Interfaz gráfica para netplotbrain
Versión 7.0

Visualiza redes cerebrales en 3D sin escribir código.

Novedades de la v7:
  - Interfaz sobria y completamente en español.
  - Importación de CSV / TSV / Excel (.xlsx, .xls) y exportación a CSV.
  - Vista previa esquemática en tiempo real (sagital, coronal, transversal).
  - Esferas y círculos con el mismo tamaño visual.
  - Indicador de progreso mientras se descarga o se renderiza.
  - Detección de recursos (RAM / GPU) con alternativas gratuitas en la nube.
  - Render en segundo plano: la ventana ya no se congela.

Autor: Jesús Manuel Segovia Luna (Prometeo04)
"""

import sys
import os
import csv
import json
import re
import time
import base64
import platform
import subprocess
import threading
import traceback
import unicodedata
import webbrowser
import socket
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image as PILImage, ImageTk

VERSION = "9.5"


# ══════════════════════════════════════════════
# Validación de entorno (antes de importar netplotbrain)
# ══════════════════════════════════════════════
def revisar_entorno():
    errores = []
    try:
        ver_np = tuple(int(x) for x in np.__version__.split(".")[:2])
        if ver_np >= (2, 0):
            errores.append(
                f"Se detectó NumPy {np.__version__}, pero netplotbrain necesita NumPy menor a 2.0.\n"
                "Solución:  pip install \"numpy>=1.24,<2.0\""
            )
    except ValueError:
        pass
    for modulo, nombre in [("netplotbrain", "netplotbrain"), ("matplotlib", "matplotlib"),
                           ("nibabel", "nibabel"), ("templateflow", "templateflow")]:
        try:
            __import__(modulo)
        except ImportError:
            errores.append(f"Falta el paquete {nombre}.\nSolución:  pip install {nombre}")
    if errores:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("Error de entorno", "\n\n".join(errores))
        raiz.destroy()
        sys.exit(1)


revisar_entorno()

# El backend "Agg" permite renderizar en un hilo aparte sin abrir ventanas de
# matplotlib. La figura se muestra dentro de nuestra propia ventana, así que ya
# no dependemos de plt.show() (que fallaba en equipos con gráficos integrados).
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netplotbrain
import templateflow.api as tflow
import nibabel as nib


# ══════════════════════════════════════════════
# Paleta sobria
# ══════════════════════════════════════════════
C = {
    "fondo": "#F3F4F6", "panel": "#FFFFFF", "borde": "#D1D5DB",
    "texto": "#1F2937", "texto2": "#6B7280",
    "acento": "#1F5F8B", "acento_h": "#174C70", "acento_txt": "#FFFFFF",
    "cabecera": "#1E3A52", "cabecera_txt": "#FFFFFF", "cabecera_txt2": "#B8C7D6",
    "sel": "#DCE9F3", "ok": "#2F7D4F", "aviso": "#A15C07", "error": "#B42318",
    "cerebro": "#EEF1F5", "cerebro_borde": "#9AA5B1", "guia": "#C5CCD5",
}
PALETA_COMUNIDADES = ["#1F5F8B", "#B5581E", "#3F7D4E", "#7A4E9C",
                      "#A6903A", "#2E8B8B", "#A33B55", "#5F6B7A"]

# ══════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════
VISTAS = ["L", "R", "S", "I", "A", "P", "preset-4", "preset-6", "360"]
ESTILOS = ["surface", "cloudy", "filled", "glass"]
TIPOS_NODO = ["circles", "spheres", "parcels"]
# 'parcels' pinta las parcelas del propio archivo de parcelación, así que solo
# funciona cuando los nodos vienen de un NIfTI o de un atlas: con una tabla de
# coordenadas netplotbrain no tiene ninguna imagen que pintar.
TIPOS_NODO_TABLA = ["circles", "spheres"]
HEMISFERIOS = ["ambos", "left", "right"]

COLUMNAS_NODOS = ("x", "y", "z", "comunidad", "centralidad")
COLUMNAS_ARISTAS = ("i", "j", "peso")

ATLAS_TEMPLATEFLOW = {
    "Schaefer 100 (7 redes)": {"atlas": "Schaefer2018", "desc": "100Parcels7Networks", "resolution": 1},
    "Schaefer 200 (7 redes)": {"atlas": "Schaefer2018", "desc": "200Parcels7Networks", "resolution": 1},
    "Schaefer 400 (7 redes)": {"atlas": "Schaefer2018", "desc": "400Parcels7Networks", "resolution": 1},
}

# Nombres alternativos de columnas aceptados al importar (sin acentos, minúsculas).
ALIAS_COLUMNAS = {
    "x": ["x"], "y": ["y"], "z": ["z"],
    "comunidad": ["comunidad", "community", "modulo", "red", "network", "grupo"],
    "centralidad": ["centralidad", "centrality", "tamano", "size", "tamanio"],
    "i": ["i", "origen", "source", "from", "desde", "nodo_i"],
    "j": ["j", "destino", "target", "to", "hasta", "nodo_j"],
    "peso": ["peso", "weight", "w", "valor", "value"],
}

# Factor para igualar el tamaño visual de esferas y círculos (calibrado midiendo
# el render real de netplotbrain en las vistas preset). Ver _radios_esfera().
FACTOR_ESFERA = 1.05

# Escala aproximada del cerebro infantil respecto al adulto, solo para la vista
# previa esquemática (raíz cúbica del cociente de volúmenes típicos).
ESCALA_INFANTIL = [0.62, 0.66, 0.70, 0.74, 0.77, 0.83, 0.87, 0.90, 0.92, 0.94, 0.95, 0.96]

URL_COLAB = "https://colab.research.google.com/"
URL_BINDER = "https://mybinder.org/v2/gh/wiheto/netplotbrain/main"
COMANDO_COLAB = '!pip install "numpy<2" netplotbrain templateflow'
URL_CREAR_SPACE = "https://huggingface.co/new-space"
URL_CLOUD_RUN = "https://console.cloud.google.com/run"


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower()


# ══════════════════════════════════════════════
# Configuración persistente (muy pequeña)
# ══════════════════════════════════════════════
class Config:
    ruta = Path.home() / ".netplotbrain_gui.json"

    @classmethod
    def leer(cls):
        try:
            return json.loads(cls.ruta.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def guardar(cls, datos):
        try:
            cls.ruta.write_text(json.dumps(datos, indent=2), encoding="utf-8")
        except Exception:
            pass


# ══════════════════════════════════════════════
# Cliente de la nube (servidor propio en Hugging Face Spaces)
# ══════════════════════════════════════════════
class ErrorNube(Exception):
    """Error al usar el servidor de nube. El mensaje ya está listo para mostrarse al usuario."""


LIMITE_NODOS_NUBE = 500
LIMITE_ARISTAS_NUBE = 20000


def _a_json(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"No se puede serializar {type(obj).__name__}")


def _df_a_split(df):
    return json.loads(df.to_json(orient="split", index=False))


class ClienteNube:
    """Habla con el servidor de render de la carpeta nube/ (ver nube/README.md)."""

    CAMPOS = ("template", "template_style", "template_voxelsize", "template_alpha", "view", "title",
              "node_type", "node_scale", "node_alpha", "hemisphere", "frames", "node_color", "node_size",
              "node_sizevminvmax", "node_sizelegend", "edge_widthscale", "edge_weights",
              "edge_threshold", "edge_thresholddirection")

    @staticmethod
    def url_normalizada(url):
        """Devuelve la URL limpia (sin / final) o '' si está vacía. Lanza ErrorNube si no sirve."""
        url = (url or "").strip()
        if not url:
            return ""
        if "://" not in url:
            url = "https://" + url
        partes = urllib.parse.urlparse(url)
        if partes.scheme not in ("http", "https") or not partes.netloc:
            raise ErrorNube("La URL no es válida. Debe verse como https://usuario-nombre.hf.space")
        host = partes.netloc.lower()
        if host in ("huggingface.co", "www.huggingface.co"):
            raise ErrorNube(
                "Esa es la página del Space en huggingface.co, no la dirección de su servicio.\n"
                "Necesitas la URL directa, que termina en .hf.space (en la página del Space, "
                "menú de tres puntos → \"Embed this Space\" → \"Direct URL\").")
        return url.rstrip("/")

    @staticmethod
    def compatible(kw):
        """(True, '') si este render puede hacerse en la nube; si no, (False, motivo)."""
        nodos = kw.get("nodes")
        if not isinstance(nodos, pd.DataFrame):
            return False, ("La nube solo acepta nodos desde la tabla de nodos "
                           "(no desde un NIfTI de parcelación ni un atlas).")
        if len(nodos) > LIMITE_NODOS_NUBE:
            return False, f"Demasiados nodos para el servidor gratuito ({len(nodos)} > {LIMITE_NODOS_NUBE})."
        tpl = kw.get("template")
        if not isinstance(tpl, str) or os.path.exists(tpl) or tpl.lower().endswith((".nii", ".nii.gz")):
            return False, ("La nube solo acepta templates de TemplateFlow por nombre, "
                           "no un archivo NIfTI de tu equipo.")
        aristas = kw.get("edges")
        if isinstance(aristas, pd.DataFrame) and len(aristas) > LIMITE_ARISTAS_NUBE:
            return False, f"Demasiadas aristas para el servidor gratuito ({len(aristas)} > {LIMITE_ARISTAS_NUBE})."
        return True, ""

    @classmethod
    def payload(cls, kw, dpi=150):
        """Convierte los argumentos de netplotbrain.plot() a un diccionario JSON para el servidor."""
        p = {k: kw[k] for k in cls.CAMPOS if k in kw and kw[k] is not None}
        p["nodes"] = _df_a_split(kw["nodes"])
        aristas = kw.get("edges")
        if aristas is not None:
            if isinstance(aristas, pd.DataFrame):
                p["edges"] = _df_a_split(aristas)
            else:
                p["edges"] = np.asarray(aristas, dtype=float).tolist()
        p["dpi"] = dpi
        return p

    @staticmethod
    def _encabezados(token, json_body=False):
        h = {"User-Agent": f"NetPlotBrainGUI/{VERSION}", "Accept": "*/*"}
        if json_body:
            h["Content-Type"] = "application/json"
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    @staticmethod
    def _mensaje_http(codigo, cuerpo):
        try:
            datos = json.loads(cuerpo.decode("utf-8", errors="replace"))
        except ValueError:
            datos = None
        if isinstance(datos, dict) and isinstance(datos.get("error"), str):
            return datos["error"]
        if isinstance(datos, dict) and isinstance(datos.get("detail"), list):
            partes = []
            for d in datos["detail"][:3]:
                if isinstance(d, dict):
                    donde = ".".join(str(x) for x in d.get("loc", [])[1:])
                    partes.append(f"{donde}: {d.get('msg', '')}".strip(": "))
            return ("El servidor no aceptó los parámetros (" + "; ".join(partes) + "). "
                    "Puede que el servidor y la GUI sean de versiones distintas.")
        if codigo in (401, 403):
            return (f"El servidor rechazó el acceso (código {codigo}). Si tu Space es privado, "
                    "escribe tu token de Hugging Face en la configuración de Nube.")
        if codigo == 404:
            return "No se encontró el servicio en esa URL (404). ¿Es la URL de tu Space de NetPlotBrainGUI?"
        if codigo == 429:
            return "El servidor recibió demasiadas solicitudes (429). Espera un momento y reintenta."
        if codigo in (502, 503, 504):
            return (f"El servidor no está listo (código {codigo}). Si estaba dormido puede tardar cerca de "
                    "un minuto en despertar: espera un poco y reintenta.")
        return f"El servidor respondió con el código {codigo}."

    @classmethod
    def _abrir(cls, req, timeout):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            try:
                return resp.headers.get("Content-Type", ""), resp.read()
            finally:
                resp.close()
        except urllib.error.HTTPError as e:
            try:
                cuerpo = e.read()
            except OSError:
                cuerpo = b""
            raise ErrorNube(cls._mensaje_http(e.code, cuerpo)) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ErrorNube("El servidor tardó demasiado en responder. Si estaba dormido, "
                                "reintenta en un minuto.") from None
            raise ErrorNube(f"No se pudo conectar con el servidor. Revisa la URL y tu conexión a internet.\n"
                            f"({e.reason})") from None
        except (socket.timeout, TimeoutError):
            raise ErrorNube("El servidor tardó demasiado en responder. Si estaba dormido, "
                            "reintenta en un minuto.") from None
        except OSError as e:
            raise ErrorNube(f"Se interrumpió la conexión con el servidor ({type(e).__name__}).") from None

    @classmethod
    def probar(cls, url, token=None, timeout=100):
        """Comprueba GET /salud. Devuelve la versión del servidor o lanza ErrorNube."""
        url = cls.url_normalizada(url)
        if not url:
            raise ErrorNube("Escribe primero la URL del servidor.")
        req = urllib.request.Request(url + "/salud", headers=cls._encabezados(token), method="GET")
        tipo, cuerpo = cls._abrir(req, timeout)
        try:
            datos = json.loads(cuerpo.decode("utf-8", errors="replace"))
        except ValueError:
            datos = None
        if not (isinstance(datos, dict) and datos.get("ok") is True):
            raise ErrorNube("La URL respondió, pero no parece ser un servidor de NetPlotBrainGUI. "
                            "Si es un Space que estaba dormido, ábrelo una vez en el navegador y reintenta.")
        return str(datos.get("version", "?"))

    @classmethod
    def renderizar(cls, url, payload, token=None, timeout=180):
        """Manda el render al servidor. Devuelve los bytes del PNG o lanza ErrorNube."""
        url = cls.url_normalizada(url)
        if not url:
            raise ErrorNube("No hay una URL de servidor configurada.")
        try:
            datos = json.dumps(payload, default=_a_json, allow_nan=False).encode("utf-8")
        except ValueError:
            raise ErrorNube("Los datos contienen valores no numéricos (NaN o infinitos) "
                            "y no se pueden enviar.") from None
        req = urllib.request.Request(url + "/renderizar", data=datos, method="POST",
                                     headers=cls._encabezados(token, json_body=True))
        tipo, cuerpo = cls._abrir(req, timeout)
        if not tipo.lower().startswith("image/png") or not cuerpo.startswith(b"\x89PNG"):
            raise ErrorNube("El servidor respondió algo que no es una imagen. ¿Estaba dormido o la URL no "
                            "es de tu servidor? Ábrela en el navegador para despertarlo y reintenta.")
        return cuerpo


# ══════════════════════════════════════════════
# Recursos del equipo
# ══════════════════════════════════════════════
class Recursos:
    RE_INTEGRADA = re.compile(
        r"intel|uhd|iris|hd graphics|radeon\(tm\) graphics|radeon graphics|vega \d+ graphics|"
        r"apple m\d|adreno|microsoft basic|virtualbox|vmware|llvmpipe|parallels|virtio", re.I)
    RE_DEDICADA = re.compile(r"nvidia|geforce|rtx|gtx|quadro|radeon rx|radeon pro|arc a\d", re.I)

    @staticmethod
    def ram():
        """Devuelve (total_gb, libre_gb) o (None, None) si no se puede medir."""
        try:
            import psutil
            m = psutil.virtual_memory()
            return m.total / 1024 ** 3, m.available / 1024 ** 3
        except Exception:
            pass
        try:
            if sys.platform == "win32":
                import ctypes

                class MEM(ctypes.Structure):
                    _fields_ = [("l", ctypes.c_ulong), ("carga", ctypes.c_ulong),
                                ("total", ctypes.c_ulonglong), ("libre", ctypes.c_ulonglong),
                                ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                                ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong),
                                ("e", ctypes.c_ulonglong)]
                m = MEM()
                m.l = ctypes.sizeof(MEM)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
                return m.total / 1024 ** 3, m.libre / 1024 ** 3
            if Path("/proc/meminfo").exists():
                d = {}
                for linea in Path("/proc/meminfo").read_text().splitlines():
                    k, v = linea.split(":")
                    d[k] = int(v.split()[0]) / 1024 ** 2
                return d["MemTotal"], d.get("MemAvailable", d["MemFree"])
        except Exception:
            pass
        return None, None

    @classmethod
    def gpus(cls):
        """Lista de dicts {nombre, tipo} con tipo en dedicada / integrada / desconocida."""
        nombres = []
        try:
            if sys.platform == "win32":
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                    capture_output=True, text=True, timeout=10, creationflags=0x08000000)
                nombres = [n.strip() for n in r.stdout.splitlines() if n.strip()]
            elif sys.platform == "darwin":
                r = subprocess.run(["system_profiler", "SPDisplaysDataType"],
                                   capture_output=True, text=True, timeout=10)
                nombres = [l.split(":", 1)[1].strip() for l in r.stdout.splitlines()
                           if "Chipset Model" in l]
            else:
                r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
                nombres = [l.split(":", 2)[-1].strip() for l in r.stdout.splitlines()
                           if re.search(r"vga|3d|display", l, re.I)]
        except Exception:
            nombres = []
        salida = []
        for n in nombres:
            if cls.RE_DEDICADA.search(n):
                tipo = "dedicada"
            elif cls.RE_INTEGRADA.search(n):
                tipo = "integrada"
            else:
                tipo = "desconocida"
            salida.append({"nombre": n, "tipo": tipo})
        return salida

    @classmethod
    def diagnostico(cls):
        total, libre = cls.ram()
        gpus = cls.gpus()
        if any(g["tipo"] == "dedicada" for g in gpus):
            tipo_gpu = "dedicada"
        elif gpus:
            tipo_gpu = "integrada" if any(g["tipo"] == "integrada" for g in gpus) else "desconocida"
        else:
            tipo_gpu = "no detectada"
        return {"ram_total": total, "ram_libre": libre, "gpus": gpus, "tipo_gpu": tipo_gpu}

    # Mediciones de referencia (netplotbrain, template pequeño, mismos nodos):
    #   estilo    voxel  tiempo    RAM pico
    #   surface     4    0.29 s     21 MB
    #   surface     2    0.59 s     21 MB
    #   surface     1    2.59 s     83 MB
    #   cloudy      4    0.29 s     21 MB
    #   cloudy      2    0.66 s     49 MB
    #   cloudy      1    5.01 s    380 MB
    #   glass       4    1.18 s     21 MB
    #   glass       2    2.02 s     48 MB
    #   filled      4  102.56 s    225 MB   <- caso atípico: ~350x más lento
    #                                          que surface incluso en su ajuste
    #                                          más suave.
    # Con un template real (más grande) los tiempos y la RAM absolutos suben,
    # pero la relación entre estilos/voxel se mantiene igual de parecida, así
    # que sirve para clasificar sin tener que medir cada combinación posible.
    @staticmethod
    def estimar_tarea(estilo, voxel, vista=None, frames=None, node_type=None):
        """Clasifica una configuración de render en 'ligero'/'moderado'/'pesado'."""
        puntos = 0
        if estilo == "filled":
            puntos += 7  # ya es "pesado" aun en su ajuste más suave (medido: 102s a voxel 4)
        elif estilo == "glass":
            puntos += 2
        elif estilo == "cloudy":
            puntos += 1
        if node_type == "parcels":
            puntos += 5  # parcels pinta cada región del atlas en 3D; render muy lento
        if voxel is not None:
            if voxel <= 1:
                puntos += 3
            elif voxel == 2:
                puntos += 1
        if vista == "360" and frames:
            puntos += 1 + frames // 8
        if puntos >= 7:
            nivel = "pesado"
        elif puntos >= 3:
            nivel = "moderado"
        else:
            nivel = "ligero"
        return nivel, puntos

    @staticmethod
    def problemas(diag, estilo=None, voxel=None, vista=None, frames=None, node_type=None):
        """Devuelve (lista_de_motivos, ajustes_recomendados_dict)."""
        motivos, ajustes = [], {}
        total, libre = diag["ram_total"], diag["ram_libre"]
        nivel = None
        if estilo is not None:
            nivel, _ = Recursos.estimar_tarea(estilo, voxel, vista, frames, node_type)

        requiere_gb = {"ligero": 1.0, "moderado": 2.5, "pesado": 5.0}.get(nivel, 2.0)
        if libre is not None and libre < requiere_gb:
            if nivel:
                motivos.append(
                    f"Esta configuración ({nivel}) suele necesitar más RAM libre de la que "
                    f"tienes ahora ({libre:.1f} GB; se recomiendan ~{requiere_gb:.0f} GB).")
            else:
                motivos.append(f"Memoria RAM libre baja: {libre:.1f} GB.")
        if total is not None and total < 8.0 and nivel in (None, "moderado", "pesado"):
            motivos.append(f"Memoria RAM total limitada: {total:.1f} GB.")

        if estilo == "glass" and diag["tipo_gpu"] != "dedicada":
            motivos.append("El estilo 'glass' suele tardar más sin tarjeta gráfica dedicada.")
            ajustes["estilo"] = "surface"
        if estilo == "filled":
            motivos.append(
                "El estilo 'filled' es, con mucho, el más lento (en nuestras pruebas, "
                "~350 veces más que 'surface' incluso con voxel size grande).")
            ajustes.setdefault("estilo", "surface")
            ajustes.setdefault("voxel", 3)
        if node_type == "parcels":
            motivos.append(
                "El tipo de nodo 'parcels' pinta cada región del atlas en 3D. "
                "Es un proceso muy lento que puede tardar muchos minutos; "
                "puedes cancelar el render en cualquier momento desde el botón Cancelar.")
            ajustes.setdefault("node_type", "circles")
        if nivel == "pesado" and voxel is not None and voxel < 3:
            ajustes.setdefault("voxel", 3)
        return motivos, ajustes

    @staticmethod
    def texto_resumen(diag):
        partes = []
        if diag["ram_total"] is not None:
            partes.append(f"RAM {diag['ram_total']:.0f} GB ({diag['ram_libre']:.1f} libres)")
        if diag["gpus"]:
            partes.append("GPU: " + "; ".join(f"{g['nombre']} ({g['tipo']})" for g in diag["gpus"]))
        else:
            partes.append("GPU no detectada")
        return "  ·  ".join(partes)


# ══════════════════════════════════════════════
# Lectura de archivos (CSV / TSV / Excel)
# ══════════════════════════════════════════════
def leer_csv_robusto(ruta, header=0):
    muestra, codificacion = "", "utf-8-sig"
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, "r", encoding=enc, newline="") as f:
                muestra = f.read(4096)
            codificacion = enc
            break
        except UnicodeDecodeError:
            continue
    try:
        sep = csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        sep = "\t" if str(ruta).lower().endswith(".tsv") else ","
    decimal = "," if sep == ";" else "."
    return pd.read_csv(ruta, sep=sep, decimal=decimal, encoding=codificacion, header=header)


def leer_tabla_archivo(ruta, elegir_hoja=None, header=0):
    """Lee CSV/TSV/TXT o Excel y devuelve un DataFrame."""
    ext = Path(ruta).suffix.lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        try:
            libro = pd.ExcelFile(ruta)
        except ImportError as e:
            raise RuntimeError(
                "Falta una librería para leer Excel.\n"
                "Solución:  pip install openpyxl xlrd") from e
        hojas = libro.sheet_names
        hoja = hojas[0]
        if len(hojas) > 1 and elegir_hoja is not None:
            hoja = elegir_hoja(hojas)
            if hoja is None:
                return None
        return libro.parse(hoja, header=header)
    return leer_csv_robusto(ruta, header=header)


def mapear_columnas(df, columnas, requeridas):
    """Renombra columnas usando alias. Devuelve (df_nuevo, faltantes)."""
    inverso = {}
    for canon in columnas:
        for alias in ALIAS_COLUMNAS.get(canon, [canon]):
            inverso[_normalizar(alias)] = canon
    nuevo = {}
    for col in df.columns:
        canon = inverso.get(_normalizar(col))
        if canon and canon not in nuevo.values():
            nuevo[col] = canon
    df = df.rename(columns=nuevo)
    faltantes = [c for c in requeridas if c not in df.columns]
    return df, faltantes


def a_matriz(df):
    """Convierte un DataFrame a matriz numérica, descartando encabezados si hace falta."""
    intentos = [df, df.iloc[1:, :], df.iloc[:, 1:], df.iloc[1:, 1:]]
    for candidato in intentos:
        num = candidato.apply(pd.to_numeric, errors="coerce")
        if num.size and not num.isna().any().any():
            return num.to_numpy(dtype=float)
    raise ValueError("La matriz contiene celdas no numéricas.")


def leer_matriz_archivo(ruta, elegir_hoja=None):
    if str(ruta).lower().endswith(".npy"):
        return np.load(ruta)
    df = leer_tabla_archivo(ruta, elegir_hoja=elegir_hoja, header=None)
    if df is None:
        return None
    return a_matriz(df)


# ══════════════════════════════════════════════
# Validación de datos
# ══════════════════════════════════════════════
class ValidadorDatos:
    @staticmethod
    def nodos(df):
        errs = []
        if df.empty:
            return ["La tabla de nodos está vacía."]
        for c in ["x", "y", "z"]:
            if c not in df.columns:
                errs.append(f"Falta la columna '{c}'.")
            elif not pd.api.types.is_numeric_dtype(df[c]):
                errs.append(f"La columna '{c}' debe ser numérica.")
        return errs

    @staticmethod
    def aristas(df, n):
        errs = []
        for c in ["i", "j"]:
            if c not in df.columns:
                return [f"Falta la columna '{c}'."]
        if not pd.api.types.is_numeric_dtype(df["i"]) or not pd.api.types.is_numeric_dtype(df["j"]):
            return ["Las columnas 'i' y 'j' deben ser numéricas."]
        mx = n - 1
        if not df[df["i"] > mx].empty:
            errs.append(f"Hay aristas con 'i' fuera de rango (máximo {mx}).")
        if not df[df["j"] > mx].empty:
            errs.append(f"Hay aristas con 'j' fuera de rango (máximo {mx}).")
        lazos = df[df["i"] == df["j"]]
        if not lazos.empty:
            errs.append(f"Hay {len(lazos)} arista(s) de un nodo consigo mismo.")
        return errs

    @staticmethod
    def matriz(mat, n_nodos=None):
        errs = []
        if mat.ndim != 2:
            errs.append("La matriz debe ser bidimensional.")
        elif mat.shape[0] != mat.shape[1]:
            errs.append(f"La matriz no es cuadrada: {mat.shape[0]}×{mat.shape[1]}.")
        if n_nodos and mat.ndim == 2 and mat.shape[0] != n_nodos:
            errs.append(f"La matriz tiene {mat.shape[0]} filas pero hay {n_nodos} nodos.")
        return errs

    @staticmethod
    def limpiar_aristas(df, n):
        if df.empty:
            return df, 0
        mx = n - 1
        mascara = (df["i"] <= mx) & (df["j"] <= mx)
        return df[mascara].reset_index(drop=True), int(len(df) - mascara.sum())


# ══════════════════════════════════════════════
# Archivero de templates
# ══════════════════════════════════════════════
class GestorTemplates:
    @staticmethod
    def carpeta():
        return Path(os.environ.get("TEMPLATEFLOW_HOME", Path.home() / ".cache" / "templateflow"))

    @staticmethod
    def disponibles():
        try:
            return sorted(tflow.templates())
        except Exception:
            return []

    @staticmethod
    def descargado(nombre):
        base = nombre.split("_cohort")[0]
        carpeta = GestorTemplates.carpeta() / f"tpl-{base}"
        return carpeta.exists() and any(carpeta.rglob("*.nii*"))

    @staticmethod
    def descargar(nombre):
        tflow.get(nombre, suffix="T1w")


# ══════════════════════════════════════════════
# Widgets propios
# ══════════════════════════════════════════════
class Spinner(tk.Canvas):
    """Círculo de carga animado."""

    def __init__(self, parent, tam=52, bg=None):
        super().__init__(parent, width=tam, height=tam, highlightthickness=0, bg=bg or C["panel"])
        pad = tam * 0.12
        self.create_oval(pad, pad, tam - pad, tam - pad, outline=C["borde"], width=4)
        self.arco = self.create_arc(pad, pad, tam - pad, tam - pad, start=0, extent=100,
                                    style="arc", outline=C["acento"], width=4)
        self.angulo = 0
        self._job = None

    def iniciar(self):
        if self._job is None:
            self._tick()

    def _tick(self):
        self.angulo = (self.angulo - 12) % 360
        self.itemconfigure(self.arco, start=self.angulo)
        self._job = self.after(30, self._tick)

    def detener(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None


class FilaDeslizador(ttk.Frame):
    def __init__(self, parent, texto, variable, desde, hasta, comando=None):
        super().__init__(parent, style="Panel.TFrame")
        self.var = variable
        self.comando = comando
        ttk.Label(self, text=texto, width=15, style="Panel.TLabel").pack(side="left")
        self.etq = ttk.Label(self, text=str(variable.get()), width=4, anchor="e", style="Valor.TLabel")
        self.etq.pack(side="right")
        self.esc = ttk.Scale(self, from_=desde, to=hasta, orient="horizontal", command=self._cambio)
        self.esc.set(variable.get())
        self.esc.pack(side="right", fill="x", expand=True, padx=6)

    def _cambio(self, valor):
        n = int(round(float(valor)))
        self.var.set(n)
        self.etq.configure(text=str(n))
        if self.comando:
            self.comando()

    def fijar(self, n):
        self.esc.set(n)
        self._cambio(n)


class EditorTabla(ttk.Frame):
    """Tabla editable con formulario, importación (CSV/Excel) y exportación CSV."""

    def __init__(self, parent, app, columnas, requeridas, por_defecto, tipos, en_cambio, en_formulario=None):
        super().__init__(parent, style="Panel.TFrame")
        self.app = app
        self.columnas = columnas
        self.requeridas = requeridas
        self.por_defecto = por_defecto
        self.tipos = tipos
        self.en_cambio = en_cambio
        self.en_formulario = en_formulario

        marco = ttk.Frame(self, style="Panel.TFrame")
        marco.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(marco, columns=columnas, show="headings", height=7, selectmode="browse")
        for col in columnas:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=90, anchor="center")
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._al_seleccionar)

        # Formulario en línea (alimenta la vista previa en tiempo real)
        form = ttk.Frame(self, style="Panel.TFrame")
        form.pack(fill="x", pady=(8, 0))
        self.entradas = {}
        for k, col in enumerate(columnas):
            f = ttk.Frame(form, style="Panel.TFrame")
            f.grid(row=0, column=k, padx=(0, 6), sticky="ew")
            ttk.Label(f, text=col.capitalize(), style="Sec.TLabel").pack(anchor="w")
            e = ttk.Entry(f, width=9)
            e.pack(fill="x")
            e.bind("<KeyRelease>", self._al_teclear)
            self.entradas[col] = e
            form.columnconfigure(k, weight=1)
        self.limpiar_formulario()

        self.error_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.error_var, foreground=C["error"], style="Panel.TLabel").pack(anchor="w")

        botones = ttk.Frame(self, style="Panel.TFrame")
        botones.pack(fill="x", pady=(4, 0))
        ttk.Button(botones, text="Agregar", command=self.agregar).pack(side="left", padx=(0, 4))
        ttk.Button(botones, text="Actualizar selección", command=self.actualizar).pack(side="left", padx=4)
        ttk.Button(botones, text="Eliminar", command=self.eliminar).pack(side="left", padx=4)
        ttk.Button(botones, text="Exportar CSV", command=self.exportar).pack(side="right", padx=(4, 0))
        ttk.Button(botones, text="Importar CSV / Excel", command=self.importar).pack(side="right", padx=4)

    # ── formulario ──
    def limpiar_formulario(self):
        for col, e in self.entradas.items():
            e.delete(0, "end")
            e.insert(0, self.por_defecto()[self.columnas.index(col)])

    def valores_formulario(self):
        return {c: e.get().strip() for c, e in self.entradas.items()}

    def _al_teclear(self, _evento=None):
        self.error_var.set("")
        if self.en_formulario:
            self.en_formulario(self.valores_formulario())

    def _al_seleccionar(self, _evento=None):
        sel = self.tree.selection()
        if not sel:
            return
        valores = self.tree.item(sel[0], "values")
        for col, v in zip(self.columnas, valores):
            self.entradas[col].delete(0, "end")
            self.entradas[col].insert(0, v)
        self.error_var.set("")
        if self.en_formulario:
            self.en_formulario(self.valores_formulario())

    def _validar_formulario(self):
        vals = self.valores_formulario()
        for col, tipo in self.tipos.items():
            v = vals[col]
            if tipo == "float":
                try:
                    float(v.replace(",", "."))
                except ValueError:
                    return None, f"'{col}' debe ser un número."
            elif tipo == "int":
                try:
                    if int(float(v)) != float(v) or float(v) < 0:
                        raise ValueError
                except ValueError:
                    return None, f"'{col}' debe ser un entero mayor o igual a 0."
            elif tipo == "texto" and v == "":
                return None, f"'{col}' no puede estar vacío."
        fila = tuple(vals[c].replace(",", ".") if self.tipos.get(c) == "float" else vals[c]
                     for c in self.columnas)
        return fila, None

    # ── acciones ──
    def agregar(self):
        fila, err = self._validar_formulario()
        if err:
            self.error_var.set(err)
            return
        item = self.tree.insert("", "end", values=fila)
        self.tree.selection_set(item)
        self.tree.see(item)
        self.en_cambio()

    def actualizar(self):
        sel = self.tree.selection()
        if not sel:
            self.error_var.set("Selecciona una fila de la tabla para actualizarla.")
            return
        fila, err = self._validar_formulario()
        if err:
            self.error_var.set(err)
            return
        self.tree.item(sel[0], values=fila)
        self.en_cambio()

    def eliminar(self):
        sel = self.tree.selection()
        if not sel:
            self.error_var.set("Selecciona una fila para eliminarla.")
            return
        self.tree.delete(sel[0])
        self.en_cambio()

    def poner_filas(self, filas):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for f in filas:
            self.tree.insert("", "end", values=tuple(str(v) for v in f))
        self.en_cambio()

    def limpiar(self):
        self.poner_filas([])

    def obtener_dataframe(self):
        datos = [self.tree.item(i, "values") for i in self.tree.get_children()]
        df = pd.DataFrame(datos, columns=self.columnas)
        for col in df.columns:
            conv = pd.to_numeric(df[col], errors="coerce")
            if not conv.isna().any():
                df[col] = conv
        return df

    def importar(self):
        ruta = filedialog.askopenfilename(
            title="Importar tabla",
            filetypes=[("Tablas", "*.csv *.tsv *.txt *.xlsx *.xlsm *.xls"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            df = leer_tabla_archivo(ruta, elegir_hoja=self.app.elegir_hoja)
            if df is None:
                return
            df, faltantes = mapear_columnas(df, self.columnas, self.requeridas)
            if faltantes:
                # ¿Sin encabezados? Se ofrece interpretar las columnas por posición.
                sin_enc = leer_tabla_archivo(ruta, elegir_hoja=None, header=None)
                if sin_enc is not None and sin_enc.shape[1] >= len(self.requeridas):
                    if messagebox.askyesno(
                            "Encabezados no encontrados",
                            f"No se encontraron las columnas: {', '.join(faltantes)}.\n\n"
                            f"¿Interpretar las columnas del archivo en este orden?\n"
                            f"{', '.join(self.columnas)}"):
                        df = sin_enc.iloc[:, :len(self.columnas)].copy()
                        df.columns = self.columnas[:df.shape[1]]
                        faltantes = []
                if faltantes:
                    messagebox.showerror("Importar", f"Faltan las columnas requeridas: {', '.join(faltantes)}.")
                    return
            for c in self.columnas:
                if c not in df.columns:
                    df[c] = self.por_defecto()[self.columnas.index(c)]
            df = df[list(self.columnas)].dropna(how="all")
            filas = [tuple(str(v) for v in fila) for fila in df.itertuples(index=False, name=None)]
            if self.tree.get_children():
                r = messagebox.askyesnocancel(
                    "Importar", "La tabla ya tiene datos.\n\nSí = reemplazar\nNo = agregar al final")
                if r is None:
                    return
                if not r:
                    filas = [self.tree.item(i, "values") for i in self.tree.get_children()] + filas
            self.poner_filas(filas)
            messagebox.showinfo("Importar", f"Se importaron {len(df)} filas.")
        except Exception as e:
            messagebox.showerror("Error al importar", str(e))

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        try:
            datos = [self.tree.item(i, "values") for i in self.tree.get_children()]
            pd.DataFrame(datos, columns=self.columnas).to_csv(ruta, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Exportar", f"Archivo guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))


# ══════════════════════════════════════════════
# Vista previa esquemática (sagital / coronal / transversal)
# ══════════════════════════════════════════════
def _elipse(cx, cy, a, b, n=72, huevo=0.0):
    pts = []
    for k in range(n):
        t = 2 * np.pi * k / n
        ancho = 1.0 - huevo * max(0.0, np.sin(t))
        pts.append((cx + a * ancho * np.cos(t), cy + b * np.sin(t)))
    return pts


class VistaPrevia(ttk.Frame):
    """Tres cortes esquemáticos que se redibujan al editar coordenadas."""

    # h/v: columna que va en el eje horizontal y vertical de cada corte.
    CORTES = {
        "Sagital": dict(h="y", v="z", lim=(-118, 88, -68, 92), izq="Post", der="Ant", sup="Sup", inf="Inf"),
        "Coronal": dict(h="x", v="z", lim=(-88, 88, -68, 92), izq="Izq", der="Der", sup="Sup", inf="Inf"),
        "Transversal": dict(h="x", v="y", lim=(-88, 88, -118, 88), izq="Izq", der="Der", sup="Ant", inf="Post"),
    }

    NOMBRES_ARCHIVO = {"Sagital": "preview_sagital.png", "Coronal": "preview_coronal.png",
                       "Transversal": "preview_transversal.png"}

    def __init__(self, parent, app):
        super().__init__(parent, style="Panel.TFrame")
        self.app = app
        self.escala = 1.0
        self.candidato = None
        self._job = None
        self.lienzos = {}
        self._fotos = {}  # referencias vivas a los ImageTk.PhotoImage (si no, Tk las recicla)
        self.fondo = self._cargar_fondo_real()
        fila = ttk.Frame(self, style="Panel.TFrame")
        fila.pack(fill="both", expand=True)
        for k, nombre in enumerate(self.CORTES):
            col = ttk.Frame(fila, style="Panel.TFrame")
            col.grid(row=0, column=k, sticky="nsew", padx=3)
            fila.columnconfigure(k, weight=1)
            ttk.Label(col, text=nombre, style="Sec.TLabel").pack(anchor="w")
            cv = tk.Canvas(col, height=190, bg=C["panel"], highlightthickness=1,
                           highlightbackground=C["borde"])
            cv.pack(fill="both", expand=True)
            cv.bind("<Configure>", lambda e: self.programar())
            self.lienzos[nombre] = cv
        texto_pie = ("Cortes reales (template ligero descargado con generar_vista_previa.py)."
                    if self.fondo else "Vista esquemática aproximada. No representa el template real.")
        self.etq_pie = ttk.Label(self, text=texto_pie, style="Sec.TLabel")
        self.etq_pie.pack(anchor="w", pady=(4, 0))

    def _cargar_fondo_real(self):
        """
        Si existe assets/preview_*.png + preview_meta.json (generados con
        generar_vista_previa.py a partir de un template real), los usa como
        fondo. Si falta cualquier cosa o algo falla, se sigue con el dibujo
        esquemático de siempre — esto nunca es un error para el usuario.
        """
        try:
            carpeta_assets = Path(__file__).resolve().parent / "assets"
            meta_path = carpeta_assets / "preview_meta.json"
            if not meta_path.exists():
                return None
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fondo = {}
            for nombre, archivo in self.NOMBRES_ARCHIVO.items():
                ruta_img = carpeta_assets / archivo
                if nombre not in meta or not ruta_img.exists():
                    return None
                datos = dict(meta[nombre])
                datos["imagen"] = PILImage.open(ruta_img).convert("L")
                fondo[nombre] = datos
            return fondo
        except Exception:
            return None

    def fijar_escala(self, escala):
        self.escala = escala
        self.programar()

    def fijar_candidato(self, xyz):
        self.candidato = xyz
        self.programar()

    def programar(self):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(50, self.dibujar)

    # ── geometría de cada corte, en mm (h, v) ──
    def _formas(self, nombre):
        if nombre == "Sagital":
            return [(_elipse(-17, 28, 88, 52), True), (_elipse(-62, -32, 27, 17), True),
                    ([(-30, -15), (-8, -15), (-4, -58), (-24, -58)], True)], (-17, 28)
        if nombre == "Coronal":
            return [(_elipse(0, 30, 70, 52), True),
                    ([(-9, -20), (9, -20), (8, -58), (-8, -58)], True)], (0, 30)
        return [(_elipse(0, -17.5, 70, 87.5, huevo=0.16), True)], (0, -17.5)

    def dibujar(self):
        self._job = None
        df = self.app.editor_nodos.obtener_dataframe()
        aristas = self.app.editor_aristas.obtener_dataframe()
        for nombre, cv in self.lienzos.items():
            cfg = self.CORTES[nombre]
            cv.delete("all")
            w, h = max(cv.winfo_width(), 60), max(cv.winfo_height(), 60)
            datos_fondo = self.fondo.get(nombre) if self.fondo else None

            if datos_fondo is not None:
                h0, h1 = datos_fondo["h_min"], datos_fondo["h_max"]
                v0, v1 = datos_fondo["v_min"], datos_fondo["v_max"]
            else:
                h0, h1, v0, v1 = cfg["lim"]
            esc = min((w - 26) / (h1 - h0), (h - 22) / (v1 - v0))
            ox = w / 2 - esc * (h0 + h1) / 2
            oy = h / 2 + esc * (v0 + v1) / 2

            def px(hh, vv):
                return ox + esc * hh, oy - esc * vv

            if datos_fondo is not None:
                # La imagen real ya cubre exactamente [h0,h1]x[v0,v1], así que se
                # escala al mismo tamaño en pantalla que usa px() para los nodos.
                aw = max(int(round(esc * (h1 - h0))), 1)
                ah = max(int(round(esc * (v1 - v0))), 1)
                img = datos_fondo["imagen"].resize((aw, ah), PILImage.LANCZOS)
                foto = ImageTk.PhotoImage(img)
                self._fotos[nombre] = foto  # evita que Tk la recicle
                x0, y0 = px(h0, v1)  # esquina superior-izquierda de la imagen en pantalla
                cv.create_image(x0, y0, image=foto, anchor="nw")
            else:
                formas, (cx, cy) = self._formas(nombre)
                for pts, _ in formas:
                    escalados = [(cx + (p[0] - cx) * self.escala, cy + (p[1] - cy) * self.escala) for p in pts]
                    plano = [c for p in escalados for c in px(*p)]
                    cv.create_polygon(plano, fill=C["cerebro"], outline=C["cerebro_borde"], width=1, smooth=False)
            # línea media / guía
            if nombre != "Sagital":
                x0, y0 = px(0, v0)
                x1, y1 = px(0, v1)
                cv.create_line(x0, y0, x1, y1, fill=C["guia"], dash=(3, 3))
            # etiquetas de orientación
            cv.create_text(6, h / 2, text=cfg["izq"], anchor="w", fill=C["texto2"], font=("", 8))
            cv.create_text(w - 6, h / 2, text=cfg["der"], anchor="e", fill=C["texto2"], font=("", 8))
            cv.create_text(w / 2, 8, text=cfg["sup"], fill=C["texto2"], font=("", 8))
            cv.create_text(w / 2, h - 8, text=cfg["inf"], fill=C["texto2"], font=("", 8))

            if not df.empty and all(c in df.columns and pd.api.types.is_numeric_dtype(df[c]) for c in "xyz"):
                # aristas (máximo 400 para mantener fluidez)
                if not aristas.empty and all(c in aristas.columns and pd.api.types.is_numeric_dtype(aristas[c])
                                             for c in ("i", "j")):
                    for _, a in aristas.head(400).iterrows():
                        i, j = int(a["i"]), int(a["j"])
                        if 0 <= i < len(df) and 0 <= j < len(df):
                            p1 = px(df.iloc[i][cfg["h"]], df.iloc[i][cfg["v"]])
                            p2 = px(df.iloc[j][cfg["h"]], df.iloc[j][cfg["v"]])
                            cv.create_line(*p1, *p2, fill="#B7C0CB")
                comunidades = {}
                for _, n in df.iterrows():
                    clave = n["comunidad"] if "comunidad" in df.columns else 0
                    color = PALETA_COMUNIDADES[comunidades.setdefault(clave, len(comunidades)) % len(PALETA_COMUNIDADES)]
                    cx_, cy_ = px(n[cfg["h"]], n[cfg["v"]])
                    cv.create_oval(cx_ - 3.5, cy_ - 3.5, cx_ + 3.5, cy_ + 3.5, fill=color, outline="white")

            if self.candidato is not None:
                d = dict(zip("xyz", self.candidato))
                cx_, cy_ = px(d[cfg["h"]], d[cfg["v"]])
                cv.create_line(cx_, 0, cx_, h, fill=C["acento"], dash=(2, 3))
                cv.create_line(0, cy_, w, cy_, fill=C["acento"], dash=(2, 3))
                cv.create_oval(cx_ - 5, cy_ - 5, cx_ + 5, cy_ + 5, outline=C["acento"], width=2)
                cv.create_text(w - 6, h - 20, anchor="e", fill=C["acento"], font=("", 8),
                               text=f"x {self.candidato[0]:g}   y {self.candidato[1]:g}   z {self.candidato[2]:g}")


# ══════════════════════════════════════════════
# Aplicación principal
# ══════════════════════════════════════════════
class AplicacionNetPlotBrain:
    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title(f"NetPlotBrain GUI v{VERSION}")
        self.raiz.geometry("1200x820")
        self.raiz.minsize(1040, 720)
        self.raiz.configure(bg=C["fondo"])

        self.ruta_template_nifti = None
        self.ruta_nodos_nifti = None
        self.ruta_matriz = None
        self.modo_nodos = tk.StringVar(value="tabla")     # tabla | nifti | atlas
        self.modo_aristas = tk.StringVar(value="tabla")   # tabla | matriz
        self.diag_recursos = None
        self._ocupado = False
        self.ultima_figura = None
        self.ultima_png = None
        self.ventana_figura = None
        self.config = Config.leer()
        # El token (solo para Spaces privados) vive únicamente en memoria durante la sesión.
        self.token_nube = os.environ.get("NETPLOTBRAIN_NUBE_TOKEN", "")

        self._construir_interfaz()
        self._cargar_demo()
        self._actualizar_fuente()
        self.vista_previa.programar()
        self._diag_resultado = None
        threading.Thread(target=self._diagnosticar_recursos, daemon=True).start()
        self.raiz.after(300, self._esperar_diagnostico)

    # ── interfaz ──
    def _construir_interfaz(self):
        # Cabecera
        cab = tk.Frame(self.raiz, bg=C["cabecera"], height=64)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        izq = tk.Frame(cab, bg=C["cabecera"])
        izq.pack(side="left", padx=18, fill="y")
        tk.Label(izq, text="NetPlotBrain GUI", bg=C["cabecera"], fg=C["cabecera_txt"],
                 font=(self.fuente, 16, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(izq, text="Visualización de redes cerebrales en 3D", bg=C["cabecera"],
                 fg=C["cabecera_txt2"], font=(self.fuente, 9)).pack(anchor="w")
        der = tk.Frame(cab, bg=C["cabecera"])
        der.pack(side="right", padx=18, fill="y")
        self.recursos_var = tk.StringVar(value="Analizando recursos del equipo…")
        self.lbl_recursos = tk.Label(der, textvariable=self.recursos_var, bg=C["cabecera"], fg=C["cabecera_txt2"],
                                     font=(self.fuente, 9), wraplength=480, justify="right")
        self.lbl_recursos.pack(side="left", padx=(0, 10))
        ttk.Button(der, text="Recursos", style="Cabecera.TButton",
                   command=self.mostrar_recursos).pack(side="left", pady=16)
        ttk.Button(der, text="Nube", style="Cabecera.TButton",
                   command=self.configurar_nube).pack(side="left", padx=(8, 0), pady=16)

        cuerpo = ttk.Frame(self.raiz, style="Fondo.TFrame")
        cuerpo.pack(fill="both", expand=True, padx=12, pady=10)

        # ── Panel izquierdo ──
        izquierdo = ttk.Frame(cuerpo, style="Panel.TFrame", padding=14)
        izquierdo.pack(side="left", fill="y", padx=(0, 10))
        izquierdo.configure(borderwidth=1, relief="solid")

        def seccion(texto):
            ttk.Label(izquierdo, text=texto, style="Seccion.TLabel").pack(fill="x", pady=(10, 2))
            ttk.Separator(izquierdo).pack(fill="x", pady=(0, 4))

        def combo(texto, variable, valores, comando=None):
            f = ttk.Frame(izquierdo, style="Panel.TFrame")
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=texto, width=15, style="Panel.TLabel").pack(side="left")
            c = ttk.Combobox(f, textvariable=variable, values=valores, state="readonly", width=26)
            c.pack(side="right", fill="x", expand=True)
            if comando:
                c.bind("<<ComboboxSelected>>", comando)
            return c

        seccion("Template")
        self.var_template = tk.StringVar(value="MNI152NLin2009cAsym")
        self.combo_template = combo("Template", self.var_template, self._lista_templates(),
                                    self._al_cambiar_template)
        self.marco_nifti = ttk.Frame(izquierdo, style="Panel.TFrame")
        self.etq_nifti = ttk.Label(self.marco_nifti, text="Sin archivo", style="Sec.TLabel")
        self.etq_nifti.pack(side="left")
        ttk.Button(self.marco_nifti, text="Elegir NIfTI…", command=self._elegir_template_nifti).pack(side="right")

        self.var_estilo = tk.StringVar(value="surface")
        combo("Estilo", self.var_estilo, ESTILOS)
        self.var_opacidad = tk.IntVar(value=30)
        FilaDeslizador(izquierdo, "Opacidad (%)", self.var_opacidad, 1, 100).pack(fill="x", pady=2)
        self.var_voxel = tk.IntVar(value=2)
        self.fila_voxel = FilaDeslizador(izquierdo, "Voxel size", self.var_voxel, 1, 5)
        self.fila_voxel.pack(fill="x", pady=2)

        seccion("Visualización")
        self.var_vista = tk.StringVar(value="preset-4")
        combo("Vista", self.var_vista, VISTAS)
        self.var_hemisferio = tk.StringVar(value="ambos")
        combo("Hemisferio", self.var_hemisferio, HEMISFERIOS)
        self.var_cuadros = tk.IntVar(value=8)
        FilaDeslizador(izquierdo, "Cuadros (360)", self.var_cuadros, 4, 24).pack(fill="x", pady=2)

        seccion("Nodos")
        self.var_tipo_nodo = tk.StringVar(value="circles")
        self.combo_tipo_nodo = combo("Tipo", self.var_tipo_nodo, TIPOS_NODO)
        self.var_escala_nodo = tk.IntVar(value=40)
        FilaDeslizador(izquierdo, "Escala", self.var_escala_nodo, 5, 150).pack(fill="x", pady=2)

        seccion("Aristas")
        self.var_grosor = tk.IntVar(value=1)
        FilaDeslizador(izquierdo, "Grosor", self.var_grosor, 1, 10).pack(fill="x", pady=2)
        self.var_umbral = tk.IntVar(value=0)
        FilaDeslizador(izquierdo, "Umbral (%)", self.var_umbral, 0, 100).pack(fill="x", pady=2)

        f = ttk.Frame(izquierdo, style="Panel.TFrame")
        f.pack(fill="x", pady=(10, 2))
        ttk.Label(f, text="Título", width=15, style="Panel.TLabel").pack(side="left")
        self.var_titulo = tk.StringVar(value="Mi red cerebral")
        ttk.Entry(f, textvariable=self.var_titulo).pack(side="right", fill="x", expand=True)

        ttk.Separator(izquierdo).pack(fill="x", pady=10)
        ttk.Button(izquierdo, text="Generar datos aleatorios", command=self._generar_aleatorio).pack(fill="x", pady=2)
        ttk.Button(izquierdo, text="Archivero de templates", command=self._abrir_archivero).pack(fill="x", pady=2)
        self.btn_guardar = ttk.Button(izquierdo, text="Guardar última imagen…", command=self._guardar_imagen,
                                      state="disabled")
        self.btn_guardar.pack(fill="x", pady=2)
        ttk.Button(izquierdo, text="Generar figura", style="Acento.TButton",
                   command=self.generar_figura).pack(fill="x", pady=(8, 2), ipady=5)

        # ── Panel derecho ──
        derecho = ttk.Frame(cuerpo, style="Fondo.TFrame")
        derecho.pack(side="right", fill="both", expand=True)

        self.cuaderno = ttk.Notebook(derecho)
        self.cuaderno.pack(fill="both", expand=True)

        pestana_nodos = ttk.Frame(self.cuaderno, style="Panel.TFrame", padding=10)
        pestana_aristas = ttk.Frame(self.cuaderno, style="Panel.TFrame", padding=10)
        pestana_archivo = ttk.Frame(self.cuaderno, style="Panel.TFrame", padding=14)
        pestana_matriz = ttk.Frame(self.cuaderno, style="Panel.TFrame", padding=14)
        self.cuaderno.add(pestana_nodos, text="Nodos")
        self.cuaderno.add(pestana_aristas, text="Aristas")
        self.cuaderno.add(pestana_archivo, text="Nodos desde NIfTI / Atlas")
        self.cuaderno.add(pestana_matriz, text="Matriz de adyacencia")

        self.vista_previa = None  # se crea después de los editores, pero el editor la usa
        self.editor_nodos = EditorTabla(
            pestana_nodos, self, COLUMNAS_NODOS, ("x", "y", "z"), lambda: ("0", "0", "0", "1", "1.0"),
            {"x": "float", "y": "float", "z": "float", "comunidad": "texto", "centralidad": "float"},
            self._datos_cambiaron, self._formulario_nodo)
        self.editor_nodos.pack(fill="both", expand=True)
        self.editor_aristas = EditorTabla(
            pestana_aristas, self, COLUMNAS_ARISTAS, ("i", "j"), lambda: ("0", "1", "1.0"),
            {"i": "int", "j": "int", "peso": "float"}, self._datos_cambiaron)
        self.editor_aristas.pack(fill="both", expand=True)

        self._construir_pestana_archivo(pestana_archivo)
        self._construir_pestana_matriz(pestana_matriz)

        marco_prev = ttk.Frame(derecho, style="Panel.TFrame", padding=(10, 8))
        marco_prev.pack(fill="x", pady=(10, 0))
        marco_prev.configure(borderwidth=1, relief="solid")
        ttk.Label(marco_prev, text="Vista previa en tiempo real", style="Seccion.TLabel").pack(anchor="w")
        self.vista_previa = VistaPrevia(marco_prev, self)
        self.vista_previa.pack(fill="x", pady=(4, 0))

        # Barra de estado
        pie = ttk.Frame(self.raiz, style="Fondo.TFrame")
        pie.pack(fill="x", padx=12, pady=(0, 8))
        self.var_estado = tk.StringVar(value="Listo.")
        ttk.Label(pie, textvariable=self.var_estado, style="Fondo.TLabel").pack(side="left")
        self.var_fuente = tk.StringVar()
        ttk.Label(pie, textvariable=self.var_fuente, style="Fondo.TLabel").pack(side="right")

        # Superposición de progreso
        self.overlay = tk.Frame(self.raiz, bg=C["panel"], highlightbackground=C["borde"], highlightthickness=1)
        self.spinner = Spinner(self.overlay)
        self.spinner.pack(padx=40, pady=(24, 8))
        self.overlay_msg = ttk.Label(self.overlay, text="", style="Panel.TLabel", justify="center")
        self.overlay_msg.pack(padx=30)
        self.overlay_tiempo = ttk.Label(self.overlay, text="00:00", style="Sec.TLabel")
        self.overlay_tiempo.pack(pady=(4, 8))
        self.btn_cancelar_render = ttk.Button(self.overlay, text="Cancelar", command=self._cancelar_render)
        self.btn_cancelar_render.pack(pady=(0, 20))
        self._evento_cancelar = threading.Event()

    def _construir_pestana_archivo(self, p):
        ttk.Label(p, text="Fuente de nodos", style="Seccion.TLabel").pack(anchor="w")
        f = ttk.Frame(p, style="Panel.TFrame")
        f.pack(anchor="w", pady=(2, 10))
        for valor, texto in [("tabla", "Tabla de nodos"), ("nifti", "Archivo NIfTI"), ("atlas", "Atlas de TemplateFlow")]:
            ttk.Radiobutton(f, text=texto, value=valor, variable=self.modo_nodos,
                            command=self._actualizar_fuente).pack(side="left", padx=(0, 14))

        ttk.Label(p, text="Opción 1: NIfTI de parcelación (.nii / .nii.gz)", style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        self.etq_nodos_nifti = ttk.Label(p, text="Ningún archivo seleccionado", style="Sec.TLabel")
        self.etq_nodos_nifti.pack(anchor="w", padx=12)
        ttk.Button(p, text="Seleccionar NIfTI de parcelación…", command=self._elegir_nodos_nifti).pack(anchor="w", pady=4)

        ttk.Separator(p).pack(fill="x", pady=12)
        ttk.Label(p, text="Opción 2: Atlas de TemplateFlow (se descarga automáticamente)",
                  style="Panel.TLabel").pack(anchor="w", pady=(0, 2))
        self.var_atlas = tk.StringVar(value=list(ATLAS_TEMPLATEFLOW.keys())[0])
        ttk.Combobox(p, textvariable=self.var_atlas, values=list(ATLAS_TEMPLATEFLOW.keys()),
                     state="readonly", width=40).pack(anchor="w", padx=12, pady=4)
        ttk.Button(p, text="Usar este atlas", command=self._usar_atlas).pack(anchor="w", pady=4)
        self.etq_estado_archivo = ttk.Label(p, text="", style="Aviso.TLabel", justify="left")
        self.etq_estado_archivo.pack(anchor="w", pady=10)

    def _construir_pestana_matriz(self, p):
        ttk.Label(p, text="Fuente de aristas", style="Seccion.TLabel").pack(anchor="w")
        f = ttk.Frame(p, style="Panel.TFrame")
        f.pack(anchor="w", pady=(2, 10))
        for valor, texto in [("tabla", "Tabla de aristas"), ("matriz", "Matriz de adyacencia")]:
            ttk.Radiobutton(f, text=texto, value=valor, variable=self.modo_aristas,
                            command=self._actualizar_fuente).pack(side="left", padx=(0, 14))
        ttk.Label(p, text="Matriz cuadrada (NxN) en CSV, Excel (.xlsx / .xls) o NumPy (.npy)",
                  style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        self.etq_matriz = ttk.Label(p, text="Ningún archivo seleccionado", style="Sec.TLabel")
        self.etq_matriz.pack(anchor="w", padx=12)
        ttk.Button(p, text="Seleccionar matriz…", command=self._elegir_matriz).pack(anchor="w", pady=4)
        self.etq_estado_matriz = ttk.Label(p, text="", style="Aviso.TLabel", justify="left")
        self.etq_estado_matriz.pack(anchor="w", pady=10)

    # ── listas / nombres de templates ──
    def _lista_templates(self):
        items = ["— Adulto —", "MNI152NLin2009cAsym", "MNI152NLin6Asym", "OASIS30ANTs", "— Infante —"]
        for i in range(12):
            items.append(f"MNIInfant_cohort-{i}")
        items += ["— Otros —", "WHS (rata)", "NIfTI personalizado…"]
        return items

    def _nombre_template(self, seleccion):
        if seleccion.startswith("—"):
            return None
        if seleccion == "WHS (rata)":
            return "WHS"
        if seleccion.startswith("NIfTI personalizado"):
            return "__custom__"
        return seleccion

    def _al_cambiar_template(self, _evento=None):
        nombre = self._nombre_template(self.var_template.get())
        if nombre is None:
            self.var_template.set("MNI152NLin2009cAsym")
            nombre = "MNI152NLin2009cAsym"
        if nombre == "__custom__":
            self.marco_nifti.pack(fill="x", pady=2, after=self.combo_template.master)
        else:
            self.marco_nifti.pack_forget()
            self.ruta_template_nifti = None
        escala = 1.0
        m = re.search(r"MNIInfant_cohort-(\d+)", nombre)
        if m:
            escala = ESCALA_INFANTIL[min(int(m.group(1)), len(ESCALA_INFANTIL) - 1)]
        self.vista_previa.fijar_escala(escala)

    # ── datos / vista previa ──
    def _datos_cambiaron(self):
        if self.vista_previa is not None:
            self.vista_previa.programar()

    def _formulario_nodo(self, valores):
        try:
            xyz = tuple(float(valores[c].replace(",", ".")) for c in "xyz")
        except ValueError:
            xyz = None
        self.vista_previa.fijar_candidato(xyz)

    def _actualizar_fuente(self):
        # Con nodos desde tabla, 'parcels' no es una opción válida: se retira del
        # desplegable para que no se pueda elegir una combinación que fallaría.
        if self.modo_nodos.get() == "tabla":
            self.combo_tipo_nodo.configure(values=TIPOS_NODO_TABLA)
            if self.var_tipo_nodo.get() == "parcels":
                self.var_tipo_nodo.set("circles")
        else:
            self.combo_tipo_nodo.configure(values=TIPOS_NODO)
        nodos = {"tabla": "tabla", "nifti": "NIfTI", "atlas": "atlas"}[self.modo_nodos.get()]
        aristas = {"tabla": "tabla", "matriz": "matriz"}[self.modo_aristas.get()]
        modo = {"auto": "automático", "local": "local", "nube": "nube"}.get(self.config.get("modo_render", "auto"), "automático")
        self.var_fuente.set(f"Fuente activa: nodos = {nodos}  ·  aristas = {aristas}  ·  render = {modo}")

    def _cargar_demo(self):
        self.editor_nodos.poner_filas([
            ("-20", "60", "30", "1", "0.8"), ("20", "60", "30", "1", "0.6"),
            ("-40", "10", "50", "2", "1.0"), ("40", "10", "50", "2", "0.7"),
            ("0", "-30", "60", "3", "0.9"), ("-30", "-60", "40", "3", "0.5")])
        self.editor_aristas.poner_filas([
            ("0", "1", "0.8"), ("0", "2", "0.5"), ("1", "3", "0.7"),
            ("2", "4", "0.9"), ("3", "4", "0.6"), ("4", "5", "0.4")])

    # ── selección de archivos ──
    def elegir_hoja(self, hojas):
        ventana = tk.Toplevel(self.raiz)
        ventana.title("Elegir hoja")
        ventana.transient(self.raiz)
        ventana.grab_set()
        ventana.configure(bg=C["panel"])
        self._centrar(ventana)
        ttk.Label(ventana, text="El libro tiene varias hojas. ¿Cuál importar?", style="Panel.TLabel").pack(padx=16, pady=(14, 6))
        var = tk.StringVar(value=hojas[0])
        ttk.Combobox(ventana, textvariable=var, values=hojas, state="readonly").pack(padx=16, pady=4)
        resultado = {"hoja": None}

        def aceptar():
            resultado["hoja"] = var.get()
            ventana.destroy()
        ttk.Button(ventana, text="Aceptar", style="Acento.TButton", command=aceptar).pack(pady=12)
        self.raiz.wait_window(ventana)
        return resultado["hoja"]

    def _elegir_template_nifti(self):
        p = filedialog.askopenfilename(title="Template NIfTI", filetypes=[("NIfTI", "*.nii *.nii.gz")])
        if p:
            self.ruta_template_nifti = p
            self.etq_nifti.configure(text=Path(p).name)

    def _elegir_nodos_nifti(self):
        p = filedialog.askopenfilename(title="NIfTI de parcelación", filetypes=[("NIfTI", "*.nii *.nii.gz")])
        if not p:
            return
        try:
            img = nib.load(p)
            if img.ndim != 3:
                messagebox.showerror("Error", f"El archivo tiene {img.ndim} dimensiones; se necesita un volumen 3D.")
                return
            n = len(np.unique(img.get_fdata())) - 1
            self.ruta_nodos_nifti = p
            self.modo_nodos.set("nifti")
            self.etq_nodos_nifti.configure(text=Path(p).name)
            self.etq_estado_archivo.configure(text=f"Cargado: {n} parcelas detectadas.")
            self.var_tipo_nodo.set("parcels")
            self._actualizar_fuente()
        except Exception as e:
            messagebox.showerror("Error al cargar el NIfTI", str(e))

    def _usar_atlas(self):
        nombre = self.var_atlas.get()
        if nombre not in ATLAS_TEMPLATEFLOW:
            messagebox.showerror("Error", "Atlas no reconocido.")
            return
        self.modo_nodos.set("atlas")
        self.etq_estado_archivo.configure(
            text=f"Atlas seleccionado: {nombre}\nSe descargará al generar la figura si aún no existe.")
        self._actualizar_fuente()

    def _elegir_matriz(self):
        p = filedialog.askopenfilename(
            title="Matriz de adyacencia",
            filetypes=[("Matrices", "*.csv *.tsv *.txt *.xlsx *.xlsm *.xls *.npy"), ("Todos", "*.*")])
        if not p:
            return
        try:
            mat = leer_matriz_archivo(p, elegir_hoja=self.elegir_hoja)
            if mat is None:
                return
            errs = ValidadorDatos.matriz(mat)
            if errs:
                messagebox.showerror("Matriz no válida", "\n".join(errs))
                return
            self.ruta_matriz = p
            self.modo_aristas.set("matriz")
            self.etq_matriz.configure(text=Path(p).name)
            self.etq_estado_matriz.configure(text=f"Matriz de {mat.shape[0]}×{mat.shape[1]} cargada.")
            self._actualizar_fuente()
        except Exception as e:
            messagebox.showerror("Error al leer la matriz", str(e))

    # ── archivero de templates ──
    def _abrir_archivero(self):
        win = tk.Toplevel(self.raiz)
        win.title("Archivero de templates")
        win.configure(bg=C["panel"])
        win.geometry("520x470")
        win.transient(self.raiz)
        self._centrar(win)
        ttk.Label(win, text="Templates disponibles en TemplateFlow", style="Seccion.TLabel").pack(anchor="w", padx=14, pady=(12, 2))
        ttk.Label(win, text="✓ descargado    ○ no descargado", style="Sec.TLabel").pack(anchor="w", padx=14)
        marco = ttk.Frame(win, style="Panel.TFrame")
        marco.pack(fill="both", expand=True, padx=14, pady=8)
        lista = tk.Listbox(marco, font=(self.fuente, 10), selectbackground=C["sel"], selectforeground=C["texto"],
                           highlightthickness=1, highlightbackground=C["borde"], borderwidth=0, activestyle="none")
        sb = ttk.Scrollbar(marco, command=lista.yview)
        lista.configure(yscrollcommand=sb.set)
        lista.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        pie = ttk.Frame(win, style="Panel.TFrame")
        pie.pack(fill="x", padx=14, pady=(0, 12))
        spin = Spinner(pie, tam=28)
        estado = ttk.Label(pie, text="Cargando lista de templates…", style="Sec.TLabel")
        estado.pack(side="left")
        boton = ttk.Button(pie, text="Descargar seleccionado", style="Acento.TButton")
        boton.pack(side="right")
        nombres = []

        def cargar():
            nombres.extend(GestorTemplates.disponibles())
            for t in nombres:
                lista.insert("end", f"  {'✓' if GestorTemplates.descargado(t) else '○'}  {t}")
            estado.configure(text=f"{len(nombres)} templates encontrados.")

        def descargar():
            sel = lista.curselection()
            if not sel:
                estado.configure(text="Selecciona un template de la lista.")
                return
            idx, nombre = sel[0], nombres[sel[0]]
            boton.state(["disabled"])
            spin.pack(side="right", padx=8)
            spin.iniciar()
            estado.configure(text=f"Descargando {nombre}…")
            resultado = {}

            def trabajo():
                try:
                    GestorTemplates.descargar(nombre)
                    resultado["ok"] = True
                except Exception as e:
                    resultado["error"] = str(e)

            hilo = threading.Thread(target=trabajo, daemon=True)
            hilo.start()

            def vigilar():
                if hilo.is_alive():
                    win.after(200, vigilar)
                    return
                spin.detener()
                spin.pack_forget()
                boton.state(["!disabled"])
                if resultado.get("ok"):
                    lista.delete(idx)
                    lista.insert(idx, f"  ✓  {nombre}")
                    estado.configure(text=f"{nombre} descargado.")
                else:
                    estado.configure(text=f"Error: {resultado.get('error', '')[:70]}")
            win.after(200, vigilar)

        boton.configure(command=descargar)
        win.after(100, cargar)

    # ── generador aleatorio ──
    def _generar_aleatorio(self):
        d = tk.Toplevel(self.raiz)
        d.title("Generar datos aleatorios")
        d.configure(bg=C["panel"])
        d.transient(self.raiz)
        d.grab_set()
        d.resizable(False, False)
        self._centrar(d)
        entradas = {}
        for i, (etq, val) in enumerate([("Nodos", "10"), ("Comunidades", "3"), ("Probabilidad de arista", "0.3")]):
            ttk.Label(d, text=etq, style="Panel.TLabel").grid(row=i, column=0, padx=14, pady=6, sticky="e")
            e = ttk.Entry(d, width=10)
            e.insert(0, val)
            e.grid(row=i, column=1, padx=14, pady=6)
            entradas[etq] = e

        def generar():
            try:
                n = int(entradas["Nodos"].get())
                nc = int(entradas["Comunidades"].get())
                pe = float(entradas["Probabilidad de arista"].get())
            except ValueError:
                messagebox.showerror("Error", "Valores inválidos.", parent=d)
                return
            if not 2 <= n <= 200:
                messagebox.showerror("Error", "El número de nodos debe estar entre 2 y 200.", parent=d)
                return
            if nc < 1 or not 0 <= pe <= 1:
                messagebox.showerror("Error", "Comunidades ≥ 1 y probabilidad entre 0 y 1.", parent=d)
                return
            rango = 40 if "Infant" in self.var_template.get() else 70
            nodos = [(np.random.randint(-rango, rango), np.random.randint(-rango, rango),
                      np.random.randint(-10, rango), np.random.randint(1, nc + 1),
                      round(float(np.random.uniform(0.2, 1.0)), 2)) for _ in range(n)]
            aristas = [(i, j, round(float(np.random.uniform(0.1, 1.0)), 2))
                       for i in range(n) for j in range(i + 1, n) if np.random.random() < pe]
            self.editor_nodos.poner_filas(nodos)
            self.editor_aristas.poner_filas(aristas)
            self.modo_nodos.set("tabla")
            self.modo_aristas.set("tabla")
            self._actualizar_fuente()
            self.var_estado.set(f"Se generaron {n} nodos y {len(aristas)} aristas.")
            d.destroy()
        ttk.Button(d, text="Generar", style="Acento.TButton", command=generar).grid(
            row=3, column=0, columnspan=2, pady=12, padx=14, sticky="ew")
        self._centrar(d)

    # ── tareas en segundo plano con indicador de progreso ──
    def _mostrar_overlay(self, mensaje):
        self.overlay_msg.configure(text=mensaje)
        self.overlay_tiempo.configure(text="00:00")
        self.btn_cancelar_render.state(["!disabled"])
        self.overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.overlay.lift()
        self.spinner.iniciar()
        self.raiz.configure(cursor="watch")
        self.raiz.update_idletasks()
        try:
            self.overlay.grab_set()   # bloquea el resto de controles mientras se trabaja
        except tk.TclError:
            pass

    def _ocultar_overlay(self):
        try:
            self.overlay.grab_release()
        except tk.TclError:
            pass
        self.spinner.detener()
        self.overlay.place_forget()
        self.raiz.configure(cursor="")

    def _cancelar_render(self):
        """Señala al hilo de render que debe abortar. matplotlib no es interrumpible,
        pero al marcar el evento el _vigilar descarta el resultado cuando el hilo termine."""
        self._evento_cancelar.set()
        self.btn_cancelar_render.state(["disabled"])
        self.overlay_msg.configure(text="Cancelando… (esperando a que matplotlib termine)")

    def _ejecutar_tarea(self, mensaje, trabajo, al_terminar):
        if self._ocupado:
            return
        self._ocupado = True
        self._evento_cancelar.clear()
        self._mostrar_overlay(mensaje)
        resultado = {}

        def _correr():
            try:
                resultado["ok"] = trabajo()
            except BaseException as e:  # noqa: BLE001
                resultado["error"] = e
                resultado["tb"] = traceback.format_exc()

        hilo = threading.Thread(target=_correr, daemon=True)
        hilo.start()
        t0 = time.time()

        def _vigilar():
            seg = int(time.time() - t0)
            self.overlay_tiempo.configure(text=f"{seg // 60:02d}:{seg % 60:02d}")
            if hilo.is_alive():
                self.raiz.after(200, _vigilar)
                return
            self._ocultar_overlay()
            self._ocupado = False
            if self._evento_cancelar.is_set():
                self._evento_cancelar.clear()
                # Liberar memoria de la figura que pudo haberse generado
                if "ok" in resultado and resultado["ok"] is not None:
                    fig = resultado["ok"][0] if isinstance(resultado["ok"], tuple) else None
                    if fig is not None:
                        plt.close(fig)
                self.var_estado.set("Render cancelado.")
                return
            al_terminar(resultado)
        self.raiz.after(200, _vigilar)

    # ── recursos ──
    def _diagnosticar_recursos(self):
        # Corre en un hilo; no toca Tk. El hilo principal recoge el resultado.
        self._diag_resultado = Recursos.diagnostico()

    def _esperar_diagnostico(self):
        if self._diag_resultado is None:
            self.raiz.after(300, self._esperar_diagnostico)
        else:
            self._recursos_listos(self._diag_resultado)

    def _recursos_listos(self, diag):
        self.diag_recursos = diag
        self.recursos_var.set(Recursos.texto_resumen(diag))
        # Ya no se abre una ventana al arrancar: todavía no se sabe qué se va a renderizar, y el aviso
        # específico de la tarea sale justo antes de renderizar. Aquí solo se resalta la cabecera
        # (en ámbar) si, con los ajustes actuales, el equipo no alcanzaría; el detalle está en «Recursos».
        motivos, _ = Recursos.problemas(diag, self.var_estilo.get(), self.var_voxel.get(),
                                        self.var_vista.get(), self.var_cuadros.get(),
                                        self.var_tipo_nodo.get())
        self.lbl_recursos.configure(fg="#F2C879" if motivos else C["cabecera_txt2"])

    def mostrar_recursos(self):
        if self.diag_recursos is None:
            messagebox.showinfo("Recursos", "Todavía se están analizando los recursos del equipo.")
            return
        motivos, ajustes = Recursos.problemas(self.diag_recursos, self.var_estilo.get(), self.var_voxel.get(),
                                              self.var_vista.get(), self.var_cuadros.get(),
                                              self.var_tipo_nodo.get())
        self.aviso_recursos(motivos, ajustes, contexto="manual")

    # ── configuración de la nube ──
    MODOS_RENDER = {"auto": "Automático (pregunta cuando conviene)",
                    "local": "Siempre local",
                    "nube": "Siempre en la nube"}

    def _url_nube(self):
        """URL del servidor de nube ya limpia, o '' si no hay una válida configurada."""
        try:
            return ClienteNube.url_normalizada(self.config.get("url_nube", ""))
        except ErrorNube:
            return ""

    def _centrar(self, ventana):
        """
        Centra una ventana sobre la principal, sin que se salga de la pantalla. Sin esto, el
        gestor de ventanas la coloca donde quiere y puede quedar cortada contra un borde.
        Se ejecuta diferido (after_idle) para medir la ventana ya con su contenido dentro.
        """
        def _colocar():
            if not ventana.winfo_exists():
                return
            ventana.update_idletasks()
            ancho = ventana.winfo_width() if ventana.winfo_width() > 1 else ventana.winfo_reqwidth()
            alto = ventana.winfo_height() if ventana.winfo_height() > 1 else ventana.winfo_reqheight()
            px, py = self.raiz.winfo_rootx(), self.raiz.winfo_rooty()
            pw, ph = self.raiz.winfo_width(), self.raiz.winfo_height()
            x = px + (pw - ancho) // 2
            y = py + (ph - alto) // 3        # algo por encima del centro: se lee mejor
            margen = 10
            x = max(margen, min(x, ventana.winfo_screenwidth() - ancho - margen))
            y = max(margen, min(y, ventana.winfo_screenheight() - alto - margen))
            ventana.geometry(f"+{x}+{y}")
        ventana.after_idle(_colocar)

    def _recomendacion_nube(self):
        """Según el equipo detectado, dice si vale la pena configurar la nube."""
        diag = self.diag_recursos
        if diag is None:
            return ("Analizando los recursos del equipo…", "Sec.TLabel")
        libre, total = diag.get("ram_libre"), diag.get("ram_total")
        gpu = diag.get("tipo_gpu")
        if libre is None:
            return ("No se pudo medir la memoria de este equipo; la nube sirve como respaldo "
                    "si algún render resulta muy lento.", "Sec.TLabel")
        # El render más pesado medido (filled) usó ~225 MB, pero el pico depende del template:
        # por debajo de ~2.5 GB libres conviene tener la nube a la mano.
        if libre < 2.5 or (total is not None and total < 8):
            cuerpo = (f"Tu equipo tiene {libre:.1f} GB de RAM libre"
                      f"{f' de {total:.0f} GB' if total else ''}. Para los estilos pesados "
                      "('filled', o voxel size 1) puede quedarse corto: aquí la nube ayuda.")
            if gpu != "dedicada":
                cuerpo += " Además no se detectó tarjeta gráfica dedicada, así que 'glass' también será lento."
            return (cuerpo, "Aviso.TLabel")
        cuerpo = (f"Tu equipo ({libre:.1f} GB de RAM libre"
                  f"{f' de {total:.0f} GB' if total else ''}"
                  f"{', GPU dedicada' if gpu == 'dedicada' else ''}) alcanza para los renders normales. "
                  "La nube es opcional: útil solo para los estilos más pesados.")
        return (cuerpo, "Panel.TLabel")

    def guia_crear_space(self):
        """Explica las tres opciones reales para alojar el servidor de render."""
        d = tk.Toplevel(self.raiz)
        d.title("Dónde poner el servidor de render")
        d.configure(bg=C["panel"])
        d.transient(self.raiz)
        d.grab_set()
        d.resizable(False, False)
        self._centrar(d)
        ttk.Label(d, text="Dónde poner el servidor de render", style="Seccion.TLabel").pack(
            anchor="w", padx=18, pady=(16, 2))
        ttk.Label(d, text="Los archivos del servidor están en la carpeta nube/ del proyecto y sirven igual "
                          "en las tres opciones: solo cambia la dirección que escribes en la ventana anterior.",
                  style="Sec.TLabel", wraplength=560, justify="left").pack(anchor="w", padx=18)

        opciones = [
            ("Otra computadora de tu red  —  sin costo",
             "La mejor opción si trabajas con datos de personas: nada sale de tu red. En esa máquina se instala "
             "Docker, se construye la imagen de la carpeta nube/ y se anota su dirección IP local.",
             "Panel.TLabel"),
            ("Google Cloud Run  —  nivel gratuito amplio, pide tarjeta",
             "Se apaga solo cuando no se usa y permite exigir autenticación y elegir en qué región viven los "
             "datos. Hay que registrar una tarjeta aunque no se llegue a cobrar.",
             "Panel.TLabel"),
            ("Hugging Face Spaces  —  requiere plan PRO de pago",
             "Los Spaces que ejecutan código (Docker) ya no se pueden crear con una cuenta gratuita. "
             "Solo conviene si ya tienes PRO.",
             "Aviso.TLabel"),
        ]
        for titulo, detalle, estilo in opciones:
            ttk.Label(d, text="•  " + titulo, style=estilo, wraplength=560,
                      justify="left").pack(anchor="w", padx=22, pady=(10, 0))
            ttk.Label(d, text=detalle, style="Sec.TLabel", wraplength=525,
                      justify="left").pack(anchor="w", padx=38)

        ttk.Label(d, text="En cualquier servidor que se vea desde internet, quien conozca la dirección podría usarlo. "
                          "Protégelo con autenticación (token, o identidad en Cloud Run) o mantenlo en tu red local.",
                  style="Aviso.TLabel", wraplength=560, justify="left").pack(anchor="w", padx=18, pady=(14, 0))

        fila = ttk.Frame(d, style="Panel.TFrame")
        fila.pack(anchor="w", padx=18, pady=(10, 0))

        def abrir_carpeta():
            carpeta = Path(__file__).resolve().parent / "nube"
            if not carpeta.exists():
                messagebox.showinfo("Carpeta nube", f"No se encontró la carpeta:\n{carpeta}\n\n"
                                                    "Está en el repositorio del proyecto, junto a este programa.")
                return
            try:
                if sys.platform == "win32":
                    os.startfile(str(carpeta))  # noqa: S606
                    return
                orden = ["open"] if sys.platform == "darwin" else ["xdg-open"]
                r = subprocess.run(orden + [str(carpeta)], capture_output=True, text=True)
                if r.returncode != 0:
                    raise OSError((r.stderr or "").strip()[:120] or "el gestor de archivos no respondió")
            except Exception as e:  # noqa: BLE001
                messagebox.showinfo("Carpeta nube", f"Ábrela manualmente:\n{carpeta}\n\n({e})")

        ttk.Button(fila, text="Abrir carpeta nube/", style="Acento.TButton",
                   command=abrir_carpeta).pack(side="left")
        ttk.Button(fila, text="Abrir Cloud Run",
                   command=lambda: webbrowser.open(URL_CLOUD_RUN)).pack(side="left", padx=8)
        ttk.Button(fila, text="Hugging Face (PRO)",
                   command=lambda: webbrowser.open(URL_CREAR_SPACE)).pack(side="left")
        ttk.Button(d, text="Cerrar", command=d.destroy).pack(anchor="e", padx=18, pady=14)

    def configurar_nube(self):
        d = tk.Toplevel(self.raiz)
        d.title("Servidor de nube")
        d.configure(bg=C["panel"])
        d.transient(self.raiz)
        d.grab_set()
        d.resizable(False, False)
        self._centrar(d)
        ttk.Label(d, text="Servidor de nube (opcional)", style="Seccion.TLabel").pack(anchor="w", padx=18, pady=(16, 2))
        ttk.Label(d, text=("Si tu equipo no tiene recursos para un render pesado, el trabajo puede hacerse en un servidor "
                           "aparte: una máquina de tu red local (lo más privado y sin costo), Google Cloud Run, "
                           "o un Space de Hugging Face (este último ya requiere plan PRO de pago).\n"
                           "Los datos de tus nodos viajan a ese servidor: no envíes información sensible de personas."),
                  style="Sec.TLabel", wraplength=500, justify="left").pack(anchor="w", padx=18)

        texto_reco, estilo_reco = self._recomendacion_nube()
        ttk.Label(d, text=texto_reco, style=estilo_reco, wraplength=500,
                  justify="left").pack(anchor="w", padx=18, pady=(8, 0))
        fila_guia = ttk.Frame(d, style="Panel.TFrame")
        fila_guia.pack(anchor="w", padx=18, pady=(6, 0))
        ttk.Button(fila_guia, text="¿Dónde pongo mi servidor?",
                   command=self.guia_crear_space).pack(side="left")

        var_url = tk.StringVar(value=self.config.get("url_nube", ""))
        var_token = tk.StringVar(value=self.token_nube)
        clave_actual = self.config.get("modo_render", "auto")
        var_modo = tk.StringVar(value=self.MODOS_RENDER.get(clave_actual, self.MODOS_RENDER["auto"]))

        ttk.Label(d, text="URL del servidor (red local: http://192.168.x.x:7860  ·  nube: https://…)",
                  style="Panel.TLabel").pack(anchor="w", padx=18, pady=(12, 2))
        ttk.Entry(d, textvariable=var_url, width=62).pack(anchor="w", padx=18)
        ttk.Label(d, text="Token de Hugging Face (solo si tu Space es privado; no se guarda en disco)",
                  style="Panel.TLabel").pack(anchor="w", padx=18, pady=(10, 2))
        ttk.Entry(d, textvariable=var_token, width=62, show="•").pack(anchor="w", padx=18)
        ttk.Label(d, text="Modo de render", style="Panel.TLabel").pack(anchor="w", padx=18, pady=(10, 2))
        ttk.Combobox(d, textvariable=var_modo, values=list(self.MODOS_RENDER.values()),
                     state="readonly", width=40).pack(anchor="w", padx=18)

        fila_probar = ttk.Frame(d, style="Panel.TFrame")
        fila_probar.pack(fill="x", padx=18, pady=(12, 0))
        btn_probar = ttk.Button(fila_probar, text="Probar conexión")
        btn_probar.pack(side="left")
        spin = Spinner(fila_probar, tam=24)
        estado = tk.StringVar(value="")
        lbl_estado = ttk.Label(d, textvariable=estado, style="Panel.TLabel", wraplength=500, justify="left")
        lbl_estado.pack(anchor="w", padx=18, pady=(6, 0))

        def poner(texto, color):
            estado.set(texto)
            lbl_estado.configure(foreground=color)

        def probar():
            try:
                url = ClienteNube.url_normalizada(var_url.get())
            except ErrorNube as e:
                poner(str(e), C["error"])
                return
            if not url:
                poner("Escribe primero la URL del servidor.", C["error"])
                return
            token = var_token.get().strip() or None
            btn_probar.state(["disabled"])
            spin.pack(side="left", padx=8)
            spin.iniciar()
            poner("Conectando… (si el servidor estaba dormido puede tardar hasta un minuto)", C["texto2"])
            res = {}

            def trabajo():
                try:
                    res["version"] = ClienteNube.probar(url, token)
                except ErrorNube as e:
                    res["error"] = str(e)
                except Exception as e:  # noqa: BLE001
                    res["error"] = f"{type(e).__name__}: {e}"
            hilo = threading.Thread(target=trabajo, daemon=True)
            hilo.start()

            def vigilar():
                if hilo.is_alive():
                    d.after(200, vigilar)
                    return
                spin.detener()
                spin.pack_forget()
                btn_probar.state(["!disabled"])
                if "version" in res:
                    poner(f"Conexión correcta (versión del servidor: {res['version']}).", C["ok"])
                else:
                    poner(res["error"], C["error"])
            d.after(200, vigilar)
        btn_probar.configure(command=probar)
        self._probar_nube_dialogo = probar  # para pruebas automáticas

        def guardar():
            try:
                url = ClienteNube.url_normalizada(var_url.get())
            except ErrorNube as e:
                poner(str(e), C["error"])
                return
            clave = {v: k for k, v in self.MODOS_RENDER.items()}[var_modo.get()]
            if clave == "nube" and not url:
                poner("Para usar «Siempre en la nube» escribe la URL del servidor.", C["error"])
                return
            self.config["url_nube"] = url
            self.config["modo_render"] = clave
            Config.guardar(self.config)
            self.token_nube = var_token.get().strip()
            self._actualizar_fuente()
            d.destroy()
        pie = ttk.Frame(d, style="Panel.TFrame")
        pie.pack(fill="x", padx=18, pady=14)
        ttk.Button(pie, text="Guardar", style="Acento.TButton", command=guardar).pack(side="left")
        ttk.Button(pie, text="Cancelar", command=d.destroy).pack(side="right")

    def aviso_recursos(self, motivos, ajustes, contexto, nube=None):
        """
        Diálogo de recursos. Devuelve 'continuar', 'ajustar', 'nube' o 'cancelar'.
        nube: None = no hay servidor configurado (se sugiere configurarlo); 'off' = el usuario
        eligió "Siempre local" (no se menciona la nube); ('ok', '') = disponible para este
        render; ('incompatible', motivo) = hay servidor, pero este render no puede ir ahí.
        """
        d = tk.Toplevel(self.raiz)
        d.title("Recursos del equipo")
        d.configure(bg=C["panel"])
        d.transient(self.raiz)
        d.grab_set()
        d.resizable(False, False)
        self._centrar(d)
        ttk.Label(d, text="Recursos del equipo", style="Seccion.TLabel").pack(anchor="w", padx=18, pady=(16, 2))
        ttk.Label(d, text=Recursos.texto_resumen(self.diag_recursos), style="Sec.TLabel",
                  wraplength=520, justify="left").pack(anchor="w", padx=18)
        if motivos:
            ttk.Label(d, text="Posibles problemas:", style="Panel.TLabel").pack(anchor="w", padx=18, pady=(12, 2))
            for m in motivos:
                ttk.Label(d, text="•  " + m, style="Aviso.TLabel", wraplength=520, justify="left").pack(anchor="w", padx=28)
            propio_disponible = contexto == "render" and isinstance(nube, tuple) and nube[0] == "ok"
            if not propio_disponible:
                ttk.Label(d, text="Alternativas gratuitas en la nube (se usan manualmente, fuera de la app):",
                          style="Panel.TLabel").pack(anchor="w", padx=18, pady=(12, 2))
                ttk.Label(d, text="•  Google Colab: gratuito con cuenta de Google, con límites de uso.\n"
                                  "•  Binder: gratuito y sin cuenta; las sesiones son temporales.",
                          style="Sec.TLabel", justify="left").pack(anchor="w", padx=28)
            if contexto == "render" and nube != "off":
                if nube is None:
                    ttk.Label(d, text="Tip: puedes configurar tu propio servidor de nube con el botón «Nube» de arriba.",
                              style="Sec.TLabel", wraplength=520, justify="left").pack(anchor="w", padx=18, pady=(10, 0))
                elif nube[0] == "ok":
                    ttk.Label(d, text="Tienes un servidor de nube configurado: este render puede hacerse ahí "
                                      "en vez de en tu equipo.",
                              style="Panel.TLabel", wraplength=520, justify="left").pack(anchor="w", padx=18, pady=(10, 0))
                else:
                    ttk.Label(d, text="Hay un servidor de nube configurado, pero este render no puede hacerse ahí: " + nube[1],
                              style="Aviso.TLabel", wraplength=520, justify="left").pack(anchor="w", padx=18, pady=(10, 0))
            if not propio_disponible:
                fila = ttk.Frame(d, style="Panel.TFrame")
                fila.pack(anchor="w", padx=28, pady=6)
                ttk.Button(fila, text="Abrir Google Colab", command=lambda: webbrowser.open(URL_COLAB)).pack(side="left", padx=(0, 6))
                ttk.Button(fila, text="Abrir Binder", command=lambda: webbrowser.open(URL_BINDER)).pack(side="left", padx=6)

                def copiar():
                    self.raiz.clipboard_clear()
                    self.raiz.clipboard_append(COMANDO_COLAB)
                    self.var_estado.set("Comando de instalación copiado. Pégalo en una celda de Colab.")
                ttk.Button(fila, text="Copiar comando de instalación", command=copiar).pack(side="left", padx=6)
        else:
            ttk.Label(d, text="No se detectaron problemas con la configuración actual.",
                      style="Panel.TLabel").pack(anchor="w", padx=18, pady=12)

        avisar = tk.BooleanVar(value=not self.config.get("omitir_aviso_recursos"))
        ttk.Checkbutton(d, text="Avisarme antes de renderizar cuando el trabajo sea pesado para mi equipo",
                        variable=avisar).pack(anchor="w", padx=18, pady=(8, 0))
        eleccion = {"valor": "continuar"}

        def cerrar(valor):
            eleccion["valor"] = valor
            self.config["omitir_aviso_recursos"] = not avisar.get()
            Config.guardar(self.config)
            d.destroy()
        pie = ttk.Frame(d, style="Panel.TFrame")
        pie.pack(fill="x", padx=18, pady=14)
        if ajustes:
            texto = " y ".join(([f"estilo {ajustes['estilo']}"] if "estilo" in ajustes else []) +
                               ([f"voxel size {ajustes['voxel']}"] if "voxel" in ajustes else []) +
                               ([f"nodos {ajustes['node_type']}"] if "node_type" in ajustes else []))
            ttk.Button(pie, text=f"Aplicar ajustes ({texto})", style="Acento.TButton",
                       command=lambda: cerrar("ajustar")).pack(side="left")
        if contexto == "render" and isinstance(nube, tuple) and nube[0] == "ok":
            ttk.Button(pie, text="Renderizar en la nube", style="Acento.TButton",
                       command=lambda: cerrar("nube")).pack(side="left", padx=(8, 0))
        ttk.Button(pie, text="Continuar en mi equipo" if contexto == "render" else "Cerrar",
                   command=lambda: cerrar("continuar")).pack(side="right")
        if contexto == "render":
            ttk.Button(pie, text="Cancelar", command=lambda: cerrar("cancelar")).pack(side="right", padx=6)
        d.protocol("WM_DELETE_WINDOW", lambda: cerrar("cancelar" if contexto == "render" else "continuar"))
        self.raiz.wait_window(d)
        if eleccion["valor"] == "ajustar":
            if "estilo" in ajustes:
                self.var_estilo.set(ajustes["estilo"])
            if "voxel" in ajustes:
                self.fila_voxel.fijar(ajustes["voxel"])
            if "node_type" in ajustes:
                self.var_tipo_nodo.set(ajustes["node_type"])
        return eleccion["valor"]

    # ── tamaño de esferas ──
    @staticmethod
    def _tamanos_circulo(df, escala):
        """Área (puntos²) que netplotbrain usaría para cada nodo con node_type='circles'."""
        if "centralidad" in df.columns and pd.api.types.is_numeric_dtype(df["centralidad"]):
            v = df["centralidad"].astype(float)
            if v.max() > v.min():
                return ((v - v.min()) / (v.max() - v.min()) * 1.0 + 0.05) * escala
        return pd.Series(np.full(len(df), 1.0 * escala), index=df.index)

    def _radios_esfera(self, df, escala, voxel):
        """
        Las esferas de netplotbrain usan un radio en unidades de vóxel, mientras que los
        círculos usan un área en puntos². Se convierte para que ambos se vean iguales:
        diámetro del círculo ≈ raíz(área)  ->  radio de la esfera = raíz(área) / voxel size.
        """
        s = self._tamanos_circulo(df, escala)
        return (np.sqrt(np.maximum(s.to_numpy(dtype=float), 0.0)) / max(voxel, 1)) * FACTOR_ESFERA

    # ── construcción de argumentos ──
    def construir_argumentos(self):
        """Valida la entrada y devuelve el dict de kwargs (o None si hay un error)."""
        seleccion = self.var_template.get()
        tpl = self._nombre_template(seleccion)
        if tpl is None:
            messagebox.showwarning("Template", "Selecciona un template válido.")
            return None
        if tpl == "__custom__":
            if not self.ruta_template_nifti:
                messagebox.showwarning("Template", "Selecciona un archivo NIfTI para usar como template.")
                return None
            if not os.path.exists(self.ruta_template_nifti):
                messagebox.showerror(
                    "Template no encontrado",
                    f"El archivo ya no existe o fue movido:\n{self.ruta_template_nifti}\n\n"
                    "Selecciona el NIfTI nuevamente.")
                return None
            tpl = self.ruta_template_nifti

        modo_nodos = self.modo_nodos.get()
        nodos = None
        n_nodos = None
        if modo_nodos == "tabla":
            nodos = self.editor_nodos.obtener_dataframe()
            errs = ValidadorDatos.nodos(nodos)
            if errs:
                messagebox.showerror("Error en los nodos", "\n".join(errs))
                return None
            n_nodos = len(nodos)
        elif modo_nodos == "nifti":
            if not self.ruta_nodos_nifti:
                messagebox.showerror("Error", "No hay un NIfTI de parcelación cargado.")
                return None
            nodos = self.ruta_nodos_nifti
        else:
            nodos = ATLAS_TEMPLATEFLOW.get(self.var_atlas.get())
            if not nodos:
                messagebox.showerror("Error", "Atlas no reconocido.")
                return None

        if self.var_tipo_nodo.get() == "parcels" and modo_nodos == "tabla":
            messagebox.showerror(
                "Tipo de nodo no compatible",
                "El tipo 'parcels' dibuja las parcelas de un archivo de parcelación, así que "
                "necesita que los nodos vengan de un NIfTI o de un atlas de TemplateFlow.\n\n"
                "Con una tabla de coordenadas usa 'circles' o 'spheres', o carga una parcelación "
                "en la pestaña «Nodos desde NIfTI / Atlas».")
            return None

        modo_aristas = self.modo_aristas.get()
        aristas = None
        if modo_aristas == "tabla":
            df_a = self.editor_aristas.obtener_dataframe()
            if not df_a.empty:
                if n_nodos is not None:
                    errs = ValidadorDatos.aristas(df_a, n_nodos)
                    if errs:
                        r = messagebox.askyesnocancel(
                            "Aristas", "\n".join(errs) + "\n\n¿Limpiar automáticamente las aristas problemáticas?")
                        if r is None or r is False:
                            return None
                        df_a, _ = ValidadorDatos.limpiar_aristas(df_a, n_nodos)
                aristas = df_a
        else:
            if not self.ruta_matriz:
                messagebox.showerror("Error", "No hay una matriz de adyacencia cargada.")
                return None
            try:
                aristas = leer_matriz_archivo(self.ruta_matriz)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer la matriz:\n{e}")
                return None
            errs = ValidadorDatos.matriz(aristas, n_nodos)
            if errs:
                messagebox.showerror("Matriz no válida", "\n".join(errs))
                return None

        voxel = int(self.var_voxel.get())
        escala = int(self.var_escala_nodo.get())
        kw = {
            "template": tpl,
            "template_style": self.var_estilo.get(),
            "template_alpha": self.var_opacidad.get() / 100.0,
            "template_voxelsize": voxel,
            "view": self.var_vista.get(),
            "title": self.var_titulo.get(),
            "node_type": self.var_tipo_nodo.get(),
            "node_scale": escala,
            "node_alpha": 0.9,
        }
        if kw["view"] == "360":
            kw["frames"] = int(self.var_cuadros.get())
        hemi = self.var_hemisferio.get()
        if hemi != "ambos":
            kw["hemisphere"] = hemi

        if modo_nodos == "tabla" and isinstance(nodos, pd.DataFrame):
            nodos = nodos.copy()
            if "comunidad" in nodos.columns:
                kw["node_color"] = "comunidad"
            if kw["node_type"] == "spheres":
                # Corrección de tamaño: se pasan radios ya convertidos (ver _radios_esfera)
                nodos["_radio_esfera"] = self._radios_esfera(nodos, escala, voxel)
                kw["node_size"] = "_radio_esfera"
                kw["node_scale"] = 1
                kw["node_sizelegend"] = False
            else:
                variable = "centralidad" in nodos.columns and pd.api.types.is_numeric_dtype(nodos["centralidad"]) \
                    and nodos["centralidad"].max() > nodos["centralidad"].min()
                if variable:
                    kw["node_size"] = "centralidad"
                    # netplotbrain normaliza el tamaño dentro de CADA panel de las vistas preset
                    # (un panel con un solo nodo lo hace desaparecer y los tamaños dejan de ser
                    # comparables entre paneles). Se fija el rango global para evitarlo.
                    kw["node_sizevminvmax"] = [float(nodos["centralidad"].min()),
                                               float(nodos["centralidad"].max())]
                else:
                    kw["node_size"] = 1.0
        elif kw["node_type"] == "spheres" and isinstance(nodos, (str, dict)):
            # Sin tabla no hay tamaños por nodo: se usa un radio fijo equivalente
            kw["node_size"] = float(np.sqrt(escala) / max(voxel, 1))
            kw["node_scale"] = 1
        kw["nodes"] = nodos

        if aristas is not None:
            kw["edges"] = aristas
            kw["edge_widthscale"] = int(self.var_grosor.get())
            if isinstance(aristas, pd.DataFrame) and "peso" in aristas.columns:
                kw["edge_weights"] = "peso"
            umbral = self.var_umbral.get() / 100.0
            if umbral > 0:
                kw["edge_threshold"] = umbral
                kw["edge_thresholddirection"] = ">"
        return kw

    # ── generación de la figura ──
    def generar_figura(self):
        if self._ocupado:
            return
        kw = self.construir_argumentos()
        if kw is None:
            return
        modo = self.config.get("modo_render", "auto")
        url = self._url_nube()

        # Modo "Siempre en la nube": no se pregunta nada, solo se valida que se pueda.
        if modo == "nube":
            if not url:
                messagebox.showerror("Nube", "El modo «Siempre en la nube» necesita la URL de tu servidor.\n"
                                              "Configúrala con el botón «Nube» de arriba.")
                return
            ok, motivo = ClienteNube.compatible(kw)
            if not ok:
                messagebox.showerror("Este render no puede hacerse en la nube",
                                     motivo + "\n\nCambia el modo a «Automático» o «Siempre local» "
                                              "con el botón «Nube».")
                return
            self._renderizar_nube(kw, url, respaldo_local=False)
            return

        # Revisión de recursos antes de renderizar (modos "Automático" y "Siempre local")
        if self.diag_recursos is not None and not self.config.get("omitir_aviso_recursos"):
            motivos, ajustes = Recursos.problemas(self.diag_recursos, kw["template_style"], kw["template_voxelsize"],
                                                  kw["view"], kw.get("frames"), kw.get("node_type"))
            motivos_render = [m for m in motivos if "estilo" in m or "voxel" in m or "RAM libre" in m]
            if motivos_render:
                if modo == "local":
                    nube = "off"
                elif not url:
                    nube = None
                else:
                    ok, motivo = ClienteNube.compatible(kw)
                    nube = ("ok", "") if ok else ("incompatible", motivo)
                decision = self.aviso_recursos(motivos_render, ajustes, contexto="render", nube=nube)
                if decision == "cancelar":
                    return
                if decision == "nube":
                    self._renderizar_nube(kw, url, respaldo_local=True)
                    return
                if decision == "ajustar":
                    kw = self.construir_argumentos()
                    if kw is None:
                        return
        self._renderizar_local(kw)

    def _renderizar_local(self, kw):
        template = kw["template"]
        descarga = isinstance(template, str) and not os.path.exists(template) and not GestorTemplates.descargado(template)
        mensaje = ("Descargando el template desde TemplateFlow…\n(solo la primera vez, puede tardar varios minutos)"
                   if descarga else "Generando la figura…")
        self.var_estado.set("Generando la figura…")

        def trabajo():
            plt.close("all")
            fig, _ax = netplotbrain.plot(**kw)
            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=150, facecolor="white", bbox_inches="tight")
            return fig, buf.getvalue()

        self._ejecutar_tarea(mensaje, trabajo, self._figura_lista)

    def _renderizar_nube(self, kw, url, respaldo_local):
        token = self.token_nube or None
        self.var_estado.set("Renderizando en la nube…")

        def trabajo():
            png = ClienteNube.renderizar(url, ClienteNube.payload(kw), token)
            return None, png

        self._ejecutar_tarea(
            "Renderizando en la nube…\n(si el servidor estaba dormido puede tardar cerca de 1 minuto)",
            trabajo,
            lambda res: self._figura_lista(res, kw=kw, desde_nube=True, respaldo_local=respaldo_local))

    def _figura_lista(self, resultado, kw=None, desde_nube=False, respaldo_local=False):
        if "error" in resultado:
            e = resultado["error"]
            if not isinstance(e, ErrorNube):  # los ErrorNube ya traen un mensaje claro; no hace falta el traceback
                print(resultado.get("tb", ""), file=sys.stderr)
            msg = str(e)
            if desde_nube:
                if isinstance(e, ErrorNube):
                    messagebox.showerror("No se pudo usar la nube", msg)
                else:
                    messagebox.showerror("Error al usar la nube", f"{type(e).__name__}: {msg}")
                self.var_estado.set("No se pudo renderizar en la nube.")
                if respaldo_local and kw is not None and messagebox.askyesno(
                        "Renderizar en tu equipo", "¿Quieres hacer el render en tu equipo en su lugar?"):
                    self._renderizar_local(kw)
                return
            if isinstance(e, FileNotFoundError):
                messagebox.showerror("Template no encontrado",
                                     f"No se pudo obtener el template.\nRevisa tu conexión a internet.\n\n{msg}")
            elif "nonzero" in msg.lower() or "0-d" in msg:
                messagebox.showerror("Incompatibilidad con NumPy",
                                     f"Solución:  pip install \"numpy>=1.24,<2.0\"\n\n{msg}")
            elif "multiply sequence" in msg.lower():
                messagebox.showerror("Error de tipo",
                                     f"Un parámetro numérico recibió un tipo incorrecto.\n\n{msg}")
            else:
                messagebox.showerror("Error al generar la figura", f"{type(e).__name__}: {msg}")
            self.var_estado.set("Ocurrió un error al generar la figura.")
            return
        fig, png = resultado["ok"]
        self.ultima_figura = fig      # None si el render se hizo en la nube (solo llega la imagen)
        self.ultima_png = png
        self.btn_guardar.state(["!disabled"])
        self.var_estado.set("Figura generada en la nube." if desde_nube else "Figura generada.")
        self._mostrar_figura(png)

    def _mostrar_figura(self, png):
        if self.ventana_figura is not None and self.ventana_figura.winfo_exists():
            self.ventana_figura.destroy()
        win = tk.Toplevel(self.raiz)
        self.ventana_figura = win
        win.title("Figura generada")
        win.configure(bg=C["panel"])
        barra = ttk.Frame(win, style="Panel.TFrame", padding=(10, 8))
        barra.pack(side="top", fill="x")
        ttk.Button(barra, text="Guardar imagen…", style="Acento.TButton", command=self._guardar_imagen).pack(side="left")
        btn_inter = ttk.Button(barra, text="Vista interactiva", command=self._vista_interactiva)
        btn_inter.pack(side="left", padx=8)
        if self.ultima_figura is None:
            btn_inter.state(["disabled"])
            ttk.Label(barra, text="Generada en la nube: solo imagen PNG (sin vista interactiva).",
                      style="Sec.TLabel").pack(side="left", padx=8)
        ttk.Button(barra, text="Cerrar", command=win.destroy).pack(side="right")

        imagen = tk.PhotoImage(data=base64.b64encode(png))
        win._imagen = imagen  # evita que se libere
        marco = ttk.Frame(win, style="Panel.TFrame")
        marco.pack(fill="both", expand=True)
        lienzo = tk.Canvas(marco, bg=C["panel"], highlightthickness=0)
        sy = ttk.Scrollbar(marco, orient="vertical", command=lienzo.yview)
        sx = ttk.Scrollbar(marco, orient="horizontal", command=lienzo.xview)
        lienzo.configure(yscrollcommand=sy.set, xscrollcommand=sx.set, scrollregion=(0, 0, imagen.width(), imagen.height()))
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        lienzo.pack(side="left", fill="both", expand=True)
        lienzo.create_image(0, 0, image=imagen, anchor="nw")
        ancho = min(imagen.width() + 24, self.raiz.winfo_screenwidth() - 120)
        alto = min(imagen.height() + 90, self.raiz.winfo_screenheight() - 120)
        win.geometry(f"{max(ancho, 520)}x{max(alto, 420)}")

    def _vista_interactiva(self):
        """Incrusta la figura en una ventana con la barra de herramientas de matplotlib."""
        if self.ultima_figura is None:
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        self.var_estado.set("Preparando la vista interactiva…")
        self.raiz.configure(cursor="watch")
        self.raiz.update_idletasks()
        try:
            win = tk.Toplevel(self.raiz)
            win.title("Vista interactiva")
            lienzo = FigureCanvasTkAgg(self.ultima_figura, master=win)
            barra = NavigationToolbar2Tk(lienzo, win, pack_toolbar=False)
            barra.update()
            barra.pack(side="bottom", fill="x")
            lienzo.get_tk_widget().pack(fill="both", expand=True)
            lienzo.draw()
        finally:
            self.raiz.configure(cursor="")
            self.var_estado.set("Listo.")

    def _guardar_imagen(self):
        if self.ultima_figura is None and self.ultima_png is None:
            messagebox.showinfo("Guardar imagen", "Primero genera una figura.")
            return
        if self.ultima_figura is None:
            # Render hecho en la nube: solo se tiene el PNG (150 dpi), no la figura de matplotlib.
            ruta = filedialog.asksaveasfilename(title="Guardar imagen", defaultextension=".png",
                                                filetypes=[("PNG", "*.png")])
            if not ruta:
                return
            if not ruta.lower().endswith(".png"):
                ruta += ".png"
            png = self.ultima_png

            def trabajo_png():
                Path(ruta).write_bytes(png)
                return ruta

            def listo_png(res):
                if "error" in res:
                    messagebox.showerror("Error al guardar", str(res["error"]))
                else:
                    messagebox.showinfo("Guardar imagen",
                                        f"Imagen guardada en:\n{ruta}\n\n(Las imágenes de la nube son PNG a 150 dpi; "
                                        "para SVG/PDF o 300 dpi, renderiza en tu equipo.)")
            self._ejecutar_tarea("Guardando la imagen…", trabajo_png, listo_png)
            return
        ruta = filedialog.asksaveasfilename(
            title="Guardar imagen", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg"), ("PDF", "*.pdf")])
        if not ruta:
            return
        fig = self.ultima_figura

        def trabajo():
            fig.savefig(ruta, dpi=300, bbox_inches="tight", facecolor="white")
            return ruta

        def listo(res):
            if "error" in res:
                messagebox.showerror("Error al guardar", str(res["error"]))
            else:
                messagebox.showinfo("Guardar imagen", f"Imagen guardada en:\n{ruta}")
        self._ejecutar_tarea("Guardando la imagen…", trabajo, listo)

    # ── fuente tipográfica ──
    @property
    def fuente(self):
        familias = set(tkfont.families())
        for f in ("Segoe UI", "Helvetica Neue", "Noto Sans", "DejaVu Sans", "Arial"):
            if f in familias:
                return f
        return "TkDefaultFont"


# ══════════════════════════════════════════════
# Estilos ttk
# ══════════════════════════════════════════════
def configurar_estilos(raiz, fuente):
    estilo = ttk.Style(raiz)
    if "clam" in estilo.theme_names():
        estilo.theme_use("clam")
    base = (fuente, 10)
    raiz.option_add("*Font", base)
    raiz.option_add("*TCombobox*Listbox.background", C["panel"])
    raiz.option_add("*TCombobox*Listbox.foreground", C["texto"])
    raiz.option_add("*TCombobox*Listbox.selectBackground", C["sel"])
    raiz.option_add("*TCombobox*Listbox.selectForeground", C["texto"])

    estilo.configure(".", background=C["panel"], foreground=C["texto"], font=base)
    estilo.configure("Fondo.TFrame", background=C["fondo"])
    estilo.configure("Panel.TFrame", background=C["panel"])
    estilo.configure("TFrame", background=C["panel"])
    estilo.configure("Panel.TLabel", background=C["panel"], foreground=C["texto"])
    estilo.configure("TLabel", background=C["panel"], foreground=C["texto"])
    estilo.configure("Fondo.TLabel", background=C["fondo"], foreground=C["texto2"], font=(fuente, 9))
    estilo.configure("Sec.TLabel", background=C["panel"], foreground=C["texto2"], font=(fuente, 9))
    estilo.configure("Valor.TLabel", background=C["panel"], foreground=C["acento"], font=(fuente, 10, "bold"))
    estilo.configure("Seccion.TLabel", background=C["panel"], foreground=C["acento"], font=(fuente, 10, "bold"))
    estilo.configure("Aviso.TLabel", background=C["panel"], foreground=C["aviso"])
    estilo.configure("TSeparator", background=C["borde"])

    estilo.configure("TButton", background="#E5E7EB", foreground=C["texto"], bordercolor=C["borde"],
                     focusthickness=0, padding=(10, 5), relief="flat", width=-1)
    estilo.map("TButton", background=[("active", "#D8DCE2"), ("disabled", "#EEF0F3")],
               foreground=[("disabled", "#9CA3AF")])
    estilo.configure("Acento.TButton", background=C["acento"], foreground=C["acento_txt"], bordercolor=C["acento"],
                     font=(fuente, 10, "bold"))
    estilo.map("Acento.TButton", background=[("active", C["acento_h"]), ("disabled", "#9DB5C6")],
               foreground=[("disabled", "#FFFFFF")])
    estilo.configure("Cabecera.TButton", background="#2C4E6B", foreground=C["cabecera_txt"], bordercolor="#3B6285")
    estilo.map("Cabecera.TButton", background=[("active", "#36607F")])

    estilo.configure("TNotebook", background=C["fondo"], borderwidth=0)
    estilo.configure("TNotebook.Tab", background="#E5E7EB", foreground=C["texto2"], padding=(14, 6), borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", C["panel"])], foreground=[("selected", C["acento"])])

    estilo.configure("Treeview", background=C["panel"], fieldbackground=C["panel"], foreground=C["texto"],
                     bordercolor=C["borde"], rowheight=24)
    estilo.configure("Treeview.Heading", background="#E5E7EB", foreground=C["texto"], font=(fuente, 9, "bold"),
                     relief="flat")
    estilo.map("Treeview", background=[("selected", C["sel"])], foreground=[("selected", C["texto"])])
    estilo.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=C["borde"], padding=4)
    estilo.configure("TCombobox", fieldbackground="#FFFFFF", background="#E5E7EB", bordercolor=C["borde"],
                     arrowcolor=C["texto2"], padding=3)
    estilo.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")], selectbackground=[("readonly", "#FFFFFF")],
               selectforeground=[("readonly", C["texto"])])
    estilo.configure("Horizontal.TScale", background=C["panel"], troughcolor="#D9DEE4")
    estilo.configure("TCheckbutton", background=C["panel"])
    estilo.configure("TRadiobutton", background=C["panel"])


# ══════════════════════════════════════════════
# Programa principal
# ══════════════════════════════════════════════
def main():
    raiz = tk.Tk()
    app_fuente = "TkDefaultFont"
    familias = set(tkfont.families())
    for f in ("Segoe UI", "Helvetica Neue", "Noto Sans", "DejaVu Sans", "Arial"):
        if f in familias:
            app_fuente = f
            break
    configurar_estilos(raiz, app_fuente)
    AplicacionNetPlotBrain(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
