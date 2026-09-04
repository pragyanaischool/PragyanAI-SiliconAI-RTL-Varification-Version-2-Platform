`timescale 1ns/1ps
module tb_fifo;
  reg clk=0,reset=0,wr_en=0,rd_en=0; reg [7:0] din; wire [7:0] dout; wire full,empty; wire [4:0] count;
  fifo_8x16 uut(.clk(clk),.reset(reset),.wr_en(wr_en),.rd_en(rd_en),.din(din),.dout(dout),.full(full),.empty(empty),.count(count));
  always #5 clk=~clk;
  task write_byte; input [7:0] v; begin @(negedge clk); din=v; wr_en=1; rd_en=0; @(negedge clk); wr_en=0; end endtask
  task read_byte; input [7:0] exp; begin @(negedge clk); rd_en=1; wr_en=0; @(posedge clk); #1; if(dout!==exp) $display("[FAIL] read=%h exp=%h",dout,exp); rd_en=0; end endtask
  integer i;
  initial begin
    $display("[TB] fifo start"); reset=1; repeat(2) @(posedge clk); reset=0;
    if(!empty || count!==0) $display("[FAIL] reset state");
    write_byte(8'h11); write_byte(8'h22);
    read_byte(8'h11); read_byte(8'h22);
    for(i=0;i<16;i=i+1) write_byte(i);
    if(!full || count!==16) $display("[FAIL] full count=%0d full=%b",count,full);
    write_byte(8'hEE);
    if(count!==16) $display("[FAIL] overflow accepted");
    $display("[TB] fifo done count=%0d",count); $finish;
  end
endmodule
