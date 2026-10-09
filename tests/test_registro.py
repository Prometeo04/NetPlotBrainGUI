import sys, re, ast, tempfile, time, platform, json
from pathlib import Path

src = open(str(Path(__file__).resolve().parent.parent / 'netplotbrain_gui_v9.py')).read()
lineas = src.splitlines()
arbol = ast.parse(src)
clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == 'Registro')
codigo = "\n".join(lineas[clase.lineno-1:clase.end_lineno])
ns = {'Path': Path, 'time': time, 'platform': platform, 'sys': sys, 'VERSION': '9.5'}
exec(codigo, ns)
Registro = ns['Registro']

Registro.ruta = Path(tempfile.mkdtemp())/"prueba.log"
fallos = []
def chk(c, m):
    print(("  ok    " if c else "  FALLA ") + m)
    if not c: fallos.append(m)

r = Registro.escribir("Error de prueba", "Traceback (most recent call last):\n  ValueError: x")
chk(r is not None and r.exists(), "crea el archivo y devuelve la ruta")
texto = r.read_text(encoding="utf-8")
chk("Error de prueba" in texto and "ValueError" in texto, "guarda titulo y traceback")
chk(re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", texto) is not None, "incluye fecha y hora")
chk("NetPlotBrain GUI v9.5" in texto and "Python" in texto, "incluye version y plataforma")

Registro.escribir("Segundo error", "otro traceback")
texto = r.read_text(encoding="utf-8")
chk("Error de prueba" in texto and "Segundo error" in texto, "acumula sin perder lo anterior")

class FalsoDF:
    def __init__(self, n): self._n = n
    def __len__(self): return self._n
    def __repr__(self): return "x,y,z\n30,-20,20\n-30,-20,20 <-- COORDENADAS DE PACIENTE"

ctx = {"template":"MNI152NLin2009cAsym","template_style":"filled","view":"LSR",
       "node_type":"parcels","nodes_filas":15,"edges_filas":22}
Registro.escribir("Con contexto", "traceback", contexto=ctx)
texto = r.read_text(encoding="utf-8")
chk("filled" in texto and "parcels" in texto, "guarda los ajustes del render")
chk("nodes_filas = 15" in texto, "guarda el tamano de las tablas")
chk("PACIENTE" not in texto, "NO guarda las coordenadas de los nodos")

Registro.escribir("Grande", "tb", contexto={"nodes": FalsoDF(500)})
texto = r.read_text(encoding="utf-8")
chk("PACIENTE" not in texto, "un valor enorme se resume en vez de volcarse")
chk("<FalsoDF>" in texto, "lo reduce a su tipo")

Registro.LIMITE_BYTES = 200
Registro.escribir("Tras rotar", "tb corto")
texto = r.read_text(encoding="utf-8")
chk("Error de prueba" not in texto and "Tras rotar" in texto, "rota el archivo al pasar el limite")

Registro.ruta = Path("/ruta/que/no/existe/x.log")
try:
    chk(Registro.escribir("x","y") is None, "si no puede escribir devuelve None sin lanzar")
except Exception as e:
    chk(False, f"lanzo excepcion: {e}")

print("\n" + "="*55)
print(f"{len(fallos)} fallos" if fallos else "Todas las pruebas del registro pasaron.")
sys.exit(1 if fallos else 0)
