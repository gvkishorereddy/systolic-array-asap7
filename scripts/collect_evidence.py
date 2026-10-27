#!/usr/bin/env python3
"""Archive real ORFS output with hashes; never generate synthetic PPA reports."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/orfs'
NAME = 'asap7/systolic_array_8x8/base'


def main():
    manifest_path = WORK / 'latest_run.json'
    if not manifest_path.is_file():
        raise SystemExit('No run manifest. Run make physical first.')
    run = json.loads(manifest_path.read_text())
    if run['status'] != 'command_completed' or run['target'] not in ('all', 'finish'):
        raise SystemExit('Only a completed all/finish run can be archived as a final implementation.')
    # Prevent pairing a modified source tree with an older result directory.
    for name, expected in run['input_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Input changed since this run: {name}')
    result_dir = WORK / 'results' / NAME
    if not (result_dir / '6_final.gds').is_file():
        raise SystemExit('Missing 6_final.gds; nothing is being presented as a completed layout.')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = ROOT / 'evidence' / stamp
    destination.mkdir(parents=True)
    shutil.copy2(manifest_path, destination / 'run_manifest.json')
    console = ROOT / run['console_log']
    shutil.copy2(console, destination / 'console.log')
    for category in ('results', 'reports', 'logs'):
        source = WORK / category / NAME
        if source.is_dir():
            shutil.copytree(source, destination / category)
    hashes = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination / 'sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(f'Archived {len(hashes)} real files to {destination}')
    print('Review timing, DRC, and power assumptions before reporting any physical result.')


if __name__ == '__main__':
    main()
