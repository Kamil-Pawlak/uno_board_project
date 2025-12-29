import time

# Pamięć współdzielona dla mock-a
MOCK_CONTROLS = {
    "acc_x": 0.0,
    "acc_y": 0.0,
    "acc_z": 9.8,
    "pot_val": 0,
    "state": 1,  # 1 = Neutral, 2 = Drawing, 3 = Erase
    "button_pressed": False,
}


class MockSerial:
    def __init__(self, port, baudrate, timeout=1):
        print(f"[MOCK] Keyboard Sim Started on {port}")
        self.buffer = b""
        self.last_data_time = time.time()
        self.last_heartbeat = time.time()
        self.state_connecting = True

    @property
    def in_waiting(self):
        self._generate_packet()
        return len(self.buffer)

    # Obsługa heartbeat
    def write(self, data):
        if b"!" in data:
            self.last_heartbeat = time.time()
            if self.state_connecting:
                self.state_connecting = False
                print("[MOCK] Connected!")

    def readline(self):
        self._generate_packet()
        if b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            return line + b"\n"
        return b""

    def _generate_packet(self):
        current_time = time.time()

        # Logika timeout
        if current_time - self.last_heartbeat > 3.0:
            self.state_connecting = True

        # Generowanie danych co 50ms
        if current_time - self.last_data_time > 0.05:
            self.last_data_time = current_time

            if self.state_connecting:
                self.buffer += b"?\r\n"
            else:
                state = MOCK_CONTROLS["state"]
                ax = MOCK_CONTROLS["acc_x"]
                ay = MOCK_CONTROLS["acc_y"]
                az = MOCK_CONTROLS["acc_z"]
                pot = MOCK_CONTROLS["pot_val"]

                # Logika guzika (zmiana trybu)
                if MOCK_CONTROLS["button_pressed"]:
                    state += 1
                    if state > 3:
                        state = 1
                    MOCK_CONTROLS["state"] = state
                    MOCK_CONTROLS["button_pressed"] = False

                # 3. FORMAT: "State;AccX;AccY;AccZ;Pot"
                packet = f"{state};{ax:.2f};{ay:.2f};{az:.2f};{pot}\r\n"
                self.buffer += packet.encode("utf-8")

    def close(self):
        pass
