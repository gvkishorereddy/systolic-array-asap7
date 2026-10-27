#!/usr/bin/env python3
"""Run generic Yosys elaboration and structural checks; save logs and input hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'ghcr.io/librelane/librelane:3.0.17'
SCRIPT = ('read_verilog -sv rtl/mac_pe.sv rtl/systolic_array.sv; '
          'hierarchy -check -top systolic_array; proc; opt; check -assert; stat')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', action='store_true', help='Use the versioned LibreLane tool image.')
    args = parser.parse_args()
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    summary = reports / 'rtl_elaboration.json'
    summary.unlink(missing_ok=True)
    if args.docker:
        if not shutil.which('docker'):
            parser.error('Docker is required for --docker.')
        base = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
                '--tmpfs', '/tmp', '-v', f'{ROOT}:/project:ro', '-w', '/project',
                '--entrypoint', 'yosys', IMAGE]
    else:
        if not shutil.which('yosys'):
            parser.error('Install Yosys or pass --docker.')
        base = ['yosys']
    version = subprocess.run(base + ['-V'], cwd=ROOT, text=True, capture_output=True)
    if version.returncode:
        print(version.stderr, file=sys.stderr)
        return version.returncode
    command = base + ['-Q', '-T', '-p', SCRIPT]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log = result.stdout + result.stderr
    (reports / 'rtl_elaboration.log').write_text(log)
    if result.returncode:
        print(log, file=sys.stderr)
        return result.returncode
    record = {
        'status': 'PASS', 'scope': 'generic elaboration and structural checks',
        'top': 'systolic_array', 'yosys_version': version.stdout.strip(),
        'yosys_script': SCRIPT, 'tool_image': IMAGE if args.docker else None,
        'rtl_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted((ROOT / 'rtl').glob('*.sv'))}
    }
    summary.write_text(json.dumps(record, indent=2) + '\n')
    print('PASS: Yosys hierarchy, process lowering, optimization, and structural checks.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
