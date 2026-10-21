"""Install audit engines into user state. Never write runtime data into the kit."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from live_http import SafeClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', default=str(Path.home() / '.local/share/seo-kit/runtime'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    runtime = Path(args.runtime).expanduser().resolve()
    if runtime.is_relative_to(root):
        parser.error('runtime must be outside this repository')
    python = runtime / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    uv = shutil.which('uv')
    if not python.exists():
        subprocess.run([uv, 'venv', str(runtime)] if uv else [sys.executable, '-m', 'venv', str(runtime)], check=True)
    command = [uv, 'pip', 'install', '--python', str(python)] if uv else [str(python), '-m', 'pip', 'install']
    subprocess.run([*command, '--require-hashes', '-r', str(root / '.agents' / 'requirements-audit.lock')], check=True)
    subprocess.run([str(python), '-m', 'playwright', 'install', 'chromium'], check=True)
    response = SafeClient(max_bytes=15000000).fetch('https://cdn.ampproject.org/v0/validator_wasm.js')
    if response.status != 200:
        raise ValueError(f'AMP validator download returned HTTP {response.status}')
    destination = runtime.parent / 'amp-validator-wasm.js'
    destination.write_bytes(response.body)
    print(f'Audit Python: {python}\nAMP validator: {destination}')
    print('Install npm dependencies with npm install. Run npm run test:browser to verify isolation and rendering.')


if __name__ == '__main__':
    main()
