#!/usr/bin/env python3
"""
ESA (Electronically Steerable Antenna) Simulator — AMIP Protocol
Simulates TMYTEK flat-panel antenna on TCP port 5005
Handles beam steering commands and status queries.
"""

import socket
import struct
import time

# Minimal AMIP protocol (Antenna Modem Interface Protocol)
class AMIPCommand:
    SET_BEAM = 0x01
    GET_STATUS = 0x02
    GET_BEAM = 0x03


class ESASimulator:
    def __init__(self, host="127.0.0.1", port=5005):
        self.host = host
        self.port = port
        self.beam_id = 0
        self.power = False
        self.temperature = 35.0

    def parse_command(self, data):
        """Parse incoming AMIP command."""
        if len(data) < 2:
            return None

        cmd = data[0]
        payload = data[1:]

        if cmd == AMIPCommand.SET_BEAM:
            # Beam ID is 1-32 for phased array
            if len(payload) >= 1:
                self.beam_id = payload[0]
                return b"\x01\x00"  # ACK

        elif cmd == AMIPCommand.GET_BEAM:
            # Return current beam ID
            return struct.pack("BB", AMIPCommand.GET_BEAM, self.beam_id)

        elif cmd == AMIPCommand.GET_STATUS:
            # Return status: power, temp, beam_id
            status = struct.pack("BBB", self.power, int(self.temperature), self.beam_id)
            return struct.pack("B", AMIPCommand.GET_STATUS) + status

        return None

    def run(self):
        """Run ESA simulator."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)
        print(f"[ESA Sim] Listening on {self.host}:{self.port}...")

        try:
            while True:
                try:
                    conn, addr = server.accept()
                    print(f"[ESA Sim] Client connected: {addr}")
                    self.power = True

                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break

                        response = self.parse_command(data)
                        if response:
                            conn.sendall(response)
                            print(f"[ESA Sim] Cmd {data[0]:02x} → Beam {self.beam_id}")

                except ConnectionResetError:
                    print("[ESA Sim] Client disconnected")
                    self.power = False
                except BrokenPipeError:
                    print("[ESA Sim] Client disconnected")
                    self.power = False

        except KeyboardInterrupt:
            print("[ESA Sim] Shutdown")
        finally:
            server.close()


if __name__ == "__main__":
    esa = ESASimulator()
    esa.run()
