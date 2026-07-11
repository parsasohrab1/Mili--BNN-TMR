// Mili BNN-TMR — CSR Register File (fixed latched control regs)

`include "mili_pkg.sv"

module reg_file (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               reg_cs,
  input  logic               reg_we,
  input  logic [5:0]         reg_addr,
  input  logic [31:0]        reg_wdata,
  output logic [31:0]        reg_rdata,
  output mili_pkg::pwr_mode_e dpm_req_mode,
  output logic               dpm_auto_en,
  input  mili_pkg::pwr_mode_e dpm_cur_mode,
  input  logic               dpm_busy,
  input  logic [11:0]        dpm_cur_freq,
  output logic               tmr_en,
  output logic               tmr_fault_inject,
  output logic [1:0]         tmr_fault_lane,
  input  logic               tmr_disagree,
  input  logic [15:0]        tmr_err_count,
  output logic               infer_start,
  output logic               infer_abort,
  input  logic               infer_busy,
  input  logic               infer_done,
  input  logic [23:0]        infer_cycles,
  output logic [31:0]        input_addr,
  output logic [31:0]        output_addr,
  output logic [31:0]        model_addr,
  output logic [15:0]        batch_size,
  input  logic [15:0]        ecc_corr_cnt,
  input  logic [15:0]        ecc_uncorr_cnt,
  output logic [5:0]         irq_en,
  input  logic [5:0]         irq_stat_in,
  output logic [5:0]         irq_stat
);

  logic [31:0] ctrl, status;
  logic [31:0] dpm_ctrl_r, tmr_ctrl_r, infer_ctrl_r;
  logic [31:0] irq_en_r, irq_stat_r, clk_cfg_r;

  assign ctrl[0]   = 1'b1;
  assign ctrl[31:1] = 32'h0;

  always_comb begin
    status    = 32'h0;
    status[0] = 1'b1;
    status[1] = ecc_uncorr_cnt != 0;
    status[2] = 1'b1;
    status[3] = tmr_en;
  end

  assign dpm_req_mode     = mili_pkg::pwr_mode_e'(dpm_ctrl_r[1:0]);
  assign dpm_auto_en      = dpm_ctrl_r[4];
  assign tmr_en           = tmr_ctrl_r[0];
  assign tmr_fault_inject = tmr_ctrl_r[1];
  assign tmr_fault_lane   = tmr_ctrl_r[3:2];
  assign infer_start      = infer_ctrl_r[0];
  assign infer_abort      = infer_ctrl_r[1];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dpm_ctrl_r   <= {30'h0, mili_pkg::PWR_NORMAL};
      tmr_ctrl_r   <= 32'h1;
      infer_ctrl_r <= '0;
      irq_en_r     <= '0;
      irq_stat_r   <= '0;
      input_addr   <= 32'h8000_0000;
      output_addr  <= 32'h81E0_0000;
      model_addr   <= 32'h8000_0000;
      batch_size   <= 16'd1;
      clk_cfg_r    <= 32'd400;
    end else begin
      irq_stat_r <= (irq_stat_r & ~reg_wdata[5:0]) | irq_stat_in;
      if (infer_done)
        infer_ctrl_r[0] <= 1'b0;

      if (reg_cs && reg_we) begin
        unique case (reg_addr)
          6'h04: dpm_ctrl_r   <= reg_wdata;
          6'h07: tmr_ctrl_r   <= reg_wdata;
          6'h09: infer_ctrl_r <= reg_wdata;
          6'h02: irq_en_r     <= reg_wdata[5:0];
          6'h03: irq_stat_r   <= irq_stat_r & ~reg_wdata[5:0];
          6'h06: clk_cfg_r    <= reg_wdata;
          6'h0B: input_addr   <= reg_wdata;
          6'h0C: output_addr  <= reg_wdata;
          6'h0D: model_addr   <= reg_wdata;
          6'h0E: batch_size   <= reg_wdata[15:0];
          default: ;
        endcase
      end
    end
  end

  assign irq_en   = irq_en_r;
  assign irq_stat = irq_stat_r;

  always_comb begin
    reg_rdata = 32'h0;
    if (reg_cs && !reg_we) begin
      unique case (reg_addr)
        6'h00: reg_rdata = ctrl;
        6'h01: reg_rdata = status;
        6'h02: reg_rdata = {26'h0, irq_en_r};
        6'h03: reg_rdata = {26'h0, irq_stat_r};
        6'h04: reg_rdata = dpm_ctrl_r;
        6'h05: reg_rdata = {16'h0, dpm_busy, 4'h0, dpm_cur_freq, dpm_cur_mode};
        6'h06: reg_rdata = clk_cfg_r;
        6'h07: reg_rdata = tmr_ctrl_r;
        6'h08: reg_rdata = {14'h0, tmr_err_count, tmr_disagree};
        6'h09: reg_rdata = infer_ctrl_r;
        6'h0A: reg_rdata = {5'h0, infer_cycles, infer_done, infer_busy};
        6'h0B: reg_rdata = input_addr;
        6'h0C: reg_rdata = output_addr;
        6'h0D: reg_rdata = model_addr;
        6'h0E: reg_rdata = {16'h0, batch_size};
        6'h10: reg_rdata = {ecc_uncorr_cnt, ecc_corr_cnt};
        default: reg_rdata = 32'h0;
      endcase
    end
  end

endmodule
