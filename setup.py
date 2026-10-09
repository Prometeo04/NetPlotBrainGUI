#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador de NetPlotBrain GUI
==============================

Prepara todo lo necesario para usar la aplicación sin tocar el resto de tu
sistema:

  1. Busca un Python compatible (3.9 - 3.12). Si no lo encuentra, lo descarga.
  2. Crea un entorno virtual aislado (.venv) dentro de esta carpeta.
  3. Instala numpy<2.0 primero, luego el resto de las librerías con versiones
     fijas y probadas.
  4. Comprueba que tkinter funcione.
  5. Genera las imágenes de vista previa a partir de un template real.
  6. Descarga los templates de TemplateFlow (opcional).
  7. Crea un acceso directo en el escritorio (Windows).

Se ejecuta con cualquier Python moderno:

    python setup.py

Aunque el Python con el que lo ejecutes sea incompatible (por ejemplo 3.13),
el instalador descargará uno compatible solo para esta aplicación. Tu Python
del sistema no se modifica.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
ES_WINDOWS = platform.system() == "Windows"

# netplotbrain depende de numpy<2.0, que no tiene ruedas (wheels) para 3.13+.
# Por abajo, pandas 3.x y matplotlib 3.10 necesitan al menos 3.9.
VERSIONES_OK = [(3, 12), (3, 11), (3, 10), (3, 9)]
PREFERIDA = (3, 12)

APP = "netplotbrain_gui_v9.py"


# ──────────────────────────────────────────────────────────────────────
# Utilidades de consola
# ──────────────────────────────────────────────────────────────────────
def titulo(texto):
    print()
    print("=" * 68)
    print(f"  {texto}")
    print("=" * 68)


def paso(n, total, texto):
    print(f"\n[{n}/{total}] {texto}")


def ok(texto):
    print(f"  OK  {texto}")


def aviso(texto):
    print(f"  !   {texto}")


def error(texto):
    print(f"  X   {texto}")


def correr(cmd, **kw):
    """Ejecuta un comando mostrando su salida. Devuelve True si salió bien."""
    try:
        subprocess.check_call(cmd, **kw)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def capturar(cmd):
    """Ejecuta un comando y devuelve su stdout limpio, o None si falla."""
    try:
        salida = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
        return salida.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def preguntar(texto, opciones, por_defecto):
    """Pregunta al usuario. Si no hay terminal interactiva, usa el valor por defecto."""
    if not sys.stdin or not sys.stdin.isatty():
        print(f"{texto} -> {por_defecto} (sin terminal interactiva)")
        return por_defecto
    while True:
        try:
            r = input(texto).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return por_defecto
        if not r:
            return por_defecto
        if r in opciones:
            return r
        print(f"  Responde con: {', '.join(opciones)}")


# ──────────────────────────────────────────────────────────────────────
# 1. Encontrar (o descargar) un Python compatible
# ──────────────────────────────────────────────────────────────────────
def version_de(ejecutable):
    """(mayor, menor) del Python en esa ruta, o None si no se puede averiguar."""
    salida = capturar([ejecutable, "-c",
                       "import sys; print(f'{sys.version_info[0]} {sys.version_info[1]}')"])
    if not salida:
        return None
    try:
        a, b = salida.split()
        return (int(a), int(b))
    except ValueError:
        return None


