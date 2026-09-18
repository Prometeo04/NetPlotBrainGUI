"""
NetPlotBrainGUI — Setup automatico
Ejecuta despues de clonar: python setup.py

Verifica:
  - Version de Python (3.9-3.12)
  - Instala dependencias con wheels precompilados
  - Detecta escritorio (OneDrive o normal)
  - Crea acceso directo con icono
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    ver = sys.version_info
    print(f"Python detectado: {ver.major}.{ver.minor}.{ver.micro}")
    print(f"Ejecutable: {sys.executable}\n")

    if ver.major != 3 or ver.minor < 9:
        print("X ERROR: Se requiere Python 3.9 o superior.")
        print("  Descarga desde: https://www.python.org/downloads/")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    if ver.minor >= 13:
        print(f"!! ADVERTENCIA: Python 3.{ver.minor} es muy reciente.")
        print("  netplotbrain y NumPy < 2.0 no tienen soporte oficial.")
        print("  Se recomienda Python 3.12 (la mas estable compatible).")
        print("  Descarga: https://www.python.org/downloads/release/python-3129/")
        print()
        alt = find_compatible_python()
        if alt:
            print(f"  Se encontro Python compatible: {alt}")
            print(f"  Ejecuta: \"{alt}\" setup.py")
            input("\nPresiona Enter para salir...")
            sys.exit(1)
        else:
            print("  No se encontro otra version compatible instalada.")
            print("  Instala Python 3.12 desde el enlace de arriba.")
            print()
            resp = input("  Intentar de todas formas? (s/n): ").strip().lower()
            if resp != "s":
                sys.exit(1)
            print()


def find_compatible_python():
    if sys.platform != "win32":
        return None
    for minor in [12, 11, 10, 9]:
        try:
            r = subprocess.run(["py", f"-3.{minor}", "--version"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return f"py -3.{minor}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        for base in [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
            Path("C:/Python"), Path("C:/Program Files/Python"),
        ]:
            exe = base / f"Python3{minor}" / "python.exe"
            if exe.exists():
                return str(exe)
    return None


def install_dependencies():
    print("Instalando dependencias...\n")

    print("  [1/6] NumPy...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "numpy>=1.24,<2.0", "--only-binary=:all:"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("  X No hay version precompilada de NumPy para tu Python.")
        print(f"    Python {sys.version_info.major}.{sys.version_info.minor} no es compatible con numpy<2.0")
        print("    Solucion: instala Python 3.12")
        print("    https://www.python.org/downloads/release/python-3129/")
        input("\nPresiona Enter para salir...")
        sys.exit(1)
    print("    OK NumPy")

    for step, pkg in [("2/9","matplotlib"),("3/9","pandas"),("4/9","nibabel"),
                      ("5/9","scipy"),("6/9","scikit-image"),("7/9","networkx"),
                      ("8/9","netplotbrain"),("9/9","templateflow")]:
        print(f"  [{step}] {pkg}...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                          capture_output=True, text=True)
        if r.returncode != 0:
            print(f"    !! Error: {r.stderr[:100]}")
        else:
            print(f"    OK {pkg}")

    print("\nDependencias listas.\n")


def find_desktop():
    user = Path.home()
    for od in ["OneDrive", "OneDrive - Personal", "OneDrive - Empresa"]:
        for d in ["Desktop", "Escritorio"]:
            p = user / od / d
            if p.exists(): return p
    for d in ["Desktop", "Escritorio"]:
        p = user / d
        if p.exists(): return p
    return None


def create_shortcut(desktop_path, app_dir):
    shortcut_path = desktop_path / "NetPlotBrain GUI.lnk"
    ico_path = app_dir / "netplotbrain_gui.ico"

    candidates = sorted(app_dir.glob("netplotbrain_gui*.py"), reverse=True)
    if not candidates:
        print("X No se encontro netplotbrain_gui_v*.py"); return False
    script_path = candidates[0]
    print(f"  Script: {script_path.name}")

    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists(): pythonw = Path(sys.executable)

    ico_arg = str(ico_path) if ico_path.exists() else ""

    ps = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{pythonw}"
$s.Arguments = '"{script_path}"'
$s.WorkingDirectory = "{app_dir}"
{f'$s.IconLocation = "{ico_path}"' if ico_arg else ''}
$s.Description = "NetPlotBrain GUI - Visualiza redes cerebrales en 3D"
$s.Save()
'''
    r = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  Acceso directo creado en: {desktop_path}"); return True
    else:
        print(f"  Error: {r.stderr.strip()[:100]}"); return False


def main():
    print()
    print("===========================================")
    print("   NETPLOTBRAIN GUI - SETUP AUTOMATICO")
    print("===========================================")
    print()

    app_dir = Path(__file__).parent.resolve()
    print(f"Carpeta: {app_dir}\n")

    check_python_version()
    install_dependencies()

    if sys.platform == "win32":
        desktop = find_desktop()
        if desktop:
            print(f"Escritorio: {desktop}")
            create_shortcut(desktop, app_dir)
        else:
            print("No se encontro el escritorio.")
    else:
        print(f"Ejecuta: python {app_dir / 'netplotbrain_gui_v6.py'}")

    print()
    print("===========================================")
    print("  Listo! Busca 'NetPlotBrain GUI' en")
    print("  tu escritorio y haz doble clic.")
    print("===========================================")
    print()
    input("Presiona Enter para salir...")


if __name__ == "__main__":
    main()
