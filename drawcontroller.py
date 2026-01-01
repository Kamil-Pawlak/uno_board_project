import pygame
import sys
import threading
import time

TEST_MODE = False  # Przy teście rzeczywistym, zmienić na False
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

# --- USTAWIENIA PĘDZLA ---
brush_size = 5
brush_color = (0, 0, 0)

COLOR_PRESETS = {
    pygame.K_1: (0, 0, 0),
    pygame.K_2: (255, 0, 0),
    pygame.K_3: (0, 255, 0),
    pygame.K_4: (0, 0, 255),
    pygame.K_5: (255, 165, 0),
}

# --- MENU KOLORÓW NA EKRANIE ---
COLOR_BUTTONS = [
    {"color": (0, 0, 0)},
    {"color": (255, 0, 0)},
    {"color": (0, 255, 0)},
    {"color": (0, 0, 255)},
    {"color": (255, 165, 0)},
]


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
            if time.time() - last_sent > 1.0:
                ser.write(b"!")
                last_sent = time.time()

            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8").strip()
                    if line == "?" or line == "":
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

                except ValueError:
                    pass

            time.sleep(0.01)

    except Exception as e:
        print(f"Serial Error: {e}")
        app_state["mode_str"] = f"ERROR: {e}"


def update_cursor_logic(screen_w, screen_h):
    if not app_state["connected"]:
        return

    speed = 5.0
    ax = app_state["acc"][0]
    ay = app_state["acc"][1]

    cursor["x"] -= ay * speed
    cursor["y"] -= ax * speed

    cursor["x"] = max(0, min(screen_w, cursor["x"]))
    cursor["y"] = max(0, min(screen_h, cursor["y"]))


def draw_color_menu(screen, font, brush_color):
    """Rysuje przyciski wyboru koloru i zwraca kliknięty kolor lub None."""
    mouse_pos = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()[0]

    x = 10
    y = screen.get_height() - 40
    size = 30
    spacing = 10

    selected_color = None

    for btn in COLOR_BUTTONS:
        rect = pygame.Rect(x, y, size, size)

        # podświetlenie
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (200, 200, 200), rect)
            if click:
                selected_color = btn["color"]

        # ramka aktywnego koloru
        border = 3 if btn["color"] == brush_color else 1
        pygame.draw.rect(screen, btn["color"], rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, border)

        x += size + spacing

    return selected_color


def draw_port_selection(screen, font, ports):
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

        text_surf = font.render(f"{port}", True, (0, 0, 0))
        screen.blit(text_surf, (30, y_pos + 10))

        y_pos += 50

    return selected


