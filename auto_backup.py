import sys
import os
import shutil
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import filedialog, messagebox

class ProjectBackupHandler(FileSystemEventHandler):
    """
    Handler, który tworzy "migawkę" (snapshot) wszystkich
    plików projektu, gdy którykolwiek z nich zostanie zmieniony.
    """
    def __init__(self, files_to_backup, backup_root_dir):
        # Używamy setu dla szybkiego dostępu
        self.files_to_backup = set(os.path.normpath(p) for p in files_to_backup)
        self.backup_root_dir = os.path.normpath(backup_root_dir)
        
        # Zapobiega tworzeniu wielu backupów na raz (np. przy "Zapisz wszystko")
        self.last_backup_time = 0
        self.debounce_seconds = 2 # Czekaj 2 sekundy przed kolejnym backupem

        print("Handler gotowy.")
        
    def on_modified(self, event):
        """Wywoływane, gdy coś w folderze się zmieni."""
        
        src_path = os.path.normpath(event.src_path)

        # 1. Sprawdzamy, czy to jeden z plików, które śledzimy
        if event.is_directory or src_path not in self.files_to_backup:
            return # To nie jest plik, który nas interesuje

        # 2. Sprawdzamy, czy nie robimy backupu zbyt często (debounce)
        now = time.time()
        if now - self.last_backup_time < self.debounce_seconds:
            # Prawdopodobnie "Zapisz wszystko", ignorujemy kolejne wywołania
            return 
        
        self.last_backup_time = now # Rejestrujemy czas tego backupu

        # --- Tworzenie migawki ---
        
        print(f"\nWykryto zmianę w: {os.path.basename(src_path)}")
        print("Tworzenie migawki całego projektu...")
        
        try:
            # 1. Stwórz nazwę folderu dla migawki
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            snapshot_dir = os.path.join(self.backup_root_dir, timestamp)
            
            # 2. Stwórz sam folder
            os.makedirs(snapshot_dir)

            # 3. Skopiuj WSZYSTKIE pliki projektu do tego folderu
            copied_files = 0
            for file_to_copy in self.files_to_backup:
                try:
                    # Kopiujemy plik, zachowując jego oryginalną nazwę
                    dest_file = os.path.join(snapshot_dir, os.path.basename(file_to_copy))
                    shutil.copy2(file_to_copy, dest_file)
                    copied_files += 1
                except Exception as e:
                    print(f"  BŁĄD: Nie można skopiować {file_to_copy}. {e}")
            
            print(f"ZAPISANO MIGAWKĘ: {timestamp} (skopiowano {copied_files} plików)")

        except Exception as e:
            print(f"KRYTYCZNY BŁĄD: Nie można utworzyć folderu migawki! {e}")

def main():
    root = tk.Tk()
    root.withdraw()

    # Krok 1: Wybierz pliki do projektu
    print("Krok 1: Wybierz WSZYSTKIE pliki projektu, które mają być backupowane razem.")
    print("(Możesz zaznaczyć wiele plików trzymając Ctrl lub Shift)")
    
    file_paths = filedialog.askopenfilenames(title="Krok 1: Wybierz pliki projektu")
    
    if not file_paths:
        print("Nie wybrano żadnych plików. Zamykanie programu.")
        sys.exit()

    # Krok 2: Wybierz folder docelowy na backupy
    print("\nKrok 2: Wybierz FOLDER, w którym będą zapisywane migawki (backupy).")
    
    backup_root_dir = filedialog.askdirectory(title="Krok 2: Wybierz główny folder na backupy")
    
    if not backup_root_dir:
        print("Nie wybrano folderu docelowego. Zamykanie programu.")
        sys.exit()

    # Sprawdzenie bezpieczeństwa (czy backup nie jest w folderze projektu)
    paths_to_watch = set(os.path.dirname(p) for p in file_paths)
    for watch_path in paths_to_watch:
        if os.path.normpath(backup_root_dir).startswith(os.path.normpath(watch_path)):
            msg = "OSTRZEŻENIE: Wybrałeś folder backupów, który jest wewnątrz folderu projektu. Może to spowodować problemy. Czy chcesz kontynuować?"
            if not messagebox.askyesno("Ostrzeżenie", msg):
                print("Anulowano.")
                sys.exit()

    # Tworzymy JEDEN handler dla wszystkich plików
    event_handler = ProjectBackupHandler(file_paths, backup_root_dir)
    
    print("---")
    print(f"Folder na backupy: {backup_root_dir}")
    print("Monitorowane pliki projektu:")
    for p in event_handler.files_to_backup:
        print(f"- {p}")
    print("---")
    print("Program działa w tle. Naciśnij Ctrl+C, aby zakończyć.")

    # Uruchamiamy obserwatora
    observer = Observer()
    for path in paths_to_watch:
        # Obserwujemy każdy folder, w którym jest choć jeden plik projektu
        observer.schedule(event_handler, path, recursive=False)
    
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nZatrzymano monitorowanie.")
    observer.join()

if __name__ == "__main__":
    main()