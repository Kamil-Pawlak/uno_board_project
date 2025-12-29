# UWAGA
Przy korzystaniu z fizycznego arduino należy w controller.py zmienić wartość TEST_MODE na false oraz ustawić nazwę wykorzystywanego
portu szeregowego w zmiennej SERIAL_PORT

# Użyte biblioteki:
- pygame
- pyserial
- threading
- time

# Sposób komunikacji po porcie szeregowym
Obecnie program w Python, zczytuje przesłany przez arduino sygnał, konwertuje go z byte-ów na string (i usuwa niewidzialne znaki), dzieli go po średnikach oraz dokonuje konwersji na odpowiednie wartości, poszczególnych segmentów stringa. Wykorzystywane jest również try-catch, by program się nie wywalił przy nieodpowiednim sygnale

# Opis działania programu
Odpalamy controller.py, wtedy tworzy się nam okienko generowane za pomocą pyGame, kursor, stan, status połączenia oraz wartości potencjometru i akcelerometru. Potencjometr (symulowany lewą i prawą strzałką) obecnie tylko zmienia wartość, guzik (symulowany spacją) zmienia stan programu (netural, draw, erase), natomiast akcelerometr (symulowany WASD) pozwala na ruszanie kursorem po okienku.
