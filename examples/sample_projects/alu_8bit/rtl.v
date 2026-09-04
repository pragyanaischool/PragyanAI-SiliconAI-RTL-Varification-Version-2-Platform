module alu8(input [7:0] a, input [7:0] b, input [2:0] op, output reg [7:0] y, output zero);
always @(*) begin
  case (op)
    3'b000: y = a + b;
    3'b001: y = a - b;
    3'b010: y = a & b;
    3'b011: y = a | b;
    3'b100: y = a ^ b;
    3'b101: y = a;
    3'b110: y = b;
    default: y = 8'h00;
  endcase
end
assign zero = (y == 8'h00);
endmodule
