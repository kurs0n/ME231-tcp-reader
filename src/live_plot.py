from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class LivePlot:
    def __init__(self, parent, buffer_lock):
        self.parent = parent
        self.buffer_lock = buffer_lock
        self.buffer = None
        self.interval_ms = 1000

        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)

        # Zakladka 1: Pomiary podstawowe (Moce, Napiecia, Prady)
        self.tab_basic = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_basic, text="Przebiegi podstawowe (P, U, I)")
        self.figure_basic = Figure(figsize=(10, 6), dpi=100)
        self.axes_basic = self.figure_basic.subplots(3, 1, sharex=True)
        self.canvas_basic = FigureCanvasTkAgg(self.figure_basic, master=self.tab_basic)
        self.canvas_basic.get_tk_widget().pack(fill="both", expand=True)

        # Zakladka 2: Harmoniczne THD (Napiecia i Prady)
        self.tab_thd = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_thd, text="Harmoniczne THD (U & I)")
        self.figure_thd = Figure(figsize=(10, 6), dpi=100)
        self.axes_thd = self.figure_thd.subplots(2, 1, sharex=True)
        self.canvas_thd = FigureCanvasTkAgg(self.figure_thd, master=self.tab_thd)
        self.canvas_thd.get_tk_widget().pack(fill="both", expand=True)

        # Zakladka 3: Wszystkie wykresy polaczone
        self.tab_all = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_all, text="Wszystkie wykresy")
        self.figure_all = Figure(figsize=(10, 7), dpi=100)
        self.axes_all = self.figure_all.subplots(5, 1, sharex=True)
        self.canvas_all = FigureCanvasTkAgg(self.figure_all, master=self.tab_all)
        self.canvas_all.get_tk_widget().pack(fill="both", expand=True)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def start(self, cfg):
        self.interval_ms = max(250, int(cfg["poll_interval"] * 1000))
        self.update()

    def set_buffer(self, buffer):
        self.buffer = buffer

    def set_interval(self, cfg):
        self.interval_ms = max(250, int(cfg["poll_interval"] * 1000))

    def _plot_basic(self, samples, xs, labels, step):
        for ax in self.axes_basic:
            ax.clear()
        if samples:
            self.axes_basic[0].plot(xs, [s.get("P_calkowita_kW", 0) for s in samples], label="P [kW]")
            self.axes_basic[0].plot(xs, [s.get("Q_calkowita_kvar", 0) for s in samples], label="Q [kvar]")
            self.axes_basic[0].plot(xs, [s.get("S_calkowita_kVA", 0) for s in samples], label="S [kVA]")
            self.axes_basic[0].set_ylabel("Moc")

            self.axes_basic[1].plot(xs, [s.get("U1_V", 0) for s in samples], label="U1 [V]")
            self.axes_basic[1].plot(xs, [s.get("U2_V", 0) for s in samples], label="U2 [V]")
            self.axes_basic[1].plot(xs, [s.get("U3_V", 0) for s in samples], label="U3 [V]")
            self.axes_basic[1].set_ylabel("Napiecie [V]")

            self.axes_basic[2].plot(xs, [s.get("I1_A", 0) for s in samples], label="I1 [A]")
            self.axes_basic[2].plot(xs, [s.get("I2_A", 0) for s in samples], label="I2 [A]")
            self.axes_basic[2].plot(xs, [s.get("I3_A", 0) for s in samples], label="I3 [A]")
            self.axes_basic[2].set_ylabel("Prad [A]")
            self.axes_basic[2].set_xlabel("Czas")
            self.axes_basic[2].set_xticks(xs[::step])
            self.axes_basic[2].set_xticklabels(labels[::step], rotation=20)

            for ax in self.axes_basic:
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3)
        self.figure_basic.tight_layout()
        self.canvas_basic.draw_idle()

    def _plot_thd(self, samples, xs, labels, step):
        for ax in self.axes_thd:
            ax.clear()
        if samples:
            self.axes_thd[0].plot(xs, [s.get("THD_U1_proc", 0) for s in samples], label="THD U1 [%]", color="tab:blue")
            self.axes_thd[0].plot(xs, [s.get("THD_U2_proc", 0) for s in samples], label="THD U2 [%]", color="tab:orange")
            self.axes_thd[0].plot(xs, [s.get("THD_U3_proc", 0) for s in samples], label="THD U3 [%]", color="tab:green")
            self.axes_thd[0].set_ylabel("THD U [%]")

            self.axes_thd[1].plot(xs, [s.get("THD_I1_proc", 0) for s in samples], label="THD I1 [%]", color="tab:blue")
            self.axes_thd[1].plot(xs, [s.get("THD_I2_proc", 0) for s in samples], label="THD I2 [%]", color="tab:orange")
            self.axes_thd[1].plot(xs, [s.get("THD_I3_proc", 0) for s in samples], label="THD I3 [%]", color="tab:green")
            self.axes_thd[1].set_ylabel("THD I [%]")
            self.axes_thd[1].set_xlabel("Czas")
            self.axes_thd[1].set_xticks(xs[::step])
            self.axes_thd[1].set_xticklabels(labels[::step], rotation=20)

            for ax in self.axes_thd:
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3)
        self.figure_thd.tight_layout()
        self.canvas_thd.draw_idle()

    def _plot_all(self, samples, xs, labels, step):
        for ax in self.axes_all:
            ax.clear()
        if samples:
            self.axes_all[0].plot(xs, [s.get("P_calkowita_kW", 0) for s in samples], label="P [kW]")
            self.axes_all[0].plot(xs, [s.get("Q_calkowita_kvar", 0) for s in samples], label="Q [kvar]")
            self.axes_all[0].plot(xs, [s.get("S_calkowita_kVA", 0) for s in samples], label="S [kVA]")
            self.axes_all[0].set_ylabel("Moc")

            self.axes_all[1].plot(xs, [s.get("U1_V", 0) for s in samples], label="U1 [V]")
            self.axes_all[1].plot(xs, [s.get("U2_V", 0) for s in samples], label="U2 [V]")
            self.axes_all[1].plot(xs, [s.get("U3_V", 0) for s in samples], label="U3 [V]")
            self.axes_all[1].set_ylabel("U [V]")

            self.axes_all[2].plot(xs, [s.get("I1_A", 0) for s in samples], label="I1 [A]")
            self.axes_all[2].plot(xs, [s.get("I2_A", 0) for s in samples], label="I2 [A]")
            self.axes_all[2].plot(xs, [s.get("I3_A", 0) for s in samples], label="I3 [A]")
            self.axes_all[2].set_ylabel("I [A]")

            self.axes_all[3].plot(xs, [s.get("THD_U1_proc", 0) for s in samples], label="THD U1 [%]")
            self.axes_all[3].plot(xs, [s.get("THD_U2_proc", 0) for s in samples], label="THD U2 [%]")
            self.axes_all[3].plot(xs, [s.get("THD_U3_proc", 0) for s in samples], label="THD U3 [%]")
            self.axes_all[3].set_ylabel("THD U [%]")

            self.axes_all[4].plot(xs, [s.get("THD_I1_proc", 0) for s in samples], label="THD I1 [%]")
            self.axes_all[4].plot(xs, [s.get("THD_I2_proc", 0) for s in samples], label="THD I2 [%]")
            self.axes_all[4].plot(xs, [s.get("THD_I3_proc", 0) for s in samples], label="THD I3 [%]")
            self.axes_all[4].set_ylabel("THD I [%]")
            self.axes_all[4].set_xlabel("Czas")
            self.axes_all[4].set_xticks(xs[::step])
            self.axes_all[4].set_xticklabels(labels[::step], rotation=20)

            for ax in self.axes_all:
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3)
        self.figure_all.tight_layout()
        self.canvas_all.draw_idle()

    def _render_current_tab(self):
        with self.buffer_lock:
            samples = list(self.buffer) if self.buffer else []

        xs = list(range(len(samples))) if samples else []
        labels = [sample["t"] for sample in samples] if samples else []
        step = max(1, len(xs) // 8) if samples else 1

        try:
            current_tab = self.notebook.index(self.notebook.select())
        except Exception:
            current_tab = 0

        if current_tab == 0:
            self._plot_basic(samples, xs, labels, step)
        elif current_tab == 1:
            self._plot_thd(samples, xs, labels, step)
        elif current_tab == 2:
            self._plot_all(samples, xs, labels, step)

    def _on_tab_changed(self, event=None):
        self._render_current_tab()

    def update(self):
        self._render_current_tab()
        self.parent.after(self.interval_ms, self.update)
