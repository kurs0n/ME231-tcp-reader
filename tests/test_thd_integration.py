import csv
import os
import struct
import tempfile
import unittest
from unittest.mock import MagicMock

from openpyxl import load_workbook

from src.config import (
    MEASUREMENTS,
    MEASUREMENTS_MAIN,
    MEASUREMENTS_THD_I,
    MEASUREMENTS_THD_U,
)
from src.exporter import export_csv_to_xlsx
from src.modbus import read_all_fast


class TestTHDConfiguration(unittest.TestCase):
    def test_thd_registers_defined(self):
        self.assertIn("THD_U1_proc", MEASUREMENTS_THD_U)
        self.assertIn("THD_U2_proc", MEASUREMENTS_THD_U)
        self.assertIn("THD_U3_proc", MEASUREMENTS_THD_U)
        self.assertEqual(MEASUREMENTS_THD_U["THD_U1_proc"], 5000)
        self.assertEqual(MEASUREMENTS_THD_U["THD_U2_proc"], 5002)
        self.assertEqual(MEASUREMENTS_THD_U["THD_U3_proc"], 5004)

        self.assertIn("THD_I1_proc", MEASUREMENTS_THD_I)
        self.assertIn("THD_I2_proc", MEASUREMENTS_THD_I)
        self.assertIn("THD_I3_proc", MEASUREMENTS_THD_I)
        self.assertEqual(MEASUREMENTS_THD_I["THD_I1_proc"], 4000)
        self.assertEqual(MEASUREMENTS_THD_I["THD_I2_proc"], 4002)
        self.assertEqual(MEASUREMENTS_THD_I["THD_I3_proc"], 4004)

        for key in MEASUREMENTS_THD_U:
            self.assertIn(key, MEASUREMENTS)
        for key in MEASUREMENTS_THD_I:
            self.assertIn(key, MEASUREMENTS)


class TestModbusTHDReading(unittest.TestCase):
    def _float_to_regs(self, val):
        packed = struct.pack(">f", val)
        return list(struct.unpack(">HH", packed))

    def test_read_all_fast_decoding(self):
        client = MagicMock()

        # Rejestry główne 1000..1083 (84 rejestry)
        main_regs = [0] * 84
        # Ustaw np. U1_V (1010 -> offset 10) na 230.5 V
        u1_regs = self._float_to_regs(230.5)
        main_regs[10] = u1_regs[0]
        main_regs[11] = u1_regs[1]

        # Rejestry THD I 4000..4005 (6 rejestrów)
        thd_i_regs = []
        thd_i_regs.extend(self._float_to_regs(1.25))  # THD_I1
        thd_i_regs.extend(self._float_to_regs(2.50))  # THD_I2
        thd_i_regs.extend(self._float_to_regs(3.75))  # THD_I3

        # Rejestry THD U 5000..5005 (6 rejestrów)
        thd_u_regs = []
        thd_u_regs.extend(self._float_to_regs(0.85))  # THD_U1
        thd_u_regs.extend(self._float_to_regs(1.10))  # THD_U2
        thd_u_regs.extend(self._float_to_regs(1.45))  # THD_U3

        def mock_read(address, count, **kwargs):
            res = MagicMock()
            res.isError.return_value = False
            if address == 1000 and count == 84:
                res.registers = main_regs
                return res
            elif address == 4000 and count == 6:
                res.registers = thd_i_regs
                return res
            elif address == 5000 and count == 6:
                res.registers = thd_u_regs
                return res
            res.isError.return_value = True
            return res

        client.read_holding_registers.side_effect = mock_read

        data = read_all_fast(client, slave_id=1)
        self.assertIsNotNone(data)
        self.assertEqual(data["U1_V"], 230.5)
        self.assertEqual(data["THD_I1_proc"], 1.25)
        self.assertEqual(data["THD_I2_proc"], 2.5)
        self.assertEqual(data["THD_I3_proc"], 3.75)
        self.assertEqual(data["THD_U1_proc"], 0.85)
        self.assertEqual(data["THD_U2_proc"], 1.1)
        self.assertEqual(data["THD_U3_proc"], 1.45)

    def test_read_all_fast_graceful_on_thd_failure(self):
        client = MagicMock()
        main_regs = [0] * 84

        def mock_read(address, count, **kwargs):
            res = MagicMock()
            if address == 1000:
                res.isError.return_value = False
                res.registers = main_regs
                return res
            # Błąd odczytu dla 4000 i 5000
            res.isError.return_value = True
            return res

        client.read_holding_registers.side_effect = mock_read

        data = read_all_fast(client, slave_id=1)
        self.assertIsNotNone(data)
        # THD powinno mieć domyślnie 0.0 zamiast rzucać wyjątkiem
        self.assertEqual(data["THD_I1_proc"], 0.0)
        self.assertEqual(data["THD_U1_proc"], 0.0)


