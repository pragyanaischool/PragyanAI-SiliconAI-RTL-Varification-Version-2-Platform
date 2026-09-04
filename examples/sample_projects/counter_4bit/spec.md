# 4-bit Synchronous Counter

## Requirements
- Module: `counter`
- Inputs: `clk`, `reset`
- Output: `count[3:0]`
- Reset is synchronous and active-high.
- On reset, count must become 0 on the next rising clock edge.
- Otherwise count increments by 1 every rising edge.
- The counter wraps from 15 to 0.
- No X/Z values are expected during normal operation.

## Verification Goals
1. Reset behavior
2. First increment after reset
3. Multi-cycle counting
4. 15-to-0 rollover
5. Reset asserted during counting
