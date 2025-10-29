Bot do Notatek z Wykładów

Ten bot automatycznie transkrybuje nagrania audio/wideo z wykładów, przetwarza je przez AI, a następnie klasyfikuje i zapisuje notatki w odpowiednich folderach.

Wymagania

Zainstalowany Python 3.10+

Zainstalowany ffmpeg i dodany do ścieżki systemowej (PATH).

Zainstalowane biblioteki: requests, openai-whisper, gdown, openai, tiktoken.

pip install requests openai-whisper gdown openai tiktoken


LM Studio działające na komputerze.

Pierwsza Konfiguracja

Token Bota: Stwórz plik TokenBota.txt i wklej do niego token API od BotFather.

Model AI: Pobierz model (np. openai/gpt-oss-20b) w LM Studio.

Ścieżki w plikach .bat: Upewnij się, że ścieżki do środowiska wirtualnego (whisper-gpu-env) i folderu bota (Nagrania_bot) w plikach start_bota.bat i czysc_kolejke.bat są poprawne.

Baza Przedmiotów: Stwórz plik przedmioty.json i dodaj do niego swoje przedmioty i ich opisy (zobacz przykładowe_przedmioty.json).

Foldery: Stwórz folder prompts (na szablony) i audio_do_przetworzenia (na generowane notatki).

Uruchamianie

Zawsze uruchamiaj bota za pomocą skryptu:

start_bota.bat


Skrypt ten automatycznie załaduje odpowiedni model do LM Studio, uruchomi serwer i następnie odpali bota.

Dostępne Komendy Bota

/start, /help - Wyświetla pomoc.

/nowyprompt - Pozwala stworzyć nowy szablon promptu w rozmowie z botem.

/usunprompt - Wyświetla listę szablonów, które można usunąć.

/listanotatek - Pokazuje listę wszystkich wygenerowanych plików .txt w folderze notatek i jego podfolderach.

Wypadek (Bot utknął w pętli)

Jeśli bot z jakiegoś powodu się zawiesił i po restarcie w kółko przetwarza tę samą wiadomość:

Zatrzymaj bota.

Uruchom czysc_kolejke.bat.

Uruchom start_bota.bat ponownie.
