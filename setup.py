"""
NetPlotBrainGUI — Setup automático
Ejecuta después de clonar: python setup.py

Detecta automáticamente:
  - Ruta del escritorio (OneDrive o normal)
  - Ruta de Python
  - Instala dependencias
  - Crea acceso directo con icono
"""

import os
import sys
import subprocess
from pathlib import Path


def find_desktop():
    """Encuentra el escritorio del usuario (soporta OneDrive)."""
    user = Path.home()
    # Intentar OneDrive primero (español e inglés)
    for onedrive_name in ["OneDrive", "OneDrive - Personal"]:
        for desk_name in ["Desktop", "Escritorio"]:
            p = user / onedrive_name / desk_name
            if p.exists():
                return p
    # Escritorio normal
    for desk_name in ["Desktop", "Escritorio"]:
        p = user / desk_name
        if p.exists():
            return p
    return None


def install_dependencies():
    """Instala las dependencias del requirements.txt."""
    req = Path(__file__).parent / "requirements.txt"
    if req.exists():
        print("Instalando dependencias...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], check=False)
        # templateflow no está en requirements.txt pero la v6 lo necesita
        subprocess.run([sys.executable, "-m", "pip", "install", "templateflow"], check=False)
        print("✓ Dependencias instaladas.\n")
    else:
        print("⚠ No se encontró requirements.txt\n")


def create_shortcut(desktop_path, app_dir):
    """Crea un acceso directo .lnk en el escritorio usando PowerShell."""
    shortcut_path = desktop_path / "NetPlotBrain GUI.lnk"
    ico_path = app_dir / "netplotbrain_gui.ico"
    script_path = app_dir / "netplotbrain_gui_v6.py"

    # Usar pythonw.exe para no mostrar terminal
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)  # fallback a python.exe

    # Verificar que el script principal existe
    if not script_path.exists():
        # Buscar cualquier netplotbrain_gui*.py
        candidates = list(app_dir.glob("netplotbrain_gui*.py"))
        if candidates:
            script_path = sorted(candidates)[-1]  # la versión más reciente
            print(f"  Script detectado: {script_path.name}")
        else:
            print("✗ No se encontró netplotbrain_gui_v*.py en la carpeta.")
            return False

    # Verificar icono
    ico_arg = str(ico_path) if ico_path.exists() else ""

    # Crear shortcut con PowerShell
    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{pythonw}"
$s.Arguments = '"{script_path}"'
$s.WorkingDirectory = "{app_dir}"
{f'$s.IconLocation = "{ico_path}"' if ico_arg else ''}
$s.Description = "NetPlotBrain GUI - Visualiza redes cerebrales en 3D"
$s.Save()
'''
    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"✓ Acceso directo creado: {shortcut_path}")
        if ico_arg:
            print(f"  Icono: {ico_path.name}")
        return True
    else:
        print(f"✗ Error al crear acceso directo: {result.stderr.strip()}")
        return False


def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   NETPLOTBRAIN GUI — SETUP AUTOMÁTICO   ║")
    print("╚══════════════════════════════════════════╝")
    print()

    app_dir = Path(__file__).parent.resolve()
    print(f"Carpeta del proyecto: {app_dir}")

    # 1. Instalar dependencias
    install_dependencies()

    # 2. Detectar escritorio
    desktop = find_desktop()
    if desktop is None:
        print("✗ No se pudo encontrar el escritorio.")
        print("  Puedes crear el acceso directo manualmente.")
        input("\nPresiona Enter para salir...")
        return

    print(f"Escritorio detectado: {desktop}\n")

    # 3. Crear shortcut
    if sys.platform == "win32":
        success = create_shortcut(desktop, app_dir)
    else:
        print("⚠ Los accesos directos automáticos solo funcionan en Windows.")
        print(f"  Para ejecutar: python {app_dir / 'netplotbrain_gui_v6.py'}")
        success = True

    # 4. Resumen
    print()
    if success:
        print("═══════════════════════════════════════════")
        print("  ✓ ¡Listo! Busca 'NetPlotBrain GUI' en")
        print("    tu escritorio y haz doble clic.")
        print("═══════════════════════════════════════════")
    else:
        print("  Para ejecutar manualmente:")
        print(f"  python {app_dir / 'netplotbrain_gui_v6.py'}")

    print()
    input("Presiona Enter para salir...")


if __name__ == "__main__":
    main()
