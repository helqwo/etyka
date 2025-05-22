import pandas as pd
import numpy as np
from scipy.stats import entropy
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

# Główna klasa aplikacji
class BiasAnalyzer:
    def __init__(self, root):
        self.report = ""
        self.root = root
        self.root.title("Analiza Stronniczosci Danych")
        self.df = None
        # stworzenie GUI
        self.create_gui()

    # Funkcja tworząca interfejs użytkownika
    def create_gui(self):
        frame_top = tk.Frame(self.root, padx=10, pady=10)
        frame_top.pack(fill='x')

        self.label_file = tk.Label(frame_top, text="Wczytaj plik CSV:")
        self.label_file.pack(side='left')

        self.button_load = tk.Button(frame_top, text="Wybierz plik", command=self.load_file)
        self.button_load.pack(side='left', padx=10)

        self.button_export = tk.Button(frame_top, text="Eksportuj raport", command=self.export_report)
        self.button_export.pack(side='right', padx=10)

        # Scrollable column selector
        self.frame_columns_container = tk.LabelFrame(self.root, text="Wybierz kolumny do analizy", padx=10, pady=10)
        self.frame_columns_container.pack(fill='both', padx=10, pady=10, expand=True)

        self.canvas = tk.Canvas(self.frame_columns_container, height=150)
        self.scrollbar = tk.Scrollbar(self.frame_columns_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.button_analyze = tk.Button(self.root, text="Analizuj Stronniczosc", command=self.analyze_selected)
        self.button_analyze.pack(pady=10)

        self.text_report = tk.Text(self.root, height=20, wrap='word')
        self.text_report.pack(fill='both', expand=True, padx=10, pady=10)

    # Funkcja wczytująca plik CSV podany przez użytkownika
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        try:
            # wczytanie danych z pliku CSV
            self.df = pd.read_csv(file_path)
            # wyświetlenie checkboxów z nazwami kolumn
            self.create_selection()
        except Exception as e:
            messagebox.showerror("Błąd", f"Błąd wczytywania pliku: {e}")

    # Funkcja tworząca checkboxy dla wprowadzonych kolumn
    def create_selection(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.column_vars = {}
        for col in self.df.columns:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(self.scrollable_frame, text=col, variable=var)
            chk.pack(anchor='w')
            self.column_vars[col] = var

    # Funkcja analizująca dane z wybranych kolumn
    def analyze_selected(self):
        if self.df is None:
            messagebox.showwarning("Brak danych", "Wczytaj plik CSV")
            return

        selected_cols = [col for col, var in self.column_vars.items() if var.get()]  # zbierz wybrane kolumny
        if not selected_cols:
            messagebox.showwarning("Brak wyboru", "Wybierz co najmniej jedną kolumnę")
            return

        report = "=== RAPORT STRONNICZOSCI ===\n\n"
        for col in selected_cols:
            result = self.analyze_column(self.df[col])  # analizuj kolumnę
            report += f"Kolumna: {col}\n"
            report += f"Typ: {result['type']}\n"
            report += "Rozkład:\n"
            for k, v in result['distribution'].items():
                report += f" - {k}: {v:.2f}%\n"
            if result['type'] == 'kategoryczna':
                report += f"Entropia: {result['entropy']}\n"
            if result['type'] == 'liczbowa':
                report += f"Skośność (skew): {result['skew']}\n"
            if result['biased']:
                report += "POTENCJALNA STRONNICZOŚĆ\n"
            report += "\n"

        self.report = report
        self.text_report.delete(1.0, tk.END)
        self.text_report.insert(tk.END, report)

    # Funkcja analizująca pojedynczą kolumnę
    def analyze_column(self, series):
        series = series.dropna()

        if series.dtype == 'object' or series.nunique() < 10:
            counts = series.value_counts(normalize=True)
            top_value_percent = counts.max()
            ent = entropy(counts)
            max_ent = np.log2(series.nunique()) if series.nunique() > 1 else 1
            rel_ent = ent / max_ent
            # warunek stronniczosci
            biased = top_value_percent > 0.7 or rel_ent < 0.6

            return {
                "type": "kategoryczna",
                "distribution": counts.mul(100).round(2).to_dict(),
                "biased": biased,
                "entropy": round(ent, 2),
                "relative_entropy": round(rel_ent, 2)
            }

        else:  # dane liczbowe
            skew = series.skew()
            bins = pd.cut(series, bins=5)
            counts = bins.value_counts(normalize=True)
            top_bin_percent = counts.max()
            # warunek stronniczości
            biased = top_bin_percent > 0.5 or abs(skew) > 1

            return {
                "type": "liczbowa",
                "distribution": {str(k): round(v * 100, 2) for k, v in counts.items()},
                "biased": biased,
                "skew": round(skew, 2)
            }

    def export_report(self):
        if not self.report.strip():
            messagebox.showwarning("Brak raportu", "Najpierw wykonaj analizę.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Plik tekstowy", "*.txt")])
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.report)
            messagebox.showinfo("Zapisano", f"Raport zapisany do: {file_path}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać pliku: {e}")


# Uruchomienie aplikacji
if __name__ == '__main__':
    root = tk.Tk()
    app = BiasAnalyzer(root)
    root.mainloop()
