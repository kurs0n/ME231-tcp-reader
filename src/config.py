import tkinter as tk
import threading
from collections import deque
from datetime import datetime
from queue import Queue, Empty
from tkinter import messagebox, ttk

from .exporter import export_csv_to_xlsx
from .live_plot import LivePlot


DEFAULT_CONFIG = {
    "ip": "10.10.100.254",
    "port": 8899,
    "slave_id": 1,
    "poll_interval": 1.0,
    "max_live_points": 120,
    "csv_file": "me231_pomiary.csv",
    "xlsx_file": "me231_raport.xlsx",
    "export_xlsx_on_exit": True,
}

MEASUREMENTS = {
    "I1_A": 1000,
    "I2_A": 1002,
    "I3_A": 1004,
    "IN_A": 1006,
    "U1_V": 1010,
    "U2_V": 1012,
    "U3_V": 1014,
    "U_srednie_V": 1016,
    "U12_V": 1018,
    "U23_V": 1020,
    "U31_V": 1022,
    "U_linia_srednie_V": 1024,
    "P1_kW": 1028,
    "P2_kW": 1030,
    "P3_kW": 1032,
    "P_calkowita_kW": 1034,
    "Q1_kvar": 1036,
    "Q2_kvar": 1038,
    "Q3_kvar": 1040,
    "Q_calkowita_kvar": 1042,
    "S1_kVA": 1044,
    "S2_kVA": 1046,
    "S3_kVA": 1048,
    "S_calkowita_kVA": 1050,
    "PF_1": 1052,
    "PF_2": 1054,
    "PF_3": 1056,
    "PF_calkowity": 1058,
    "dPF_1": 1060,
    "dPF_2": 1062,
    "dPF_3": 1064,
    "dPF_calkowite": 1066,
    "f_sieci_Hz": 1074,
    "Energia_czynna_pobrana_kWh": 1076,
    "Energia_czynna_oddana_kWh": 1078,
    "Energia_bierna_indukcyjna_kvarh": 1080,
    "Energia_bierna_pojemnosciowa_kvarh": 1082,
}


def dated_filename(filename):
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    root, dot, extension = filename.rpartition(".")
    if dot and root:
        return f"{root}_{date_prefix}.{extension}"
    return f"{filename}_{date_prefix}"


def validate_config(vars_map):
    ip = vars_map["ip"].get().strip()
    port = int(vars_map["port"].get().strip())
    slave_id = int(vars_map["slave_id"].get().strip())
    poll_interval = float(
        vars_map["poll_interval"].get().strip().replace(",", ".")
    )
    max_live_points = int(vars_map["max_live_points"].get().strip())
    csv_file = vars_map["csv_file"].get().strip()
    xlsx_file = vars_map["xlsx_file"].get().strip()

    if not ip:
        raise ValueError("Podaj adres IP.")
    if not (1 <= port <= 65535):
        raise ValueError("Port musi być w zakresie 1–65535.")
    if not (1 <= slave_id <= 247):
        raise ValueError("Slave ID musi być w zakresie 1–247.")
    if poll_interval <= 0:
        raise ValueError("Interwał odczytu musi być większy od 0.")
    if max_live_points < 5:
        raise ValueError("Liczba próbek na wykresie powinna wynosić co najmniej 5.")
    if not csv_file:
        raise ValueError("Podaj nazwę pliku CSV.")
    if vars_map["export_xlsx_on_exit"].get() and not xlsx_file:
        raise ValueError("Podaj nazwę pliku XLSX.")

    return {
        "ip": ip,
        "port": port,
        "slave_id": slave_id,
        "poll_interval": poll_interval,
        "max_live_points": max_live_points,
        "csv_file": csv_file,
        "xlsx_file": xlsx_file,
        "export_xlsx_on_exit": vars_map["export_xlsx_on_exit"].get(),
    }


