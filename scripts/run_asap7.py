#!/usr/bin/env python3
"""Run an installed ORFS flow and record actual commands, versions, and status."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_REVISION = '64939f3717ad7c694199ba04cb98924b98022868'


def probe(command):
    result = subprocess.run(command, text=True, capture_output=True)
    return (result.stdout + result.stderr).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orfs-root', default=os.environ.get('ORFS_ROOT'))
    parser.add_argument('--target', choices=['all', 'synth', 'floorplan', 'place',
                                          'cts', 'route', 'finish'], default='all')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if not args.orfs_root:
        parser.error('Set ORFS_ROOT or supply --orfs-root to a built ORFS checkout.')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    orfs = Path(args.orfs_root).expanduser().resolve()
    if not (orfs / 'flow/Makefile').is_file():
        parser.error(f'No ORFS flow/Makefile under {orfs}')
    if not (orfs / 'flow/platforms/asap7/config.mk').is_file():
        parser.error('The ORFS checkout must include the ASAP7 platform.')
    make = os.environ.get('MAKE') or shutil.which('gmake') or shutil.which('make')
    if not make:
        parser.error('GNU Make 4.3 or newer is required.')
    version = probe([make, '--version'])
    match = re.search(r'GNU Make (\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (4, 3):
        parser.error('GNU Make 4.3 or newer is required; set MAKE if necessary.')
    tools = {'make': version.splitlines()[0]}
    for tool, flag in [('yosys', '-V'), ('openroad', '-version'), ('klayout', '-v')]:
        if not shutil.which(tool):
            parser.error(f'{tool} is missing; source the built ORFS env.sh first.')
        tools[tool] = probe([tool, flag])

    work = ROOT / 'build/orfs'
    work.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log_path = work / f'{timestamp}_{args.target}.log'
    manifest_path = work / 'latest_run.json'
    inputs = sorted((ROOT / 'rtl').glob('*.sv')) + sorted((ROOT / 'flow/asap7').glob('*'))
    command = [make, '-C', str(orfs / 'flow'),
               f'DESIGN_CONFIG={ROOT / "flow/asap7/config.mk"}',
               f'WORK_HOME={work}', 'FLOW_VARIANT=base',
               f'NUM_CORES={args.jobs}', args.target]
    manifest = {
        'started_utc': timestamp, 'status': 'running', 'target': args.target,
        'command': command, 'console_log': str(log_path.relative_to(ROOT)),
        'orfs_revision': probe(['git', '-C', str(orfs), 'rev-parse', 'HEAD']),
        'configuration_reference_revision': REFERENCE_REVISION,
        'tool_versions': tools,
        'input_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in inputs},
        'note': 'Flow completion alone does not establish timing or physical signoff.'
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Running:', ' '.join(command), flush=True)
    status = 1
    try:
        with log_path.open('w') as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
            try:
                for line in process.stdout:
                    print(line, end='', flush=True)
                    log.write(line)
                status = process.wait()
            except KeyboardInterrupt:
                process.terminate()
                process.wait()
                status = 130
    finally:
        manifest['returncode'] = status
        manifest['status'] = 'command_completed' if status == 0 else 'failed_or_interrupted'
        manifest['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return status


if __name__ == '__main__':
    sys.exit(main())
