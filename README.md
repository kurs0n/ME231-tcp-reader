# Monitoring licznika ME231

Aplikacja desktopowa odczytuje pomiary z licznika ME231 przez bramkę USR-DR164 (Modbus TCP), zapisuje dane do CSV i pokazuje wykresy na żywo. Po zamknięciu może utworzyć raport XLSX z wykresami.

## Wymagania

- Python 3.10 lub nowszy
- Dostęp sieciowy do USR-DR164
- Pakiet Tkinter (na macOS jest zwykle dostępny z Pythona)

## Instalacja

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Uruchomienie

```bash
python3 -m src.main
```

W oknie programu ustaw adres IP bramki, port, Slave ID licznika oraz nazwy plików. Domyślne nazwy zawierają bieżącą datę, np. `me231_pomiary_2026-11-21.csv`. Przycisk `Start` uruchamia zbieranie danych w osobnym wątku, a `Stop` zatrzymuje je i generuje raport XLSX. Dane CSV są dopisywane do wskazanego pliku.

Na wykresach pokazywana jest sama godzina (`GG:MM:SS`); pełna data pozostaje w pliku CSV. Wykresy na żywo podzielone są na zakładki: przebiegi podstawowe (moce, napięcia, prądy), odkształcenia harmoniczne THD (dla napięć i prądów fazowych) oraz widok łączony.

Raport XLSX zawiera osobne arkusze: `Pomiary` z danymi oraz `Moce`, `Napiecia`, `Prady`, `THD_Napiecia` i `THD_Prady` z wykresami.

Błędy połączenia, odczytu lub zapisu są pokazywane w oknie aplikacji albo wypisywane w terminalu. Przy braku połączenia aplikacja przypomina o przełączeniu sieci Wi-Fi na `USR-DR164_8282`.

## Build na windows
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name ME231 --collect-all matplotlib --collect-all pymodbus launcher.py
```

## Publikacja Windows x64 na GitHub Releases

Workflow GitHub Actions buduje plik `ME231.exe` dla Windows x64 i dołącza go do GitHub Release po wypchnięciu taga w formacie `v*`, np.:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Wynikowy plik znajdziesz w sekcji Releases repozytorium.

## Struktura projektu

- `src/main.py` - uruchomienie aplikacji
- `src/config.py` - ustawienia i okno konfiguracyjne
- `src/modbus.py` - komunikacja z ME231 i zapis CSV
- `src/live_plot.py` - wykresy na żywo
- `src/exporter.py` - eksport danych do XLSX
