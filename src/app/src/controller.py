import pygame
import sys
import threading
import time
import serial
import serial.tools.list_ports

# ==============================
# KONFIGURACJA
# ==============================
TEST_MODE = False          # Zmień na False przy rzeczywistym Arduino
BAUD_RATE = 9600

current_port = None
thread_started = False
disconnect_start = None
mock_killed = False

if TEST_MODE:
    from arduino_mock import MockSerial as SerialConnection, MOCK_CONTROLS
    # current_port = "MOCK_PORT"  # ustawiane później po wyborze
else:
    SerialConnection = serial.Serial

# ==============================
# STAN APLIKACJI
# ==============================
app_state = {
    "mode_id": 0,      # 0=Conn, 1=Neutral, 2=Draw, 3=Erase
    "mode_str": "CONNECTING...",
    "acc": [0.0, 0.0, 0.0],
    "pot": 0,
    "connected": False,
}

cursor = {"x": 400.0, "y": 300.0}

# Ustawienia pędzla
brush_size = 5
brush_color = (0, 0, 0)

# Presety kolorów (klawisze 1-5)
COLOR_PRESETS = {
    pygame.K_1: (0, 0, 0),      # czarny
    pygame.K_2: (255, 0, 0),    # czerwony
    pygame.K_3: (0, 255, 0),    # zielony
    pygame.K_4: (0, 0, 255),    # niebieski
    pygame.K_5: (255, 165, 0),  # pomarańczowy
}

# Przyciski menu kolorów na ekranie
COLOR_BUTTONS = [
    {"color": (0, 0, 0)},
    {"color": (255, 0, 0)},
    {"color": (0, 255, 0)},
    {"color": (0, 0, 255)},
    {"color": (255, 165, 0)},
]

# ==============================
# FUNKCJE POMOCNICZE
# ==============================
def get_mode_name(mode_id):
    if mode_id == 0: return "CONNECTING..."
    if mode_id == 1: return "NEUTRAL (Moving)"
    if mode_id == 2: return "DRAWING (Active)"
    if mode_id == 3: return "ERASING (Active)"
    return "UNKNOWN"

# ==============================
# KOMUNIKACJA SZEREGOWA
# ==============================
def serial_worker(port_name):
    global app_state, current_port

    try:
        ser = SerialConnection(port_name, BAUD_RATE, timeout=1)
        time.sleep(2)
        last_sent = 0

        while current_port is not None:
            # Heartbeat
            if time.time() - last_sent > 1.0:
                try:
                    ser.write(b"!")
                    last_sent = time.time()
                except:
                    app_state["connected"] = False
                    break

            # Odczyt danych
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8").strip()
                    if not line or line == "?":
                        continue

                    parts = line.split(";")
                    if len(parts) >= 4:
                        state_id = int(parts[0])
                        ax = float(parts[1])
                        ay = float(parts[2])
                        az = float(parts[3])
                        pot = int(parts[4]) if len(parts) > 4 else 0

                        app_state["mode_id"] = state_id
                        app_state["mode_str"] = get_mode_name(state_id)
                        app_state["acc"] = [ax, ay, az]
                        app_state["pot"] = pot
                        app_state["connected"] = state_id != 0

                        if TEST_MODE and mock_killed:
                            app_state["connected"] = False

                except ValueError:
                    pass
                except Exception:
                    app_state["connected"] = False
                    break

            time.sleep(0.01)

    except Exception as e:
        print(f"Serial Error: {e}")
        app_state["mode_str"] = f"Error: {e}"
        app_state["connected"] = False

# ==============================
# LOGIKA KURSORA
# ==============================
def update_cursor_logic(screen_w, screen_h):
    if not app_state["connected"]:
        return

    speed = 5.0
    ax = app_state["acc"][0]
    ay = app_state["acc"][1]

    cursor["x"] -= ay * speed
    cursor["y"] -= ax * speed

    cursor["x"] = max(0, min(cursor["x"], screen_w))
    cursor["y"] = max(0, min(cursor["y"], screen_h))