def draw_interface(screen, font, canvas):
    global brush_size, brush_color

    w, h = screen.get_size()
    screen.blit(canvas, (0, 0))

    update_cursor_logic(w, h)
    cx, cy = int(cursor["x"]), int(cursor["y"])

    # --- RYSOWANIE / GUMOWANIE ---
    if app_state["mode_id"] == 2:
        pygame.draw.circle(canvas, brush_color, (cx, cy), brush_size)

    elif app_state["mode_id"] == 3:
        pygame.draw.circle(canvas, (255, 255, 255), (cx, cy), brush_size)

    # Kursor
    cursor_color = (0, 0, 0)
    if app_state["mode_id"] == 2:
        cursor_color = (0, 200, 0)
    if app_state["mode_id"] == 3:
        cursor_color = (255, 0, 0)

    pygame.draw.circle(screen, cursor_color, (cx, cy), 10, 2)
    pygame.draw.line(screen, cursor_color, (cx - 8, cy), (cx + 8, cy), 2)
    pygame.draw.line(screen, cursor_color, (cx, cy - 8), (cx, cy + 8), 2)

    # Teksty
    x_pos, y_pos, line_height = 10, 10, 25

    if app_state["connected"]:
        conn_text = "Status: Connected"
        color = (0, 150, 0)
    else:
        conn_text = "Status: Disconnected"
        color = (200, 0, 0)

    screen.blit(font.render(conn_text, True, color), (x_pos, y_pos))
    y_pos += line_height

    screen.blit(font.render(f"Brush size: {brush_size}", True, (0, 0, 0)), (x_pos, y_pos))
    y_pos += line_height

    screen.blit(font.render(f"Brush color: {brush_color}", True, (0, 0, 0)), (x_pos, y_pos))
    y_pos += line_height

    pot_text = f"Potentiometer: {app_state['pot']}"
    screen.blit(font.render(pot_text, True, (0, 0, 0)), (x_pos, y_pos))
    y_pos += line_height

    acc = app_state["acc"]
    acc_text = f"Accelerometer: X:{acc[0]:.2f} Y:{acc[1]:.2f} Z:{acc[2]:.2f}"
    screen.blit(font.render(acc_text, True, (0, 0, 0)), (x_pos, y_pos))

    y_pos += line_height
    mode_text = f"Mode: {app_state['mode_str']}"

    mode_color = (0, 0, 0)
    if app_state["mode_id"] == 2:
        mode_color = (0, 150, 0)
    if app_state["mode_id"] == 3:
        mode_color = (200, 0, 0)

    screen.blit(font.render(mode_text, True, mode_color), (x_pos, y_pos))

    # --- MENU WYBORU KOLORÓW ---
    new_color = draw_color_menu(screen, font, brush_color)
    if new_color:
        brush_color = new_color


def main():
    global current_port, thread_started, brush_size, brush_color

    pygame.init()
    screen = pygame.display.set_mode((600, 400), pygame.RESIZABLE)
    pygame.display.set_caption("Grove Cursor Controller")
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    clock = pygame.time.Clock()

    # --- PŁÓTNO ---
    canvas = pygame.Surface((600, 400))
    canvas.fill((255, 255, 255))

    available_ports = []
    if not TEST_MODE:
        available_ports = sorted(serial.tools.list_ports.comports())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:

                # --- ZMIANA KOLORU KLAWISZAMI ---
                if event.key in COLOR_PRESETS:
                    brush_color = COLOR_PRESETS[event.key]

                # --- ZMIANA GRUBOŚCI ---
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    brush_size = min(100, brush_size + 1)

                if event.key == pygame.K_MINUS:
                    brush_size = max(1, brush_size - 1)

                # --- CZYSZCZENIE TABLICY ---
                if event.key == pygame.K_c:
                    canvas.fill((255, 255, 255))

                if TEST_MODE and event.key == pygame.K_SPACE:
                    MOCK_CONTROLS["button_pressed"] = True

                if not TEST_MODE and current_port is None and event.key == pygame.K_r:
                    available_ports = sorted(serial.tools.list_ports.comports())

        if current_port is None:
            selection = draw_port_selection(screen, font, available_ports)
            if selection:
                current_port = str(selection.device) if not TEST_MODE else selection
        else:
            if not thread_started:
                t = threading.Thread(
                    target=serial_worker, args=(current_port,), daemon=True
                )
                t.start()
                thread_started = True

            if TEST_MODE:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_w]:
                    MOCK_CONTROLS["acc_y"] -= 0.1
                if keys[pygame.K_s]:
                    MOCK_CONTROLS["acc_y"] += 0.1
                if keys[pygame.K_a]:
                    MOCK_CONTROLS["acc_x"] -= 0.1
                if keys[pygame.K_d]:
                    MOCK_CONTROLS["acc_x"] += 0.1

                if keys[pygame.K_LEFT]:
                    MOCK_CONTROLS["pot_val"] = max(0, MOCK_CONTROLS["pot_val"] - 10)
                if keys[pygame.K_RIGHT]:
                    MOCK_CONTROLS["pot_val"] = min(1023, MOCK_CONTROLS["pot_val"] + 10)

            draw_interface(screen, font, canvas)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()