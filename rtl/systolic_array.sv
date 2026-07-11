// Mili BNN-TMR — 8×8 Systolic Array (64 PEs)
// Wavefront matrix multiply for BNN binary MAC operations

`include "mili_pkg.sv"

module systolic_array #(
  parameter int ROWS = mili_pkg::PE_ROWS,
  parameter int COLS = mili_pkg::PE_COLS,
  parameter int ACC_W = mili_pkg::ACC_WIDTH
) (
  input  logic                        clk,
  input  logic                        rst_n,
  input  logic                        start,
  input  logic [ROWS-1:0]             a_row [ROWS],
  input  logic [COLS-1:0]             w_col [COLS],
  output logic                        done,
  output logic signed [ACC_W-1:0]     result [ROWS][COLS]
);

  localparam int WAVE_CYCLES = ROWS + COLS - 1;

  logic                        pe_en;
  logic                        pe_clear;
  logic [ROWS-1:0]             h_a [ROWS][COLS+1];
  logic [COLS-1:0]             h_w [ROWS+1][COLS];
  logic signed [ACC_W-1:0]     pe_acc [ROWS][COLS];

  logic [$clog2(WAVE_CYCLES+1)-1:0] cycle_cnt;
  logic                           computing;

  // Drive left column with activations, top row with weights
  genvar r, c;
  generate
    for (r = 0; r < ROWS; r++) begin : gen_a_in
      assign h_a[r][0] = computing ? a_row[r] : 1'b0;
    end
    for (c = 0; c < COLS; c++) begin : gen_w_in
      assign h_w[0][c] = computing ? w_col[c] : 1'b0;
    end

    for (r = 0; r < ROWS; r++) begin : gen_row
      for (c = 0; c < COLS; c++) begin : gen_col
        pe #(.ACC_W(ACC_W)) u_pe (
          .clk     (clk),
          .rst_n   (rst_n),
          .en      (pe_en),
          .clear   (pe_clear),
          .a_in    (h_a[r][c]),
          .w_in    (h_w[r][c]),
          .a_out   (h_a[r][c+1]),
          .w_out   (h_w[r+1][c]),
          .acc_out (pe_acc[r][c])
        );
      end
    end
  endgenerate

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      computing <= 1'b0;
      cycle_cnt <= '0;
      done      <= 1'b0;
    end else begin
      done <= 1'b0;
      if (start && !computing) begin
        computing <= 1'b1;
        cycle_cnt <= '0;
      end else if (computing) begin
        if (cycle_cnt == WAVE_CYCLES - 1) begin
          computing <= 1'b0;
          done      <= 1'b1;
        end else begin
          cycle_cnt <= cycle_cnt + 1'b1;
        end
      end
    end
  end

  assign pe_en    = computing;
  assign pe_clear = (cycle_cnt == '0) && computing;

  always_ff @(posedge clk) begin
    if (done) begin
      for (int i = 0; i < ROWS; i++)
        for (int j = 0; j < COLS; j++)
          result[i][j] <= pe_acc[i][j];
    end
  end

endmodule
