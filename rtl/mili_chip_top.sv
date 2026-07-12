// Mili BNN-TMR — Top-Level Chip Integration

`include "mili_pkg.sv"

module mili_chip_top (
  input  logic        clk_sys,
  input  logic        clk_io,
  input  logic        rst_n,
  // PCIe
  input  logic        pcie_rx_valid,
  input  logic        pcie_rx_we,
  input  logic [31:0] pcie_rx_addr,
  input  logic [31:0] pcie_rx_wdata,
  output logic        pcie_rx_ready,
  output logic        pcie_tx_valid,
  output logic [31:0] pcie_tx_rdata,
  input  logic        pcie_refclk,
  input  logic [3:0]  pcie_rxp,
  input  logic [3:0]  pcie_rxn,
  output logic [3:0]  pcie_txp,
  output logic [3:0]  pcie_txn,
  // SPI
  input  logic        spi_sck,
  input  logic        spi_cs_n,
  input  logic        spi_mosi,
  output logic        spi_miso,
  // I2C
  inout  wire         i2c_scl,
  inout  wire         i2c_sda,
  // UART
  output logic        uart_tx,
  input  logic        uart_rx,
  // IRQ to host
  output logic        irq
);

  // ── Register bus (arbiter: PCIe > SPI > I2C > UART) ──────────
  logic        reg_cs, reg_we;
  logic [5:0]  reg_addr;
  logic [31:0] reg_wdata, reg_rdata;

  logic        pcie_csr_cs, pcie_csr_we;
  logic [5:0]  pcie_csr_addr;
  logic [31:0] pcie_csr_wdata;
  logic        spi_reg_cs, spi_reg_we;
  logic [5:0]  spi_reg_addr;
  logic [31:0] spi_reg_wdata;

  assign reg_cs    = pcie_csr_cs | spi_reg_cs;
  assign reg_we    = pcie_csr_cs ? pcie_csr_we : spi_reg_we;
  assign reg_addr  = pcie_csr_cs ? pcie_csr_addr  : spi_reg_addr;
  assign reg_wdata = pcie_csr_cs ? pcie_csr_wdata : spi_reg_wdata;

  // ── DPM ──────────────────────────────────────────────────────
  mili_pkg::pwr_mode_e dpm_req, dpm_cur;
  logic dpm_auto, dpm_busy;
  logic [11:0] dpm_freq;
  logic clk_gate;

  // ── TMR / Inference ──────────────────────────────────────────
  logic        tmr_en, tmr_fault_inj, tmr_disagree;
  logic [1:0]  tmr_fault_lane;
  logic [15:0] tmr_err_cnt;
  logic        infer_start, infer_abort, infer_busy, infer_done;
  logic [23:0] infer_cycles;
  logic [31:0] input_addr, output_addr, model_addr;
  logic [15:0] batch_size;
  logic [5:0]  irq_en, irq_stat;

  // ── SRAM ─────────────────────────────────────────────────────
  logic        sram_req, sram_we, sram_ack;
  logic [24:0] sram_addr;
  logic [255:0] sram_wdata, sram_rdata;
  logic [15:0] ecc_corr, ecc_uncorr;

  // ── Systolic inputs (simplified: use batch_size LSBs) ────────
  logic [7:0] a_row [8];
  logic [7:0] w_col [8];
  logic signed [31:0] tmr_result [8][8];
  logic        tmr_done;

  genvar gi;
  generate
    for (gi = 0; gi < 8; gi++) begin
      assign a_row[gi] = 8'(batch_size + gi);
      assign w_col[gi] = 8'(batch_size ^ (gi * 3));
    end
  endgenerate

  // ── Register File ────────────────────────────────────────────
  reg_file u_regs (
    .clk            (clk_io),
    .rst_n          (rst_n),
    .reg_cs         (reg_cs),
    .reg_we         (reg_we),
    .reg_addr       (reg_addr),
    .reg_wdata      (reg_wdata),
    .reg_rdata      (reg_rdata),
    .dpm_req_mode   (dpm_req),
    .dpm_auto_en    (dpm_auto),
    .dpm_cur_mode   (dpm_cur),
    .dpm_busy       (dpm_busy),
    .dpm_cur_freq   (dpm_freq),
    .tmr_en         (tmr_en),
    .tmr_fault_inject(tmr_fault_inj),
    .tmr_fault_lane (tmr_fault_lane),
    .tmr_disagree   (tmr_disagree),
    .tmr_err_count  (tmr_err_cnt),
    .infer_start    (infer_start),
    .infer_abort    (infer_abort),
    .infer_busy     (infer_busy),
    .infer_done     (infer_done),
    .infer_cycles   (infer_cycles),
    .input_addr     (input_addr),
    .output_addr    (output_addr),
    .model_addr     (model_addr),
    .batch_size     (batch_size),
    .ecc_corr_cnt   (ecc_corr),
    .ecc_uncorr_cnt (ecc_uncorr),
    .irq_en         (irq_en),
    .irq_stat_in    (irq_stat),
    .irq_stat       (irq_stat)
  );

  // ── DPM Controller ───────────────────────────────────────────
  dpm_ctrl u_dpm (
    .clk         (clk_io),
    .rst_n       (rst_n),
    .auto_en     (dpm_auto),
    .req_mode    (dpm_req),
    .batch_size  (batch_size),
    .queue_depth (8'd0),
    .cur_mode    (dpm_cur),
    .cur_freq_mhz(dpm_freq),
    .busy        (dpm_busy),
    .clk_gate_en (clk_gate)
  );

  // ── TMR Triplex + Systolic ───────────────────────────────────
  logic gated_clk;
  assign gated_clk = clk_sys & clk_gate;

  tmr_triplex u_tmr (
    .clk           (gated_clk),
    .rst_n         (rst_n),
    .tmr_en        (tmr_en),
    .fault_inject  (tmr_fault_inj),
    .fault_lane    (tmr_fault_lane),
    .start         (infer_start),
    .a_row         (a_row),
    .w_col         (w_col),
    .done          (tmr_done),
    .result        (tmr_result),
    .disagree      (tmr_disagree),
    .err_count     (tmr_err_cnt)
  );

  // Inference sequencer
  always_ff @(posedge gated_clk or negedge rst_n) begin
    if (!rst_n) begin
      infer_busy   <= 1'b0;
      infer_done   <= 1'b0;
      infer_cycles <= '0;
    end else begin
      infer_done <= 1'b0;
      if (infer_start && !infer_busy) begin
        infer_busy   <= 1'b1;
        infer_cycles <= '0;
      end else if (infer_busy) begin
        infer_cycles <= infer_cycles + 1'b1;
        if (tmr_done || infer_abort) begin
          infer_busy <= 1'b0;
          infer_done <= tmr_done;
        end
      end
    end
  end

  // ── SRAM Controller ──────────────────────────────────────────
  sram_ctrl u_sram (
    .clk           (clk_sys),
    .rst_n         (rst_n),
    .req           (sram_req),
    .we            (sram_we),
    .addr          (sram_addr),
    .wdata         (sram_wdata),
    .rdata         (sram_rdata),
    .ack           (sram_ack),
    .ready         (),
    .ecc_corr_cnt  (ecc_corr),
    .ecc_uncorr_cnt(ecc_uncorr)
  );

  // ── PCIe Interface ───────────────────────────────────────────
  pcie_if u_pcie (
    .clk         (clk_io),
    .rst_n       (rst_n),
    .rx_valid    (pcie_rx_valid),
    .rx_we       (pcie_rx_we),
    .rx_addr     (pcie_rx_addr),
    .rx_wdata    (pcie_rx_wdata),
    .rx_ready    (pcie_rx_ready),
    .tx_valid    (pcie_tx_valid),
    .tx_rdata    (pcie_tx_rdata),
    .pcie_refclk (pcie_refclk),
    .pcie_rxp    (pcie_rxp),
    .pcie_rxn    (pcie_rxn),
    .pcie_txp    (pcie_txp),
    .pcie_txn    (pcie_txn),
    .pcie_link_up(),
    .csr_cs      (pcie_csr_cs),
    .csr_we      (pcie_csr_we),
    .csr_addr    (pcie_csr_addr),
    .csr_wdata   (pcie_csr_wdata),
    .csr_rdata   (reg_rdata),
    .sram_req    (sram_req),
    .sram_we     (sram_we),
    .sram_addr   (sram_addr),
    .sram_wdata  (sram_wdata),
    .sram_rdata  (sram_rdata),
    .sram_ack    (sram_ack)
  );

  // ── SPI Interface ────────────────────────────────────────────
  spi_if u_spi (
    .clk       (clk_io),
    .rst_n     (rst_n),
    .spi_sck   (spi_sck),
    .spi_cs_n  (spi_cs_n),
    .spi_mosi  (spi_mosi),
    .spi_miso  (spi_miso),
    .reg_cs    (spi_reg_cs),
    .reg_we    (spi_reg_we),
    .reg_addr  (spi_reg_addr),
    .reg_wdata (spi_reg_wdata),
    .reg_rdata (reg_rdata),
    .dma_req   (),
    .dma_we    (),
    .dma_addr  (),
    .dma_wdata (),
    .dma_rdata (32'h0),
    .dma_ack   (1'b0)
  );

  // ── I2C / UART (independent register access) ─────────────────
  i2c_if u_i2c (
    .clk, .rst_n, .i2c_scl, .i2c_sda,
    .reg_cs(), .reg_we(), .reg_addr(), .reg_wdata(), .reg_rdata
  );

  uart_if u_uart (
    .clk(clk_io), .rst_n, .uart_tx, .uart_rx,
    .reg_cs(), .reg_we(), .reg_addr(), .reg_wdata(), .reg_rdata
  );

  // ── IRQ ──────────────────────────────────────────────────────
  assign irq = |(irq_stat & irq_en);

endmodule
