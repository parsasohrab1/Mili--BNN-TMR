// Mili BNN-TMR — Dynamic Power Management Controller (DVFS)
// States: Sleep / Idle / Normal / Turbo

`include "mili_pkg.sv"

module dpm_ctrl #(
  parameter int SWITCH_CYCLES = 40  // < 100us @ 400MHz
) (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               auto_en,
  input  mili_pkg::pwr_mode_e req_mode,
  input  logic [15:0]        batch_size,
  input  logic [7:0]         queue_depth,
  output mili_pkg::pwr_mode_e cur_mode,
  output logic [11:0]        cur_freq_mhz,
  output logic               busy,
  output logic               clk_gate_en
);

  mili_pkg::pwr_mode_e target_mode;
  mili_pkg::pwr_mode_e next_mode;
  logic [$clog2(SWITCH_CYCLES+1)-1:0] switch_cnt;
  logic                               switching;

  function automatic mili_pkg::pwr_mode_e auto_select(
    input logic [15:0] batch,
    input logic [7:0]  qdepth
  );
    if (batch == 0 && qdepth == 0)
      return PWR_SLEEP;
    else if (batch <= 4 && qdepth < 2)
      return PWR_IDLE;
    else if (batch >= 32 || qdepth >= 8)
      return PWR_TURBO;
    else
      return PWR_NORMAL;
  endfunction

  assign target_mode = auto_en ? auto_select(batch_size, queue_depth) : req_mode;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cur_mode    <= PWR_NORMAL;
      switching   <= 1'b0;
      switch_cnt  <= '0;
      busy        <= 1'b0;
    end else begin
      if (!switching && target_mode != cur_mode) begin
        switching  <= 1'b1;
        busy       <= 1'b1;
        switch_cnt <= '0;
      end else if (switching) begin
        if (switch_cnt == SWITCH_CYCLES - 1) begin
          cur_mode   <= target_mode;
          switching  <= 1'b0;
          busy       <= 1'b0;
        end else begin
          switch_cnt <= switch_cnt + 1'b1;
        end
      end
    end
  end

  always_comb begin
    unique case (cur_mode)
      PWR_SLEEP:  begin cur_freq_mhz = 12'd0;   clk_gate_en = 1'b0; end
      PWR_IDLE:   begin cur_freq_mhz = 12'd100; clk_gate_en = 1'b1; end
      PWR_NORMAL: begin cur_freq_mhz = 12'd400; clk_gate_en = 1'b1; end
      PWR_TURBO:  begin cur_freq_mhz = 12'd800; clk_gate_en = 1'b1; end
      default:    begin cur_freq_mhz = 12'd400; clk_gate_en = 1'b1; end
    endcase
  end

endmodule
