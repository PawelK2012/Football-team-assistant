import signal
import subprocess
import sys
from time import sleep
from types import FrameType


def run_servers(commands: list[list[str]]) -> int:
    stop_signal = 0

    def stop(signum: int, _frame: FrameType | None) -> None:
        nonlocal stop_signal
        stop_signal = signum

    previous = {signum: signal.signal(signum, stop) for signum in (signal.SIGINT, signal.SIGTERM)}
    servers: list[subprocess.Popen[bytes]] = []
    try:
        for command in commands:
            if stop_signal:
                break
            servers.append(subprocess.Popen(command))
        while not stop_signal:
            for server in servers:
                code = server.poll()
                if code is not None:
                    return code if code >= 0 else 128 - code
            sleep(0.1)
        return 128 + stop_signal
    finally:
        try:
            for server in servers:
                server.terminate()
            for server in servers:
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)


def main() -> int:
    chat_app, chat_port, admin_app, admin_port, *flags = sys.argv[1:]
    commands = [
        [sys.executable, "-m", "uvicorn", app, "--port", port, *flags]
        for app, port in ((chat_app, chat_port), (admin_app, admin_port))
    ]
    return run_servers(commands)


if __name__ == "__main__":
    sys.exit(main())
