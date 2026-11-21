from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class LivePlot:
    def __init__(self, parent, buffer_lock):
        self.parent = parent
        self.buffer_lock = buffer_lock
        self.buffer = None
        self.interval_ms = 1000
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.axes = self.figure.subplots(3, 1, sharex=True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def start(self, cfg):
        self.interval_ms = max(250, int(cfg["poll_interval"] * 1000))
        self.update()

    def set_buffer(self, buffer):
        self.buffer = buffer

    def set_interval(self, cfg):
        self.interval_ms = max(250, int(cfg["poll_interval"] * 1000))

    def update(self):
        with self.buffer_lock:
            samples = list(self.buffer) if self.buffer else []

        for ax in self.axes:
            ax.clear()

        if samples:
            xs = list(range(len(samples)))
            labels = [sample["t"] for sample in samples]
            step = max(1, len(xs) // 8)

            self.axes[0].plot(xs, [s.get("P_calkowita_kW", 0) for s in samples], label="P [kW]")
            self.axes[0].plot(xs, [s.get("Q_calkowita_kvar", 0) for s in samples], label="Q [kvar]")
            self.axes[0].plot(xs, [s.get("S_calkowita_kVA", 0) for s in samples], label="S [kVA]")
            self.axes[0].set_ylabel("Moc")

            self.axes[1].plot(xs, [s.get("U1_V", 0) for s in samples], label="U1 [V]")
            self.axes[1].plot(xs, [s.get("U2_V", 0) for s in samples], label="U2 [V]")
            self.axes[1].plot(xs, [s.get("U3_V", 0) for s in samples], label="U3 [V]")
            self.axes[1].set_ylabel("Napiecie [V]")

            self.axes[2].plot(xs, [s.get("I1_A", 0) for s in samples], label="I1 [A]")
            self.axes[2].plot(xs, [s.get("I2_A", 0) for s in samples], label="I2 [A]")
            self.axes[2].plot(xs, [s.get("I3_A", 0) for s in samples], label="I3 [A]")
            self.axes[2].set_ylabel("Prad [A]")
            self.axes[2].set_xlabel("Czas")
            self.axes[2].set_xticks(xs[::step])
            self.axes[2].set_xticklabels(labels[::step], rotation=20)

            for ax in self.axes:
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.parent.after(self.interval_ms, self.update)
