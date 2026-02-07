# llm_handler.py
# Moduł odpowiedzialny za komunikację z lokalnym modelem językowym (LM Studio).

import tiktoken
from openai import OpenAI
import json
import config
import time

# Inicjalizacja klienta OpenAI do komunikacji z lokalnym serwerem
client = OpenAI(base_url=config.LOKALNE_AI_URL, api_key="not-needed")

def log_status(wiadomosc):
    """Wyświetla sformatowany komunikat o statusie modułu LLM."""
    print(f"[LLM HANDLER STATUS] {wiadomosc}")

def podziel_tekst_na_fragmenty(tekst: str, limit_tokenow: int = config.CHUNK_TOKEN_LIMIT) -> list[str]:
    """Dzieli tekst na fragmenty, szanując limity tokenów."""
    log_status(f"Dzielenie tekstu na fragmenty po ok. {limit_tokenow} tokenów...")
    try:
        kodowanie = tiktoken.get_encoding("cl100k_base")
    except Exception:
        kodowanie = tiktoken.get_encoding("p50k_base")

    tokeny = kodowanie.encode(tekst)
    fragmenty_tekstowe = []
    aktualny_fragment_start = 0
    while aktualny_fragment_start < len(tokeny):
        koniec_fragmentu = aktualny_fragment_start + limit_tokenow
        fragment_tokenow = tokeny[aktualny_fragment_start:koniec_fragmentu]
        fragment_tekstowy = kodowanie.decode(fragment_tokenow)
        fragmenty_tekstowe.append(fragment_tekstowy)
        aktualny_fragment_start = koniec_fragmentu
    log_status(f"Podzielono tekst na {len(fragmenty_tekstowe)} fragmentów.")
    return fragmenty_tekstowe

def przetworz_fragmenty_wstepnie(fragmenty: list[str], prompt_uzytkownika: str, model_name: str = "local-model") -> (str, bool):
    """Wysyła każdy fragment do AI i zbiera 'notatki cząstkowe' (Faza "Map")."""
    
    # ZMIANA: Ulepszony PROMPT_MAP
    PROMPT_MAP = (
        "Jesteś asystentem AI specjalizującym się w syntezie informacji. "
        "Twoim zadaniem jest przeanalizować PONIŻSZY FRAGMENT TEKSTU. Jest to tylko mały fragment dłuższego dokumentu. "
        "Twoim zadaniem jest **wyłącznie** przeanalizowanie poniższego fragmentu i zastosowanie się do instrukcji użytkownika. "
        "**Nie próbuj zgadywać**, co było wcześniej lub co będzie później. Skup się *tylko* na dostarczonym tekście.\n\n"
        "Odpowiedz w formacie Markdown (używaj nagłówków, list, pogrubień).\n\n"
        "**Jeśli fragment tekstu jest pusty, bezwartościowy lub nie zawiera informacji pasujących do instrukcji, odpowiedz po prostu: \"[BRAK DANYCH]\"**\n\n"
        "--- INSTRUKCJE UŻYTKOWNIKA ---\n"
        f"{prompt_uzytkownika}\n\n"
        "--- FRAGMENT TRANSKRYPCJI ---"
    )
    
    wszystkie_notatki_czastkowe = []
    laczna_liczba_fragmentow = len(fragmenty)
    for i, fragment in enumerate(fragmenty):
        log_status(f"Przetwarzanie fragmentu {i+1}/{laczna_liczba_fragmentow}...")
        final_prompt_map = f"{PROMPT_MAP}\n{fragment}"
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": final_prompt_map}],
                temperature=0.7
            )
            notatka_czastkowa = completion.choices[0].message.content
            # ZMIANA: Ignorujemy puste odpowiedzi
            if notatka_czastkowa.strip() != "[BRAK DANYCH]":
                wszystkie_notatki_czastkowe.append(f"\n### Notatki z fragmentu {i+1}\n{notatka_czastkowa}")
        except Exception as e:
            log_status(f"Błąd podczas przetwarzania fragmentu {i+1}: {e}")
            wszystkie_notatki_czastkowe.append(f"\n### BŁĄD PRZETWARZANIA FRAGMENTU {i+1} ###")
            return "\n".join(wszystkie_notatki_czastkowe), False
    return "\n".join(wszystkie_notatki_czastkowe), True

