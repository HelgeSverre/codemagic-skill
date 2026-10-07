"""Exercise the distributed credential wrapper under a real controlling terminal."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from zipfile import ZipFile

from test_distribution import builder

# A fresh session owns the PTY. Its child gets pipes, just like an MCP server,
# but can still take the controlling terminal through interactive job control.
SUPERVISOR = """
import fcntl, json, os, subprocess, sys, termios
fcntl.ioctl(0, termios.TIOCSCTTY, 0)
before = os.tcgetpgrp(0)
try:
    child = subprocess.run(sys.argv[1:], input='request\\n', capture_output=True,
                           text=True, timeout=10)
except subprocess.TimeoutExpired as error:
    raise RuntimeError(f'Launcher timed out: stdout={error.stdout!r}, '
                       f'stderr={error.stderr!r}') from error
print(json.dumps(dict(before=before, after=os.tcgetpgrp(0),
                     stdout=child.stdout, stderr=child.stderr, code=child.returncode)))
"""

PROBE = """
import json, os, sys
from pathlib import Path
with open('/dev/tty') as tty:
    foreground = os.tcgetpgrp(tty.fileno())
checkpoint = Path(os.environ['TEST_CHECKPOINT'])
if sys.argv[1] == 'startup':
    checkpoint.write_text(str(foreground))
else:
    print(json.dumps(dict(startup=int(checkpoint.read_text()), foreground=foreground,
                          token=os.environ.get('CODEMAGIC_API_KEY'),
                          args=sys.argv[2:], stdin=sys.stdin.read())))
    sys.exit(17)
"""


@unittest.skipUnless(os.name == "posix" and shutil.which("zsh"), "Requires POSIX PTY and zsh")
class TTYWrapperTests(unittest.TestCase):
    def run_wrapper(self, unsafe=False):
        import pty

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extracted = root / "plugin with spaces"
            with ZipFile(builder.build(root)) as archive:
                archive.extractall(extracted)
            wrapper = extracted / "skills/codemagic/scripts/with_zsh_env.sh"
            self.assertTrue(wrapper.is_file(), "Credential wrapper missing from plugin ZIP")
            probe = root / "probe.py"
            probe.write_text(textwrap.dedent(PROBE))
            (root / ".zshrc").write_text(
                'print "shell startup output"\n'
                'export CODEMAGIC_API_KEY="synthetic-from-zsh"\n'
                '"$TEST_PYTHON" "$TEST_PROBE" startup\n'
            )
            env = {
                "PATH": os.environ["PATH"],
                "HOME": str(root),
                "ZDOTDIR": str(root),
                "TERM": "xterm",
                "TEST_PYTHON": sys.executable,
                "TEST_PROBE": str(probe),
                "TEST_CHECKPOINT": str(root / "checkpoint"),
            }
            # A negative control proves that this harness detects the original
            # takeover during .zshrc, even when exec later restores the TTY.
            if unsafe:
                command = ["zsh", "-ic", 'exec "$@"', "unsafe-wrapper"]
            else:
                command = ["sh", str(wrapper)]
            arguments = ["argument with spaces", "$(not-a-command)", "", "--flag"]
            command.extend([sys.executable, str(probe), "command", *arguments])
            master, slave = pty.openpty()
            try:
                result = subprocess.run(
                    [sys.executable, "-c", SUPERVISOR, *command],
                    stdin=slave,
                    capture_output=True,
                    start_new_session=True,
                    env=env,
                    text=True,
                    timeout=15,
                )
            finally:
                os.close(slave)
                os.close(master)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            payload = json.loads(report["stdout"].splitlines()[-1])
            self.assertEqual(report["code"], 17)
            self.assertEqual(payload["args"], arguments)
            self.assertEqual(payload["stdin"], "request\n")
            self.assertEqual(payload["token"], "synthetic-from-zsh")
            return report, payload

    def test_wrapper_preserves_terminal_and_stdio(self):
        report, payload = self.run_wrapper()
        self.assertEqual(payload["startup"], report["before"])
        self.assertEqual(payload["foreground"], report["before"])
        self.assertEqual(report["after"], report["before"])
        self.assertIn("shell startup output", report["stderr"])
        self.assertEqual(json.loads(report["stdout"]), payload)

    def test_probe_detects_plain_interactive_zsh_taking_terminal(self):
        report, payload = self.run_wrapper(unsafe=True)
        self.assertNotEqual(payload["startup"], report["before"])


if __name__ == "__main__":
    unittest.main()