class TestExporterTHD(unittest.TestCase):
    def test_export_creates_thd_sheets_and_charts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_pomiary.csv")
            xlsx_path = os.path.join(tmpdir, "test_raport.xlsx")

            headers = ["Czas"] + list(MEASUREMENTS.keys())
            rows = [
                headers,
                ["2026-11-28 12:00:01"] + [1.0] * len(MEASUREMENTS),
                ["2026-11-28 12:00:02"] + [2.0] * len(MEASUREMENTS),
                ["2026-11-28 12:00:03"] + [3.0] * len(MEASUREMENTS),
            ]

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerows(rows)

            success = export_csv_to_xlsx(csv_path, xlsx_path)
            self.assertTrue(success)
            self.assertTrue(os.path.isfile(xlsx_path))

            wb = load_workbook(xlsx_path)
            sheet_names = wb.sheetnames
            self.assertIn("Pomiary", sheet_names)
            self.assertIn("Moce", sheet_names)
            self.assertIn("Napiecia", sheet_names)
            self.assertIn("Prady", sheet_names)
            self.assertIn("THD_Napiecia", sheet_names)
            self.assertIn("THD_Prady", sheet_names)

            thd_u_sheet = wb["THD_Napiecia"]
            self.assertEqual(len(thd_u_sheet._charts), 1)
            chart_u = thd_u_sheet._charts[0]
            # openpyxl wczytuje tytul jako obiekt Title z bogatym tekstem (rich text)
            title_text_u = chart_u.title.text.rich.p[0].r[0].t
            self.assertIn("THD", title_text_u)

            thd_i_sheet = wb["THD_Prady"]
            self.assertEqual(len(thd_i_sheet._charts), 1)
            chart_i = thd_i_sheet._charts[0]
            title_text_i = chart_i.title.text.rich.p[0].r[0].t
            self.assertIn("THD", title_text_i)


class TestLivePlotMethods(unittest.TestCase):
    def test_live_plot_plotting_functions(self):
        from unittest.mock import MagicMock, patch

        mock_parent = MagicMock()
        mock_lock = MagicMock()

        with patch("src.live_plot.ttk.Notebook") as mock_nb_cls, \
             patch("src.live_plot.ttk.Frame") as mock_frame_cls, \
             patch("src.live_plot.FigureCanvasTkAgg") as mock_canvas_cls:
            from src.live_plot import LivePlot
            lp = LivePlot(mock_parent, mock_lock)

            samples = [
                {
                    "t": "12:00:00",
                    "P_calkowita_kW": 1.5,
                    "Q_calkowita_kvar": 0.5,
                    "S_calkowita_kVA": 1.6,
                    "U1_V": 230.1,
                    "U2_V": 231.2,
                    "U3_V": 229.8,
                    "I1_A": 6.5,
                    "I2_A": 6.6,
                    "I3_A": 6.4,
                    "THD_U1_proc": 1.2,
                    "THD_U2_proc": 1.4,
                    "THD_U3_proc": 1.1,
                    "THD_I1_proc": 4.5,
                    "THD_I2_proc": 4.8,
                    "THD_I3_proc": 4.2,
                },
                {
                    "t": "12:00:01",
                    "P_calkowita_kW": 1.6,
                    "Q_calkowita_kvar": 0.5,
                    "S_calkowita_kVA": 1.7,
                    "U1_V": 230.2,
                    "U2_V": 231.1,
                    "U3_V": 229.9,
                    "I1_A": 6.6,
                    "I2_A": 6.7,
                    "I3_A": 6.5,
                    "THD_U1_proc": 1.3,
                    "THD_U2_proc": 1.5,
                    "THD_U3_proc": 1.2,
                    "THD_I1_proc": 4.6,
                    "THD_I2_proc": 4.9,
                    "THD_I3_proc": 4.3,
                },
            ]
            xs = [0, 1]
            labels = ["12:00:00", "12:00:01"]
            step = 1

            # Sprawdzenie czy metody rysowania wykonują się bez błędów
            lp._plot_basic(samples, xs, labels, step)
            lp._plot_thd(samples, xs, labels, step)
            lp._plot_all(samples, xs, labels, step)

            # Sprawdzenie zachowania przy pustych próbkach
            lp._plot_basic([], [], [], 1)
            lp._plot_thd([], [], [], 1)
            lp._plot_all([], [], [], 1)


if __name__ == "__main__":
    unittest.main()
