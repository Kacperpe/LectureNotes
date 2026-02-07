# llm_handler.py
# ModuÅ‚ odpowiedzialny za komunikacjÄ™ z lokalnym modelem jÄ™zykowym (LM Studio).

import tiktoken
from openai import OpenAI
import json
import config
import time

# Inicjalizacja klienta OpenAI do komunikacji z lokalnym serwerem
client = OpenAI(base_url=config.LOKALNE_AI_URL, api_key="not-needed")

def log_status(wiadomosc):
    """WyÅ›wietla sformatowany komunikat o statusie moduÅ‚u LLM."""
    print(f"[LLM HANDLER STATUS] {wiadomosc}")

def podziel_tekst_na_fragmenty(tekst: str, limit_tokenow: int = config.CHUNK_TOKEN_LIMIT) -> list[str]:
    """Dzieli tekst na fragmenty, szanujÄ…c limity tokenÃ³w."""
    log_status(f"Dzielenie tekstu na fragmenty po ok. {limit_tokenow} tokenÃ³w...")
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
    log_status(f"Podzielono tekst na {len(fragmenty_tekstowe)} fragmentÃ³w.")
    return fragmenty_tekstowe

def przetworz_fragmenty_wstepnie(fragmenty: list[str], prompt_uzytkownika: str, model_name: str = "local-model") -> (str, bool):
    """WysyÅ‚a kaÅ¼dy fragment do AI i zbiera 'notatki czÄ…stkowe' (Faza "Map")."""
    
    # ZMIANA: Ulepszony PROMPT_MAP
    PROMPT_MAP = (
        "JesteÅ› asystentem AI specjalizujÄ…cym siÄ™ w syntezie informacji. "
        "Twoim zadaniem jest przeanalizowaÄ‡ PONIÅ»SZY FRAGMENT TEKSTU. Jest to tylko maÅ‚y fragment dÅ‚uÅ¼szego dokumentu. "
        "Twoim zadaniem jest **wyÅ‚Ä…cznie** przeanalizowanie poniÅ¼szego fragmentu i zastosowanie siÄ™ do instrukcji uÅ¼ytkownika. "
        "**Nie prÃ³buj zgadywaÄ‡**, co byÅ‚o wczeÅ›niej lub co bÄ™dzie pÃ³Åºniej. Skup siÄ™ *tylko* na dostarczonym tekÅ›cie.\n\n"
        "Odpowiedz w formacie Markdown (uÅ¼ywaj nagÅ‚Ã³wkÃ³w, list, pogrubieÅ„).\n\n"
        "**JeÅ›li fragment tekstu jest pusty, bezwartoÅ›ciowy lub nie zawiera informacji pasujÄ…cych do instrukcji, odpowiedz po prostu: \"[BRAK DANYCH]\"**\n\n"
        "--- INSTRUKCJE UÅ»YTKOWNIKA ---\n"
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
            log_status(f"BÅ‚Ä…d podczas przetwarzania fragmentu {i+1}: {e}")
            wszystkie_notatki_czastkowe.append(f"\n### BÅÄ„D PRZETWARZANIA FRAGMENTU {i+1} ###")
            return "\n".join(wszystkie_notatki_czastkowe), False
    return "\n".join(wszystkie_notatki_czastkowe), True

def dokonaj_finalnej_syntezy(polaczone_notatki: str) -> (str, bool):
    """Tworzy ostatecznÄ…, spÃ³jnÄ… notatkÄ™ z notatek czÄ…stkowych (Faza "Reduce")."""
    log_status("Rozpoczynanie finalnej syntezy (Reduce)...")
    
    # ZMIANA: Ulepszony PROMPT_REDUCE
    PROMPT_REDUCE = (
        "JesteÅ› starszym redaktorem. PoniÅ¼ej znajduje siÄ™ zbiÃ³r notatek "
        "czÄ…stkowych (wygenerowanych fragment po fragmencie z dÅ‚ugiego dokumentu). "
        "Twoim zadaniem jest zredagowanie ich i poÅ‚Ä…czenie w jeden, spÃ³jny, logicznie uporzÄ…dkowany "
        "dokument. \n\n"
        "**TWOJE ZADANIA:**\n"
        "1. **PoÅ‚Ä…cz** wszystkie poniÅ¼sze notatki w jeden pÅ‚ynny tekst.\n"
        "2. **UsuÅ„** wszelkie powtÃ³rzenia i zbÄ™dne frazy.\n"
        "3. **Zignoruj** wszelkie komunikaty o bÅ‚Ä™dach (np. 'BÅÄ„D PRZETWARZANIA') oraz nagÅ‚Ã³wki fragmentÃ³w (np. '### Notatki z fragmentu 5').\n"
        "4. **Nadaj** caÅ‚oÅ›ci profesjonalnÄ… formÄ™ i spÃ³jnÄ… strukturÄ™.\n"
        "5. **Formatuj** caÅ‚oÅ›Ä‡ jako czytelny dokument Markdown (uÅ¼ywaj nagÅ‚Ã³wkÃ³w, list, pogrubieÅ„ itp.).\n\n"
        "--- NOTATKI CZÄ„STKOWE DO SYNTEZY ---\n{polaczone_notatki}\n---"
    )
    
    try:
        kodowanie = tiktoken.get_encoding("cl100k_base")
    except Exception:
        kodowanie = tiktoken.get_encoding("p50k_base")
    tokeny_notatek = kodowanie.encode(polaczone_notatki)
    
    if len(tokeny_notatek) < config.CHUNK_TOKEN_LIMIT:
        log_status("Notatki czÄ…stkowe mieszczÄ… siÄ™ w limicie. Synteza jednoetapowa.")
        final_prompt_reduce = PROMPT_REDUCE.format(polaczone_notatki=polaczone_notatki)
        try:
            completion = client.chat.completions.create(
                model=getattr(config, "LLM_MODEL_NAME", "local-model"),
                messages=[{"role": "user", "content": final_prompt_reduce}],
                temperature=0.5
            )
            return completion.choices[0].message.content, True
        except Exception as e:
            log_status(f"BÅ‚Ä…d podczas finalnej syntezy: {e}")
            return polaczone_notatki, False
    else:
        log_status("Notatki czÄ…stkowe wciÄ…Å¼ za duÅ¼e. Uruchamianie syntezy rekurencyjnej...")
        fragmenty_notatek = podziel_tekst_na_fragmenty(polaczone_notatki)
        prompt_rekurencyjny = (
            "Zredaguj i poÅ‚Ä…cz poniÅ¼sze fragmenty notatek w spÃ³jnÄ… sekcjÄ™. "
            "UsuÅ„ powtÃ³rzenia i zachowaj logiczny ciÄ…g. PamiÄ™taj o formatowaniu Markdown."
        )
        polaczone_notatki_poziom2, success = przetworz_fragmenty_wstepnie(fragmenty_notatek, prompt_rekurencyjny, model_name=getattr(config, "LLM_MODEL_NAME", "local-model"))
        if not success:
            return polaczone_notatki_poziom2, False
        return dokonaj_finalnej_syntezy(polaczone_notatki_poziom2)

def wygeneruj_temat_notatki(tekst: str) -> str:
    """WymyÅ›la krÃ³tki tytuÅ‚ dla notatki."""
    log_status("Generowanie tematu notatki...")
    try:
        prompt = (
            "Na podstawie poniÅ¼szego tekstu, wymyÅ›l krÃ³tki, zwiÄ™zÅ‚y tytuÅ‚ (2-5 sÅ‚Ã³w), "
            "ktÃ³ry podsumowuje jego gÅ‚Ã³wny temat. ZwrÃ³Ä‡ tylko i wyÅ‚Ä…cznie sam tytuÅ‚, "
            "bez Å¼adnych dodatkowych zdaÅ„ i cudzysÅ‚owÃ³w.\n\n"
            f"Tekst: \"{tekst[:1500]}\""
        )
        completion = client.chat.completions.create(
            model=getattr(config, "LLM_MODEL_NAME", "local-model"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        temat = completion.choices[0].message.content.strip().replace('"', "")
        log_status(f"Wygenerowano temat: '{temat}'")
        return temat
    except Exception as e:
        log_status(f"BÅÄ„D podczas generowania tematu: {e}")
        return f"Notatka_{int(time.time())}"
def sklasyfikuj_notatke(notatka: str, przedmioty: dict) -> str:
    """OkreÅ›la, do ktÃ³rego przedmiotu pasuje notatka."""
    log_status("Klasyfikacja notatki...")
    opisy_przedmiotow = "\n".join([f"- {nazwa}: {opis}" for nazwa, opis in przedmioty.items()])
    prompt = (
        "JesteÅ› asystentem akademickim. PoniÅ¼ej znajduje siÄ™ lista przedmiotÃ³w "
        "oraz treÅ›Ä‡ notatki. Twoim zadaniem jest zdecydowaÄ‡, do ktÃ³rego przedmiotu "
        "notatka pasuje najlepiej. Odpowiedz tylko i wyÅ‚Ä…cznie JEDNYM sÅ‚owem - "
        "dokÅ‚adnÄ… nazwÄ… klucza przedmiotu (np. 'sztuczna_inteligencja').\n\n"
        f"--- DOSTÄ˜PNE PRZEDMIOTY ---\n{opisy_przedmiotow}\n\n"
        f"--- TREÅšÄ† NOTATKI ---\n{notatka[:2000]}\n\n"
        "Do ktÃ³rego przedmiotu pasuje ta notatka?"
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
            log_status(f"OSTRZEÅ»ENIE: Model zwrÃ³ciÅ‚ nieznany przedmiot '{klucz_przedmiotu}'.")
            return None
    except Exception as e:
        log_status(f"BÅÄ„D podczas klasyfikacji notatki: {e}")
        return None

