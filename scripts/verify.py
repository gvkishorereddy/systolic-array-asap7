#!/usr/bin/env python3
"""Generate deterministic golden vectors and run the RTL scoreboard."""
import hashlib
import json
import pathlib
import random
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
REPORTS = ROOT / 'reports'
BUILD.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)
rng = random.Random(20261027)
zero = [0]*16
identity = [int(i//4 == i%4) for i in range(16)]
pattern = list(range(-8,8))
cases = [(zero,zero),(identity,pattern),(pattern,identity),([1]*16,[1]*16),
         ([127]*16,[127]*16),([-128]*16,[-128]*16),([-128]*16,[127]*16),
         ([(-128 if i%2 else 127) for i in range(16)],pattern)]
while len(cases)<256:
    cases.append(([rng.randrange(-128,128) for _ in range(16)],
                  [rng.randrange(-128,128) for _ in range(16)]))
lines=[]
for a,b in cases:
    c=[sum(a[r*4+k]*b[k*4+s] for k in range(4)) for r in range(4) for s in range(4)]
    packed=sum((x&255)<<(8*i) for i,x in enumerate(a+b))
    packed |= sum((x&0xffffffff)<<(256+32*i) for i,x in enumerate(c))
    lines.append(f'{packed:0192x}')
(BUILD/'vectors.hex').write_text('\n'.join(lines)+'\n')
commands=[['iverilog','-g2012','-Wall','-s','tb_systolic','-o','build/sim',
           'rtl/mac_pe.sv','rtl/systolic_array.sv','tb/tb_systolic.sv'],
          ['vvp','build/sim']]
log=[]
for command in commands:
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    log += ['$ '+' '.join(command), result.stdout, result.stderr]
    if result.returncode:
        (REPORTS/'rtl_simulation.log').write_text('\n'.join(log))
        raise SystemExit(result.returncode)
output='\n'.join(log).rstrip()+'\n'
assert 'PASS matrices=256 output_checks=4096 compute_cycles=10' in output
(REPORTS/'rtl_simulation.log').write_text(output)
report={'status':'PASS','seed':20261027,'matrices':256,'output_checks':4096,
        'directed_matrices':8,'random_matrices':248,'compute_cycles':10,
        'simulation_clock_period_ns':20,'simulation_compute_latency_ns':200,
        'note':'Simulation clock is a stimulus setting, not physical timing signoff or Fmax.',
        'simulator':subprocess.run(['iverilog','-V'],text=True,capture_output=True).stdout.splitlines()[0],
        'rtl_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT/'rtl').glob('*.sv'))}}
(REPORTS/'rtl_simulation.json').write_text(json.dumps(report,indent=2)+'\n')
print(output)
