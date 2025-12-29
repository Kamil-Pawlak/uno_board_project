import pygame
import sys
import threading
import time

TEST_MODE = False # Przy teście rzeczywistym, zmienić na False
BAUD_RATE = 9600

current_port = None
thread_started = False

if TEST_MODE:
    from arduino_mock import MockSerial as SerialConnection, MOCK_CONTROLS

    current_port = "MOCK_PORT"
else:
    import serial
    import serial.tools.list_ports

    SerialConnection = serial.Serial

app_state = {
    "mode_id": 0,  # 0 = Conn, 1 = Neutral, 2 = Draw, 3 = Erase
    "mode_str": "CONNECTING...",
    "acc": [0.0, 0.0, 0.0],
    "pot": 0,
    "connected": False,
}

cursor = {"x": 300.0, "y": 200.0}


def get_mode_name(id):
    if id == 0:
        return "CONNECTING..."
    if id == 1:
        return "NEUTRAL (Moving)"
    if id == 2:
        return "DRAWING (Active)"
    if id == 3:
        return "ERASING (Active)"
    return "UNKNOWN"


def serial_worker(port_name):
    global app_state
    try:
        ser = SerialConnection(port_name, BAUD_RATE, timeout=1)
        time.sleep(2)
        last_sent = 0

        while True:
            # Wyślij sygnał, że jest połączony
            if time.time() - last_sent > 1.0:
                ser.write(b"!")
                last_sent = time.time()

            # Czytaj dane
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8").strip()
                    if line == "?" or line == "":
                        continue

                    # Protocol: "State;AccX;AccY;AccZ;Pot"
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

                except ValueError:
                    pass

            time.sleep(0.01)

    except Exception as e:
        print(f"Serial Error: {e}")
        app_state["mode_str"] = f"ERROR: {e}"


def update_cursor_logic(screen_w, screen_h):
    if not app_state["connected"]:
        return

    # Czułość kursora
    speed = 5.0

    ax = app_state["acc"][0]
    ay = app_state["acc"][1]

    cursor["x"] -= ay * speed
    cursor["y"] -= ax * speed

    # Sprawdzanie krawędzi
    if cursor["x"] < 0:
        cursor["x"] = 0
    if cursor["x"] > screen_w:
        cursor["x"] = screen_w
    if cursor["y"] < 0:
        cursor["y"] = 0
    if cursor["y"] > screen_h:
        cursor["y"] = screen_h


# Wybór portu
def draw_port_selection(screen, font, ports):
    """Draws the list of available ports to click"""
    screen.fill((255, 255, 255))

    title = font.render("SELECT CONNECTION PORT:", True, (0, 0, 0))
    screen.blit(title, (20, 20))

    y_pos = 60
    mouse_pos = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()[0]

    selected = None

    if not ports:
        screen.blit(
            font.render("No ports found! Check USB cable.", True, (255, 0, 0)), (20, 60)
        )
        return None

    for port in ports:
        rect = pygame.Rect(20, y_pos, 550, 40)

        color = (240, 240, 240)
        if rect.collidepoint(mouse_pos):
            color = (200, 230, 255)
            if click:
                selected = port

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 1)

        # Text
        text_surf = font.render(f"{port}", True, (0, 0, 0))
        screen.blit(text_surf, (30, y_pos + 10))

        y_pos += 50

    return selected


