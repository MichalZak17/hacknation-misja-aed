# Wykorzystanie sztucznej inteligencji

Zgodnie z regulaminem zadania (§2.8) opisujemy, gdzie i jak korzystaliśmy z AI.

## W działaniu rozwiązania

- **Odczyt opisów tekstowych.** Lokalny model językowy Qwen3.8-27B, uruchomiony na naszym serwerze w vLLM bez
  wysyłania danych na zewnątrz, odczytuje opisy z OpenStreetMap i rejestrów miejskich, np. „w portierni, klucz
  u sołtysa” albo „dostępny pon–pt 7:30–15:30”. Wynikiem są uporządkowane pola: umiejscowienie, piętro, godziny
  w składni OSM, warunki dostępu i sezonowość.
- **Granice użycia modelu.**
  - Wartość z modelu jest używana tylko wtedy, gdy żadne źródło nie podaje pola wprost.
  - Ma najniższy priorytet i jest oznaczona w danych (`field_sources`, metoda `inferred`, w panelu znaczek „AI”).
  - Model nigdy nie ustala położenia, adresu ani stanu technicznego urządzenia.
- **Wybór modelu.** Model wybraliśmy na podstawie własnego testu porównawczego na ręcznie oznaczonej próbce rekordów.
  Prompt w aplikacji jest identyczny z testowanym.

## Przy tworzeniu rozwiązania

- Asystenta programistycznego opartego na AI używaliśmy do pisania i przeglądu kodu, testów i dokumentacji oraz do
  analizy kodu źródłowego portalu dane.gov.pl.
- Architekturę, model danych, wzorcowy zakres danych, reguły scalania i priorytety źródeł oraz decyzje o tym, czego
  nie zgadywać (adres, kod pocztowy), opracował zespół. Zespół też je zweryfikował.
- Każdą zmianę sprawdzaliśmy testami na prawdziwej bazie danych i na zapisanych kopiach źródeł.
- Zgodność z portalem sprawdziliśmy funkcjami z kodu dane.gov.pl uruchomionymi na testowej instancji portalu.
- Znak i księgę znaku kampanii „Otwarte AED” przygotował zespół (geometria znaku w `marketing/src/build_logo.py`).

Rozwiązanie jest autorskie, a zespół ma do niego pełnię praw.