def run_control_window():
    """Uruchamia okno sterujące; zbieranie danych odbywa się w osobnym wątku."""
    root = tk.Tk()
    root.title("ME231 / USR-DR164 – Monitoring")
    root.minsize(900, 620)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    vars_map = {
        "ip": tk.StringVar(value=DEFAULT_CONFIG["ip"]),
        "port": tk.StringVar(value=str(DEFAULT_CONFIG["port"])),
        "slave_id": tk.StringVar(value=str(DEFAULT_CONFIG["slave_id"])),
        "poll_interval": tk.StringVar(value=str(DEFAULT_CONFIG["poll_interval"])),
        "max_live_points": tk.StringVar(value=str(DEFAULT_CONFIG["max_live_points"])),
        "csv_file": tk.StringVar(value=dated_filename(DEFAULT_CONFIG["csv_file"])),
        "xlsx_file": tk.StringVar(value=dated_filename(DEFAULT_CONFIG["xlsx_file"])),
        "export_xlsx_on_exit": tk.BooleanVar(
            value=DEFAULT_CONFIG["export_xlsx_on_exit"]
        ),
    }

    controls = ttk.Frame(frame)
    controls.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    fields = [
        ("Adres IP (USR-DR164):", "ip"),
        ("Port TCP:", "port"),
        ("Slave ID (ME231):", "slave_id"),
        ("Interwał odczytu [s]:", "poll_interval"),
        ("Liczba próbek na wykresie:", "max_live_points"),
        ("Plik CSV:", "csv_file"),
        ("Plik raportu XLSX:", "xlsx_file"),
    ]

    for idx, (label_text, key) in enumerate(fields):
        ttk.Label(controls, text=label_text).grid(
            row=idx // 4, column=(idx % 4) * 2, sticky="w", padx=(0, 6), pady=4
        )
        ttk.Entry(controls, textvariable=vars_map[key], width=18).grid(
            row=idx // 4, column=(idx % 4) * 2 + 1, sticky="ew", pady=4
        )

    ttk.Checkbutton(
        controls,
        text="Eksportuj raport XLSX z wykresami po Stop / zamknięciu",
        variable=vars_map["export_xlsx_on_exit"],
    ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 4))

    status_var = tk.StringVar(value="Zatrzymano")
    ttk.Label(controls, textvariable=status_var).grid(
        row=2, column=4, columnspan=4, sticky="e"
    )

    plot_frame = ttk.Frame(frame)
    plot_frame.grid(row=1, column=0, sticky="nsew")
    status_queue = Queue()
    stop_event = threading.Event()
    stop_event.set()
    buffer_lock = threading.Lock()
    live_buffer = deque(maxlen=DEFAULT_CONFIG["max_live_points"])
    worker = None
    closing = False

    def set_stopped(message="Zatrzymano"):
        stop_event.set()
        status_var.set(message)

    def on_stop(export=False):
        nonlocal worker
        set_stopped()
        if worker and worker.is_alive():
            worker.join(timeout=3)
        if export:
            export_active = vars_map["export_xlsx_on_exit"].get()
            if export_active:
                cfg = getattr(on_stop, "cfg", None)
                if cfg:
                    status_queue.put(("status", "Eksportowanie raportu XLSX..."))
                    export_thread = threading.Thread(
                        target=export_csv_to_xlsx,
                        args=(cfg["csv_file"], cfg["xlsx_file"], status_queue),
                        daemon=True,
                        name="xlsx-export",
                    )
                    export_thread.start()

    def on_start():
        nonlocal worker, live_buffer
        from .modbus import modbus_worker

        if worker and worker.is_alive():
            messagebox.showwarning("Zbieranie aktywne", "Najpierw zatrzymaj zbieranie danych.", parent=root)
            return
        try:
            cfg = validate_config(vars_map)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Błąd konfiguracji", str(exc), parent=root)
            return

        stop_event.clear()
        live_buffer = deque(maxlen=cfg["max_live_points"])
        live_plot.set_buffer(live_buffer)
        live_plot.set_interval(cfg)
        status_var.set("Łączenie...")
        on_stop.cfg = cfg
        worker = threading.Thread(
            target=modbus_worker,
            args=(cfg, stop_event, buffer_lock, live_buffer, status_queue),
            daemon=True,
            name="modbus-worker",
        )
        worker.start()
        start_btn.state(["disabled"])
        stop_btn.state(["!disabled"])

    def on_close():
        nonlocal closing
        if closing:
            return
        closing = True
        export_thread = None
        stop_event.set()
        if worker and worker.is_alive():
            worker.join(timeout=3)
        cfg = getattr(on_stop, "cfg", None)
        if vars_map["export_xlsx_on_exit"].get() and cfg:
            export_thread = threading.Thread(
                target=export_csv_to_xlsx,
                args=(cfg["csv_file"], cfg["xlsx_file"]),
                name="xlsx-export",
            )
            export_thread.start()
            export_thread.join(timeout=30)
        root.destroy()

    btn_frame = ttk.Frame(controls)
    btn_frame.grid(row=2, column=8, columnspan=2, sticky="e")
    start_btn = ttk.Button(btn_frame, text="Start", command=on_start)
    start_btn.grid(row=0, column=0, padx=(0, 8))
    stop_btn = ttk.Button(btn_frame, text="Stop", command=lambda: on_stop(export=True))
    stop_btn.grid(row=0, column=1)
    stop_btn.state(["disabled"])

    live_plot = LivePlot(plot_frame, buffer_lock)
    live_plot.start(DEFAULT_CONFIG)

    def poll_status():
        try:
            while True:
                kind, message = status_queue.get_nowait()
                status_var.set(message)
                if kind == "error":
                    messagebox.showerror("Błąd zbierania danych", message, parent=root)
        except Empty:
            pass

        if not closing:
            if stop_event.is_set():
                start_btn.state(["!disabled"])
                stop_btn.state(["disabled"])
            elif worker and not worker.is_alive():
                set_stopped("Zatrzymano z powodu błędu")
                start_btn.state(["!disabled"])
                stop_btn.state(["disabled"])
            root.after(200, poll_status)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(200, poll_status)
    root.mainloop()
