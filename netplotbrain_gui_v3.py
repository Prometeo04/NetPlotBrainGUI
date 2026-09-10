import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import netplotbrain
import matplotlib.pyplot as plt
import os


class NetPlotBrainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NetPlotBrain — Editor de Nodos y Edges v3")
        self.root.geometry("1020x750")
        self.root.configure(bg="#1e1e2e")
        self.current_fig = None

        self._setup_styles()

        self.comunidades = [
            "Default", "Atención", "Visual", "Motora",
            "Frontal", "Temporal", "Parietal", "Límbica",
        ]
        self.templates = [
            "MNI152NLin2009cAsym", "MNI152NLin6Asym",
            "MNI152NLin6Sym", "OASIS30ANTs",
        ]
        self.views = ["LSR", "L", "R", "S", "I", "A", "P", "LR", "AP", "SI"]
        self.styles_list = ["glass", "surface", "filled"]
        self.node_types = ["circles", "spheres"]

        self._build_toolbar()
        self._build_notebook()
        self._build_config()
        self._build_status()

        self._generar_random_nodos(10)
        self._generar_random_edges(12)

    # ── Estilos ──
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e1e2e", foreground="#cdd6f4",
                         fieldbackground="#1e1e2e", rowheight=26,
                         font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#313244",
                         foreground="#cdd6f4", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#45475a")])
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Segoe UI", 10))
        style.configure("TNotebook", background="#1e1e2e")
        style.configure("TNotebook.Tab", background="#313244",
                         foreground="#cdd6f4", padding=[12, 4],
                         font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", "#45475a")],
                  foreground=[("selected", "#89b4fa")])
        style.configure("TLabelframe", background="#1e1e2e",
                         foreground="#cdd6f4")
        style.configure("TLabelframe.Label", background="#1e1e2e",
                         foreground="#89b4fa", font=("Segoe UI", 10, "bold"))
        style.configure("TCombobox", font=("Segoe UI", 10))

    def _make_btn(self, parent, text, command, bg="#313244", fg="#cdd6f4",
                  font_size=9, **kw):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground="#45475a", activeforeground="#cdd6f4",
                         bd=0, padx=10, pady=4,
                         font=("Segoe UI", font_size), **kw)

    # ── Toolbar ──
    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg="#181825", pady=6, padx=10)
        toolbar.pack(fill="x")
        tk.Label(toolbar, text="NetPlotBrain", bg="#181825", fg="#89b4fa",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=(0, 20))

    # ── Notebook (pestañas Nodos / Edges) ──
    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # ── Pestaña Nodos ──
        nodos_frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(nodos_frame, text="  Nodos  ")

        nodos_btn_bar = tk.Frame(nodos_frame, bg="#1e1e2e")
        nodos_btn_bar.pack(fill="x", pady=(6, 4), padx=4)

        for txt, cmd in [
            ("+ Agregar nodo", self._agregar_nodo),
            ("Aleatorios (20)", lambda: self._generar_random_nodos(20)),
            ("Importar CSV", self._importar_nodos_csv),
            ("Exportar CSV", self._exportar_nodos_csv),
            ("Eliminar seleccionado", self._eliminar_nodo),
            ("Limpiar nodos", self._limpiar_nodos),
        ]:
            self._make_btn(nodos_btn_bar, txt, cmd).pack(side="left", padx=3)

        self.nodos_count_label = tk.Label(nodos_btn_bar, text="0 nodos",
                                           bg="#1e1e2e", fg="#6c7086",
                                           font=("Segoe UI", 9))
        self.nodos_count_label.pack(side="right", padx=10)

        tree_frame = tk.Frame(nodos_frame, bg="#1e1e2e")
        tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        n_cols = ("idx", "x", "y", "z", "comunidad", "centralidad")
        self.nodes_tree = ttk.Treeview(tree_frame, columns=n_cols,
                                        show="headings", selectmode="browse")
        widths = {"idx": 45, "x": 70, "y": 70, "z": 70,
                  "comunidad": 130, "centralidad": 90}
        for col in n_cols:
            self.nodes_tree.heading(col, text=col.upper())
            self.nodes_tree.column(col, width=widths[col], anchor="center")

        scrollbar_n = ttk.Scrollbar(tree_frame, orient="vertical",
                                     command=self.nodes_tree.yview)
        self.nodes_tree.configure(yscrollcommand=scrollbar_n.set)
        self.nodes_tree.pack(side="left", fill="both", expand=True)
        scrollbar_n.pack(side="right", fill="y")
        self.nodes_tree.bind("<Double-1>", self._editar_celda_nodo)

        # ── Pestaña Edges ──
        edges_frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(edges_frame, text="  Edges  ")

        edges_btn_bar = tk.Frame(edges_frame, bg="#1e1e2e")
        edges_btn_bar.pack(fill="x", pady=(6, 4), padx=4)

        for txt, cmd in [
            ("+ Agregar edge", self._agregar_edge),
            ("Aleatorios (15)", lambda: self._generar_random_edges(15)),
            ("Importar CSV", self._importar_edges_csv),
            ("Exportar CSV", self._exportar_edges_csv),
            ("Eliminar seleccionado", self._eliminar_edge),
            ("Limpiar edges", self._limpiar_edges),
        ]:
            self._make_btn(edges_btn_bar, txt, cmd).pack(side="left", padx=3)

        self.edges_count_label = tk.Label(edges_btn_bar, text="0 edges",
                                           bg="#1e1e2e", fg="#6c7086",
                                           font=("Segoe UI", 9))
        self.edges_count_label.pack(side="right", padx=10)

        tk.Label(edges_frame,
                 text="i y j son índices de nodos (empiezan en 0).  "
                      "weight controla el grosor de la línea.",
                 bg="#1e1e2e", fg="#585b70",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(0, 2))

        tree_frame_e = tk.Frame(edges_frame, bg="#1e1e2e")
        tree_frame_e.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        e_cols = ("i", "j", "weight")
        self.edges_tree = ttk.Treeview(tree_frame_e, columns=e_cols,
                                        show="headings", selectmode="browse")
        for col in e_cols:
            self.edges_tree.heading(col, text=col.upper())
            self.edges_tree.column(col, width=100, anchor="center")

        scrollbar_e = ttk.Scrollbar(tree_frame_e, orient="vertical",
                                     command=self.edges_tree.yview)
        self.edges_tree.configure(yscrollcommand=scrollbar_e.set)
        self.edges_tree.pack(side="left", fill="both", expand=True)
        scrollbar_e.pack(side="right", fill="y")
        self.edges_tree.bind("<Double-1>", self._editar_celda_edge)

    # ── Configuración y botones Plot ──
    def _build_config(self):
        config_frame = ttk.LabelFrame(self.root,
                                       text="Configuración de Visualización")
        config_frame.pack(fill="x", padx=10, pady=6)

        inner = tk.Frame(config_frame, bg="#1e1e2e")
        inner.pack(fill="x", padx=10, pady=8)

        row1 = tk.Frame(inner, bg="#1e1e2e")
        row1.pack(fill="x", pady=2)

        ttk.Label(row1, text="Template:").pack(side="left", padx=(0, 4))
        self.template_var = tk.StringVar(value=self.templates[0])
        ttk.Combobox(row1, textvariable=self.template_var,
                      values=self.templates, width=22,
                      state="readonly").pack(side="left", padx=(0, 12))

        ttk.Label(row1, text="Vista:").pack(side="left", padx=(0, 4))
        self.view_var = tk.StringVar(value="LSR")
        ttk.Combobox(row1, textvariable=self.view_var, values=self.views,
                      width=6, state="readonly").pack(side="left", padx=(0, 12))

        ttk.Label(row1, text="Estilo:").pack(side="left", padx=(0, 4))
        self.style_var = tk.StringVar(value="glass")
        ttk.Combobox(row1, textvariable=self.style_var,
                      values=self.styles_list, width=8,
                      state="readonly").pack(side="left", padx=(0, 12))

        ttk.Label(row1, text="Nodo:").pack(side="left", padx=(0, 4))
        self.nodetype_var = tk.StringVar(value="circles")
        ttk.Combobox(row1, textvariable=self.nodetype_var,
                      values=self.node_types, width=8,
                      state="readonly").pack(side="left", padx=(0, 12))

        ttk.Label(row1, text="Escala:").pack(side="left", padx=(0, 4))
        self.scale_var = tk.StringVar(value="80")
        tk.Entry(row1, textvariable=self.scale_var, width=5, bg="#313244",
                 fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")

        row2 = tk.Frame(inner, bg="#1e1e2e")
        row2.pack(fill="x", pady=(8, 2))

        ttk.Label(row2, text="Título:").pack(side="left", padx=(0, 4))
        self.title_var = tk.StringVar(value="Red neuronal en espacio MNI")
        tk.Entry(row2, textvariable=self.title_var, width=32, bg="#313244",
                 fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 12))

        self.edges_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(row2, text="Incluir edges",
                        variable=self.edges_enabled,
                        bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
                        activebackground="#1e1e2e",
                        activeforeground="#cdd6f4",
                        font=("Segoe UI", 10)).pack(side="left", padx=(0, 20))

        self._make_btn(row2, "Guardar PNG", self._save_plot,
                       bg="#89b4fa", fg="#1e1e2e",
                       font_size=10).pack(side="right", padx=5)
        self._make_btn(row2, "▶  PLOT", self._plot,
                       bg="#a6e3a1", fg="#1e1e2e",
                       font_size=12).pack(side="right", padx=5)

    # ── Status bar ──
    def _build_status(self):
        self.status_var = tk.StringVar(
            value="Listo — configura nodos y edges, luego dale Plot")
        tk.Label(self.root, textvariable=self.status_var, bg="#181825",
                 fg="#6c7086", anchor="w", font=("Segoe UI", 9),
                 padx=10, pady=3).pack(fill="x", side="bottom")

    # ═══════════════════════════════════════
    # NODOS
    # ═══════════════════════════════════════
    def _refresh_node_indices(self):
        for i, item in enumerate(self.nodes_tree.get_children()):
            vals = list(self.nodes_tree.item(item, "values"))
            vals[0] = i
            self.nodes_tree.item(item, values=vals)
        self.nodos_count_label.config(
            text=f"{len(self.nodes_tree.get_children())} nodos")

    def _agregar_nodo(self):
        idx = len(self.nodes_tree.get_children())
        self.nodes_tree.insert("", "end",
                                values=(idx, 0, 0, 0, "Default", 0.5))
        self._refresh_node_indices()

    def _generar_random_nodos(self, n):
        self._limpiar_nodos()
        for i in range(n):
            x = np.random.randint(-60, 60)
            y = np.random.randint(-80, 70)
            z = np.random.randint(-30, 60)
            com = np.random.choice(self.comunidades[:4])
            cent = round(np.random.uniform(0.1, 1.0), 2)
            self.nodes_tree.insert("", "end",
                                    values=(i, x, y, z, com, cent))
        self._refresh_node_indices()

    def _eliminar_nodo(self):
        sel = self.nodes_tree.selection()
        if sel:
            self.nodes_tree.delete(sel[0])
            self._refresh_node_indices()

    def _limpiar_nodos(self):
        for item in self.nodes_tree.get_children():
            self.nodes_tree.delete(item)
        self._refresh_node_indices()

    def _editar_celda_nodo(self, event):
        item = self.nodes_tree.identify_row(event.y)
        column = self.nodes_tree.identify_column(event.x)
        if not item or not column:
            return
        col_idx = int(column.replace("#", "")) - 1
        if col_idx == 0:
            return
        col_names = ("idx", "x", "y", "z", "comunidad", "centralidad")
        col_name = col_names[col_idx]
        current_val = self.nodes_tree.item(item, "values")[col_idx]
        bbox = self.nodes_tree.bbox(item, column)
        if not bbox:
            return

        if col_name == "comunidad":
            editor = ttk.Combobox(self.nodes_tree, values=self.comunidades,
                                   state="readonly", font=("Segoe UI", 10))
            editor.set(current_val)
        else:
            editor = tk.Entry(self.nodes_tree, font=("Segoe UI", 10),
                               bg="#313244", fg="#cdd6f4",
                               insertbackground="#cdd6f4")
            editor.insert(0, current_val)
            editor.select_range(0, "end")

        editor.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        editor.focus_set()

        def save(e=None):
            vals = list(self.nodes_tree.item(item, "values"))
            vals[col_idx] = editor.get()
            self.nodes_tree.item(item, values=vals)
            editor.destroy()

        editor.bind("<Return>", save)
        editor.bind("<FocusOut>", save)
        if col_name == "comunidad":
            editor.bind("<<ComboboxSelected>>", save)

    def _get_nodos_df(self):
        rows = []
        for item in self.nodes_tree.get_children():
            v = self.nodes_tree.item(item, "values")
            rows.append({
                "x": int(v[1]), "y": int(v[2]), "z": int(v[3]),
                "comunidad": str(v[4]), "centralidad": float(v[5]),
            })
        return pd.DataFrame(rows)

    def _importar_nodos_csv(self):
        path = filedialog.askopenfilename(
            title="Importar nodos",
            filetypes=[("CSV/TSV", "*.csv *.tsv"), ("Todos", "*.*")])
        if not path:
            return
        try:
            sep = "\t" if path.endswith(".tsv") else ","
            df = pd.read_csv(path, sep=sep)
            if not {"x", "y", "z"}.issubset(df.columns):
                messagebox.showerror("Error",
                    f"Necesita columnas x, y, z.\n"
                    f"Encontradas: {list(df.columns)}")
                return
            self._limpiar_nodos()
            for i, row in df.iterrows():
                self.nodes_tree.insert("", "end", values=(
                    i, int(row.get("x", 0)), int(row.get("y", 0)),
                    int(row.get("z", 0)),
                    str(row.get("comunidad", "Default")),
                    float(row.get("centralidad", 0.5))))
            self._refresh_node_indices()
            self.status_var.set(f"✓ Importados {len(df)} nodos")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _exportar_nodos_csv(self):
        if not self.nodes_tree.get_children():
            messagebox.showwarning("Sin datos", "No hay nodos.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="nodos.csv")
        if path:
            self._get_nodos_df().to_csv(path, index=False)
            self.status_var.set(f"✓ Nodos exportados: {path}")

    # ═══════════════════════════════════════
    # EDGES
    # ═══════════════════════════════════════
    def _refresh_edge_count(self):
        self.edges_count_label.config(
            text=f"{len(self.edges_tree.get_children())} edges")

    def _agregar_edge(self):
        n = len(self.nodes_tree.get_children())
        if n < 2:
            messagebox.showwarning("Pocos nodos",
                "Necesitas al menos 2 nodos para crear un edge.")
            return
        self.edges_tree.insert("", "end", values=(0, 1, 1.0))
        self._refresh_edge_count()

    def _generar_random_edges(self, m):
        self._limpiar_edges()
        n = len(self.nodes_tree.get_children())
        if n < 2:
            return
        pairs_used = set()
        count = 0
        max_possible = n * (n - 1) // 2
        m = min(m, max_possible)
        while count < m:
            i = np.random.randint(0, n)
            j = np.random.randint(0, n)
            if i == j:
                continue
            pair = (min(i, j), max(i, j))
            if pair in pairs_used:
                continue
            pairs_used.add(pair)
            w = round(np.random.uniform(0.2, 2.0), 2)
            self.edges_tree.insert("", "end",
                                    values=(pair[0], pair[1], w))
            count += 1
        self._refresh_edge_count()

    def _eliminar_edge(self):
        sel = self.edges_tree.selection()
        if sel:
            self.edges_tree.delete(sel[0])
            self._refresh_edge_count()

    def _limpiar_edges(self):
        for item in self.edges_tree.get_children():
            self.edges_tree.delete(item)
        self._refresh_edge_count()

    def _editar_celda_edge(self, event):
        item = self.edges_tree.identify_row(event.y)
        column = self.edges_tree.identify_column(event.x)
        if not item or not column:
            return
        col_idx = int(column.replace("#", "")) - 1
        current_val = self.edges_tree.item(item, "values")[col_idx]
        bbox = self.edges_tree.bbox(item, column)
        if not bbox:
            return

        editor = tk.Entry(self.edges_tree, font=("Segoe UI", 10),
                           bg="#313244", fg="#cdd6f4",
                           insertbackground="#cdd6f4")
        editor.insert(0, current_val)
        editor.select_range(0, "end")
        editor.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        editor.focus_set()

        def save(e=None):
            vals = list(self.edges_tree.item(item, "values"))
            vals[col_idx] = editor.get()
            self.edges_tree.item(item, values=vals)
            editor.destroy()

        editor.bind("<Return>", save)
        editor.bind("<FocusOut>", save)

    def _get_edges_df(self):
        rows = []
        for item in self.edges_tree.get_children():
            v = self.edges_tree.item(item, "values")
            rows.append({
                "i": int(v[0]), "j": int(v[1]), "weight": float(v[2]),
            })
        return pd.DataFrame(rows)

    def _importar_edges_csv(self):
        path = filedialog.askopenfilename(
            title="Importar edges",
            filetypes=[("CSV/TSV", "*.csv *.tsv"), ("Todos", "*.*")])
        if not path:
            return
        try:
            sep = "\t" if path.endswith(".tsv") else ","
            df = pd.read_csv(path, sep=sep)
            if not {"i", "j"}.issubset(df.columns):
                messagebox.showerror("Error",
                    f"Necesita columnas i, j.\n"
                    f"Encontradas: {list(df.columns)}")
                return
            self._limpiar_edges()
            for _, row in df.iterrows():
                self.edges_tree.insert("", "end", values=(
                    int(row["i"]), int(row["j"]),
                    float(row.get("weight", 1.0))))
            self._refresh_edge_count()
            self.status_var.set(f"✓ Importados {len(df)} edges")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _exportar_edges_csv(self):
        if not self.edges_tree.get_children():
            messagebox.showwarning("Sin datos", "No hay edges.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="edges.csv")
        if path:
            self._get_edges_df().to_csv(path, index=False)
            self.status_var.set(f"✓ Edges exportados: {path}")

    # ═══════════════════════════════════════
    # PLOT
    # ═══════════════════════════════════════
    def _plot(self):
        if not self.nodes_tree.get_children():
            messagebox.showwarning("Sin datos",
                                    "Agrega nodos antes de plotear.")
            return

        self.status_var.set(
            "Generando plot... (puede tardar la primera vez)")
        self.root.update()

        try:
            nodos = self._get_nodos_df()
            scale = int(self.scale_var.get())

            plot_args = dict(
                template=self.template_var.get(),
                template_style=self.style_var.get(),
                view=self.view_var.get(),
                nodes=nodos,
                node_size="centralidad",
                node_scale=scale,
                node_color="comunidad",
                node_type=self.nodetype_var.get(),
                title=self.title_var.get(),
            )

            if (self.edges_enabled.get()
                    and self.edges_tree.get_children()):
                edges = self._get_edges_df()
                max_idx = max(edges["i"].max(), edges["j"].max())
                if max_idx >= len(nodos):
                    messagebox.showerror("Error de edges",
                        f"Edge referencia nodo {max_idx} pero solo "
                        f"hay {len(nodos)} nodos "
                        f"(índices 0-{len(nodos)-1}).")
                    self.status_var.set("✗ Error en edges")
                    return
                plot_args["edges"] = edges

            fig, ax = netplotbrain.plot(**plot_args)
            self.current_fig = fig
            plt.show()

            n_edges = (len(self.edges_tree.get_children())
                       if self.edges_enabled.get() else 0)
            self.status_var.set(
                f"✓ Plot generado — {len(nodos)} nodos, "
                f"{n_edges} edges")
        except Exception as e:
            messagebox.showerror("Error en plot", str(e))
            self.status_var.set(f"✗ Error: {e}")

    def _save_plot(self):
        if self.current_fig is None:
            messagebox.showwarning("Sin plot",
                "Primero genera un plot con ▶ PLOT.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg"),
                       ("PDF", "*.pdf")],
            initialfile="netplot_resultado.png")
        if path:
            self.current_fig.savefig(path, dpi=150, bbox_inches="tight")
            self.status_var.set(f"✓ Guardado: {path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = NetPlotBrainGUI(root)
    root.mainloop()
