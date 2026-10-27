# 8x8 Systolic Array — ASAP7 Design Flow

Signed INT8 matrix multiplication with 64 weight-stationary processing elements,
INT32 accumulation, a self-checking SystemVerilog testbench, and an OpenROAD Flow
Scripts (ORFS) configuration for the ASAP7 predictive 7 nm platform.

## Reported ASAP7 results

| Metric | Value |
|---|---:|
| Clock frequency | 500 MHz |
| Core area | 3,903 µm² |
| Power | **5.43 mW** |
| Utilization | 30% |

Physical figures are the project owner's reported results, recorded in
[`reports/owner_reported_results.json`](reports/owner_reported_results.json).
The included verification evidence covers RTL simulation and structural checks.

**Completed verification:** the current RTL passes 256 matrix cases with 16,384
checked outputs. Actual simulator output and source hashes are in
[`reports/rtl_simulation.log`](reports/rtl_simulation.log) and
[`reports/rtl_simulation.json`](reports/rtl_simulation.json).

## Architecture and interface

- An 8×8 PE grid holds B weights locally, forwards A operands right, and
  propagates partial sums down each cycle.
- Boundary skew aligns each activation with the matching partial sum.
- A 64-entry register bank holds A, 64 PE registers hold B, and a 64-entry
  INT32 bank captures results. There are no SRAM macros.
- A scalar load/read interface limits pin count. Indices are row-major.
- Writes and new starts are ignored while busy. Start wins over an idle write.
- Reset is asynchronous and active low; reset during a calculation aborts it.

| Port | Function |
|---|---|
| `clk`, `rst_n` | Clock and active-low asynchronous reset |
| `load_en`, `load_b` | Operand write enable; select A=0 or B=1 |
| `load_addr[5:0]`, `load_data[7:0]` | Operand index and signed INT8 value |
| `start`, `busy`, `done` | Start request, computation status, one-cycle completion |
| `result_addr[5:0]`, `result_data[31:0]` | Output selection and signed INT32 result |

Load all 64 entries of each operand, pulse `start`, wait for `done`, and read
the 64 outputs. Weights persist across starts and can be reused with new A
matrices. The controller takes 23 cycles after accepting `start`, including the
final result capture; host loading and reading are additional.

## Run functional verification

Requires Python 3 and Icarus Verilog (`iverilog` and `vvp`):

```sh
make test
```

The testbench checks 8 directed and 248 seeded random matrices against Python
integer matrix products. Cases cover signed extrema, zero and identity inputs,
alternating signs, weight reuse, repeated calculations, reset during computation,
ignored busy requests, and completion timing. The testbench uses a 20 ns stimulus
clock. GitHub Actions repeats this check.

The 8×8 RTL also passes Yosys hierarchy, process lowering,
optimization, and structural checks. The raw output is in
[`reports/rtl_elaboration.log`](reports/rtl_elaboration.log). This checks generic
logic. Reproduce with an installed Yosys:

```sh
yosys -Q -T -p 'read_verilog -sv rtl/mac_pe.sv rtl/systolic_array.sv; hierarchy -check -top systolic_array; proc; opt; check -assert; stat' > reports/rtl_elaboration.log
```

## Run the ASAP7 physical flow

Use a built ORFS installation with its ASAP7 platform, Yosys, OpenROAD, KLayout,
and GNU Make 4.3 or newer. Follow the
[official ORFS installation guide](https://openroad-flow-scripts.readthedocs.io/en/latest/user/BuildLocally.html).
The configuration was written against ORFS revision
`64939f3717ad7c694199ba04cb98924b98022868`.

From a configured Linux ORFS environment:

```sh
export ORFS_ROOT=/path/to/OpenROAD-flow-scripts
source "$ORFS_ROOT/env.sh"
make physical JOBS=4
```

`ORFS_ROOT` is the local installation path. An individual stage can be requested:

```sh
python3 scripts/run_asap7.py --target synth --jobs 4
```

The runner invokes the official ORFS Makefile for synthesis, floorplanning,
placement, CTS, routing, extraction, and final layout generation. It captures
the command, input hashes, installed tool versions, ORFS revision, exit status,
and console log under `build/orfs/`. It fails if dependencies are missing.
`flow/asap7/config.mk` selects RVT/TC, 30% initial core utilization, and a
500 MHz target.

The SDC uses a **2,000 ps** clock period because the ORFS ASAP7 NLDM libraries
use picoseconds. Input/output budgets of 400 ps and clock uncertainty of 50 ps
are the interface and clock budgets used by this configuration. The platform's
PDN, routing, and extraction defaults are used.

After a successful final run:

```sh
make collect
```

The collector requires a successful final command, matching source hashes, and
a real final GDSII. It archives raw results/reports/logs with a SHA-256 manifest.

## Reference and attribution

[Rakshith Suresh's systolic-array project](https://gitlab.symbioticeda.com/rakshithsuresh2001/systolic_array)
is an architectural reference for the 8×8 weight-stationary array. This repository contains its own RTL,
testbench, and flow configuration.

The flow follows the official
[ORFS design configuration interface](https://openroad-flow-scripts.readthedocs.io/en/latest/user/AddingNewDesign.html)
and [flow variables](https://openroad-flow-scripts.readthedocs.io/en/latest/user/FlowVariables.html).
The time-unit setting is documented in the
[ASAP7 library](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib#L41).

## License

MIT for the original code here. ORFS, tools, and ASAP7 libraries retain their
own licenses; they are not bundled or relicensed by this repository.
