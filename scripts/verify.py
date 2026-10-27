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
N = 8
SIZE = N*N
zero = [0]*SIZE
identity = [int(i//N == i%N) for i in range(SIZE)]
pattern = list(range(-32,32))
cases = [(zero,zero),(identity,pattern),(pattern,identity),([1]*SIZE,[1]*SIZE),
         ([127]*SIZE,[127]*SIZE),([-128]*SIZE,[-128]*SIZE),([-128]*SIZE,[127]*SIZE),
         ([(-128 if i%2 else 127) for i in range(SIZE)],pattern)]
while len(cases)<256:
    a = [rng.randrange(-128,128) for _ in range(SIZE)]
    b = cases[-1][1] if len(cases)%2 else [rng.randrange(-128,128) for _ in range(SIZE)]
    cases.append((a,b))
lines=[]
for a,b in cases:
    c=[sum(a[r*N+k]*b[k*N+s] for k in range(N)) for r in range(N) for s in range(N)]
    packed=sum((x&255)<<(8*i) for i,x in enumerate(a+b))
    packed |= sum((x&0xffffffff)<<(1024+32*i) for i,x in enumerate(c))
    lines.append(f'{packed:0768x}')
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
assert 'PASS matrices=256 output_checks=16384 compute_cycles=23' in output
(REPORTS/'rtl_simulation.log').write_text(output)
report={'status':'PASS','array_size':'8x8','dataflow':'weight-stationary',
        'seed':20261027,'matrices':256,'output_checks':16384,
        'directed_matrices':8,'random_matrices':248,'stationary_weight_reuse_cases':124,
        'compute_cycles':23,
        'simulation_clock_period_ns':20,'simulation_compute_latency_ns':460,
        'note':'Simulation clock is a stimulus setting, not physical timing signoff or Fmax.',
        'simulator':subprocess.run(['iverilog','-V'],text=True,capture_output=True).stdout.splitlines()[0],
        'rtl_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT/'rtl').glob('*.sv'))}}
(REPORTS/'rtl_simulation.json').write_text(json.dumps(report,indent=2)+'\n')
print(output)
