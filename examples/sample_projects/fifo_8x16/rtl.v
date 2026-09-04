module fifo_8x16(input clk,input reset,input wr_en,input rd_en,input [7:0] din,output reg [7:0] dout,output full,output empty,output reg [4:0] count);
reg [7:0] mem [0:15];
reg [3:0] wr_ptr, rd_ptr;
assign full = (count == 5'd16);
assign empty = (count == 5'd0);
always @(posedge clk) begin
  if (reset) begin wr_ptr<=0; rd_ptr<=0; count<=0; dout<=0; end
  else begin
    if (wr_en && !full) begin mem[wr_ptr] <= din; wr_ptr <= wr_ptr + 1'b1; end
    if (rd_en && !empty) begin dout <= mem[rd_ptr]; rd_ptr <= rd_ptr + 1'b1; end
    case ({wr_en && !full, rd_en && !empty})
      2'b10: count <= count + 1'b1;
      2'b01: count <= count - 1'b1;
      default: count <= count;
    endcase
  end
end
endmodule
