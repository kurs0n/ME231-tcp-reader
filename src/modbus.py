import csv
import os
import struct
import time

from pymodbus.client import ModbusTcpClient

from .config import (
    MEASUREMENTS,
    MEASUREMENTS_MAIN,
    MEASUREMENTS_THD_I,
    MEASUREMENTS_THD_U,
)


def _read_holding_registers(client, address, count, slave_id):
    try:
        result = client.read_holding_registers(
            address=address, count=count, device_id=slave_id
        )
    except TypeError:
        result = client.read_holding_registers(
            address=address, count=count, slave=slave_id
        )

    if result is None or result.isError():
        return None
    return result.registers


def read_all_fast(client, slave_id):
    """Odczytuje rejestry pomiarowe 1000-1083 oraz rejestry THD (4000-4005, 5000-5005)."""
    try:
        regs_main = _read_holding_registers(client, 1000, 84, slave_id)
        if regs_main is None or len(regs_main) < 84:
            return None

        data = {}
        for name, addr in MEASUREMENTS_MAIN.items():
            idx = addr - 1000
            raw = struct.pack(">HH", regs_main[idx], regs_main[idx + 1])
            data[name] = round(struct.unpack(">f", raw)[0], 3)

        # Odczyt THD pradu (rejestry 4000-4005: I1THD, I2THD, I3THD)
        regs_thd_i = _read_holding_registers(client, 4000, 6, slave_id)
        for name, addr in MEASUREMENTS_THD_I.items():
            if regs_thd_i is not None and len(regs_thd_i) >= 6:
                idx = addr - 4000
                raw = struct.pack(">HH", regs_thd_i[idx], regs_thd_i[idx + 1])
                data[name] = round(struct.unpack(">f", raw)[0], 3)
            else:
                data[name] = 0.0

        # Odczyt THD napiecia (rejestry 5000-5005: U1THD, U2THD, U3THD)
        regs_thd_u = _read_holding_registers(client, 5000, 6, slave_id)
        for name, addr in MEASUREMENTS_THD_U.items():
            if regs_thd_u is not None and len(regs_thd_u) >= 6:
                idx = addr - 5000
                raw = struct.pack(">HH", regs_thd_u[idx], regs_thd_u[idx + 1])
                data[name] = round(struct.unpack(">f", raw)[0], 3)
            else:
                data[name] = 0.0

        return data
    except Exception:
        return None


def modbus_worker(cfg, stop_event, buffer_lock, live_buffer, status_queue=None):
    """Wątek odpytujący ME231 i dopisujący dane do CSV."""
    client = ModbusTcpClient(cfg["ip"], port=cfg["port"], timeout=3)
    csv_file = cfg["csv_file"]
    file_exists = os.path.isfile(csv_file)
    csv_headers = ["Czas"] + list(MEASUREMENTS.keys())

    def report(kind, message):
        if status_queue is not None:
            status_queue.put((kind, message))

    try:
        report("status", f"Laczenie z {cfg['ip']}:{cfg['port']}...")
        if not client.connect():
            report(
                "error",
                f"Nie można połączyć z USR-DR164 ({cfg['ip']}:{cfg['port']}). "
                "Zmień sieć Wi-Fi na USR-DR164_8282 i spróbuj ponownie.",
            )
            stop_event.set()
            return

        report("status", f"Polaczono! Zapis do {csv_file}")
        with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers, delimiter=";")
            if not file_exists:
                writer.writeheader()

            while not stop_event.is_set():
                t0 = time.monotonic()
                full_ts = time.strftime("%Y-%m-%d %H:%M:%S")
                values = read_all_fast(client, cfg["slave_id"])
                if values is None:
                    report("warning", "Brak danych. Sprawdz polaczenie i ustawienia Slave ID.")

                if values:
                    row = {"Czas": full_ts, **values}
                    writer.writerow(row)
                    f.flush()

                    with buffer_lock:
                        live_buffer.append(
                            {"t": time.strftime("%H:%M:%S"), **values}
                        )

                elapsed = time.monotonic() - t0
                sleep_time = max(0.0, cfg["poll_interval"] - elapsed)
                if stop_event.wait(sleep_time):
                    break
    except FileNotFoundError:
        report("error", f"Nie znaleziono katalogu dla pliku: {csv_file}")
        stop_event.set()
    except PermissionError:
        report("error", f"Brak uprawnien do zapisu pliku: {csv_file}")
        stop_event.set()
    except Exception as exc:
        report("error", f"Nieoczekiwany blad zbierania danych: {exc}")
        stop_event.set()
    finally:
        client.close()
