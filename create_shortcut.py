"""
Crear acceso directo de NetPlotBrainGUI en el escritorio.
Ejecuta: python create_shortcut.py
"""

import os
import sys
from pathlib import Path


def create_shortcut():
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Instalando dependencias para crear acceso directo...")
        os.system(f"{sys.executable} -m pip install pywin32 winshell")
        import winshell
        from win32com.client import Dispatch

    # Rutas
    app_dir = Path(__file__).parent.resolve()
    bat_path = str(app_dir / "NetPlotBrainGUI_launch.bat")
    ico_path = str(app_dir / "netplotbrain_gui.ico")
    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, "NetPlotBrain GUI.lnk")

    # Crear shortcut
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = bat_path
    shortcut.WorkingDirectory = str(app_dir)
    shortcut.IconLocation = ico_path
    shortcut.Description = "NetPlotBrain GUI v6.0 - Visualiza redes cerebrales en 3D"
    shortcut.WindowStyle = 7  # Minimized (oculta la terminal)
    shortcut.save()

    print(f"\n✓ Acceso directo creado en el escritorio: {shortcut_path}")
    print(f"  Icono: {ico_path}")
    print(f"  Ejecuta: {bat_path}")
    print(f"\n¡Listo! Haz doble clic en 'NetPlotBrain GUI' en tu escritorio.")


if __name__ == "__main__":
    create_shortcut()
