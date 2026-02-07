"""
Prosty interfejs graficzny do transkrypcji plikow audio/wideo z uzyciem
istniejacego modułu transcriber.py (Whisper).

Uruchom: python gui_app.py
"""

import os
import shutil
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

import config
import transcriber


# --- Stan aplikacji ---
model_whisper = None
model_loading = False
selected_file_path = None


def set_status(text):
    status_var.set(text)


def toggle_controls(enabled: bool):
    state = tk.NORMAL if enabled else tk.DISABLED
    select_btn.config(state=state)
    transcribe_btn.config(state=state)
    save_btn.config(state=state if result_text.get("1.0", tk.END).strip() else tk.DISABLED)


def load_model_async():
    global model_whisper, model_loading
    if model_whisper or model_loading:
        return

    model_loading = True
    set_status("Ładowanie modelu Whisper...")

    def worker():
        global model_whisper, model_loading
        try:
            model_whisper = transcriber.load_model(config.MODEL_WHISPER)
            root.after(0, set_status, "Model załadowany. Możesz transkrybować.")
        except BaseException as e:  # łapiemy również SystemExit z load_model
            root.after(0, messagebox.showerror, "Błąd ładowania modelu", str(e))
            root.after(0, set_status, f"Błąd ładowania modelu: {e}")
        finally:
            model_loading = False

    threading.Thread(target=worker, daemon=True).start()


def choose_file():
    global selected_file_path
    path = filedialog.askopenfilename(
        title="Wybierz plik audio lub wideo",
        filetypes=[
            ("Pliki audio/wideo", "*.mp3 *.wav *.m4a *.mp4 *.mkv *.mov *.flac *.aac"),
            ("Wszystkie pliki", "*.*"),
        ],
    )
    if path:
        selected_file_path = path
        file_var.set(path)
        set_status("Plik wybrany. Kliknij 'Transkrybuj'.")
        load_model_async()


def copy_to_temp(path: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="nagrania_gui_")
    dest_path = os.path.join(tmp_dir, os.path.basename(path))
    shutil.copy2(path, dest_path)
    return dest_path


def transcribe():
    if not selected_file_path:
        messagebox.showwarning("Brak pliku", "Najpierw wybierz plik do transkrypcji.")
        return

    def worker():
        toggle_controls(False)
        set_status("Przygotowywanie pliku...")

        # Upewnij sie, ze model jest zaladowany
        load_model_async()
        while model_loading:
            time.sleep(0.1)

        if model_whisper is None:
            root.after(0, messagebox.showerror, "Błąd modelu", "Model Whisper nie został załadowany.")
            root.after(0, set_status, "Błąd: model nie jest gotowy.")
            root.after(0, toggle_controls, True)
            return

        try:
            tmp_path = copy_to_temp(selected_file_path)
            lang = language_var.get().strip() or None
            set_status("Transkrypcja w toku...")
            text = transcriber.transkrybuj_audio(tmp_path, model_whisper, language=lang)
        except Exception as e:  # pragma: no cover - defensywnie
            root.after(0, messagebox.showerror, "Błąd transkrypcji", str(e))
            root.after(0, set_status, f"Błąd transkrypcji: {e}")
            root.after(0, toggle_controls, True)
            return

        def update_ui():
            if text:
                result_text.delete("1.0", tk.END)
                result_text.insert(tk.END, text)
                set_status("Gotowe. Wynik poniżej.")
                save_btn.config(state=tk.NORMAL)
            else:
                set_status("Brak wyniku. Sprawdź logi konsoli.")
            toggle_controls(True)

        root.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()


def save_result():
    content = result_text.get("1.0", tk.END).strip()
    if not content:
        messagebox.showwarning("Brak treści", "Nie ma nic do zapisania.")
        return

    initial_ext = config.DEFAULT_OUTPUT_EXTENSION or ".txt"
    path = filedialog.asksaveasfilename(
        title="Zapisz transkrypcję",
        defaultextension=initial_ext,
        filetypes=[("Pliki tekstowe", "*.txt *.md *.srt"), ("Wszystkie pliki", "*.*")],
    )
    if not path:
        return

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        set_status(f"Zapisano: {path}")
    except OSError as e:
        messagebox.showerror("Błąd zapisu", str(e))
        set_status("Błąd podczas zapisu.")


# --- Inicjalizacja UI ---
root = tk.Tk()
root.title("Nagrania Bot - GUI do transkrypcji")

file_var = tk.StringVar()
language_var = tk.StringVar(value=str(config.DEFAULT_TRANSCRIBE_LANGUAGE))
status_var = tk.StringVar(value="Wybierz plik, aby rozpocząć.")

padding = {"padx": 10, "pady": 6}

tk.Label(root, text="Plik do transkrypcji:").grid(row=0, column=0, sticky="w", **padding)
tk.Entry(root, textvariable=file_var, width=60, state="readonly").grid(row=0, column=1, sticky="we", **padding)
select_btn = tk.Button(root, text="Wybierz plik", command=choose_file)
select_btn.grid(row=0, column=2, **padding)

tk.Label(root, text="Język (np. pl, en, auto):").grid(row=1, column=0, sticky="w", **padding)
tk.Entry(root, textvariable=language_var, width=20).grid(row=1, column=1, sticky="w", **padding)

transcribe_btn = tk.Button(root, text="Transkrybuj", command=transcribe)
transcribe_btn.grid(row=1, column=2, **padding)

tk.Label(root, text="Wynik transkrypcji:").grid(row=2, column=0, sticky="w", **padding)
result_text = ScrolledText(root, width=90, height=25, wrap=tk.WORD)
result_text.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

save_btn = tk.Button(root, text="Zapisz do pliku", command=save_result, state=tk.DISABLED)
save_btn.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))

status_label = tk.Label(root, textvariable=status_var, anchor="w")
status_label.grid(row=4, column=1, columnspan=2, sticky="we", padx=10, pady=(0, 10))

# Rozszerzenie siatki
root.grid_rowconfigure(3, weight=1)
root.grid_columnconfigure(1, weight=1)

# Opcjonalnie zaladuj model od razu (przyspiesza pierwsza transkrypcje)
load_model_async()

root.mainloop()
