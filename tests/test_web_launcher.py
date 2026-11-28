import subprocess
import sys
from pathlib import Path


def test_server_failure_stops_the_other_server(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    stopped = tmp_path / "stopped"
    serve = """
import signal
import sys
import time
from pathlib import Path

def stop(*_args):
    Path(sys.argv[2]).touch()
    sys.exit(0)

signal.signal(signal.SIGTERM, stop)
Path(sys.argv[1]).touch()
while True:
    time.sleep(0.05)
"""
    fail = """
import sys
import time
from pathlib import Path

for _ in range(100):
    if Path(sys.argv[1]).exists():
        sys.exit(7)
    time.sleep(0.05)
sys.exit(8)
"""
    launcher = (
        "import sys; from football_team_assistant.web import run_servers; "
        f"sys.exit(run_servers([[sys.executable, '-c', {serve!r}, {str(ready)!r}, "
        f"{str(stopped)!r}], [sys.executable, '-c', {fail!r}, {str(ready)!r}]]))"
    )
    result = subprocess.run([sys.executable, "-c", launcher], timeout=10, check=False)

    assert result.returncode == 7
    assert stopped.exists()