# ==============================
# RYSOWANIE INTERFEJSU
# ==============================
def draw_color_menu(screen, current_color):
    mouse_pos = pygame.mouse.get_pos()
    clicked = pygame.mouse.get_pressed()[0]

    x = 10
    y = screen.get_height() - 50
    size = 35
    spacing = 10
    selected = None

    for btn in COLOR_BUTTONS:
        rect = pygame.Rect(x, y, size, size)
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (220, 220, 220), rect)
            if clicked:
                selected = btn["color"]

        border_width = 4 if btn["color"] == current_color else 2
        pygame.draw.rect(screen, btn["color"], rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, border_width)
        x += size + spacing

    return selected

def draw_port_selection(screen, font, ports):
    screen.fill((255, 255, 255))
    title = font.render("WYBIERZ PORT POŁĄCZENIA (R - odśwież):", True, (0, 0, 0))
    screen.blit(title, (20, 20))

    y_pos = 70
    mouse_pos = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()[0]
    selected = None

    if not ports:
        screen.blit(font.render("Nie znaleziono portów.", True, (255, 0, 0)), (20, y_pos))
        return None

    for port in ports:
        port_name = port.device if not TEST_MODE else "MOCK_PORT (testowy)"
        rect = pygame.Rect(20, y_pos, 560, 40)
        color = (200, 230, 255) if rect.collidepoint(mouse_pos) else (240, 240, 240)

        if rect.collidepoint(mouse_pos) and click:
            selected = port.device if not TEST_MODE else "MOCK_PORT"

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        text = font.render(port_name, True, (0, 0, 0))
        screen.blit(text, (30, y_pos + 10))
        y_pos += 50

    return selected

