`timescale 1ns/1ps
module tb_counter;
  reg clk = 0;
  reg reset = 0;
  wire [3:0] count;

  counter uut(.clk(clk), .reset(reset), .count(count));
  always #5 clk = ~clk;

  initial begin
    $display("[TB] counter start");
    reset = 1; #10;
    if (count !== 4'd0) $display("[FAIL] reset count=%0d", count);
    reset = 0; #10;
    if (count !== 4'd1) $display("[FAIL] increment count=%0d", count);
    #140;
    if (count !== 4'd15) $display("[INFO] count before rollover=%0d", count);
    #10;
    if (count !== 4'd0) $display("[FAIL] rollover count=%0d", count);
    reset = 1; #10; reset = 0;
    if (count !== 4'd0) $display("[FAIL] mid-run reset count=%0d", count);
    $display("[TB] counter done count=%0d", count);
    $finish;
  end
endmodule
