"""
NetPlotBrainGUI — Interfaz gráfica para netplotbrain
Versión 4.0 — ARCADE EDITION 🕹️

Permite visualizar redes cerebrales en 3D sin escribir código.
Autor: Jesús Manuel Segovia Luna (Prometeo04)
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import pandas as pd

# ══════════════════════════════════════════════
# PALETA ARCADE 80s
# ══════════════════════════════════════════════

ARCADE = {
    "bg":         "#0a0a1a",
    "bg2":        "#12122a",
    "bg3":        "#1a1a3a",
    "neon_green":  "#00ff41",
    "neon_cyan":   "#00e5ff",
    "neon_magenta":"#ff00ff",
    "neon_pink":   "#ff2d95",
    "neon_yellow": "#ffff00",
    "neon_orange": "#ff8c00",
    "text":        "#d0d0d0",
    "text_dim":    "#606080",
    "grid":        "#1e1e3e",
    "btn_bg":      "#1a1a3a",
    "entry_bg":    "#0e0e2e",
    "select_bg":   "#2a2a5a",
}

# ══════════════════════════════════════════════
# Validación de entorno al arrancar
# ══════════════════════════════════════════════

def check_environment():
    errors = []
    np_ver = tuple(int(x) for x in np.__version__.split(".")[:2])
    if np_ver >= (2, 0):
        errors.append(
            f"NumPy {np.__version__} detectado. netplotbrain requiere numpy<2.0.\n"
            f"Ejecuta: pip install 'numpy>=1.24,<2.0'"
        )
    try:
        import netplotbrain  # noqa: F401
    except ImportError:
        errors.append("netplotbrain no está instalado.\nEjecuta: pip install netplotbrain")
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        errors.append("matplotlib no está instalado.\nEjecuta: pip install matplotlib")
    try:
        import nibabel  # noqa: F401
    except ImportError:
        errors.append("nibabel no está instalado.\nEjecuta: pip install nibabel")

    if errors:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SYSTEM ERROR", "\n\n".join(errors))
        root.destroy()
        sys.exit(1)

check_environment()

import netplotbrain  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

# ══════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════

TEMPLATES = {
    "── ADULTO ──": None,
    "MNI152NLin2009cAsym": "MNI152NLin2009cAsym",
    "MNI152NLin6Asym": "MNI152NLin6Asym",
    "OASIS30ANTs": "OASIS30ANTs",
    "── INFANTE (MNIInfant) ──": None,
    "Cohorte 0 · recién nacido": "MNIInfant_cohort-0",
    "Cohorte 1 · 2 semanas": "MNIInfant_cohort-1",
    "Cohorte 2 · 1 mes": "MNIInfant_cohort-2",
    "Cohorte 3 · 2 meses": "MNIInfant_cohort-3",
    "Cohorte 4 · 3 meses": "MNIInfant_cohort-4",
    "Cohorte 5 · 6 meses": "MNIInfant_cohort-5",
    "Cohorte 6 · 9 meses": "MNIInfant_cohort-6",
    "Cohorte 7 · 12 meses": "MNIInfant_cohort-7",
    "Cohorte 8 · 15 meses": "MNIInfant_cohort-8",
    "Cohorte 9 · 18 meses": "MNIInfant_cohort-9",
    "Cohorte 10 · 21 meses": "MNIInfant_cohort-10",
    "Cohorte 11 · 24 meses": "MNIInfant_cohort-11",
    "── OTROS ──": None,
    "WHS (rata)": "WHS",
    "Archivo NIfTI personalizado...": "__custom_nifti__",
}

VIEWS = ["L", "R", "S", "I", "A", "P", "preset-4", "preset-6"]
STYLES = ["glass", "surface", "filled", "cloudy"]
NODE_TYPES = ["circles", "spheres", "parcels"]


# ══════════════════════════════════════════════
# Cerebro Pixel Art 8-bit (Canvas)
# ══════════════════════════════════════════════

def draw_pixel_brain(canvas, x_off=0, y_off=0, pixel=4):
    """Dibuja un cerebro estilo 8-bit en el canvas."""
    # Mapa de pixels: 0=vacío, 1=contorno, 2=relleno, 3=detalle/surco
    brain = [
        "00000011111100000",
        "00001122222211000",
        "00012233223322100",
        "00122322232232210",
        "01223322233223210",
        "01232232322322321",
        "12322332232233221",
        "12233223322322321",
        "12322332233232221",
        "12232223322322321",
        "12323322332332210",
        "01232232223223210",
        "01223322332232100",
        "00122232223221000",
        "00011222222110000",
        "00000111111000000",
    ]
    colors = {
        "1": ARCADE["neon_magenta"],
        "2": ARCADE["neon_pink"],
        "3": ARCADE["bg3"],
    }
    for row_i, row in enumerate(brain):
        for col_i, val in enumerate(row):
            if val in colors:
                x = x_off + col_i * pixel
                y = y_off + row_i * pixel
                canvas.create_rectangle(
                    x, y, x + pixel, y + pixel,
                    fill=colors[val], outline="", width=0
                )


# ══════════════════════════════════════════════
# Widget: Botón arcade
# ══════════════════════════════════════════════

class ArcadeButton(tk.Canvas):
    """Botón con estética neón arcade."""

    def __init__(self, parent, text, command, color=None, **kw):
        self.color = color or ARCADE["neon_green"]
        self.cmd = command
        h = kw.pop("height", 36)
        super().__init__(parent, height=h, bg=ARCADE["bg"], highlightthickness=0, cursor="hand2", **kw)
        self.text = text
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._hover_in)
        self.bind("<Leave>", self._hover_out)
        self.bind("<ButtonRelease-1>", self._click)
        self._hovered = False

    def _draw(self, event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        border_color = self.color if not self._hovered else ARCADE["neon_yellow"]
        fill_color = ARCADE["btn_bg"] if not self._hovered else ARCADE["bg3"]
        self.create_rectangle(2, 2, w-2, h-2, outline=border_color, width=2, fill=fill_color)
        self.create_text(w//2, h//2, text=self.text, fill=border_color, font=("Consolas", 10, "bold"))

    def _hover_in(self, e):
        self._hovered = True
        self._draw()

    def _hover_out(self, e):
        self._hovered = False
        self._draw()

    def _click(self, e):
        if self.cmd:
            self.cmd()


# ══════════════════════════════════════════════
# Clase: Editor de tabla (nodos / edges)
# ══════════════════════════════════════════════

class TableEditor(tk.Frame):
    def __init__(self, parent, columns, defaults_fn, **kw):
        super().__init__(parent, bg=ARCADE["bg"], **kw)
        self.columns = columns
        self.defaults_fn = defaults_fn

        style = ttk.Style()
        style.configure("Arcade.Treeview",
            background=ARCADE["bg2"],
            foreground=ARCADE["neon_green"],
            fieldbackground=ARCADE["bg2"],
            borderwidth=0,
            font=("Consolas", 10)
        )
        style.configure("Arcade.Treeview.Heading",
            background=ARCADE["bg3"],
            foreground=ARCADE["neon_cyan"],
            font=("Consolas", 10, "bold"),
            borderwidth=1,
            relief="flat"
        )
        style.map("Arcade.Treeview",
            background=[("selected", ARCADE["select_bg"])],
            foreground=[("selected", ARCADE["neon_yellow"])]
        )

        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12, style="Arcade.Treeview")
        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=80, anchor="center")

        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                                  bg=ARCADE["bg3"], troughcolor=ARCADE["bg"])
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        btn_frame = tk.Frame(self, bg=ARCADE["bg"])
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)

        for text, cmd in [
            ("+ AGREGAR", self.add_row),
            ("- ELIMINAR", self.delete_row),
            ("EDITAR", self.edit_cell),
            ("CSV ↑", self.import_csv),
            ("CSV ↓", self.export_csv),
        ]:
            ArcadeButton(btn_frame, text, cmd, color=ARCADE["neon_cyan"], height=28).pack(
                side="left", padx=2, fill="x", expand=True
            )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda e: self.edit_cell())

    def add_row(self):
        self.tree.insert("", "end", values=self.defaults_fn())

    def delete_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("SIN SELECCIÓN", "Selecciona una fila para eliminar.")
            return
        for item in selected:
            self.tree.delete(item)

    def edit_cell(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("SIN SELECCIÓN", "Selecciona una fila para editar.")
            return
        item = selected[0]
        current = self.tree.item(item, "values")

        dialog = tk.Toplevel(self)
        dialog.title("EDITAR FILA")
        dialog.configure(bg=ARCADE["bg"])
        dialog.grab_set()
        dialog.resizable(False, False)

        entries = {}
        for i, col in enumerate(self.columns):
            tk.Label(dialog, text=col.upper(), fg=ARCADE["neon_cyan"], bg=ARCADE["bg"],
                     font=("Consolas", 10)).grid(row=i, column=0, padx=8, pady=3, sticky="e")
            entry = tk.Entry(dialog, width=15, bg=ARCADE["entry_bg"], fg=ARCADE["neon_green"],
                           insertbackground=ARCADE["neon_green"], font=("Consolas", 11),
                           relief="flat", borderwidth=2)
            entry.insert(0, current[i])
            entry.grid(row=i, column=1, padx=8, pady=3)
            entries[col] = entry

        def save():
            new_vals = tuple(entries[c].get() for c in self.columns)
            self.tree.item(item, values=new_vals)
            dialog.destroy()

        ArcadeButton(dialog, "GUARDAR", save, height=30).grid(
            row=len(self.columns), column=0, columnspan=2, pady=10, padx=10, sticky="ew"
        )

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
            for item in self.tree.get_children():
                self.tree.delete(item)
            for _, row in df.iterrows():
                vals = tuple(str(row.get(c, "")) for c in self.columns)
                self.tree.insert("", "end", values=vals)
            messagebox.showinfo("DATOS CARGADOS", f"{len(df)} filas importadas.")
        except Exception as e:
            messagebox.showerror("ERROR", str(e))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            data = [self.tree.item(item, "values") for item in self.tree.get_children()]
            df = pd.DataFrame(data, columns=self.columns)
            df.to_csv(path, index=False)
            messagebox.showinfo("EXPORTADO", f"Guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("ERROR", str(e))

    def get_dataframe(self):
        data = [self.tree.item(item, "values") for item in self.tree.get_children()]
        df = pd.DataFrame(data, columns=self.columns)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        return df

    def row_count(self):
        return len(self.tree.get_children())


# ══════════════════════════════════════════════
# Validador de datos
# ══════════════════════════════════════════════

class DataValidator:
    @staticmethod
    def validate_nodes(nodes_df):
        errors = []
        for col in ["x", "y", "z"]:
            if col not in nodes_df.columns:
                errors.append(f"Falta columna '{col}' en nodos.")
            elif not pd.api.types.is_numeric_dtype(nodes_df[col]):
                errors.append(f"Columna '{col}' debe ser numérica.")
        if nodes_df.empty:
            errors.append("Tabla de nodos vacía.")
        return errors

    @staticmethod
    def validate_edges(edges_df, num_nodes):
        errors = []
        for col in ["i", "j"]:
            if col not in edges_df.columns:
                errors.append(f"Falta columna '{col}' en edges.")
                return errors
        if not pd.api.types.is_numeric_dtype(edges_df["i"]) or not pd.api.types.is_numeric_dtype(edges_df["j"]):
            errors.append("Columnas 'i' y 'j' deben ser numéricas.")
            return errors

        max_idx = num_nodes - 1
        bad_i = edges_df[edges_df["i"] > max_idx]
        bad_j = edges_df[edges_df["j"] > max_idx]
        if not bad_i.empty:
            errors.append(f"{len(bad_i)} edge(s) con 'i' fuera de rango (max={max_idx}).")
        if not bad_j.empty:
            errors.append(f"{len(bad_j)} edge(s) con 'j' fuera de rango (max={max_idx}).")
        self_loops = edges_df[edges_df["i"] == edges_df["j"]]
        if not self_loops.empty:
            errors.append(f"{len(self_loops)} self-loop(s) detectados.")
        return errors

    @staticmethod
    def clean_edges(edges_df, num_nodes):
        if edges_df.empty:
            return edges_df, 0
        max_idx = num_nodes - 1
        mask = (edges_df["i"] <= max_idx) & (edges_df["j"] <= max_idx)
        removed = len(edges_df) - mask.sum()
        return edges_df[mask].reset_index(drop=True), removed


# ══════════════════════════════════════════════
# Clase principal: App
# ══════════════════════════════════════════════

class NetPlotBrainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("▓▓ NetPlotBrain GUI v4.0 ▓▓  ARCADE EDITION")
        self.root.geometry("1000x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=ARCADE["bg"])
        self.custom_nifti_path = None

        self._build_ui()
        self._load_demo_data()

    def _build_ui(self):
        # ── Header con cerebro pixel art ──
        header = tk.Frame(self.root, bg=ARCADE["bg"], height=80)
        header.pack(fill="x", padx=10, pady=(6,0))
        header.pack_propagate(False)

        brain_canvas = tk.Canvas(header, width=76, height=68, bg=ARCADE["bg"], highlightthickness=0)
        brain_canvas.pack(side="left", padx=(10, 8))
        draw_pixel_brain(brain_canvas, x_off=2, y_off=2, pixel=4)

        title_frame = tk.Frame(header, bg=ARCADE["bg"])
        title_frame.pack(side="left", fill="y", pady=6)

        tk.Label(title_frame, text="NETPLOTBRAIN GUI",
                 fg=ARCADE["neon_green"], bg=ARCADE["bg"],
                 font=("Consolas", 22, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="▸ ARCADE EDITION  ·  Visualiza redes cerebrales en 3D",
                 fg=ARCADE["neon_cyan"], bg=ARCADE["bg"],
                 font=("Consolas", 9)).pack(anchor="w")

        # Scanlines decorativas
        scanline = tk.Canvas(header, width=200, height=68, bg=ARCADE["bg"], highlightthickness=0)
        scanline.pack(side="right", padx=10)
        for i in range(0, 68, 3):
            alpha_color = ARCADE["neon_magenta"] if i % 6 == 0 else ARCADE["bg2"]
            scanline.create_line(0, i, 200, i, fill=alpha_color, width=1)

        # Separador neón
        sep = tk.Canvas(self.root, height=2, bg=ARCADE["bg"], highlightthickness=0)
        sep.pack(fill="x", padx=10, pady=4)
        sep.bind("<Configure>", lambda e: sep.create_rectangle(0, 0, e.width, 2, fill=ARCADE["neon_green"], outline=""))

        # ── Cuerpo principal ──
        body = tk.Frame(self.root, bg=ARCADE["bg"])
        body.pack(fill="both", expand=True, padx=10, pady=4)

        # Panel izquierdo: config
        left = tk.Frame(body, bg=ARCADE["bg2"], bd=1, relief="flat", padx=12, pady=10)
        left.pack(side="left", fill="y", padx=(0, 6))

        tk.Label(left, text="═══ CONFIGURACIÓN ═══",
                 fg=ARCADE["neon_magenta"], bg=ARCADE["bg2"],
                 font=("Consolas", 11, "bold")).pack(pady=(0, 8))

        # Helper para crear labels + combos
        def add_combo(parent, label, var, values, width=28):
            f = tk.Frame(parent, bg=ARCADE["bg2"])
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, fg=ARCADE["text"], bg=ARCADE["bg2"],
                     font=("Consolas", 9), anchor="w", width=14).pack(side="left")
            combo = ttk.Combobox(f, textvariable=var, values=values, state="readonly", width=width)
            combo.pack(side="right", fill="x", expand=True)
            return combo

        def add_slider(parent, label, var, from_, to_, update_label):
            f = tk.Frame(parent, bg=ARCADE["bg2"])
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, fg=ARCADE["text"], bg=ARCADE["bg2"],
                     font=("Consolas", 9), anchor="w", width=14).pack(side="left")
            lbl = tk.Label(f, text=str(var.get()), fg=ARCADE["neon_yellow"], bg=ARCADE["bg2"],
                          font=("Consolas", 9, "bold"), width=4)
            lbl.pack(side="right")
            slider = tk.Scale(f, from_=from_, to=to_, variable=var, orient="horizontal",
                            bg=ARCADE["bg2"], fg=ARCADE["neon_green"],
                            troughcolor=ARCADE["bg"], highlightthickness=0,
                            sliderrelief="flat", showvalue=False, length=140,
                            command=lambda v: lbl.configure(text=str(int(float(v)))))
            slider.pack(side="right", padx=4)
            return slider

        # Template
        self.template_var = tk.StringVar(value="MNI152NLin2009cAsym")
        template_combo = add_combo(left, "TEMPLATE:", self.template_var, list(TEMPLATES.keys()))
        template_combo.bind("<<ComboboxSelected>>", self._on_template_change)

        # NIfTI frame
        self.nifti_frame = tk.Frame(left, bg=ARCADE["bg2"])
        self.nifti_frame.pack(fill="x")
        self.nifti_label = tk.Label(self.nifti_frame, text="Sin archivo", fg=ARCADE["text_dim"],
                                    bg=ARCADE["bg2"], font=("Consolas", 8))
        self.nifti_label.pack(side="left")
        ArcadeButton(self.nifti_frame, "NIfTI...", self._select_nifti,
                     color=ARCADE["neon_orange"], height=24).pack(side="right")
        self.nifti_frame.pack_forget()

        # Vista, Estilo, Tipo de nodo
        self.view_var = tk.StringVar(value="preset-4")
        add_combo(left, "VISTA:", self.view_var, VIEWS)

        self.style_var = tk.StringVar(value="glass")
        add_combo(left, "ESTILO:", self.style_var, STYLES)

        self.node_type_var = tk.StringVar(value="circles")
        add_combo(left, "TIPO NODO:", self.node_type_var, NODE_TYPES)

        # Sliders
        self.node_scale_var = tk.IntVar(value=40)
        add_slider(left, "ESCALA NODOS:", self.node_scale_var, 5, 150, None)

        self.edge_scale_var = tk.IntVar(value=5)
        add_slider(left, "ESCALA EDGES:", self.edge_scale_var, 1, 30, None)

        # Título
        f_title = tk.Frame(left, bg=ARCADE["bg2"])
        f_title.pack(fill="x", pady=3)
        tk.Label(f_title, text="TÍTULO:", fg=ARCADE["text"], bg=ARCADE["bg2"],
                 font=("Consolas", 9), width=14, anchor="w").pack(side="left")
        self.title_var = tk.StringVar(value="Mi red cerebral")
        tk.Entry(f_title, textvariable=self.title_var, bg=ARCADE["entry_bg"],
                 fg=ARCADE["neon_green"], insertbackground=ARCADE["neon_green"],
                 font=("Consolas", 10), relief="flat", borderwidth=2).pack(side="right", fill="x", expand=True)

        # Separador
        tk.Frame(left, height=2, bg=ARCADE["neon_magenta"]).pack(fill="x", pady=10)

        # Botones principales
        ArcadeButton(left, "🎲  GENERAR ALEATORIO", self._generate_random_nodes,
                     color=ARCADE["neon_cyan"]).pack(fill="x", pady=3)

        ArcadeButton(left, "▶  PLOTEAR RED", self.plot_network,
                     color=ARCADE["neon_green"], height=42).pack(fill="x", pady=3)

        # Status
        self.status_var = tk.StringVar(value="READY. INSERT COIN ▓")
        self.status_label = tk.Label(left, textvariable=self.status_var,
                                      fg=ARCADE["neon_yellow"], bg=ARCADE["bg2"],
                                      font=("Consolas", 8), anchor="w")
        self.status_label.pack(fill="x", pady=(8, 0))

        # ── Panel derecho: tablas ──
        right = tk.Frame(body, bg=ARCADE["bg"])
        right.pack(side="right", fill="both", expand=True)

        # Tabs manuales
        tab_bar = tk.Frame(right, bg=ARCADE["bg"])
        tab_bar.pack(fill="x")

        self._current_tab = tk.StringVar(value="nodes")
        self.tab_frames = {}

        for tab_id, label in [("nodes", "◈ NODOS"), ("edges", "◈ EDGES")]:
            btn = tk.Label(tab_bar, text=f"  {label}  ", bg=ARCADE["bg3"],
                          fg=ARCADE["neon_cyan"], font=("Consolas", 11, "bold"),
                          cursor="hand2", padx=12, pady=4)
            btn.pack(side="left", padx=(0, 2))
            btn.bind("<Button-1>", lambda e, t=tab_id: self._switch_tab(t))
            btn._tab_id = tab_id
            if tab_id == "nodes":
                btn.configure(bg=ARCADE["select_bg"], fg=ARCADE["neon_green"])
                self._nodes_tab_btn = btn
            else:
                self._edges_tab_btn = btn

        # Nodos table
        nodes_frame = tk.Frame(right, bg=ARCADE["bg"])
        self.nodes_editor = TableEditor(
            nodes_frame, columns=("x", "y", "z", "comunidad", "centralidad"),
            defaults_fn=lambda: ("0", "0", "0", "1", "1.0")
        )
        self.nodes_editor.pack(fill="both", expand=True, pady=4)
        self.tab_frames["nodes"] = nodes_frame
        nodes_frame.pack(fill="both", expand=True)

        # Edges table
        edges_frame = tk.Frame(right, bg=ARCADE["bg"])
        self.edges_editor = TableEditor(
            edges_frame, columns=("i", "j", "weight"),
            defaults_fn=lambda: ("0", "1", "1.0")
        )
        self.edges_editor.pack(fill="both", expand=True, pady=4)
        self.tab_frames["edges"] = edges_frame

        # Footer
        footer = tk.Frame(self.root, bg=ARCADE["bg"], height=22)
        footer.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(footer, text="NetPlotBrainGUI © Prometeo04  ·  Powered by netplotbrain + TemplateFlow",
                 fg=ARCADE["text_dim"], bg=ARCADE["bg"], font=("Consolas", 8)).pack(side="left")
        tk.Label(footer, text="v4.0 ARCADE",
                 fg=ARCADE["neon_magenta"], bg=ARCADE["bg"], font=("Consolas", 8, "bold")).pack(side="right")

    def _switch_tab(self, tab_id):
        for tid, frame in self.tab_frames.items():
            frame.pack_forget()
        self.tab_frames[tab_id].pack(fill="both", expand=True)
        self._current_tab.set(tab_id)

        if tab_id == "nodes":
            self._nodes_tab_btn.configure(bg=ARCADE["select_bg"], fg=ARCADE["neon_green"])
            self._edges_tab_btn.configure(bg=ARCADE["bg3"], fg=ARCADE["neon_cyan"])
        else:
            self._edges_tab_btn.configure(bg=ARCADE["select_bg"], fg=ARCADE["neon_green"])
            self._nodes_tab_btn.configure(bg=ARCADE["bg3"], fg=ARCADE["neon_cyan"])

    # ── Callbacks ──

    def _on_template_change(self, event=None):
        selected = self.template_var.get()
        template_val = TEMPLATES.get(selected)
        if template_val is None:
            self.template_var.set("MNI152NLin2009cAsym")
            return
        if template_val == "__custom_nifti__":
            self.nifti_frame.pack(fill="x", pady=2)
        else:
            self.nifti_frame.pack_forget()
            self.custom_nifti_path = None

    def _select_nifti(self):
        path = filedialog.askopenfilename(
            title="Seleccionar NIfTI",
            filetypes=[("NIfTI", "*.nii *.nii.gz"), ("Todos", "*.*")]
        )
        if path:
            self.custom_nifti_path = path
            name = path.split("/")[-1].split("\\")[-1]
            self.nifti_label.configure(text=name, fg=ARCADE["neon_orange"])

    # ── Demo data ──

    def _load_demo_data(self):
        for vals in [
            ("-20","60","30","1","0.8"), ("20","60","30","1","0.6"),
            ("-40","10","50","2","1.0"), ("40","10","50","2","0.7"),
            ("0","-30","60","3","0.9"), ("-30","-60","40","3","0.5"),
        ]:
            self.nodes_editor.tree.insert("", "end", values=vals)
        for vals in [
            ("0","1","0.8"), ("0","2","0.5"), ("1","3","0.7"),
            ("2","4","0.9"), ("3","4","0.6"), ("4","5","0.4"),
        ]:
            self.edges_editor.tree.insert("", "end", values=vals)

    # ── Generador aleatorio ──

    def _generate_random_nodes(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("GENERADOR ALEATORIO")
        dialog.configure(bg=ARCADE["bg"])
        dialog.grab_set()
        dialog.resizable(False, False)

        fields = [("Nodos:", "10"), ("Comunidades:", "3"), ("Prob. edge:", "0.3")]
        entries = {}
        for i, (label, default) in enumerate(fields):
            tk.Label(dialog, text=label, fg=ARCADE["neon_cyan"], bg=ARCADE["bg"],
                     font=("Consolas", 10)).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            e = tk.Entry(dialog, width=10, bg=ARCADE["entry_bg"], fg=ARCADE["neon_green"],
                        insertbackground=ARCADE["neon_green"], font=("Consolas", 11), relief="flat")
            e.insert(0, default)
            e.grid(row=i, column=1, padx=10, pady=5)
            entries[label] = e

        replace_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="Reemplazar datos", variable=replace_var,
                       fg=ARCADE["text"], bg=ARCADE["bg"], selectcolor=ARCADE["bg2"],
                       activebackground=ARCADE["bg"], font=("Consolas", 9)
        ).grid(row=3, column=0, columnspan=2, pady=4)

        def generate():
            try:
                n = int(entries["Nodos:"].get())
                n_comm = int(entries["Comunidades:"].get())
                p_edge = float(entries["Prob. edge:"].get())
            except ValueError:
                messagebox.showerror("ERROR", "Valores inválidos.", parent=dialog)
                return
            if n < 2 or n > 200:
                messagebox.showerror("ERROR", "Nodos: 2–200.", parent=dialog)
                return

            selected_template = self.template_var.get()
            template_val = TEMPLATES.get(selected_template, "")
            coord_range = 40 if isinstance(template_val, str) and "Infant" in template_val else 70

            xs = np.random.randint(-coord_range, coord_range, n)
            ys = np.random.randint(-coord_range, coord_range, n)
            zs = np.random.randint(-10, coord_range, n)
            comms = np.random.randint(1, n_comm + 1, n)
            cents = np.round(np.random.uniform(0.2, 1.0, n), 2)

            edge_list = []
            for i in range(n):
                for j in range(i+1, n):
                    if np.random.random() < p_edge:
                        edge_list.append((str(i), str(j), str(round(np.random.uniform(0.1, 1.0), 2))))

            if replace_var.get():
                for item in self.nodes_editor.tree.get_children():
                    self.nodes_editor.tree.delete(item)
                for item in self.edges_editor.tree.get_children():
                    self.edges_editor.tree.delete(item)

            for i in range(n):
                self.nodes_editor.tree.insert("", "end",
                    values=(str(xs[i]), str(ys[i]), str(zs[i]), str(comms[i]), str(cents[i])))
            for edge in edge_list:
                self.edges_editor.tree.insert("", "end", values=edge)

            self.status_var.set(f"GENERADOS: {n} nodos · {len(edge_list)} edges")
            dialog.destroy()

        ArcadeButton(dialog, "▶ GENERAR", generate, height=32).grid(
            row=4, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    # ── Ploteo ──

    def plot_network(self):
        self.status_var.set("VALIDANDO DATOS...")
        self.root.update_idletasks()

        nodes_df = self.nodes_editor.get_dataframe()
        edges_df = self.edges_editor.get_dataframe()

        # Validar nodos
        node_errors = DataValidator.validate_nodes(nodes_df)
        if node_errors:
            messagebox.showerror("ERROR EN NODOS", "\n".join(node_errors))
            self.status_var.set("ERROR.")
            return

        # Validar edges
        num_nodes = len(nodes_df)
        if not edges_df.empty:
            edge_errors = DataValidator.validate_edges(edges_df, num_nodes)
            if edge_errors:
                msg = "\n".join(edge_errors) + "\n\n¿Limpiar automáticamente?"
                response = messagebox.askyesnocancel("ERROR EN EDGES", msg)
                if response is None:
                    self.status_var.set("CANCELADO.")
                    return
                elif response:
                    edges_df, removed = DataValidator.clean_edges(edges_df, num_nodes)
                    messagebox.showinfo("LIMPIADO", f"{removed} edge(s) eliminados.")
                else:
                    self.status_var.set("CORRIGE LOS EDGES.")
                    return

        # Template
        selected_template = self.template_var.get()
        template_val = TEMPLATES.get(selected_template)
        if template_val is None:
            messagebox.showwarning("TEMPLATE", "Selecciona un template válido.")
            self.status_var.set("READY.")
            return
        if template_val == "__custom_nifti__":
            if not self.custom_nifti_path:
                messagebox.showwarning("NIfTI", "Selecciona un archivo NIfTI primero.")
                self.status_var.set("READY.")
                return
            template_val = self.custom_nifti_path

        # Preparar kwargs
        plot_kwargs = {
            "template": template_val,
            "template_style": self.style_var.get(),
            "view": self.view_var.get(),
            "node_type": self.node_type_var.get(),
            "node_scale": self.node_scale_var.get(),
            "title": self.title_var.get(),
            "node_alpha": 0.9,
            "nodes": nodes_df,
        }

        if "comunidad" in nodes_df.columns:
            plot_kwargs["node_color"] = "comunidad"

        # FIX: usar node_size en vez de node_columnscale
        if "centralidad" in nodes_df.columns:
            plot_kwargs["node_size"] = "centralidad"

        if not edges_df.empty:
            plot_kwargs["edges"] = edges_df
            plot_kwargs["edge_scale"] = self.edge_scale_var.get()
            # FIX: usar edge_weights en vez de edge_widthscale
            if "weight" in edges_df.columns:
                plot_kwargs["edge_weights"] = "weight"

        # Plotear
        self.status_var.set("RENDERIZANDO...")
        self.root.update_idletasks()

        try:
            plt.close("all")
            fig, ax = netplotbrain.plot(**plot_kwargs)
            plt.show()
            self.status_var.set("PLOT GENERADO ✓")
        except FileNotFoundError as e:
            messagebox.showerror("TEMPLATE NO ENCONTRADO",
                f"No se pudo descargar el template.\n\n"
                f"Revisa conexión a internet o nombre del template.\n\nDetalle: {e}")
            self.status_var.set("ERROR: TEMPLATE.")
        except Exception as e:
            error_msg = str(e)
            if "nonzero" in error_msg.lower() or "0-d" in error_msg:
                messagebox.showerror("NUMPY ERROR",
                    f"Compatibilidad con NumPy.\n\nSolución: pip install 'numpy>=1.24,<2.0'\n\n{error_msg}")
            else:
                messagebox.showerror("ERROR AL PLOTEAR",
                    f"Error inesperado:\n\n{error_msg}\n\nVerifica datos y configuración.")
            self.status_var.set(f"ERROR: {error_msg[:50]}...")


# ══════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════

def main():
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # Estilos globales para combobox
    style.configure("TCombobox",
        fieldbackground=ARCADE["entry_bg"],
        background=ARCADE["bg3"],
        foreground=ARCADE["neon_green"],
        selectbackground=ARCADE["select_bg"],
        selectforeground=ARCADE["neon_yellow"],
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", ARCADE["entry_bg"])],
        selectbackground=[("readonly", ARCADE["select_bg"])],
    )

    app = NetPlotBrainApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
