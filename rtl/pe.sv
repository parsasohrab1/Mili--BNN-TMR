// Mili BNN-TMR — Processing Element (BNN MAC)
// Computes: acc += sign(a) * sign(w), propagates a right and w down

`include "mili_pkg.sv"

module pe #(
  parameter int ACC_W = mili_pkg::ACC_WIDTH
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             en,
  input  logic             clear,
  input  logic             a_in,
  input  logic             w_in,
  output logic             a_out,
  output logic             w_out,
  output logic signed [ACC_W-1:0] acc_out
);

  logic signed [ACC_W-1:0] acc;
  logic signed [ACC_W-1:0] prod;

  assign prod = mili_pkg::bnn_sign(a_in) * mili_pkg::bnn_sign(w_in);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      acc    <= '0;
      a_out  <= '0;
      w_out  <= '0;
    end else if (en) begin
      a_out <= a_in;
      w_out <= w_in;
      if (clear)
        acc <= prod;
      else
        acc <= acc + prod;
    end
  end

  assign acc_out = acc;

endmodule
