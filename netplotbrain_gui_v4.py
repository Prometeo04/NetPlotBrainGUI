"""
NetPlotBrainGUI — Interfaz gráfica para netplotbrain
Versión 4.0

Permite visualizar redes cerebrales en 3D sin escribir código.
Autor: Jesús Manuel Segovia Luna (Prometeo04)
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import pandas as pd

# ──────────────────────────────────────────────
# Validación de entorno al arrancar
# ──────────────────────────────────────────────

def check_environment():
    """Verifica dependencias antes de arrancar."""
    errors = []

    # NumPy: versiones >=2.0 causan 'nonzero on 0d arrays'
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
        messagebox.showerror(
            "Error de entorno",
            "Se encontraron problemas:\n\n" + "\n\n".join(errors)
        )
        root.destroy()
        sys.exit(1)


check_environment()

import netplotbrain  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

TEMPLATES = {
    "── Adulto ──": None,
    "MNI152NLin2009cAsym": "MNI152NLin2009cAsym",
    "MNI152NLin6Asym": "MNI152NLin6Asym",
    "OASIS30ANTs": "OASIS30ANTs",
    "── Infante (MNIInfant) ──": None,
    "Infante cohorte 0 (recién nacido)": "MNIInfant_cohort-0",
    "Infante cohorte 1 (2 semanas)": "MNIInfant_cohort-1",
    "Infante cohorte 2 (1 mes)": "MNIInfant_cohort-2",
    "Infante cohorte 3 (2 meses)": "MNIInfant_cohort-3",
    "Infante cohorte 4 (3 meses)": "MNIInfant_cohort-4",
    "Infante cohorte 5 (6 meses)": "MNIInfant_cohort-5",
    "Infante cohorte 6 (9 meses)": "MNIInfant_cohort-6",
    "Infante cohorte 7 (12 meses)": "MNIInfant_cohort-7",
    "Infante cohorte 8 (15 meses)": "MNIInfant_cohort-8",
    "Infante cohorte 9 (18 meses)": "MNIInfant_cohort-9",
    "Infante cohorte 10 (21 meses)": "MNIInfant_cohort-10",
    "Infante cohorte 11 (24 meses)": "MNIInfant_cohort-11",
    "── Otros ──": None,
    "WHS (rata)": "WHS",
    "Archivo NIfTI personalizado...": "__custom_nifti__",
}

VIEWS = ["L", "R", "S", "I", "A", "P", "preset-4", "preset-6"]
STYLES = ["glass", "surface", "filled", "cloudy"]
NODE_TYPES = ["circles", "spheres", "parcels"]


# ──────────────────────────────────────────────
# Clase: Editor de tabla (nodos / edges)
# ──────────────────────────────────────────────

class TableEditor(ttk.Frame):
    """Tabla editable con Treeview para nodos o edges."""

    def __init__(self, parent, columns, defaults_fn, **kw):
        super().__init__(parent, **kw)
        self.columns = columns
        self.defaults_fn = defaults_fn

        # --- Treeview ---
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="center")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Botones ---
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)

        ttk.Button(btn_frame, text="+ Agregar fila", command=self.add_row).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="- Eliminar fila", command=self.delete_row).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Editar celda", command=self.edit_cell).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Importar CSV", command=self.import_csv).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Exportar CSV", command=self.export_csv).pack(side="left", padx=2)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Doble-clic para editar
        self.tree.bind("<Double-1>", lambda e: self.edit_cell())

    def add_row(self):
        values = self.defaults_fn()
        self.tree.insert("", "end", values=values)

    def delete_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Selecciona una fila para eliminar.")
            return
        for item in selected:
            self.tree.delete(item)

    def edit_cell(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Selecciona una fila para editar.")
            return
        item = selected[0]
        current = self.tree.item(item, "values")

        dialog = tk.Toplevel(self)
        dialog.title("Editar fila")
        dialog.grab_set()
        dialog.resizable(False, False)

        entries = {}
        for i, col in enumerate(self.columns):
            ttk.Label(dialog, text=col).grid(row=i, column=0, padx=8, pady=3, sticky="e")
            entry = ttk.Entry(dialog, width=15)
            entry.insert(0, current[i])
            entry.grid(row=i, column=1, padx=8, pady=3)
            entries[col] = entry

        def save():
            new_vals = tuple(entries[c].get() for c in self.columns)
            self.tree.item(item, values=new_vals)
            dialog.destroy()

        ttk.Button(dialog, text="Guardar", command=save).grid(
            row=len(self.columns), column=0, columnspan=2, pady=8
        )

    def import_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not path:
            return
        try:
            df = pd.read_csv(path)
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            for _, row in df.iterrows():
                vals = tuple(str(row.get(c, "")) for c in self.columns)
                self.tree.insert("", "end", values=vals)
            messagebox.showinfo("Importado", f"{len(df)} filas cargadas desde CSV.")
        except Exception as e:
            messagebox.showerror("Error al importar", str(e))

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        try:
            data = []
            for item in self.tree.get_children():
                data.append(self.tree.item(item, "values"))
            df = pd.DataFrame(data, columns=self.columns)
            df.to_csv(path, index=False)
            messagebox.showinfo("Exportado", f"Archivo guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))

    def get_dataframe(self):
        """Retorna el contenido como DataFrame con tipos numéricos."""
        data = []
        for item in self.tree.get_children():
            data.append(self.tree.item(item, "values"))
        df = pd.DataFrame(data, columns=self.columns)
        # Convertir columnas numéricas
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        return df

    def row_count(self):
        return len(self.tree.get_children())


# ──────────────────────────────────────────────
# Clase: Validador de datos
# ──────────────────────────────────────────────

class DataValidator:
    """Valida consistencia entre nodos y edges antes de plotear."""

    @staticmethod
    def validate_nodes(nodes_df):
        """Verifica que el DataFrame de nodos tenga las columnas y tipos correctos."""
        errors = []
        required = ["x", "y", "z"]
        for col in required:
            if col not in nodes_df.columns:
                errors.append(f"Falta la columna '{col}' en nodos.")
            else:
                if not pd.api.types.is_numeric_dtype(nodes_df[col]):
                    errors.append(f"La columna '{col}' en nodos debe ser numérica.")

        if nodes_df.empty:
            errors.append("La tabla de nodos está vacía.")

        return errors

    @staticmethod
    def validate_edges(edges_df, num_nodes):
        """Verifica que los edges referencien nodos válidos."""
        errors = []
        required = ["i", "j"]
        for col in required:
            if col not in edges_df.columns:
                errors.append(f"Falta la columna '{col}' en edges.")
                return errors

        if not pd.api.types.is_numeric_dtype(edges_df["i"]):
            errors.append("La columna 'i' en edges debe ser numérica.")
            return errors
        if not pd.api.types.is_numeric_dtype(edges_df["j"]):
            errors.append("La columna 'j' en edges debe ser numérica.")
            return errors

        # Verificar que los índices sean válidos
        max_idx = num_nodes - 1
        bad_i = edges_df[edges_df["i"] > max_idx]
        bad_j = edges_df[edges_df["j"] > max_idx]

        if not bad_i.empty:
            errors.append(
                f"Hay {len(bad_i)} edge(s) con 'i' mayor que el número de nodos ({num_nodes}).\n"
                f"Índices inválidos: {bad_i['i'].tolist()}"
            )
        if not bad_j.empty:
            errors.append(
                f"Hay {len(bad_j)} edge(s) con 'j' mayor que el número de nodos ({num_nodes}).\n"
                f"Índices inválidos: {bad_j['j'].tolist()}"
            )

        # Self-loops
        self_loops = edges_df[edges_df["i"] == edges_df["j"]]
        if not self_loops.empty:
            errors.append(
                f"Hay {len(self_loops)} edge(s) que conectan un nodo consigo mismo (self-loop)."
            )

        return errors

    @staticmethod
    def clean_edges(edges_df, num_nodes):
        """Elimina edges que referencian nodos inexistentes."""
        if edges_df.empty:
            return edges_df
        max_idx = num_nodes - 1
        mask = (edges_df["i"] <= max_idx) & (edges_df["j"] <= max_idx)
        removed = len(edges_df) - mask.sum()
        cleaned = edges_df[mask].reset_index(drop=True)
        return cleaned, removed


# ──────────────────────────────────────────────
# Clase principal: App
# ──────────────────────────────────────────────

class NetPlotBrainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NetPlotBrain GUI v4.0")
        self.root.geometry("920x700")
        self.root.minsize(800, 600)

        self.custom_nifti_path = None

        self._build_ui()
        self._load_demo_data()

    # ── Construcción de la interfaz ──

    def _build_ui(self):
        # Frame principal con dos secciones: config (izq) y tablas (der)
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=6, pady=6)

        # --- Panel izquierdo: configuración ---
        config_frame = ttk.LabelFrame(main_paned, text="Configuración", padding=10)
        main_paned.add(config_frame, weight=1)

        row = 0

        # Template
        ttk.Label(config_frame, text="Template:").grid(row=row, column=0, sticky="w", pady=3)
        self.template_var = tk.StringVar(value="MNI152NLin2009cAsym")
        template_combo = ttk.Combobox(
            config_frame, textvariable=self.template_var,
            values=list(TEMPLATES.keys()), state="readonly", width=30
        )
        template_combo.grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        template_combo.bind("<<ComboboxSelected>>", self._on_template_change)
        row += 1

        # NIfTI path (oculto por defecto)
        self.nifti_frame = ttk.Frame(config_frame)
        self.nifti_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.nifti_label = ttk.Label(self.nifti_frame, text="Ningún archivo seleccionado", foreground="gray")
        self.nifti_label.pack(side="left", padx=4)
        ttk.Button(self.nifti_frame, text="Seleccionar NIfTI", command=self._select_nifti).pack(side="right")
        self.nifti_frame.grid_remove()
        row += 1

        # Vista
        ttk.Label(config_frame, text="Vista:").grid(row=row, column=0, sticky="w", pady=3)
        self.view_var = tk.StringVar(value="preset-4")
        ttk.Combobox(
            config_frame, textvariable=self.view_var,
            values=VIEWS, state="readonly", width=30
        ).grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        row += 1

        # Estilo del template
        ttk.Label(config_frame, text="Estilo template:").grid(row=row, column=0, sticky="w", pady=3)
        self.style_var = tk.StringVar(value="glass")
        ttk.Combobox(
            config_frame, textvariable=self.style_var,
            values=STYLES, state="readonly", width=30
        ).grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        row += 1

        # Tipo de nodo
        ttk.Label(config_frame, text="Tipo de nodo:").grid(row=row, column=0, sticky="w", pady=3)
        self.node_type_var = tk.StringVar(value="circles")
        ttk.Combobox(
            config_frame, textvariable=self.node_type_var,
            values=NODE_TYPES, state="readonly", width=30
        ).grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        row += 1

        # Escala de nodos
        ttk.Label(config_frame, text="Escala de nodos:").grid(row=row, column=0, sticky="w", pady=3)
        self.node_scale_var = tk.IntVar(value=40)
        scale_frame = ttk.Frame(config_frame)
        scale_frame.grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        self.node_scale_slider = ttk.Scale(
            scale_frame, from_=5, to=150, variable=self.node_scale_var, orient="horizontal"
        )
        self.node_scale_slider.pack(side="left", fill="x", expand=True)
        self.node_scale_label = ttk.Label(scale_frame, text="40")
        self.node_scale_label.pack(side="right", padx=4)
        self.node_scale_slider.configure(command=self._update_scale_label)
        row += 1

        # Escala de edges
        ttk.Label(config_frame, text="Escala de edges:").grid(row=row, column=0, sticky="w", pady=3)
        self.edge_scale_var = tk.IntVar(value=5)
        escale_frame = ttk.Frame(config_frame)
        escale_frame.grid(row=row, column=1, sticky="ew", pady=3, padx=4)
        self.edge_scale_slider = ttk.Scale(
            escale_frame, from_=1, to=30, variable=self.edge_scale_var, orient="horizontal"
        )
        self.edge_scale_slider.pack(side="left", fill="x", expand=True)
        self.edge_scale_label = ttk.Label(escale_frame, text="5")
        self.edge_scale_label.pack(side="right", padx=4)
        self.edge_scale_slider.configure(command=self._update_edge_scale_label)
        row += 1

        # Título del plot
        ttk.Label(config_frame, text="Título:").grid(row=row, column=0, sticky="w", pady=3)
        self.title_var = tk.StringVar(value="Mi red cerebral")
        ttk.Entry(config_frame, textvariable=self.title_var, width=30).grid(
            row=row, column=1, sticky="ew", pady=3, padx=4
        )
        row += 1

        # Separador
        ttk.Separator(config_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        # Botón generar aleatorio
        ttk.Button(
            config_frame, text="🎲 Generar nodos aleatorios",
            command=self._generate_random_nodes
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        row += 1

        # Botón plotear
        plot_btn = ttk.Button(
            config_frame, text="📊 Plotear red",
            command=self.plot_network
        )
        plot_btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        row += 1

        # Status
        self.status_var = tk.StringVar(value="Listo.")
        ttk.Label(config_frame, textvariable=self.status_var, foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=6
        )

        config_frame.columnconfigure(1, weight=1)

        # --- Panel derecho: tablas ---
        tables_frame = ttk.Frame(main_paned)
        main_paned.add(tables_frame, weight=2)

        notebook = ttk.Notebook(tables_frame)
        notebook.pack(fill="both", expand=True)

        # Tab: Nodos
        nodes_tab = ttk.Frame(notebook)
        notebook.add(nodes_tab, text="  Nodos  ")

        self.nodes_editor = TableEditor(
            nodes_tab,
            columns=("x", "y", "z", "comunidad", "centralidad"),
            defaults_fn=lambda: ("0", "0", "0", "1", "1.0")
        )
        self.nodes_editor.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab: Edges
        edges_tab = ttk.Frame(notebook)
        notebook.add(edges_tab, text="  Edges  ")

        self.edges_editor = TableEditor(
            edges_tab,
            columns=("i", "j", "weight"),
            defaults_fn=lambda: ("0", "1", "1.0")
        )
        self.edges_editor.pack(fill="both", expand=True, padx=4, pady=4)

    # ── Callbacks de UI ──

    def _on_template_change(self, event=None):
        selected = self.template_var.get()
        template_val = TEMPLATES.get(selected)

        if template_val is None:
            # Es un separador, revertir
            self.template_var.set("MNI152NLin2009cAsym")
            return

        if template_val == "__custom_nifti__":
            self.nifti_frame.grid()
        else:
            self.nifti_frame.grid_remove()
            self.custom_nifti_path = None

    def _select_nifti(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo NIfTI",
            filetypes=[
                ("NIfTI", "*.nii *.nii.gz"),
                ("Todos", "*.*")
            ]
        )
        if path:
            self.custom_nifti_path = path
            # Mostrar solo el nombre del archivo
            name = path.split("/")[-1].split("\\")[-1]
            self.nifti_label.configure(text=name, foreground="black")

    def _update_scale_label(self, val):
        self.node_scale_label.configure(text=str(int(float(val))))

    def _update_edge_scale_label(self, val):
        self.edge_scale_label.configure(text=str(int(float(val))))

    # ── Datos demo ──

    def _load_demo_data(self):
        demo_nodes = [
            ("-20", "60", "30", "1", "0.8"),
            ("20", "60", "30", "1", "0.6"),
            ("-40", "10", "50", "2", "1.0"),
            ("40", "10", "50", "2", "0.7"),
            ("0", "-30", "60", "3", "0.9"),
            ("-30", "-60", "40", "3", "0.5"),
        ]
        for vals in demo_nodes:
            self.nodes_editor.tree.insert("", "end", values=vals)

        demo_edges = [
            ("0", "1", "0.8"),
            ("0", "2", "0.5"),
            ("1", "3", "0.7"),
            ("2", "4", "0.9"),
            ("3", "4", "0.6"),
            ("4", "5", "0.4"),
        ]
        for vals in demo_edges:
            self.edges_editor.tree.insert("", "end", values=vals)

    # ── Generador aleatorio ──

    def _generate_random_nodes(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Generar nodos aleatorios")
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Número de nodos:").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        n_entry = ttk.Entry(dialog, width=10)
        n_entry.insert(0, "10")
        n_entry.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(dialog, text="Comunidades:").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        c_entry = ttk.Entry(dialog, width=10)
        c_entry.insert(0, "3")
        c_entry.grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(dialog, text="Prob. de edge:").grid(row=2, column=0, padx=8, pady=6, sticky="e")
        p_entry = ttk.Entry(dialog, width=10)
        p_entry.insert(0, "0.3")
        p_entry.grid(row=2, column=1, padx=8, pady=6)

        replace_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Reemplazar datos actuales", variable=replace_var).grid(
            row=3, column=0, columnspan=2, padx=8, pady=4
        )

        def generate():
            try:
                n = int(n_entry.get())
                n_comm = int(c_entry.get())
                p_edge = float(p_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Valores inválidos. Usa números.", parent=dialog)
                return

            if n < 2 or n > 200:
                messagebox.showerror("Error", "El número de nodos debe estar entre 2 y 200.", parent=dialog)
                return
            if not (0 < p_edge <= 1):
                messagebox.showerror("Error", "La probabilidad de edge debe estar entre 0 y 1.", parent=dialog)
                return

            # Detectar si es template de infante para ajustar coordenadas
            selected_template = self.template_var.get()
            template_val = TEMPLATES.get(selected_template, "")
            if isinstance(template_val, str) and "Infant" in template_val:
                # Cerebro infante: coordenadas más pequeñas
                coord_range = 40
            else:
                coord_range = 70

            # Generar nodos
            xs = np.random.randint(-coord_range, coord_range, n)
            ys = np.random.randint(-coord_range, coord_range, n)
            zs = np.random.randint(-10, coord_range, n)  # z positivo mayormente
            comms = np.random.randint(1, n_comm + 1, n)
            cents = np.round(np.random.uniform(0.2, 1.0, n), 2)

            # Generar edges
            edges_list = []
            for i in range(n):
                for j in range(i + 1, n):
                    if np.random.random() < p_edge:
                        w = round(np.random.uniform(0.1, 1.0), 2)
                        edges_list.append((str(i), str(j), str(w)))

            # Insertar
            if replace_var.get():
                for item in self.nodes_editor.tree.get_children():
                    self.nodes_editor.tree.delete(item)
                for item in self.edges_editor.tree.get_children():
                    self.edges_editor.tree.delete(item)

            for i in range(n):
                self.nodes_editor.tree.insert(
                    "", "end",
                    values=(str(xs[i]), str(ys[i]), str(zs[i]), str(comms[i]), str(cents[i]))
                )
            for edge in edges_list:
                self.edges_editor.tree.insert("", "end", values=edge)

            self.status_var.set(f"Generados {n} nodos y {len(edges_list)} edges.")
            dialog.destroy()

        ttk.Button(dialog, text="Generar", command=generate).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    # ── Ploteo ──

    def plot_network(self):
        self.status_var.set("Validando datos...")
        self.root.update_idletasks()

        # 1. Obtener DataFrames
        nodes_df = self.nodes_editor.get_dataframe()
        edges_df = self.edges_editor.get_dataframe()

        # 2. Validar nodos
        node_errors = DataValidator.validate_nodes(nodes_df)
        if node_errors:
            messagebox.showerror(
                "Error en nodos",
                "Problemas encontrados:\n\n• " + "\n• ".join(node_errors)
            )
            self.status_var.set("Error en validación de nodos.")
            return

        # 3. Validar edges (si hay)
        num_nodes = len(nodes_df)
        if not edges_df.empty:
            edge_errors = DataValidator.validate_edges(edges_df, num_nodes)
            if edge_errors:
                # Ofrecer limpiar automáticamente
                msg = "Problemas en edges:\n\n• " + "\n• ".join(edge_errors)
                msg += "\n\n¿Quieres limpiar automáticamente los edges inválidos y continuar?"
                response = messagebox.askyesnocancel("Error en edges", msg)

                if response is None:  # Cancel
                    self.status_var.set("Cancelado.")
                    return
                elif response:  # Yes: limpiar
                    edges_df, removed = DataValidator.clean_edges(edges_df, num_nodes)
                    messagebox.showinfo(
                        "Edges limpiados",
                        f"Se eliminaron {removed} edge(s) inválidos."
                    )
                else:  # No: abortar
                    self.status_var.set("Corrige los edges manualmente.")
                    return

        # 4. Resolver template
        selected_template = self.template_var.get()
        template_val = TEMPLATES.get(selected_template)

        if template_val is None:
            messagebox.showwarning("Template inválido", "Selecciona un template válido (no un separador).")
            self.status_var.set("Listo.")
            return

        if template_val == "__custom_nifti__":
            if not self.custom_nifti_path:
                messagebox.showwarning(
                    "Sin archivo NIfTI",
                    "Selecciona un archivo NIfTI primero."
                )
                self.status_var.set("Listo.")
                return
            template_val = self.custom_nifti_path

        # 5. Preparar argumentos
        view = self.view_var.get()
        style = self.style_var.get()
        node_type = self.node_type_var.get()
        node_scale = self.node_scale_var.get()
        edge_scale = self.edge_scale_var.get()
        title = self.title_var.get()

        # Normalizar centralidad para escala de nodos
        if "centralidad" in nodes_df.columns:
            cent_vals = nodes_df["centralidad"]
            if cent_vals.max() > 0:
                nodes_df["centralidad_norm"] = (cent_vals / cent_vals.max())
            else:
                nodes_df["centralidad_norm"] = 1.0

        plot_kwargs = {
            "template": template_val,
            "template_style": style,
            "view": view,
            "node_type": node_type,
            "node_scale": node_scale,
            "title": title,
            "node_alpha": 0.9,
        }

        # Nodos
        plot_kwargs["nodes"] = nodes_df

        if "comunidad" in nodes_df.columns:
            plot_kwargs["node_color"] = "comunidad"

        if "centralidad" in nodes_df.columns:
            plot_kwargs["node_columnscale"] = "centralidad"

        # Edges
        if not edges_df.empty:
            plot_kwargs["edges"] = edges_df
            plot_kwargs["edge_scale"] = edge_scale
            if "weight" in edges_df.columns:
                plot_kwargs["edge_widthscale"] = "weight"

        # 6. Plotear con manejo de errores
        self.status_var.set("Generando visualización...")
        self.root.update_idletasks()

        try:
            plt.close("all")
            fig, ax = netplotbrain.plot(**plot_kwargs)
            plt.show()
            self.status_var.set("Visualización generada correctamente.")

        except FileNotFoundError as e:
            messagebox.showerror(
                "Template no encontrado",
                f"No se pudo descargar o encontrar el template.\n\n"
                f"Esto puede pasar si:\n"
                f"• No hay conexión a internet (TemplateFlow necesita descargar)\n"
                f"• El nombre del template es incorrecto\n"
                f"• El archivo NIfTI no existe en la ruta indicada\n\n"
                f"Detalle: {e}"
            )
            self.status_var.set("Error: template no encontrado.")

        except Exception as e:
            error_msg = str(e)

            # Detectar error conocido de nonzero
            if "nonzero" in error_msg.lower() or "0-d" in error_msg:
                messagebox.showerror(
                    "Error de NumPy",
                    f"Error conocido de compatibilidad con NumPy.\n\n"
                    f"Solución: pip install 'numpy>=1.24,<2.0'\n\n"
                    f"Detalle: {error_msg}"
                )
            else:
                messagebox.showerror(
                    "Error al plotear",
                    f"Ocurrió un error inesperado:\n\n{error_msg}\n\n"
                    f"Verifica tus datos y configuración."
                )
            self.status_var.set(f"Error: {error_msg[:60]}...")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()

    # Estilo
    style = ttk.Style()
    available_themes = style.theme_names()
    for theme in ["clam", "alt", "default"]:
        if theme in available_themes:
            style.theme_use(theme)
            break

    app = NetPlotBrainApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
