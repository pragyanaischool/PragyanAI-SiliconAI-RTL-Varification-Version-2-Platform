# 8x16 Synchronous FIFO

## Requirements
- Module: `fifo_8x16`
- Inputs: `clk`, synchronous active-high `reset`, `wr_en`, `rd_en`, `din[7:0]`
- Outputs: `dout[7:0]`, `full`, `empty`, `count[4:0]`
- Capacity is 16 entries.
- Write when `wr_en && !full`.
- Read when `rd_en && !empty`.
- Preserve FIFO ordering.
- `empty` is true when count is 0; `full` is true when count is 16.
- Simultaneous valid read/write keeps occupancy unchanged.

## Verification Goals
Reset, empty read protection, single write/read, ordering, full condition, empty condition, and simultaneous read/write.
