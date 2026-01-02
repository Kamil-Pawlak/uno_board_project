import pygame
import sys
import threading
import time
import serial
import serial.tools.list_ports


TEST_MODE = True  # Przy teście rzeczywistym zmienić na False
BAUD_RATE = 9600


current_port = None
thread_started = False
disconnect_start = None
mock_killed = False

if TEST_MODE:
    from arduino_mock import MockSerial as SerialConnection, MOCK_CONTROLS

    current_port = "MOCK_PORT"
else:
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
    global app_state, current_port

    try:
        ser = SerialConnection(port_name, BAUD_RATE, timeout=1)
        time.sleep(2)
        last_sent = 0

        while current_port is not None:

            # Heartbeat
            try:
                if time.time() - last_sent > 1.0:
                    ser.write(b"!")
                    last_sent = time.time()
            except Exception:
                app_state["connected"] = False
                break

            # Czytaj dane
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode("utf-8").strip()
                    if line == "?" or line == "":
                        continue

                    # Podział danych zgodnie z schematem: "State;AccX;AccY;AccZ;Pot"
                    parts = line.split(";")
                    if len(parts) >= 4:
                        state_id = int(parts[0])
                        ax, ay, az = float(parts[1]), float(parts[2]), float(parts[3])
                        pot = int(parts[4]) if len(parts) > 4 else 0

                        app_state["mode_id"] = state_id
                        app_state["mode_str"] = get_mode_name(state_id)
                        app_state["acc"] = [ax, ay, az]
                        app_state["pot"] = pot

                        if TEST_MODE and mock_killed:
                            app_state["connected"] = False
                        else:
                            app_state["connected"] = state_id != 0

                except ValueError:
                    pass
                except Exception:
                    app_state["connected"] = False
                    break

            time.sleep(0.01)

    except Exception as e:
        print(f"Serial Open Error: {e}")
        app_state["mode_str"] = f"Error: {e}"
        app_state["connected"] = False


# Logika kursora
def update_cursor_logic(screen_w, screen_h):
    if not app_state["connected"]:
        return

    # Czułość kursora
    speed = 5.0
    ax = app_state["acc"][0]
    ay = app_state["acc"][1]

    cursor["x"] -= ay * speed
    cursor["y"] -= ax * speed
    cursor["x"] = max(0, min(cursor["x"], screen_w))
    cursor["y"] = max(0, min(cursor["y"], screen_h))


def draw_port_selection(screen, font, ports):
    screen.fill((255, 255, 255))
    title = font.render("SELECT CONNECTION PORT (Press R to Refresh):", True, (0, 0, 0))
    screen.blit(title, (20, 20))

    y_pos = 60
    mouse_pos = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()[0]
    selected = None

    if not ports:
        screen.blit(font.render("No ports found.", True, (255, 0, 0)), (20, 60))
        return None

    for port in ports:
        rect = pygame.Rect(20, y_pos, 550, 40)
        is_hover = rect.collidepoint(mouse_pos)
        color = (200, 230, 255) if is_hover else (240, 240, 240)

        if is_hover and click:
            selected = port

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        text_surf = font.render(f"{port}", True, (0, 0, 0))
        screen.blit(text_surf, (30, y_pos + 10))
        y_pos += 50

    return selected


def draw_interface(screen, font):
    w, h = screen.get_size()
    screen.fill((255, 255, 255))

    update_cursor_logic(w, h)
    cx, cy = int(cursor["x"]), int(cursor["y"])

    cursor_color = (0, 0, 0)
    if app_state["mode_id"] == 2:
        cursor_color = (0, 200, 0)
    if app_state["mode_id"] == 3:
        cursor_color = (255, 0, 0)

    if not app_state["connected"]:
        cursor_color = (150, 150, 150)

    pygame.draw.circle(screen, cursor_color, (cx, cy), 10, 2)
    pygame.draw.line(screen, cursor_color, (cx - 8, cy), (cx + 8, cy), 2)
    pygame.draw.line(screen, cursor_color, (cx, cy - 8), (cx, cy + 8), 2)

    x_pos, y_pos, lh = 10, 10, 25

    if app_state["connected"]:
        conn_text = "Status: Connected"
        color = (0, 150, 0)
    else:
        conn_text = "Status: DISCONNECTED"
        color = (200, 0, 0)

    # Reprezentacja odebranych wartości
    screen.blit(font.render(conn_text, True, color), (x_pos, y_pos))
    y_pos += lh
    screen.blit(
        font.render(f"Potentiometer: {app_state['pot']}", True, (0, 0, 0)),
        (x_pos, y_pos),
    )
    y_pos += lh
    acc = app_state["acc"]
    screen.blit(
        font.render(
            f"Acc: X:{acc[0]:.2f} Y:{acc[1]:.2f} Z:{acc[2]:.2f}", True, (0, 0, 0)
        ),
        (x_pos, y_pos),
    )
    y_pos += lh
    screen.blit(
        font.render(f"Mode: {app_state['mode_str']}", True, (0, 0, 0)), (x_pos, y_pos)
    )

    # Ostrzeżenie o braku połączenia
    if not app_state["connected"] and current_port is not None:
        if disconnect_start is not None:
            elapsed = time.time() - disconnect_start
            remain = max(0.0, 5.0 - elapsed)

            warning_font = pygame.font.SysFont("Consolas", 24, bold=True)
            warn_text = warning_font.render(
                f"RETURNING TO MENU IN {remain:.1f}s", True, (255, 0, 0)
            )
            text_rect = warn_text.get_rect(center=(w / 2, h / 2 + 50))
            screen.blit(warn_text, text_rect)


def main():
    global current_port, thread_started, disconnect_start, mock_killed

    pygame.init()
    screen = pygame.display.set_mode((600, 400), pygame.RESIZABLE)
    pygame.display.set_caption("Grove Cursor Controller")
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    clock = pygame.time.Clock()

    available_ports = []
    if not TEST_MODE:
        available_ports = sorted(serial.tools.list_ports.comports())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                current_port = None

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if TEST_MODE:
                    if event.key == pygame.K_SPACE and not mock_killed:
                        MOCK_CONTROLS["button_pressed"] = True

                    # Symulacja odłączenia portu
                    if event.key == pygame.K_k:
                        mock_killed = True
                        print(
                            "MOCK: Connection Killed by User (Press R to reset if back in menu)"
                        )

                # Odświeżanie listy dostępnych portów
                if current_port is None and event.key == pygame.K_r:
                    if not TEST_MODE:
                        available_ports = sorted(serial.tools.list_ports.comports())
                    else:
                        mock_killed = False

        if current_port is None:
            thread_started = False
            disconnect_start = None

            selection = draw_port_selection(screen, font, available_ports)
            if selection:
                current_port = str(selection.device) if not TEST_MODE else "MOCK_PORT"
                mock_killed = False

        else:
            if not thread_started:
                t = threading.Thread(
                    target=serial_worker, args=(current_port,), daemon=True
                )
                t.start()
                thread_started = True

            # Logika rozłączania
            if not app_state["connected"]:
                if disconnect_start is None:
                    disconnect_start = time.time()

                if time.time() - disconnect_start > 5.0:
                    print("Timeout reached. Returning to menu.")
                    current_port = None
            else:
                disconnect_start = None

            # Symulacja inputu z czujników z wykorzystaniem przycisków
            if TEST_MODE and not mock_killed:
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

            draw_interface(screen, font)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