def dokonaj_finalnej_syntezy(polaczone_notatki: str) -> (str, bool):
    """Tworzy ostateczną, spójną notatkę z notatek cząstkowych (Faza "Reduce")."""
    log_status("Rozpoczynanie finalnej syntezy (Reduce)...")
    
    # ZMIANA: Ulepszony PROMPT_REDUCE
    PROMPT_REDUCE = (
        "Jesteś starszym redaktorem. Poniżej znajduje się zbiór notatek "
        "cząstkowych (wygenerowanych fragment po fragmencie z długiego dokumentu). "
        "Twoim zadaniem jest zredagowanie ich i połączenie w jeden, spójny, logicznie uporządkowany "
        "dokument. \n\n"
        "**TWOJE ZADANIA:**\n"
        "1. **Połącz** wszystkie poniższe notatki w jeden płynny tekst.\n"
        "2. **Usuń** wszelkie powtórzenia i zbędne frazy.\n"
        "3. **Zignoruj** wszelkie komunikaty o błędach (np. 'BŁĄD PRZETWARZANIA') oraz nagłówki fragmentów (np. '### Notatki z fragmentu 5').\n"
        "4. **Nadaj** całości profesjonalną formę i spójną strukturę.\n"
        "5. **Formatuj** całość jako czytelny dokument Markdown (używaj nagłówków, list, pogrubień itp.).\n\n"
        "--- NOTATKI CZĄSTKOWE DO SYNTEZY ---\n{polaczone_notatki}\n---"
    )
    
    try:
        kodowanie = tiktoken.get_encoding("cl100k_base")
    except Exception:
        kodowanie = tiktoken.get_encoding("p50k_base")
    tokeny_notatek = kodowanie.encode(polaczone_notatki)
    
    if len(tokeny_notatek) < config.CHUNK_TOKEN_LIMIT:
        log_status("Notatki cząstkowe mieszczą się w limicie. Synteza jednoetapowa.")
        final_prompt_reduce = PROMPT_REDUCE.format(polaczone_notatki=polaczone_notatki)
        try:
            completion = client.chat.completions.create(
                model=getattr(config, "LLM_MODEL_NAME", "local-model"),
                messages=[{"role": "user", "content": final_prompt_reduce}],
                temperature=0.5
            )
            return completion.choices[0].message.content, True
        except Exception as e:
            log_status(f"Błąd podczas finalnej syntezy: {e}")
            return polaczone_notatki, False
    else:
        log_status("Notatki cząstkowe wciąż za duże. Uruchamianie syntezy rekurencyjnej...")
        fragmenty_notatek = podziel_tekst_na_fragmenty(polaczone_notatki)
        prompt_rekurencyjny = (
            "Zredaguj i połącz poniższe fragmenty notatek w spójną sekcję. "
            "Usuń powtórzenia i zachowaj logiczny ciąg. Pamiętaj o formatowaniu Markdown."
        )
        polaczone_notatki_poziom2, success = przetworz_fragmenty_wstepnie(fragmenty_notatek, prompt_rekurencyjny, model_name=model_name)
        if not success:
            return polaczone_notatki_poziom2, False
        return dokonaj_finalnej_syntezy(polaczone_notatki_poziom2)

def wygeneruj_temat_notatki(tekst: str) -> str:
    """Wymyśla krótki tytuł dla notatki."""
    log_status("Generowanie tematu notatki...")
    try:
        prompt = f"Na podstawie poniższego tekstu, wymyśl krótki, zwięzły tytuł (2-5 słów), który podsumowuje jego główny temat. Zwróć tylko i wyłącznie sam tytuł, bez żadnych dodatkowych zdań i cudzysłowów.\n\nTekst: \"{tekst[:1500]}\""
            completion = client.chat.completions.create(
                model=getattr(config, "LLM_MODEL_NAME", "local-model"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        temat = completion.choices[0].message.content.strip().replace('"', '')
        log_status(f"Wygenerowano temat: '{temat}'")
        return temat
    except Exception as e:
        log_status(f"BŁĄD podczas generowania tematu: {e}")
        return f"Notatka_{int(time.time())}"

def sklasyfikuj_notatke(notatka: str, przedmioty: dict) -> str:
    """Określa, do którego przedmiotu pasuje notatka."""
    log_status("Klasyfikacja notatki...")
    opisy_przedmiotow = "\n".join([f"- {nazwa}: {opis}" for nazwa, opis in przedmioty.items()])
    prompt = (
        "Jesteś asystentem akademickim. Poniżej znajduje się lista przedmiotów "
        "oraz treść notatki. Twoim zadaniem jest zdecydować, do którego przedmiotu "
        "notatka pasuje najlepiej. Odpowiedz tylko i wyłącznie JEDNYM słowem - "
        "dokładną nazwą klucza przedmiotu (np. 'sztuczna_inteligencja').\n\n"
        f"--- DOSTĘPNE PRZEDMIOTY ---\n{opisy_przedmiotow}\n\n"
        f"--- TREŚĆ NOTATKI ---\n{notatka[:2000]}\n\n"
        "Do którego przedmiotu pasuje ta notatka?"
    )
    try:
        completion = client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        klucz_przedmiotu = completion.choices[0].message.content.strip().split()[0]
        if klucz_przedmiotu in przedmioty:
            log_status(f"Notatka sklasyfikowana jako: '{klucz_przedmiotu}'")
            return klucz_przedmiotu
        else:
            log_status(f"OSTRZEŻENIE: Model zwrócił nieznany przedmiot '{klucz_przedmiotu}'.")
            return None
    except Exception as e:
        log_status(f"BŁĄD podczas klasyfikacji notatki: {e}")
        return None