def draw_interface(screen, font, canvas):
    global brush_size, brush_color

    # Grubość pędzla zależna od potencjometru
    brush_size = max(1, int((app_state["pot"] / 1023.0) * 50) + 1)

    w, h = screen.get_size()
    screen.blit(canvas, (0, 0))

    update_cursor_logic(w, h)
    cx, cy = int(cursor["x"]), int(cursor["y"])

    # Rysowanie / gumowanie
    if app_state["mode_id"] == 2:        # DRAW
        pygame.draw.circle(canvas, brush_color, (cx, cy), brush_size)
    elif app_state["mode_id"] == 3:      # ERASE
        pygame.draw.circle(canvas, (255, 255, 255), (cx, cy), brush_size * 2)

    # Kursor wizualny
    cursor_color = (150, 150, 150)
    if app_state["mode_id"] == 2:
        cursor_color = (0, 200, 0)
    elif app_state["mode_id"] == 3:
        cursor_color = (255, 0, 0)
    if app_state["connected"]:
        pygame.draw.circle(screen, cursor_color, (cx, cy), 12, 3)
        pygame.draw.line(screen, cursor_color, (cx - 10, cy), (cx + 10, cy), 3)
        pygame.draw.line(screen, cursor_color, (cx, cy - 10), (cx, cy + 10), 3)

    # Informacje tekstowe
    x, y, lh = 10, 10, 28
    status_text = "Połączono" if app_state["connected"] else "Rozłączono"
    status_color = (0, 150, 0) if app_state["connected"] else (200, 0, 0)
    screen.blit(font.render(f"Status: {status_text}", True, status_color), (x, y))
    y += lh
    screen.blit(font.render(f"Rozmiar pędzla: {brush_size}", True, (0, 0, 0)), (x, y))
    y += lh
    screen.blit(font.render(f"Kolor: {brush_color}", True, (0, 0, 0)), (x, y))
    y += lh
    screen.blit(font.render(f"Potencjometr: {app_state['pot']}", True, (0, 0, 0)), (x, y))
    y += lh
    acc = app_state["acc"]
    screen.blit(font.render(f"Akx: {acc[0]:.2f}  Aky: {acc[1]:.2f}  Akz: {acc[2]:.2f}", True, (0, 0, 0)), (x, y))
    y += lh
    mode_color = (0, 150, 0) if app_state["mode_id"] == 2 else (200, 0, 0) if app_state["mode_id"] == 3 else (0, 0, 0)
    screen.blit(font.render(f"Tryb: {app_state['mode_str']}", True, mode_color), (x, y))

    # Menu kolorów
    new_color = draw_color_menu(screen, brush_color)
    if new_color:
        brush_color = new_color

    # Ostrzeżenie o powrocie do menu
    if not app_state["connected"] and current_port is not None and disconnect_start is not None:
        elapsed = time.time() - disconnect_start
        remain = max(0, 5.0 - elapsed)
        if remain > 0:
            warn = pygame.font.SysFont("Consolas", 30, bold=True).render(
                f"Powrót do menu za {remain:.1f}s", True, (255, 0, 0))
            screen.blit(warn, warn.get_rect(center=(w//2, h//2)))

# ==============================
# MAIN
# ==============================
def main():
    global current_port, thread_started, disconnect_start, mock_killed

    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    pygame.display.set_caption("Grove Draw Controller")
    font = pygame.font.SysFont("Consolas", 18, bold=True)
    clock = pygame.time.Clock()

    canvas = pygame.Surface((800, 600))
    canvas.fill((255, 255, 255))

    available_ports = []
    if not TEST_MODE:
        available_ports = sorted(serial.tools.list_ports.comports())

    running = True
    has_connected_once = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                current_port = None

            elif event.type == pygame.VIDEORESIZE:
                old_canvas = canvas
                canvas = pygame.Surface((event.w, event.h))
                canvas.fill((255, 255, 255))
                canvas.blit(old_canvas, (0, 0))
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                # Zmiana koloru klawiszami
                if event.key in COLOR_PRESETS:
                    global brush_color
                    brush_color = COLOR_PRESETS[event.key]

                # Czyszczenie płótna
                if event.key == pygame.K_c:
                    canvas.fill((255, 255, 255))

                # Odświeżenie listy portów
                if current_port is None and event.key == pygame.K_r:
                    if not TEST_MODE:
                        available_ports = sorted(serial.tools.list_ports.comports())
                    else:
                        mock_killed = False

                # Test mode - przycisk
                if TEST_MODE and event.key == pygame.K_SPACE:
                    MOCK_CONTROLS["button_pressed"] = True

                # Symulacja rozłączenia w trybie testowym
                if TEST_MODE and event.key == pygame.K_k:
                    mock_killed = True

        # === Wybór portu ===
        if current_port is None:
            thread_started = False
            disconnect_start = None
            has_connected_once = False

            selection = draw_port_selection(screen, font, available_ports)
            if selection:
                current_port = selection
                mock_killed = False

        else:
            # Uruchom wątek komunikacyjny
            if not thread_started:
                t = threading.Thread(target=serial_worker, args=(current_port,), daemon=True)
                t.start()
                thread_started = True

            # Logika powrotu do menu po utracie połączenia
            if app_state["connected"]:
                has_connected_once = True
                disconnect_start = None
            elif has_connected_once and disconnect_start is None:
                disconnect_start = time.time()

            if disconnect_start and time.time() - disconnect_start > 5.0:
                print("Timeout - powrót do menu wyboru portu.")
                current_port = None
                continue

            # Symulacja sterowania w trybie testowym
            if TEST_MODE and not mock_killed:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_w]: MOCK_CONTROLS["acc_y"] -= 0.1
                if keys[pygame.K_s]: MOCK_CONTROLS["acc_y"] += 0.1
                if keys[pygame.K_a]: MOCK_CONTROLS["acc_x"] -= 0.1
                if keys[pygame.K_d]: MOCK_CONTROLS["acc_x"] += 0.1
                if keys[pygame.K_LEFT]:  MOCK_CONTROLS["pot_val"] = max(0, MOCK_CONTROLS["pot_val"] - 10)
                if keys[pygame.K_RIGHT]: MOCK_CONTROLS["pot_val"] = min(1023, MOCK_CONTROLS["pot_val"] + 10)

            draw_interface(screen, font, canvas)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
