import csv
import os

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.data_source import AxDataSource, StrRef
from openpyxl.utils import get_column_letter


def export_csv_to_xlsx(csv_file, xlsx_file, status_queue=None):
    """Generuje plik XLSX z wykresami na podstawie zgromadzonego CSV."""
    def report(kind, message):
        if status_queue is not None:
            status_queue.put((kind, message))

    if not os.path.isfile(csv_file):
        print("Brak pliku CSV do eksportu.")
        report("error", "Brak pliku CSV do eksportu.")
        return False

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Pomiary"

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            for r_idx, row in enumerate(reader, start=1):
                parsed = []
                for c_idx, val in enumerate(row):
                    if r_idx == 1 or c_idx == 0:
                        parsed.append(val)
                    else:
                        try:
                            parsed.append(float(val.replace(",", ".")))
                        except ValueError:
                            parsed.append(val)
                ws.append(parsed)
    except (OSError, csv.Error) as exc:
        print(f"Blad odczytu CSV lub utworzenia raportu: {exc}")
        report("error", f"Blad odczytu CSV lub utworzenia raportu: {exc}")
        return False

    max_row = ws.max_row
    if max_row <= 2:
        wb.create_sheet("Moce")
        wb.create_sheet("Napiecia")
        wb.create_sheet("Prady")
        try:
            wb.save(xlsx_file)
            print(f"Zapisano {xlsx_file} (za malo wierszy na wykresy).")
            report("status", f"Wyeksportowano raport: {xlsx_file}")
            return True
        except (OSError, PermissionError) as exc:
            print(f"Blad zapisu raportu XLSX: {exc}")
            report("error", f"Blad zapisu raportu XLSX: {exc}")
            return False

    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    col_index = {name: idx + 1 for idx, name in enumerate(headers)}
    time_col = ws.max_column + 1
    ws.cell(row=1, column=time_col, value="Godzina")
    for row in range(2, max_row + 1):
        timestamp = str(ws.cell(row=row, column=1).value or "")
        ws.cell(row=row, column=time_col, value=timestamp.rsplit(" ", 1)[-1])
    ws.column_dimensions[get_column_letter(time_col)].hidden = True

    def add_chart(sheet_name, title, y_title, series_names):
        chart_sheet = wb.create_sheet(sheet_name)
        chart = LineChart()
        chart.title = title
        chart.y_axis.title = y_title
        chart.x_axis.title = "Czas"
        chart.width = 18
        chart.height = 10
        chart.visible_cells_only = False

        for name in series_names:
            col = col_index.get(name)
            if col:
                data = Reference(ws, min_col=col, min_row=1, max_row=max_row)
                chart.add_data(data, titles_from_data=True)

        time_col_letter = get_column_letter(time_col)
        categories = AxDataSource(
            strRef=StrRef(
                f=f"'{ws.title}'!${time_col_letter}$2:${time_col_letter}${max_row}"
            )
        )
        for series in chart.series:
            series.cat = categories
        chart_sheet.add_chart(chart, "A2")

    add_chart(
        "Moce",
        "Moce calkowite (P, Q, S)",
        "Wartosc",
        ["P_calkowita_kW", "Q_calkowita_kvar", "S_calkowita_kVA"],
    )
    add_chart(
        "Napiecia",
        "Napiecia fazowe U1, U2, U3",
        "V",
        ["U1_V", "U2_V", "U3_V"],
    )
    add_chart(
        "Prady",
        "Prady fazowe I1, I2, I3",
        "A",
        ["I1_A", "I2_A", "I3_A"],
    )

    try:
        wb.save(xlsx_file)
        print(f"Wyeksportowano raport z wykresami do {xlsx_file}")
        report("status", f"Wyeksportowano raport: {xlsx_file}")
        return True
    except (OSError, PermissionError) as exc:
        print(f"Blad zapisu raportu XLSX: {exc}")
        report("error", f"Blad zapisu raportu XLSX: {exc}")
        return False
