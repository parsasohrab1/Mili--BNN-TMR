// Mili BNN-TMR — TMR Majority Voter
// Bit-wise majority voting across three redundant computation lanes

`include "mili_pkg.sv"

module tmr_voter #(
  parameter int WIDTH = mili_pkg::ACC_WIDTH
) (
  input  logic signed [WIDTH-1:0] lane0,
  input  logic signed [WIDTH-1:0] lane1,
  input  logic signed [WIDTH-1:0] lane2,
  output logic signed [WIDTH-1:0] voted,
  output logic                    disagree
);

  genvar i;
  generate
    for (i = 0; i < WIDTH; i++) begin : gen_vote
      assign voted[i] = mili_pkg::majority3(lane0[i], lane1[i], lane2[i]);
    end
  endgenerate

  assign disagree = (lane0 != lane1) || (lane1 != lane2) || (lane0 != lane2);

endmodule
