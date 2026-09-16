"""FarmDirect FINAL — run entry point.

Usage:
    python run.py            # starts on 5000, or next free port if occupied
    PORT=8080 python run.py  # force an explicit port
"""
import os
import socket

from app_factory import create_app

app = create_app()


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def _resolve_port() -> int:
    explicit = os.environ.get("PORT")
    if explicit:
        return int(explicit)
    for port in range(5000, 5011):
        if _port_free(port):
            return port
    raise RuntimeError("No free port found from 5000 to 5010. Stop an old FarmDirect process or set PORT manually.")


if __name__ == "__main__":
    port = _resolve_port()
    print("\n" + "=" * 64)
    print("  FarmDirect FINAL — SIH integrated build")
    print(f"  Local URL:  http://localhost:{port}")
    print(f"  Marketplace: http://localhost:{port}/marketplace")
    print(f"  Live Mandi:  http://localhost:{port}/market-intelligence")
    print(f"  IVR:         http://localhost:{port}/ivr/simulator")
    if port != 5000 and not os.environ.get("PORT"):
        print("  NOTE: port 5000 was busy, so FarmDirect selected this free port automatically.")
    print("=" * 64 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
