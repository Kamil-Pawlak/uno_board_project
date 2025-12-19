# Logika po stronie arduino

## Stany:
- CONNECTING
- NEUTRAL 1
- DRAWING 2
- ERASE 3

# Opis obecnego działania
W stanie connecting arduino wysyła '?' oczekując odpowiedzi znakiem '!'. Po połączeniu trzeba cyklicznie wysyłać znak '!', inaczej po 3 sekundach arduino wraca do stanu connecting.

Pozostałe stany różnią się tylko ich numerkiem, jest on informacją dla programu w jakim stanie powinien pracować.
Po numerze stanu wysyłane są dane z akcelerometru kolejno zmienne x,y,z. 

Przykładowa wiadomość wygląda tak:

``` 1;0.04;0.08;1.08 ```
