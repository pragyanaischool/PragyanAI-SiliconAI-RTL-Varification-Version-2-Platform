`timescale 1ns/1ps
module tb_alu8;
  reg [7:0] a,b; reg [2:0] op; wire [7:0] y; wire zero;
  alu8 uut(.a(a),.b(b),.op(op),.y(y),.zero(zero));

  task check; input [2:0] t_op; input [7:0] t_a,t_b,exp;
    begin a=t_a; b=t_b; op=t_op; #1;
      if (y !== exp || zero !== (exp==0))
        $display("[FAIL] op=%b a=%h b=%h y=%h zero=%b exp=%h",op,a,b,y,zero,exp);
      else $display("[PASS] op=%b a=%h b=%h y=%h",op,a,b,y);
    end
  endtask

  initial begin
    $display("[TB] alu start");
    check(3'b000,8'h05,8'h03,8'h08);
    check(3'b001,8'h05,8'h03,8'h02);
    check(3'b010,8'hF0,8'h0F,8'h00);
    check(3'b011,8'hF0,8'h0F,8'hFF);
    check(3'b100,8'hAA,8'hFF,8'h55);
    check(3'b101,8'h5A,8'h00,8'h5A);
    check(3'b110,8'h00,8'hA5,8'hA5);
    check(3'b111,8'hFF,8'hFF,8'h00);
    check(3'b000,8'hFF,8'h01,8'h00);
    $display("[TB] alu done"); $finish;
  end
endmodule
