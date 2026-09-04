# 8-bit ALU

## Requirements
- Module: `alu8`
- Inputs: `a[7:0]`, `b[7:0]`, `op[2:0]`
- Output: `y[7:0]`, `zero`
- Combinational logic only.
- `op=000`: ADD
- `op=001`: SUB
- `op=010`: AND
- `op=011`: OR
- `op=100`: XOR
- `op=101`: PASS A
- `op=110`: PASS B
- `op=111`: output 0
- `zero` must be 1 exactly when `y==0`.

## Verification Goals
Test all operations, zero/non-zero results, boundary values, and random operand combinations.
