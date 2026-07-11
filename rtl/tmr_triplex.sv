// Mili BNN-TMR — TMR Triplex Wrapper
// Three parallel systolic lanes with majority voter per PE output

`include "mili_pkg.sv"

module tmr_triplex #(
  parameter int ROWS = mili_pkg::PE_ROWS,
  parameter int COLS = mili_pkg::PE_COLS,
  parameter int ACC_W = mili_pkg::ACC_WIDTH
) (
  input  logic                        clk,
  input  logic                        rst_n,
  input  logic                        tmr_en,
  input  logic                        fault_inject,
  input  logic [1:0]                  fault_lane,
  input  logic                        start,
  input  logic [ROWS-1:0]             a_row [ROWS],
  input  logic [COLS-1:0]             w_col [COLS],
  output logic                        done,
  output logic signed [ACC_W-1:0]     result [ROWS][COLS],
  output logic                        disagree,
  output logic [15:0]                 err_count
);

  logic signed [ACC_W-1:0] lane_result [3][ROWS][COLS];
  logic                  lane_done [3];
  logic                  any_disagree;

  genvar lane;
  generate
    for (lane = 0; lane < 3; lane++) begin : gen_lane
      systolic_array #(.ROWS(ROWS), .COLS(COLS), .ACC_W(ACC_W)) u_systolic (
        .clk    (clk),
        .rst_n  (rst_n),
        .start  (start),
        .a_row  (a_row),
        .w_col  (w_col),
        .done   (lane_done[lane]),
        .result (lane_result[lane])
      );
    end
  endgenerate

  assign done = lane_done[0] & lane_done[1] & lane_done[2];

  logic signed [ACC_W-1:0] voted_pe [ROWS][COLS];
  logic                    pe_disagree [ROWS][COLS];

  genvar r, c;
  generate
    for (r = 0; r < ROWS; r++) begin : gen_vr
      for (c = 0; c < COLS; c++) begin : gen_vc
        logic signed [ACC_W-1:0] l0, l1, l2;

        assign l0 = (fault_inject && fault_lane == 2'd0)
                      ? ~lane_result[0][r][c] : lane_result[0][r][c];
        assign l1 = (fault_inject && fault_lane == 2'd1)
                      ? ~lane_result[1][r][c] : lane_result[1][r][c];
        assign l2 = (fault_inject && fault_lane == 2'd2)
                      ? ~lane_result[2][r][c] : lane_result[2][r][c];

        tmr_voter #(.WIDTH(ACC_W)) u_voter (
          .lane0     (tmr_en ? l0 : lane_result[0][r][c]),
          .lane1     (tmr_en ? l1 : lane_result[0][r][c]),
          .lane2     (tmr_en ? l2 : lane_result[0][r][c]),
          .voted     (voted_pe[r][c]),
          .disagree  (pe_disagree[r][c])
        );
      end
    end
  endgenerate

  assign any_disagree = |pe_disagree;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      disagree  <= 1'b0;
      err_count <= '0;
    end else if (done) begin
      disagree <= any_disagree;
      if (any_disagree)
        err_count <= err_count + 16'd1;
      for (int i = 0; i < ROWS; i++)
        for (int j = 0; j < COLS; j++)
          result[i][j] <= voted_pe[i][j];
    end
  end

endmodule