# Rysowanie interfejsu
def draw_interface(screen, font):

    # Rysuj okienko
    w, h = screen.get_size()
    screen.fill((255, 255, 255))

    # Aktualizuj logikę kursora i go narysuj
    update_cursor_logic(w, h)
    cx, cy = int(cursor["x"]), int(cursor["y"])

    # Graficzna reprezentacja zmiany trybu
    cursor_color = (0, 0, 0)
    if app_state["mode_id"] == 2:
        cursor_color = (0, 200, 0)
    if app_state["mode_id"] == 3:
        cursor_color = (255, 0, 0)

    # Styl kursora
    pygame.draw.circle(screen, cursor_color, (cx, cy), 10, 2)
    pygame.draw.line(screen, cursor_color, (cx - 8, cy), (cx + 8, cy), 2)
    pygame.draw.line(screen, cursor_color, (cx, cy - 8), (cx, cy + 8), 2)

    # TExt
    x_pos, y_pos, line_height = 10, 10, 25

    # Status połączenia
    if app_state["connected"]:
        conn_text = "Status: Connected"
        color = (0, 150, 0)
    else:
        conn_text = "Status: Disconnected"
        color = (200, 0, 0)

    screen.blit(font.render(conn_text, True, color), (x_pos, y_pos))
    y_pos += line_height

    # Potencjometr
    pot_text = f"Potentiometer: {app_state['pot']}"
    screen.blit(font.render(pot_text, True, (0, 0, 0)), (x_pos, y_pos))
    y_pos += line_height

    # Akcelerometr
    acc = app_state["acc"]
    acc_text = f"Accelerometer: X:{acc[0]:.2f} Y:{acc[1]:.2f} Z:{acc[2]:.2f}"
    screen.blit(font.render(acc_text, True, (0, 0, 0)), (x_pos, y_pos))

    # Tryby i ich reprezentacja graficzna
    y_pos += line_height
    mode_text = f"Mode: {app_state['mode_str']}"

    mode_color = (0, 0, 0)
    if app_state["mode_id"] == 2:
        mode_color = (0, 150, 0)
    if app_state["mode_id"] == 3:
        mode_color = (200, 0, 0)

    screen.blit(font.render(mode_text, True, mode_color), (x_pos, y_pos))


def main():
    global current_port, thread_started
    pygame.init()
    screen = pygame.display.set_mode((600, 400), pygame.RESIZABLE)
    pygame.display.set_caption("Grove Cursor Controller")
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    clock = pygame.time.Clock()

    # Pre-fetch ports if we are in Real Mode
    available_ports = []
    if not TEST_MODE:
        # Get list of ports (Port Name, Description, Hardware ID)
        available_ports = sorted(serial.tools.list_ports.comports())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                # Symulacja guzika (spacja)
                if TEST_MODE and event.key == pygame.K_SPACE:
                    MOCK_CONTROLS["button_pressed"] = True

                # Odświeżanie na R
                if not TEST_MODE and current_port is None and event.key == pygame.K_r:
                    available_ports = sorted(serial.tools.list_ports.comports())

        # Kontroller logiczny
        if current_port is None:
            selection = draw_port_selection(screen, font, available_ports)
            if selection:
                #current port jako string nazwy portu
                current_port = str(selection.device) if not TEST_MODE else selection
        else:
            if not thread_started:
                t = threading.Thread(
                    target=serial_worker, args=(current_port,), daemon=True
                )
                t.start()
                thread_started = True

            # Symulacja kontrolek
            if TEST_MODE:
                keys = pygame.key.get_pressed()
                # Akcelerometr (WASD)
                if keys[pygame.K_w]:
                    MOCK_CONTROLS["acc_y"] -= 0.1
                if keys[pygame.K_s]:
                    MOCK_CONTROLS["acc_y"] += 0.1
                if keys[pygame.K_a]:
                    MOCK_CONTROLS["acc_x"] -= 0.1
                if keys[pygame.K_d]:
                    MOCK_CONTROLS["acc_x"] += 0.1

                # Potencjometr (lewa i prawa strzałka)
                if keys[pygame.K_LEFT]:
                    MOCK_CONTROLS["pot_val"] = max(0, MOCK_CONTROLS["pot_val"] - 10)
                if keys[pygame.K_RIGHT]:
                    MOCK_CONTROLS["pot_val"] = min(1023, MOCK_CONTROLS["pot_val"] + 10)

            draw_interface(screen, font)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
