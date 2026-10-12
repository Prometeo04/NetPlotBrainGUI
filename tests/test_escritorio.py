"""Prueba la cadena de respaldo de escritorio_windows() simulando escenarios Windows."""
import ast, os, sys, tempfile
from pathlib import Path

src = open(str(Path(__file__).resolve().parent.parent / 'setup.py')).read()
lineas = src.splitlines()
arbol = ast.parse(src)
fn = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == 'escritorio_windows')
codigo = "\n".join(lineas[fn.lineno-1:fn.end_lineno])
ns = {'os': os, 'Path': Path}
exec(codigo, ns)
escritorio_windows = ns['escritorio_windows']

fallos = []
def chk(c, m):
    print(("  ok    " if c else "  FALLA ") + m)
    if not c: fallos.append(m)

base = Path(tempfile.mkdtemp())
guardado = dict(os.environ)

def escenario(**env):
    os.environ.clear(); os.environ.update(guardado)
    for k in ("USERPROFILE", "OneDrive", "OneDriveConsumer"):
        os.environ.pop(k, None)
    os.environ.update({k: str(v) for k, v in env.items()})

# 1. OneDrive redirige el Escritorio (el caso de Segobia)
perfil = base/"perfil_1"; od = base/"od_1"
(perfil/"Desktop").mkdir(parents=True)
(od/"Desktop").mkdir(parents=True)
escenario(USERPROFILE=perfil, OneDrive=od)
r = escritorio_windows()
chk(r == str(od/"Desktop"), f"con OneDrive, prefiere el Escritorio de OneDrive -> {r}")

# 2. Sin OneDrive
perfil2 = base/"perfil_2"; (perfil2/"Desktop").mkdir(parents=True)
escenario(USERPROFILE=perfil2)
r = escritorio_windows()
chk(r == str(perfil2/"Desktop"), f"sin OneDrive, usa el del perfil -> {r}")

# 3. Windows en español: la carpeta se llama Escritorio
perfil3 = base/"perfil_3"; (perfil3/"Escritorio").mkdir(parents=True)
escenario(USERPROFILE=perfil3)
r = escritorio_windows()
chk(r == str(perfil3/"Escritorio"), f"Windows en espanol -> {r}")

# 4. OneDrive declarado pero su carpeta no existe: cae al perfil
perfil4 = base/"perfil_4"; (perfil4/"Desktop").mkdir(parents=True)
escenario(USERPROFILE=perfil4, OneDrive=base/"od_inexistente")
r = escritorio_windows()
chk(r == str(perfil4/"Desktop"), f"OneDrive fantasma, cae al perfil -> {r}")

# 5. Nada existe: devuelve None en vez de una ruta inventada
escenario(USERPROFILE=base/"no_existe")
r = escritorio_windows()
chk(r is None, f"si no hay escritorio devuelve None -> {r}")

# 6. Nunca lanza excepcion (winreg no existe en Linux)
try:
    escenario(); escritorio_windows(); chk(True, "no lanza excepcion sin winreg")
except Exception as e:
    chk(False, f"lanzo: {e}")

os.environ.clear(); os.environ.update(guardado)
print("\n" + "="*58)
print(f"{len(fallos)} fallos" if fallos else "Todas las pruebas del escritorio pasaron.")
sys.exit(1 if fallos else 0)
