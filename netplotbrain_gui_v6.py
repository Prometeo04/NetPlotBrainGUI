"""
NetPlotBrainGUI — Interfaz gráfica para netplotbrain
Versión 6.0 — ARCADE EDITION 🕹️

Visualiza redes cerebrales en 3D sin escribir código.
Soporta: templates adultos/infantiles, atlas TemplateFlow,
nodos NIfTI (parcels), matrices de adyacencia, archivero de templates.

Autor: Jesús Manuel Segovia Luna (Prometeo04)
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import pandas as pd
from pathlib import Path

# ══════════════════════════════════════════════
# PALETA ARCADE 80s
# ══════════════════════════════════════════════

A = {
    "bg": "#0a0a1a", "bg2": "#12122a", "bg3": "#1a1a3a",
    "neon_green": "#00ff41", "neon_cyan": "#00e5ff",
    "neon_magenta": "#ff00ff", "neon_pink": "#ff2d95",
    "neon_yellow": "#ffff00", "neon_orange": "#ff8c00",
    "text": "#d0d0d0", "text_dim": "#606080",
    "btn_bg": "#1a1a3a", "entry_bg": "#0e0e2e", "select_bg": "#2a2a5a",
}

# ══════════════════════════════════════════════
# Validación de entorno
# ══════════════════════════════════════════════

def check_environment():
    errors = []
    np_ver = tuple(int(x) for x in np.__version__.split(".")[:2])
    if np_ver >= (2, 0):
        errors.append(f"NumPy {np.__version__} detectado. Requiere numpy<2.0.\n→ pip install 'numpy>=1.24,<2.0'")
    for mod, name in [("netplotbrain","netplotbrain"),("matplotlib","matplotlib"),("nibabel","nibabel"),("templateflow","templateflow")]:
        try:
            __import__(mod)
        except ImportError:
            errors.append(f"{name} no instalado.\n→ pip install {name}")
    if errors:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("SYSTEM ERROR", "\n\n".join(errors))
        root.destroy(); sys.exit(1)

check_environment()

import netplotbrain
import matplotlib.pyplot as plt
import templateflow.api as tflow
import nibabel as nib

# ══════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════

VIEWS = ["L", "R", "S", "I", "A", "P", "preset-4", "preset-6", "360"]
STYLES = ["glass", "surface", "filled", "cloudy"]
NODE_TYPES = ["circles", "spheres", "parcels"]
HEMISPHERES = ["ambos", "left", "right"]

TEMPLATEFLOW_ATLASES = {
    "Schaefer 100 (7 redes)": {"atlas": "Schaefer2018", "desc": "100Parcels7Networks", "resolution": 1},
    "Schaefer 200 (7 redes)": {"atlas": "Schaefer2018", "desc": "200Parcels7Networks", "resolution": 1},
    "Schaefer 400 (7 redes)": {"atlas": "Schaefer2018", "desc": "400Parcels7Networks", "resolution": 1},
}

# ══════════════════════════════════════════════
# Pixel Brain 8-bit
# ══════════════════════════════════════════════

def draw_pixel_brain(canvas, x_off=0, y_off=0, px=4):
    brain = [
        "00000011111100000","00001122222211000","00012233223322100",
        "00122322232232210","01223322233223210","01232232322322321",
        "12322332232233221","12233223322322321","12322332233232221",
        "12232223322322321","12323322332332210","01232232223223210",
        "01223322332232100","00122232223221000","00011222222110000",
        "00000111111000000",
    ]
    colors = {"1": A["neon_magenta"], "2": A["neon_pink"], "3": A["bg3"]}
    for ri, row in enumerate(brain):
        for ci, v in enumerate(row):
            if v in colors:
                x, y = x_off + ci*px, y_off + ri*px
                canvas.create_rectangle(x, y, x+px, y+px, fill=colors[v], outline="", width=0)

# ══════════════════════════════════════════════
# ArcadeButton
# ══════════════════════════════════════════════

class ArcadeButton(tk.Canvas):
    def __init__(self, parent, text, command, color=None, **kw):
        self.color = color or A["neon_green"]
        self.cmd = command
        h = kw.pop("height", 36)
        super().__init__(parent, height=h, bg=A["bg"], highlightthickness=0, cursor="hand2", **kw)
        self.text = text; self._hovered = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", lambda e: self.cmd() if self.cmd else None)

    def _set_hover(self, v):
        self._hovered = v; self._draw()

    def _draw(self, event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        bc = A["neon_yellow"] if self._hovered else self.color
        fc = A["bg3"] if self._hovered else A["btn_bg"]
        self.create_rectangle(2, 2, w-2, h-2, outline=bc, width=2, fill=fc)
        self.create_text(w//2, h//2, text=self.text, fill=bc, font=("Consolas", 10, "bold"))

# ══════════════════════════════════════════════
# TableEditor (nodos / edges)
# ══════════════════════════════════════════════

class TableEditor(tk.Frame):
    def __init__(self, parent, columns, defaults_fn, **kw):
        super().__init__(parent, bg=A["bg"], **kw)
        self.columns = columns; self.defaults_fn = defaults_fn

        style = ttk.Style()
        style.configure("Arcade.Treeview", background=A["bg2"], foreground=A["neon_green"],
                        fieldbackground=A["bg2"], borderwidth=0, font=("Consolas", 10))
        style.configure("Arcade.Treeview.Heading", background=A["bg3"], foreground=A["neon_cyan"],
                        font=("Consolas", 10, "bold"), borderwidth=1, relief="flat")
        style.map("Arcade.Treeview", background=[("selected", A["select_bg"])],
                  foreground=[("selected", A["neon_yellow"])])

        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12, style="Arcade.Treeview")
        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=80, anchor="center")
        sb = tk.Scrollbar(self, orient="vertical", command=self.tree.yview, bg=A["bg3"], troughcolor=A["bg"])
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); sb.grid(row=0, column=1, sticky="ns")

        bf = tk.Frame(self, bg=A["bg"]); bf.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
        for txt, cmd in [("+ AGREGAR", self.add_row), ("- ELIMINAR", self.delete_row),
                         ("EDITAR", self.edit_cell), ("CSV ↑", self.import_csv), ("CSV ↓", self.export_csv)]:
            ArcadeButton(bf, txt, cmd, color=A["neon_cyan"], height=28).pack(side="left", padx=2, fill="x", expand=True)
        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda e: self.edit_cell())

    def add_row(self): self.tree.insert("", "end", values=self.defaults_fn())

    def delete_row(self):
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("SIN SELECCIÓN", "Selecciona una fila."); return
        for i in sel: self.tree.delete(i)

    def edit_cell(self):
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("SIN SELECCIÓN", "Selecciona una fila."); return
        item = sel[0]; cur = self.tree.item(item, "values")
        d = tk.Toplevel(self); d.title("EDITAR"); d.configure(bg=A["bg"]); d.grab_set(); d.resizable(False, False)
        entries = {}
        for i, col in enumerate(self.columns):
            tk.Label(d, text=col.upper(), fg=A["neon_cyan"], bg=A["bg"], font=("Consolas", 10)).grid(row=i, column=0, padx=8, pady=3, sticky="e")
            e = tk.Entry(d, width=15, bg=A["entry_bg"], fg=A["neon_green"], insertbackground=A["neon_green"], font=("Consolas", 11), relief="flat", borderwidth=2)
            e.insert(0, cur[i]); e.grid(row=i, column=1, padx=8, pady=3); entries[col] = e
        def save():
            self.tree.item(item, values=tuple(entries[c].get() for c in self.columns)); d.destroy()
        ArcadeButton(d, "GUARDAR", save, height=30).grid(row=len(self.columns), column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("TSV", "*.tsv"), ("Todos", "*.*")])
        if not path: return
        try:
            sep = "\t" if path.endswith(".tsv") else ","
            df = pd.read_csv(path, sep=sep)
            for item in self.tree.get_children(): self.tree.delete(item)
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=tuple(str(row.get(c, "")) for c in self.columns))
            messagebox.showinfo("CARGADO", f"{len(df)} filas importadas.")
        except Exception as e:
            messagebox.showerror("ERROR", str(e))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            data = [self.tree.item(i, "values") for i in self.tree.get_children()]
            pd.DataFrame(data, columns=self.columns).to_csv(path, index=False)
            messagebox.showinfo("EXPORTADO", f"Guardado en:\n{path}")
        except Exception as e: messagebox.showerror("ERROR", str(e))

    def get_dataframe(self):
        data = [self.tree.item(i, "values") for i in self.tree.get_children()]
        df = pd.DataFrame(data, columns=self.columns)
        for col in df.columns:
            try: df[col] = pd.to_numeric(df[col])
            except: pass
        return df

    def clear(self):
        for i in self.tree.get_children(): self.tree.delete(i)

# ══════════════════════════════════════════════
# DataValidator
# ══════════════════════════════════════════════

class DataValidator:
    @staticmethod
    def validate_nodes(df):
        errs = []
        for c in ["x", "y", "z"]:
            if c not in df.columns: errs.append(f"Falta columna '{c}'.")
            elif not pd.api.types.is_numeric_dtype(df[c]): errs.append(f"'{c}' debe ser numérica.")
        if df.empty: errs.append("Tabla vacía.")
        return errs

    @staticmethod
    def validate_edges(df, n):
        errs = []
        for c in ["i", "j"]:
            if c not in df.columns: errs.append(f"Falta '{c}'."); return errs
        if not pd.api.types.is_numeric_dtype(df["i"]) or not pd.api.types.is_numeric_dtype(df["j"]):
            errs.append("'i' y 'j' deben ser numéricas."); return errs
        mx = n - 1
        if not df[df["i"] > mx].empty: errs.append(f"Edges con 'i' fuera de rango (max={mx}).")
        if not df[df["j"] > mx].empty: errs.append(f"Edges con 'j' fuera de rango (max={mx}).")
        sl = df[df["i"] == df["j"]]
        if not sl.empty: errs.append(f"{len(sl)} self-loop(s).")
        return errs

    @staticmethod
    def validate_adj_matrix(mat, n_nodes=None):
        errs = []
        if mat.ndim != 2: errs.append("La matriz debe ser 2D.")
        elif mat.shape[0] != mat.shape[1]: errs.append(f"No es cuadrada: {mat.shape}.")
        if n_nodes and mat.shape[0] != n_nodes:
            errs.append(f"Tamaño ({mat.shape[0]}) ≠ nodos ({n_nodes}).")
        return errs

    @staticmethod
    def clean_edges(df, n):
        if df.empty: return df, 0
        mx = n - 1
        mask = (df["i"] <= mx) & (df["j"] <= mx)
        return df[mask].reset_index(drop=True), len(df) - mask.sum()

# ══════════════════════════════════════════════
# TemplateManager (archivero)
# ══════════════════════════════════════════════

class TemplateManager:
    """Gestiona templates de TemplateFlow: listar, verificar caché, descargar."""

    @staticmethod
    def get_tf_home():
        return Path(os.environ.get("TEMPLATEFLOW_HOME", Path.home() / ".cache" / "templateflow"))

    @staticmethod
    def list_available():
        try:
            return sorted(tflow.templates())
        except Exception:
            return []

    @staticmethod
    def is_downloaded(tpl_name):
        """Verifica si un template tiene archivos NIfTI descargados."""
        base = tpl_name.split("_cohort")[0] if "_cohort" in tpl_name else tpl_name
        tpl_dir = TemplateManager.get_tf_home() / f"tpl-{base}"
        if not tpl_dir.exists():
            return False
        return any(tpl_dir.rglob("*.nii*"))

    @staticmethod
    def download_template(tpl_name, callback=None):
        """Descarga un template en background. callback(success, msg)."""
        def _do():
            try:
                tflow.get(tpl_name, suffix="T1w")
                if callback: callback(True, f"{tpl_name} descargado.")
            except Exception as e:
                if callback: callback(False, f"Error: {e}")
        threading.Thread(target=_do, daemon=True).start()

    @staticmethod
    def get_metadata(tpl_name):
        try:
            return tflow.get_metadata(tpl_name)
        except Exception:
            return {}

# ══════════════════════════════════════════════
# App principal
# ══════════════════════════════════════════════

class NetPlotBrainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("▓▓ NetPlotBrain GUI v6.0 ▓▓  ARCADE EDITION")
        self.root.geometry("1080x780")
        self.root.minsize(900, 650)
        self.root.configure(bg=A["bg"])

        self.custom_nifti_path = None
        self.node_nifti_path = None
        self.adj_matrix_path = None
        self.node_input_mode = tk.StringVar(value="table")  # table | nifti | atlas
        self.edge_input_mode = tk.StringVar(value="table")  # table | matrix

        self._build_ui()
        self._load_demo_data()

    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self.root, bg=A["bg"], height=74)
        hdr.pack(fill="x", padx=10, pady=(6, 0)); hdr.pack_propagate(False)

        bc = tk.Canvas(hdr, width=76, height=68, bg=A["bg"], highlightthickness=0)
        bc.pack(side="left", padx=(10, 8)); draw_pixel_brain(bc, 2, 2, 4)

        tf = tk.Frame(hdr, bg=A["bg"]); tf.pack(side="left", fill="y", pady=6)
        tk.Label(tf, text="NETPLOTBRAIN GUI", fg=A["neon_green"], bg=A["bg"],
                 font=("Consolas", 22, "bold")).pack(anchor="w")
        tk.Label(tf, text="▸ ARCADE EDITION v6  ·  Templates · Atlas · Parcels · Conectomas",
                 fg=A["neon_cyan"], bg=A["bg"], font=("Consolas", 9)).pack(anchor="w")

        sep = tk.Canvas(self.root, height=2, bg=A["bg"], highlightthickness=0)
        sep.pack(fill="x", padx=10, pady=4)
        sep.bind("<Configure>", lambda e: sep.create_rectangle(0, 0, e.width, 2, fill=A["neon_green"], outline=""))

        # ── Body ──
        body = tk.Frame(self.root, bg=A["bg"])
        body.pack(fill="both", expand=True, padx=10, pady=4)

        # === LEFT PANEL ===
        left = tk.Frame(body, bg=A["bg2"], padx=12, pady=8)
        left.pack(side="left", fill="y", padx=(0, 6))

        def section_label(parent, text):
            tk.Label(parent, text=text, fg=A["neon_magenta"], bg=A["bg2"],
                     font=("Consolas", 10, "bold")).pack(fill="x", pady=(8, 4))

        def add_combo(parent, label, var, values, w=26):
            f = tk.Frame(parent, bg=A["bg2"]); f.pack(fill="x", pady=2)
            tk.Label(f, text=label, fg=A["text"], bg=A["bg2"], font=("Consolas", 9), width=14, anchor="w").pack(side="left")
            c = ttk.Combobox(f, textvariable=var, values=values, state="readonly", width=w)
            c.pack(side="right", fill="x", expand=True); return c

        def add_slider(parent, label, var, from_, to_):
            f = tk.Frame(parent, bg=A["bg2"]); f.pack(fill="x", pady=2)
            tk.Label(f, text=label, fg=A["text"], bg=A["bg2"], font=("Consolas", 9), width=14, anchor="w").pack(side="left")
            lbl = tk.Label(f, text=str(var.get()), fg=A["neon_yellow"], bg=A["bg2"], font=("Consolas", 9, "bold"), width=4)
            lbl.pack(side="right")
            s = tk.Scale(f, from_=from_, to=to_, variable=var, orient="horizontal",
                         bg=A["bg2"], fg=A["neon_green"], troughcolor=A["bg"], highlightthickness=0,
                         sliderrelief="flat", showvalue=False, length=120,
                         command=lambda v: lbl.configure(text=str(int(float(v)))))
            s.pack(side="right", padx=4); return s

        # ── TEMPLATE ──
        section_label(left, "═══ TEMPLATE ═══")

        # Template name (listado dinámico de TemplateFlow + custom)
        self.template_var = tk.StringVar(value="MNI152NLin2009cAsym")
        tpl_list = self._build_template_list()
        self.tpl_combo = add_combo(left, "TEMPLATE:", self.template_var, tpl_list)
        self.tpl_combo.bind("<<ComboboxSelected>>", self._on_template_change)

        # NIfTI custom (oculto)
        self.nifti_frame = tk.Frame(left, bg=A["bg2"])
        self.nifti_frame.pack(fill="x")
        self.nifti_label = tk.Label(self.nifti_frame, text="Sin archivo", fg=A["text_dim"], bg=A["bg2"], font=("Consolas", 8))
        self.nifti_label.pack(side="left")
        ArcadeButton(self.nifti_frame, "NIfTI...", self._select_template_nifti, color=A["neon_orange"], height=24).pack(side="right")
        self.nifti_frame.pack_forget()

        # Template style
        self.style_var = tk.StringVar(value="glass")
        add_combo(left, "ESTILO:", self.style_var, STYLES)

        # Template alpha
        self.tpl_alpha_var = tk.IntVar(value=30)
        add_slider(left, "OPACIDAD:", self.tpl_alpha_var, 1, 100)

        # Template voxelsize
        self.tpl_voxel_var = tk.IntVar(value=2)
        add_slider(left, "VOXEL SIZE:", self.tpl_voxel_var, 1, 5)

        # ── VISUALIZACIÓN ──
        section_label(left, "═══ VISUALIZACIÓN ═══")

        self.view_var = tk.StringVar(value="preset-4")
        add_combo(left, "VISTA:", self.view_var, VIEWS)

        self.hemi_var = tk.StringVar(value="ambos")
        add_combo(left, "HEMISFERIO:", self.hemi_var, HEMISPHERES)

        self.frames_var = tk.IntVar(value=8)
        add_slider(left, "FRAMES (360):", self.frames_var, 4, 24)

        # ── NODOS ──
        section_label(left, "═══ NODOS ═══")

        self.node_type_var = tk.StringVar(value="circles")
        add_combo(left, "TIPO:", self.node_type_var, NODE_TYPES)

        self.node_scale_var = tk.IntVar(value=40)
        add_slider(left, "ESCALA:", self.node_scale_var, 5, 150)

        # ── EDGES ──
        section_label(left, "═══ EDGES ═══")

        self.edge_width_var = tk.IntVar(value=1)
        add_slider(left, "GROSOR:", self.edge_width_var, 1, 10)

        self.edge_thresh_var = tk.IntVar(value=0)
        add_slider(left, "UMBRAL:", self.edge_thresh_var, 0, 100)

        # ── TÍTULO ──
        f_title = tk.Frame(left, bg=A["bg2"]); f_title.pack(fill="x", pady=4)
        tk.Label(f_title, text="TÍTULO:", fg=A["text"], bg=A["bg2"], font=("Consolas", 9), width=14, anchor="w").pack(side="left")
        self.title_var = tk.StringVar(value="Mi red cerebral")
        tk.Entry(f_title, textvariable=self.title_var, bg=A["entry_bg"], fg=A["neon_green"],
                 insertbackground=A["neon_green"], font=("Consolas", 10), relief="flat", borderwidth=2).pack(side="right", fill="x", expand=True)

        # ── BOTONES ──
        tk.Frame(left, height=2, bg=A["neon_magenta"]).pack(fill="x", pady=6)

        ArcadeButton(left, "🎲  GENERAR ALEATORIO", self._generate_random, color=A["neon_cyan"]).pack(fill="x", pady=2)
        ArcadeButton(left, "📂  ARCHIVERO TEMPLATES", self._open_template_browser, color=A["neon_orange"]).pack(fill="x", pady=2)
        ArcadeButton(left, "▶  PLOTEAR RED", self.plot_network, color=A["neon_green"], height=42).pack(fill="x", pady=2)
        ArcadeButton(left, "💾  GUARDAR IMAGEN", self._save_image, color=A["neon_magenta"]).pack(fill="x", pady=2)

        self.status_var = tk.StringVar(value="READY. INSERT COIN ▓")
        tk.Label(left, textvariable=self.status_var, fg=A["neon_yellow"], bg=A["bg2"],
                 font=("Consolas", 8), anchor="w").pack(fill="x", pady=(6, 0))

        # === RIGHT PANEL (tabs) ===
        right = tk.Frame(body, bg=A["bg"])
        right.pack(side="right", fill="both", expand=True)

        # Tab bar
        tab_bar = tk.Frame(right, bg=A["bg"]); tab_bar.pack(fill="x")
        self._current_tab = tk.StringVar(value="nodes")
        self.tab_frames = {}
        self._tab_btns = {}

        for tid, label in [("nodes", "◈ NODOS"), ("edges", "◈ EDGES"),
                           ("node_file", "◈ NODOS NIfTI/ATLAS"), ("edge_matrix", "◈ MATRIZ ADY")]:
            btn = tk.Label(tab_bar, text=f" {label} ", bg=A["bg3"], fg=A["neon_cyan"],
                           font=("Consolas", 10, "bold"), cursor="hand2", padx=8, pady=4)
            btn.pack(side="left", padx=(0, 2))
            btn.bind("<Button-1>", lambda e, t=tid: self._switch_tab(t))
            self._tab_btns[tid] = btn

        # -- Tab: Nodos (tabla) --
        nf = tk.Frame(right, bg=A["bg"])
        self.nodes_editor = TableEditor(nf, columns=("x", "y", "z", "comunidad", "centralidad"),
                                        defaults_fn=lambda: ("0", "0", "0", "1", "1.0"))
        self.nodes_editor.pack(fill="both", expand=True, pady=4)
        self.tab_frames["nodes"] = nf
        nf.pack(fill="both", expand=True)

        # -- Tab: Edges (tabla) --
        ef = tk.Frame(right, bg=A["bg"])
        self.edges_editor = TableEditor(ef, columns=("i", "j", "weight"),
                                        defaults_fn=lambda: ("0", "1", "1.0"))
        self.edges_editor.pack(fill="both", expand=True, pady=4)
        self.tab_frames["edges"] = ef

        # -- Tab: Nodos NIfTI / Atlas --
        nff = tk.Frame(right, bg=A["bg2"], padx=20, pady=20)
        tk.Label(nff, text="CARGAR NODOS DESDE ARCHIVO O ATLAS", fg=A["neon_cyan"], bg=A["bg2"],
                 font=("Consolas", 12, "bold")).pack(pady=(0, 16))

        # Opción 1: NIfTI parcelación
        tk.Label(nff, text="Opción 1: Archivo NIfTI de parcelación (.nii / .nii.gz)",
                 fg=A["text"], bg=A["bg2"], font=("Consolas", 10)).pack(anchor="w", pady=(8, 4))
        self.node_nifti_label = tk.Label(nff, text="Ningún archivo seleccionado", fg=A["text_dim"],
                                         bg=A["bg2"], font=("Consolas", 9))
        self.node_nifti_label.pack(anchor="w", padx=20)
        ArcadeButton(nff, "📂 SELECCIONAR NIfTI PARCELACIÓN", self._select_node_nifti,
                     color=A["neon_orange"]).pack(fill="x", pady=4)

        tk.Frame(nff, height=2, bg=A["neon_magenta"]).pack(fill="x", pady=12)

        # Opción 2: Atlas TemplateFlow
        tk.Label(nff, text="Opción 2: Atlas de TemplateFlow (descarga automática)",
                 fg=A["text"], bg=A["bg2"], font=("Consolas", 10)).pack(anchor="w", pady=(8, 4))
        self.atlas_var = tk.StringVar(value=list(TEMPLATEFLOW_ATLASES.keys())[0])
        ttk.Combobox(nff, textvariable=self.atlas_var, values=list(TEMPLATEFLOW_ATLASES.keys()),
                     state="readonly", width=40).pack(anchor="w", padx=20, pady=4)
        ArcadeButton(nff, "⬇ USAR ATLAS TEMPLATEFLOW", self._use_atlas,
                     color=A["neon_cyan"]).pack(fill="x", pady=4)

        self.node_file_status = tk.Label(nff, text="", fg=A["neon_yellow"], bg=A["bg2"], font=("Consolas", 9))
        self.node_file_status.pack(anchor="w", pady=8)
        self.tab_frames["node_file"] = nff

        # -- Tab: Matriz de adyacencia --
        emf = tk.Frame(right, bg=A["bg2"], padx=20, pady=20)
        tk.Label(emf, text="CARGAR EDGES DESDE MATRIZ DE ADYACENCIA", fg=A["neon_cyan"], bg=A["bg2"],
                 font=("Consolas", 12, "bold")).pack(pady=(0, 16))
        tk.Label(emf, text="Archivo CSV (NxN, sin headers) o NumPy .npy",
                 fg=A["text"], bg=A["bg2"], font=("Consolas", 10)).pack(anchor="w", pady=(8, 4))
        self.adj_label = tk.Label(emf, text="Ningún archivo seleccionado", fg=A["text_dim"],
                                  bg=A["bg2"], font=("Consolas", 9))
        self.adj_label.pack(anchor="w", padx=20)
        ArcadeButton(emf, "📂 SELECCIONAR MATRIZ", self._select_adj_matrix,
                     color=A["neon_orange"]).pack(fill="x", pady=4)
        self.adj_status = tk.Label(emf, text="", fg=A["neon_yellow"], bg=A["bg2"], font=("Consolas", 9))
        self.adj_status.pack(anchor="w", pady=8)
        self.tab_frames["edge_matrix"] = emf

        # Footer
        ft = tk.Frame(self.root, bg=A["bg"], height=22); ft.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(ft, text="NetPlotBrainGUI © Prometeo04  ·  netplotbrain + TemplateFlow",
                 fg=A["text_dim"], bg=A["bg"], font=("Consolas", 8)).pack(side="left")
        tk.Label(ft, text="v6.0 ARCADE", fg=A["neon_magenta"], bg=A["bg"],
                 font=("Consolas", 8, "bold")).pack(side="right")

        self._switch_tab("nodes")

    # ── Tab switching ──
    def _switch_tab(self, tid):
        for t, f in self.tab_frames.items(): f.pack_forget()
        self.tab_frames[tid].pack(fill="both", expand=True)
        for t, b in self._tab_btns.items():
            if t == tid: b.configure(bg=A["select_bg"], fg=A["neon_green"])
            else: b.configure(bg=A["bg3"], fg=A["neon_cyan"])
        self._current_tab.set(tid)

    # ── Template list builder ──
    def _build_template_list(self):
        items = ["── ADULTO ──", "MNI152NLin2009cAsym", "MNI152NLin6Asym", "OASIS30ANTs",
                 "── INFANTE ──"]
        for i in range(12):
            ages = ["recién nacido","2 sem","1 mes","2 meses","3 meses","6 meses",
                    "9 meses","12 meses","15 meses","18 meses","21 meses","24 meses"]
            items.append(f"MNIInfant_cohort-{i} · {ages[i]}")
        items += ["── OTROS ──", "WHS (rata)", "NIfTI personalizado..."]
        return items

    def _resolve_template_name(self, sel):
        """Extrae el nombre real del template del string del combobox."""
        if sel.startswith("──"): return None
        if "·" in sel: return sel.split("·")[0].strip()
        if sel == "WHS (rata)": return "WHS"
        if sel == "NIfTI personalizado...": return "__custom__"
        return sel

    # ── Callbacks ──
    def _on_template_change(self, event=None):
        sel = self.template_var.get()
        resolved = self._resolve_template_name(sel)
        if resolved is None:
            self.template_var.set("MNI152NLin2009cAsym"); return
        if resolved == "__custom__":
            self.nifti_frame.pack(fill="x", pady=2)
        else:
            self.nifti_frame.pack_forget(); self.custom_nifti_path = None

    def _select_template_nifti(self):
        p = filedialog.askopenfilename(title="NIfTI Template", filetypes=[("NIfTI", "*.nii *.nii.gz")])
        if p:
            self.custom_nifti_path = p
            self.nifti_label.configure(text=Path(p).name, fg=A["neon_orange"])

    def _select_node_nifti(self):
        p = filedialog.askopenfilename(title="NIfTI Parcelación", filetypes=[("NIfTI", "*.nii *.nii.gz")])
        if not p: return
        try:
            img = nib.load(p)
            if img.ndim != 3:
                messagebox.showerror("ERROR", f"El archivo es {img.ndim}D. Se necesita 3D para parcelación.")
                return
            n_parcels = len(np.unique(img.get_fdata())) - 1  # minus background (0)
            self.node_nifti_path = p
            self.node_input_mode.set("nifti")
            self.node_nifti_label.configure(text=Path(p).name, fg=A["neon_orange"])
            self.node_file_status.configure(text=f"✓ Cargado: {n_parcels} parcels detectados")
            self.node_type_var.set("parcels")
        except Exception as e:
            messagebox.showerror("ERROR AL CARGAR NIfTI", str(e))

    def _use_atlas(self):
        atlas_name = self.atlas_var.get()
        atlas_dict = TEMPLATEFLOW_ATLASES.get(atlas_name)
        if not atlas_dict:
            messagebox.showerror("ERROR", "Atlas no reconocido."); return
        self.node_input_mode.set("atlas")
        self.node_file_status.configure(text=f"✓ Atlas seleccionado: {atlas_name}\n  Se descargará al plotear si no existe.")

    def _select_adj_matrix(self):
        p = filedialog.askopenfilename(title="Matriz de adyacencia",
                                       filetypes=[("CSV", "*.csv"), ("NumPy", "*.npy"), ("Todos", "*.*")])
        if not p: return
        try:
            if p.endswith(".npy"):
                mat = np.load(p)
            else:
                mat = np.loadtxt(p, delimiter=",")
            errs = DataValidator.validate_adj_matrix(mat)
            if errs:
                messagebox.showerror("ERROR EN MATRIZ", "\n".join(errs)); return
            self.adj_matrix_path = p
            self.edge_input_mode.set("matrix")
            self.adj_label.configure(text=Path(p).name, fg=A["neon_orange"])
            self.adj_status.configure(text=f"✓ Matriz {mat.shape[0]}×{mat.shape[1]} cargada")
        except Exception as e:
            messagebox.showerror("ERROR", str(e))

    # ── Template browser ──
    def _open_template_browser(self):
        win = tk.Toplevel(self.root); win.title("ARCHIVERO DE TEMPLATES")
        win.configure(bg=A["bg"]); win.geometry("500x450"); win.grab_set()

        tk.Label(win, text="═══ TEMPLATES DISPONIBLES ═══", fg=A["neon_magenta"], bg=A["bg"],
                 font=("Consolas", 12, "bold")).pack(pady=10)

        frame = tk.Frame(win, bg=A["bg"]); frame.pack(fill="both", expand=True, padx=10, pady=4)
        listbox = tk.Listbox(frame, bg=A["bg2"], fg=A["neon_green"], font=("Consolas", 10),
                             selectbackground=A["select_bg"], selectforeground=A["neon_yellow"],
                             highlightthickness=0, borderwidth=0)
        sb = tk.Scrollbar(frame, command=listbox.yview, bg=A["bg3"], troughcolor=A["bg"])
        listbox.configure(yscrollcommand=sb.set)
        listbox.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")

        status_label = tk.Label(win, text="Cargando templates...", fg=A["neon_yellow"], bg=A["bg"],
                                font=("Consolas", 9))
        status_label.pack(pady=4)

        def load_list():
            templates = TemplateManager.list_available()
            for tpl in templates:
                cached = "✓" if TemplateManager.is_downloaded(tpl) else "○"
                listbox.insert("end", f"  {cached}  {tpl}")
            status_label.configure(text=f"{len(templates)} templates en TemplateFlow")

        def download_selected():
            sel = listbox.curselection()
            if not sel: messagebox.showwarning("SIN SELECCIÓN", "Selecciona un template.", parent=win); return
            text = listbox.get(sel[0]).strip()
            tpl = text.split()[-1]  # get name after symbol
            status_label.configure(text=f"Descargando {tpl}...")
            def cb(ok, msg):
                win.after(0, lambda: status_label.configure(text=msg))
                if ok:
                    win.after(0, lambda: listbox.delete(sel[0]))
                    win.after(0, lambda: listbox.insert(sel[0], f"  ✓  {tpl}"))
            TemplateManager.download_template(tpl, cb)

        ArcadeButton(win, "⬇ DESCARGAR SELECCIONADO", download_selected,
                     color=A["neon_cyan"]).pack(fill="x", padx=10, pady=4)

        win.after(100, load_list)

    # ── Demo data ──
    def _load_demo_data(self):
        for v in [("-20","60","30","1","0.8"),("20","60","30","1","0.6"),
                  ("-40","10","50","2","1.0"),("40","10","50","2","0.7"),
                  ("0","-30","60","3","0.9"),("-30","-60","40","3","0.5")]:
            self.nodes_editor.tree.insert("", "end", values=v)
        for v in [("0","1","0.8"),("0","2","0.5"),("1","3","0.7"),
                  ("2","4","0.9"),("3","4","0.6"),("4","5","0.4")]:
            self.edges_editor.tree.insert("", "end", values=v)

    # ── Random generator ──
    def _generate_random(self):
        d = tk.Toplevel(self.root); d.title("GENERADOR"); d.configure(bg=A["bg"]); d.grab_set(); d.resizable(False, False)
        fields = [("Nodos:", "10"), ("Comunidades:", "3"), ("Prob. edge:", "0.3")]
        entries = {}
        for i, (l, df) in enumerate(fields):
            tk.Label(d, text=l, fg=A["neon_cyan"], bg=A["bg"], font=("Consolas", 10)).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            e = tk.Entry(d, width=10, bg=A["entry_bg"], fg=A["neon_green"], insertbackground=A["neon_green"],
                         font=("Consolas", 11), relief="flat"); e.insert(0, df)
            e.grid(row=i, column=1, padx=10, pady=5); entries[l] = e

        def gen():
            try:
                n=int(entries["Nodos:"].get()); nc=int(entries["Comunidades:"].get()); pe=float(entries["Prob. edge:"].get())
            except: messagebox.showerror("ERROR", "Valores inválidos.", parent=d); return
            if n<2 or n>200: messagebox.showerror("ERROR", "Nodos: 2–200.", parent=d); return
            cr = 40 if "Infant" in self.template_var.get() else 70
            self.nodes_editor.clear(); self.edges_editor.clear()
            for i in range(n):
                self.nodes_editor.tree.insert("", "end", values=(
                    str(np.random.randint(-cr,cr)), str(np.random.randint(-cr,cr)),
                    str(np.random.randint(-10,cr)), str(np.random.randint(1,nc+1)),
                    str(round(np.random.uniform(0.2,1.0),2))))
            for i in range(n):
                for j in range(i+1,n):
                    if np.random.random()<pe:
                        self.edges_editor.tree.insert("","end",values=(str(i),str(j),str(round(np.random.uniform(0.1,1.0),2))))
            self.node_input_mode.set("table"); self.edge_input_mode.set("table")
            self.status_var.set(f"GENERADOS: {n} nodos"); d.destroy()

        ArcadeButton(d, "▶ GENERAR", gen, height=32).grid(row=3, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    # ── Save image ──
    def _save_image(self):
        p = filedialog.asksaveasfilename(defaultextension=".png",
                                          filetypes=[("PNG", "*.png"), ("SVG", "*.svg")])
        if not p: return
        try:
            fig = plt.gcf()
            fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
            messagebox.showinfo("GUARDADO", f"Imagen guardada en:\n{p}")
        except Exception as e:
            messagebox.showerror("ERROR", str(e))

    # ══════════════════════════════════════════
    # PLOTEO PRINCIPAL
    # ══════════════════════════════════════════

    def plot_network(self):
        self.status_var.set("VALIDANDO..."); self.root.update_idletasks()

        # ── Resolver template ──
        sel = self.template_var.get()
        tpl = self._resolve_template_name(sel)
        if tpl is None:
            messagebox.showwarning("TEMPLATE", "Selecciona un template válido."); return
        if tpl == "__custom__":
            if not self.custom_nifti_path:
                messagebox.showwarning("NIfTI", "Selecciona un archivo NIfTI."); return
            tpl = self.custom_nifti_path

        # ── Resolver nodos ──
        node_mode = self.node_input_mode.get()
        nodes_input = None
        nodes_df_extra = None

        if node_mode == "table":
            nodes_input = self.nodes_editor.get_dataframe()
            errs = DataValidator.validate_nodes(nodes_input)
            if errs:
                messagebox.showerror("ERROR NODOS", "\n".join(errs)); return

        elif node_mode == "nifti":
            if not self.node_nifti_path:
                messagebox.showerror("ERROR", "No hay NIfTI de parcelación cargado."); return
            nodes_input = self.node_nifti_path

        elif node_mode == "atlas":
            atlas_name = self.atlas_var.get()
            atlas_dict = TEMPLATEFLOW_ATLASES.get(atlas_name)
            if not atlas_dict:
                messagebox.showerror("ERROR", "Atlas no reconocido."); return
            nodes_input = atlas_dict

        # ── Resolver edges ──
        edge_mode = self.edge_input_mode.get()
        edges_input = None

        if edge_mode == "table":
            edges_df = self.edges_editor.get_dataframe()
            if not edges_df.empty:
                if node_mode == "table":
                    n_nodes = len(nodes_input)
                    errs = DataValidator.validate_edges(edges_df, n_nodes)
                    if errs:
                        msg = "\n".join(errs) + "\n\n¿Limpiar automáticamente?"
                        r = messagebox.askyesnocancel("EDGES", msg)
                        if r is None: return
                        elif r: edges_df, rm = DataValidator.clean_edges(edges_df, n_nodes)
                        else: return
                edges_input = edges_df

        elif edge_mode == "matrix":
            if not self.adj_matrix_path:
                messagebox.showerror("ERROR", "No hay matriz cargada."); return
            try:
                if self.adj_matrix_path.endswith(".npy"):
                    edges_input = np.load(self.adj_matrix_path)
                else:
                    edges_input = np.loadtxt(self.adj_matrix_path, delimiter=",")
            except Exception as e:
                messagebox.showerror("ERROR", f"No se pudo cargar la matriz:\n{e}"); return

        # ── Construir kwargs ──
        kwargs = {
            "template": tpl,
            "template_style": self.style_var.get(),
            "template_alpha": self.tpl_alpha_var.get() / 100.0,
            "template_voxelsize": int(self.tpl_voxel_var.get()),
            "view": self.view_var.get(),
            "title": self.title_var.get(),
            "node_type": self.node_type_var.get(),
            "node_scale": int(self.node_scale_var.get()),  # FIX: cast to int
            "node_alpha": 0.9,
        }

        # Frames para 360
        if kwargs["view"] == "360":
            kwargs["frames"] = int(self.frames_var.get())

        # Hemisferio
        hemi = self.hemi_var.get()
        if hemi != "ambos":
            kwargs["hemisphere"] = hemi

        # Nodos
        kwargs["nodes"] = nodes_input
        if nodes_df_extra is not None:
            kwargs["nodes_df"] = nodes_df_extra

        # node_color y node_size solo si son tabla y la columna existe
        if node_mode == "table" and isinstance(nodes_input, pd.DataFrame):
            if "comunidad" in nodes_input.columns:
                kwargs["node_color"] = "comunidad"
            if "centralidad" in nodes_input.columns:
                kwargs["node_size"] = "centralidad"

        # Edges
        if edges_input is not None:
            kwargs["edges"] = edges_input
            kwargs["edge_widthscale"] = int(self.edge_width_var.get())  # FIX: correcto + cast int

            # edge_weights solo si es DataFrame con columna weight
            if isinstance(edges_input, pd.DataFrame) and "weight" in edges_input.columns:
                kwargs["edge_weights"] = "weight"

            # Threshold
            thresh = self.edge_thresh_var.get() / 100.0
            if thresh > 0:
                kwargs["edge_threshold"] = thresh
                kwargs["edge_thresholddirection"] = ">"

        # ── Plotear ──
        self.status_var.set("RENDERIZANDO..."); self.root.update_idletasks()

        try:
            plt.close("all")
            fig, ax = netplotbrain.plot(**kwargs)
            plt.show()
            self.status_var.set("PLOT GENERADO ✓")

        except FileNotFoundError as e:
            messagebox.showerror("TEMPLATE NO ENCONTRADO",
                f"No se pudo descargar el template.\nRevisa tu conexión a internet.\n\n{e}")
            self.status_var.set("ERROR: TEMPLATE.")

        except Exception as e:
            msg = str(e)
            if "nonzero" in msg.lower() or "0-d" in msg:
                messagebox.showerror("NUMPY ERROR",
                    f"Compatibilidad NumPy.\n→ pip install 'numpy>=1.24,<2.0'\n\n{msg}")
            elif "multiply sequence" in msg.lower():
                messagebox.showerror("ERROR DE TIPO",
                    f"Un parámetro numérico recibió un tipo incorrecto.\n"
                    f"Esto suele pasar con node_scale o edge_widthscale.\n\n{msg}")
            else:
                messagebox.showerror("ERROR", f"Error inesperado:\n\n{msg}")
            self.status_var.set(f"ERROR: {msg[:50]}...")


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════

def main():
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names(): style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=A["entry_bg"], background=A["bg3"],
                    foreground=A["neon_green"], selectbackground=A["select_bg"], selectforeground=A["neon_yellow"])
    style.map("TCombobox", fieldbackground=[("readonly", A["entry_bg"])],
              selectbackground=[("readonly", A["select_bg"])])
    app = NetPlotBrainApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
