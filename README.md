# uno_board_project

Arduino służy jako kontroler do rysowania po tablicy wyświetlanej w dedykowanym programie. Poruszamy się kursorem, przy pomocy akcelerometru. Potencjometrem możemy ustalać grubość pędzla. Ekran wyświetla aktualny tryb pracy. Urządzenie działa w 3 trybach: rysowanie, zmazywanie, neutralny. Dioda służy jako indykator połączenia z programem, a buzzer jako dodatkowy efekt przy zmianie położenia kursora. Arduino komunikuje się z programem na komputerze za pomocą interfejsu seryjnego. Program ten wyświetla tablice po której można rysować.

## Moduły użyte w projekcie:
- grove beginner kit
- ### wejście:
  - akcelerometr,
  - przycisk,
  - potencjometr;
- ### wyjście:
  - dioda,
  - buzzer,
  - ekran,
  - port szeregowy (program na komputerze)

## Opis programu:
Program po uruchomieniu prosi o wybranie portu komunikacji z arduino. Następnie oczekuje na sygnał połączenia z arduino, który następuje po wciśnięciu przycisku na mikrokontrolerze. Następnie program otrzymuje rozkazy od mikrokontrolera dotyczące trybu pracy i położenia kursora i obsługuje te polecenia.
Komunikacja między arduino i programem jest obustronna. Arduino oczekuje na sygnał o poprawnym połączeniu z programem, w przypadku braku tego sygnału przechodzi w stan przed połączeniem.
## Technologie użyte w programie:
- Python,
- pyGame,
- pySerial