def tiene_tkinter(ejecutable):
    return correr([ejecutable, "-c", "import tkinter"],
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def buscar_en_sistema():
    """Busca un Python compatible ya instalado. Devuelve su ruta o None."""
    # El propio intérprete que está corriendo el setup
    actual = sys.version_info[:2]
    if actual in VERSIONES_OK:
        return sys.executable

    candidatos = []
    if ES_WINDOWS:
        # El lanzador «py» sabe qué versiones hay instaladas
        for mayor, menor in VERSIONES_OK:
            ruta = capturar(["py", f"-{mayor}.{menor}", "-c",
                             "import sys; print(sys.executable)"])
            if ruta:
                candidatos.append(ruta)
    for mayor, menor in VERSIONES_OK:
        encontrado = shutil.which(f"python{mayor}.{menor}")
        if encontrado:
            candidatos.append(encontrado)

    for ruta in candidatos:
        v = version_de(ruta)
        if v in VERSIONES_OK:
            return ruta
    return None


def instalar_uv():
    """Instala la herramienta uv, que sabe descargar intérpretes de Python."""
    if shutil.which("uv"):
        return shutil.which("uv")

    print("  Instalando uv (gestor que descarga versiones de Python)...")
    intentos = [
        [sys.executable, "-m", "pip", "install", "--quiet", "uv"],
        [sys.executable, "-m", "pip", "install", "--quiet", "--user", "uv"],
        [sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages", "uv"],
    ]
    for cmd in intentos:
        if correr(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            break

    # uv puede quedar en el PATH, o como módulo del Python actual
    if shutil.which("uv"):
        return shutil.which("uv")
    if correr([sys.executable, "-m", "uv", "--version"],
              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        return [sys.executable, "-m", "uv"]
    return None


def descargar_python():
    """Descarga un CPython compatible con uv. Devuelve su ruta o None."""
    uv = instalar_uv()
    if uv is None:
        return None
    base = uv if isinstance(uv, list) else [uv]
    etiqueta = f"{PREFERIDA[0]}.{PREFERIDA[1]}"

    print(f"  Descargando Python {etiqueta} (unos 30 MB, solo para esta aplicación)...")
    if not correr(base + ["python", "install", etiqueta]):
        return None
    ruta = capturar(base + ["python", "find", etiqueta])
    if ruta and Path(ruta).exists():
        return ruta
    return None


def resolver_python():
    """Devuelve la ruta de un Python compatible, o None si no se pudo conseguir."""
    actual = sys.version_info[:2]
    print(f"  Python que ejecuta este instalador: {actual[0]}.{actual[1]}")

    ruta = buscar_en_sistema()
    if ruta:
        v = version_de(ruta)
        if ruta == sys.executable:
            ok(f"Esta versión es compatible ({v[0]}.{v[1]}).")
        else:
            ok(f"Se encontró Python {v[0]}.{v[1]} instalado en el sistema.")
            print(f"      {ruta}")
        return ruta

    aviso(f"Python {actual[0]}.{actual[1]} no es compatible con netplotbrain.")
    print("      netplotbrain necesita numpy<2.0, que no existe para Python 3.13 o")
    print("      posterior. Se puede descargar un Python 3.12 solo para esta")
    print("      aplicación, sin tocar el que ya tienes instalado.")

    r = preguntar("\n  ¿Descargar Python 3.12 automáticamente? [S/n]: ", ["s", "n"], "s")
    if r == "n":
        return None

    ruta = descargar_python()
    if ruta:
        v = version_de(ruta)
        ok(f"Python {v[0]}.{v[1]} descargado.")
        print(f"      {ruta}")
        return ruta

    error("No se pudo descargar Python automáticamente.")
    print("      Instálalo a mano desde https://www.python.org/downloads/")
    print("      (elige la versión 3.12) y vuelve a ejecutar este instalador.")
    return None


# ──────────────────────────────────────────────────────────────────────
# 2. Entorno virtual
# ──────────────────────────────────────────────────────────────────────
def python_del_venv():
    return VENV / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")


def venv_ve_el_sistema():
    """
    ¿El .venv existente fue creado con --system-site-packages?

    Las versiones anteriores del instalador lo hacían. Es un problema: si una
    librería ya está instalada globalmente con la versión exacta que pide
    requirements.txt, pip NO la copia dentro del .venv y la aplicación acaba
    dependiendo de la copia global. El día que esa copia global cambie —al
    instalar vectorbt, por ejemplo— la aplicación se rompe, que es justo lo que
    el entorno aislado debía evitar.
    """
    cfg = VENV / "pyvenv.cfg"
    try:
        for linea in cfg.read_text(encoding="utf-8").splitlines():
            if linea.lower().replace(" ", "").startswith("include-system-site-packages=true"):
                return True
    except Exception:
        pass
    return False


def crear_venv(python_base):
    if python_del_venv().exists():
        v = version_de(str(python_del_venv()))
        if v not in VERSIONES_OK:
            aviso("El .venv existente tiene una versión de Python incompatible; se recrea.")
            shutil.rmtree(VENV, ignore_errors=True)
        elif venv_ve_el_sistema():
            aviso("El .venv existente se creó con la configuración antigua, que deja")
            print("      entrar librerías del sistema. Se recrea para que quede aislado")
            print("      de verdad (se vuelven a descargar las librerías).")
            shutil.rmtree(VENV, ignore_errors=True)
        else:
            ok(f"Ya existe un .venv aislado con Python {v[0]}.{v[1]}; se reutiliza.")
            return True

    print("  Creando entorno virtual aislado en .venv ...")
    # Sin --system-site-packages, a propósito: todas las librerías se instalan
    # DENTRO del .venv. Así la aplicación no depende de nada que tengas
    # instalado globalmente, y nada que instales después puede romperla.
    if not correr([python_base, "-m", "venv", str(VENV)]):
        error("No se pudo crear el entorno virtual.")
        if not ES_WINDOWS:
            print("      En Debian/Ubuntu puede faltar el paquete python3-venv:")
            print("        sudo apt install python3-venv")
        return False
    ok("Entorno virtual creado (aislado del Python del sistema).")
    return True


def instalar_librerias():
    py = str(python_del_venv())
    correr([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
           stdout=subprocess.DEVNULL)

    # numpy va primero y como rueda precompilada: si pip intentara construirlo
    # desde el código fuente tardaría muchísimo y probablemente fallaría.
    print("  Instalando numpy<2.0 (requisito de netplotbrain)...")
    if not correr([py, "-m", "pip", "install", "--only-binary", ":all:",
                   "numpy>=1.24,<2.0"]):
        error("No se pudo instalar numpy<2.0.")
        print("      Revisa tu conexión a internet y vuelve a intentarlo.")
        return False
    ok("numpy instalado.")

    req = None
    for nombre in ("requirements.txt", "requirements_v9.txt", "requirements_v7.txt"):
        if (RAIZ / nombre).exists():
            req = RAIZ / nombre
            break
    if req is None:
        error("No se encontró requirements.txt junto a este instalador.")
        return False

    print(f"  Instalando el resto de las librerías ({req.name})...")
    if not correr([py, "-m", "pip", "install", "-r", str(req)]):
        error("Falló la instalación de alguna librería.")
        return False
    ok("Librerías instaladas.")
    return comprobar_aislamiento()


def comprobar_aislamiento():
    """
    Confirma que las librerías clave viven DENTRO del .venv.

    Si alguna se estuviera tomando del Python del sistema, la aplicación
    quedaría a merced de lo que instales después en ese Python. Mejor
    enterarse ahora que el día que deje de arrancar.
    """
    codigo = (
        "import json,sys,numpy,pandas,netplotbrain,matplotlib\n"
        "mods={'numpy':numpy,'pandas':pandas,'netplotbrain':netplotbrain,"
        "'matplotlib':matplotlib}\n"
        "print(json.dumps({n:m.__file__ for n,m in mods.items()}))\n"
    )
    salida = capturar([str(python_del_venv()), "-c", codigo])
    if not salida:
        aviso("No se pudo comprobar el aislamiento del entorno.")
        return True
    try:
        rutas = json.loads(salida.splitlines()[-1])
    except (ValueError, IndexError):
        return True

    base = str(VENV.resolve())
    fuera = [n for n, r in rutas.items() if not str(Path(r).resolve()).startswith(base)]
    if fuera:
        aviso(f"Estas librerías se están tomando de fuera del .venv: {', '.join(fuera)}")
        print("      La aplicación funcionará, pero podría romperse si cambias esas")
        print("      librerías en tu Python del sistema. Para arreglarlo, borra la")
        print("      carpeta .venv y vuelve a ejecutar el instalador.")
    else:
        ok("Todas las librerías quedaron dentro del .venv.")
    return True


def revisar_tkinter():
    """tkinter es parte de la biblioteca estándar, pero en Linux suele venir aparte."""
    py = str(python_del_venv())
    if tiene_tkinter(py):
        ok("tkinter disponible.")
        return True
    error("tkinter no está disponible; la aplicación no podrá abrir su ventana.")
    sistema = platform.system()
    if sistema == "Linux":
        print("      Instálalo con el gestor de paquetes de tu distribución:")
        print("        Debian / Ubuntu :  sudo apt install python3-tk")
        print("        Fedora          :  sudo dnf install python3-tkinter")
        print("        Arch            :  sudo pacman -S tk")
        print("      Después vuelve a ejecutar este instalador.")
    elif sistema == "Darwin":
        print("      Instálalo con:  brew install python-tk")
    else:
        print("      Reinstala Python marcando la opción «tcl/tk and IDLE».")
    return False


# ──────────────────────────────────────────────────────────────────────
# 3. Vista previa y templates
# ──────────────────────────────────────────────────────────────────────
def generar_vista_previa():
    script = RAIZ / "generar_vista_previa.py"
    if not script.exists():
        aviso("No se encontró generar_vista_previa.py; se usará el dibujo esquemático.")
        return
    if (RAIZ / "assets" / "preview_meta.json").exists():
        ok("Las imágenes de vista previa ya existen.")
        return
    print("  Descargando un template ligero y generando los cortes (unos 450 KB)...")
    if correr([str(python_del_venv()), str(script)]):
        ok("Vista previa lista.")
    else:
        aviso("No se pudo generar la vista previa real; la aplicación usará el")
        print("      dibujo esquemático. Esto no impide renderizar.")


def precargar_templates():
    """
    Descarga por adelantado los archivos de TemplateFlow que netplotbrain pide.
    Lee el propio mapa de netplotbrain (template_get_kwargs.json) para pedir
    exactamente los mismos archivos que usará al renderizar, y no otros.
    """
    py = str(python_del_venv())
    print("\n  Los templates se descargan la primera vez que renderizas, lo que puede")
    print("  tardar varios minutos. Se pueden descargar ahora:")
    print("    [1] Solo los templates de adulto más usados  (~200 MB, recomendado)")
    print("    [2] Todos, incluidos los infantiles          (~600 MB)")
    print("    [3] Ninguno; descargar al usarlos")
    r = preguntar("  Elige [1/2/3]: ", ["1", "2", "3"], "1")
    if r == "3":
        ok("Se descargarán cuando los necesites.")
        return

    codigo = r'''
import json, sys
from pathlib import Path
try:
    import netplotbrain, templateflow.api as tf
except Exception as e:
    print("  No se pudieron importar netplotbrain/templateflow:", e); sys.exit(0)

solo_adulto = (sys.argv[1] == "1")
base = Path(netplotbrain.__file__).resolve().parent
mapa = None
for p in base.rglob("template_get_kwargs.json"):
    mapa = json.loads(p.read_text(encoding="utf-8")); break
if mapa is None:
    print("  No se encontró el mapa de templates de netplotbrain; se omite.")
    sys.exit(0)

for nombre, kwargs in mapa.items():
    if solo_adulto and "Infant" in nombre:
        continue
    try:
        print(f"    {nombre} ...", flush=True)
        tf.get(nombre, **kwargs)
    except Exception as e:
        print(f"    {nombre}: no se pudo descargar ({type(e).__name__})")
print("  Descarga de templates terminada.")
'''
    if not correr([py, "-c", codigo, r]):
        aviso("La precarga de templates no terminó bien; se descargarán al usarlos.")


# ──────────────────────────────────────────────────────────────────────
# 4. Acceso directo
# ──────────────────────────────────────────────────────────────────────
def crear_acceso_directo():
    if not ES_WINDOWS:
        print("  Para abrir la aplicación:")
        print(f"    {python_del_venv()} {RAIZ / APP}")
        return
    py = str(python_del_venv())
    codigo = r'''
import os, sys
try:
    import winshell
    from win32com.client import Dispatch
except Exception:
    sys.exit(3)
escritorio = winshell.desktop()
atajo = os.path.join(escritorio, "NetPlotBrain GUI.lnk")
s = Dispatch("WScript.Shell").CreateShortCut(atajo)
s.Targetpath = sys.argv[1]
s.Arguments = f'"{sys.argv[2]}"'
s.WorkingDirectory = sys.argv[3]
if os.path.exists(sys.argv[4]):
    s.IconLocation = sys.argv[4]
s.save()
print(atajo)
'''
    pythonw = Path(py).with_name("pythonw.exe")
    destino = str(pythonw if pythonw.exists() else py)
    correr([py, "-m", "pip", "install", "--quiet", "pywin32", "winshell"],
           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if correr([py, "-c", codigo, destino, str(RAIZ / APP), str(RAIZ),
               str(RAIZ / "netplotbrain_gui.ico")]):
        ok("Acceso directo creado en el escritorio.")
    else:
        aviso("No se pudo crear el acceso directo. Para abrir la aplicación:")
        print(f"      {py} {RAIZ / APP}")


# ──────────────────────────────────────────────────────────────────────
# Programa principal
# ──────────────────────────────────────────────────────────────────────
def main():
    titulo("Instalador de NetPlotBrain GUI")
    print("  Carpeta de instalación:")
    print(f"    {RAIZ}")

    if not (RAIZ / APP).exists():
        error(f"No se encontró {APP} en esta carpeta.")
        print("      Ejecuta el instalador desde la carpeta del proyecto.")
        return 1

    total = 7

    paso(1, total, "Buscando un Python compatible (3.9 - 3.12)")
    python_base = resolver_python()
    if python_base is None:
        return 1

    paso(2, total, "Creando el entorno virtual")
    if not crear_venv(python_base):
        return 1

    paso(3, total, "Instalando las librerías")
    if not instalar_librerias():
        return 1

    paso(4, total, "Comprobando tkinter")
    if not revisar_tkinter():
        return 1

    paso(5, total, "Generando las imágenes de vista previa")
    generar_vista_previa()

    paso(6, total, "Templates de TemplateFlow")
    precargar_templates()

    paso(7, total, "Acceso directo")
    crear_acceso_directo()

    titulo("Instalación terminada")
    print("  La aplicación quedó aislada en .venv: las versiones que necesita")
    print("  (numpy<2.0 entre otras) no afectan a tus otros proyectos.")
    print()
    print("  Para abrirla:")
    if ES_WINDOWS:
        print("    - Doble clic en «NetPlotBrain GUI» en el escritorio, o")
        print(f"    - {python_del_venv()} {APP}")
    else:
        print(f"    {python_del_venv()} {APP}")
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstalación interrumpida.")
        sys.exit(1)
