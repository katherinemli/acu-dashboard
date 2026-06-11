#!/usr/bin/env python3
"""
Modem Simulator — Fake u-blox GPS + modem lock signals
Outputs NMEA RMC sentences on TCP port 10001
"""

import socket
import time
import math
from datetime import datetime, timedelta

def generate_rmc_sentence(lat, lon, speed=1.5, course=90.0):
    """Generate NMEA RMC (Recommended Minimum) sentence."""
    now = datetime.utcnow()
    utc_time = now.strftime("%H%M%S.00")
    date = now.strftime("%d%m%y")

    # Simulate satellite orbit: move position slowly
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    lat_abs = abs(lat)
    lon_abs = abs(lon)

    lat_deg = int(lat_abs)
    lat_min = (lat_abs - lat_deg) * 60
    lon_deg = int(lon_abs)
    lon_min = (lon_abs - lon_deg) * 60

    # Checksum
    sentence = f"GPRMC,{utc_time},A,{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lon_deg:03d}{lon_min:07.4f},{lon_dir},{speed:.2f},{course:.2f},{date},,*"

    checksum = 0
    for char in sentence[6:]:  # Skip $GPRMC
        if char == '*':
            break
        checksum ^= ord(char)

    return f"${sentence}{checksum:02X}\r\n"


def run_modem_sim(port=10001, duration=None):
    """Run modem simulator."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    print(f"[Modem Sim] Listening on {port}...")

    start_time = time.time()
    lat, lon = 48.8566, 2.3522  # Paris

    try:
        while True:
            if duration and time.time() - start_time > duration:
                break

            try:
                conn, addr = server.accept()
                print(f"[Modem Sim] Client connected: {addr}")

                cycle = 0
                while True:
                    cycle += 1

                    # Move position slowly (satellite tracking simulation)
                    lat += 0.001 * math.sin(cycle / 50.0)
                    lon += 0.001 * math.cos(cycle / 50.0)

                    sentence = generate_rmc_sentence(lat, lon)
                    conn.sendall(sentence.encode())

                    time.sleep(0.5)

            except ConnectionResetError:
                print("[Modem Sim] Client disconnected")
            except BrokenPipeError:
                print("[Modem Sim] Client disconnected")

    except KeyboardInterrupt:
        print("[Modem Sim] Shutdown")
    finally:
        server.close()


if __name__ == "__main__":
    run_modem_sim()
