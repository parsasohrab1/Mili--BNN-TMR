// Mili BNN-TMR — PCIe Gen4 Interface
// Stack: PHY (Gen4 LTSSM) → TLP → MMIO bridge (CSR + SRAM)
// SIM_DIRECT=1: bypass PHY/TLP for Verilator host port (tb_top)

`include "mili_pkg.sv"

module pcie_if #(
  parameter int  BAR_SIZE    = 256 * 1024,
  parameter bit  SIM_DIRECT  = 1'b1
) (
  input  logic               clk,
  input  logic               rst_n,
  // Simplified host port (Verilator / DMA shim)
  input  logic               rx_valid,
  input  logic               rx_we,
  input  logic [31:0]        rx_addr,
  input  logic [31:0]        rx_wdata,
  output logic               rx_ready,
  output logic               tx_valid,
  output logic [31:0]        tx_rdata,
  // PCIe Gen4 serial (production)
  input  logic               pcie_refclk,
  input  logic [3:0]         pcie_rxp,
  input  logic [3:0]         pcie_rxn,
  output logic [3:0]         pcie_txp,
  output logic [3:0]         pcie_txn,
  output logic               pcie_link_up,
  // Internal bus
  output logic               csr_cs,
  output logic               csr_we,
  output logic [5:0]         csr_addr,
  output logic [31:0]        csr_wdata,
  input  logic [31:0]        csr_rdata,
  output logic               sram_req,
  output logic               sram_we,
  output logic [24:0]        sram_addr,
  output logic [255:0]       sram_wdata,
  input  logic [255:0]       sram_rdata,
  input  logic               sram_ack
);

  localparam logic [31:0] CSR_BASE  = 32'h4000_0000;
  localparam logic [31:0] SRAM_BASE = 32'h8000_0000;

  // ── PHY + TLP (production path) ─────────────────────────────
  logic               link_up;
  logic               tlp_host_rx_valid, tlp_host_rx_we;
  logic [31:0]        tlp_host_rx_addr, tlp_host_rx_wdata;
  logic               tlp_host_rx_ready;
  logic               tlp_host_tx_valid;
  logic [31:0]        tlp_host_tx_rdata;
  logic               phy_tx_valid, phy_tx_ready;
  logic [31:0]        phy_tx_data, phy_rx_data;
  logic               phy_rx_valid, phy_rx_ready;

  if (!SIM_DIRECT) begin : gen_pcie_stack
    pcie_phy_gen4 u_phy (
      .clk        (clk),
      .rst_n      (rst_n),
      .refclk     (pcie_refclk),
      .rxp        (pcie_rxp),
      .rxn        (pcie_rxn),
      .txp        (pcie_txp),
      .txn        (pcie_txn),
      .link_up    (link_up),
      .ltssm_state(),
      .tx_valid   (phy_tx_valid),
      .tx_data    (phy_tx_data),
      .tx_ready   (phy_tx_ready),
      .rx_valid   (phy_rx_valid),
      .rx_data    (phy_rx_data),
      .rx_ready   (phy_rx_ready)
    );

    pcie_tlp u_tlp (
      .clk            (clk),
      .rst_n          (rst_n),
      .link_up        (link_up),
      .phy_rx_valid   (phy_rx_valid),
      .phy_rx_data    (phy_rx_data),
      .phy_rx_ready   (phy_rx_ready),
      .phy_tx_valid   (phy_tx_valid),
      .phy_tx_data    (phy_tx_data),
      .phy_tx_ready   (phy_tx_ready),
      .host_rx_valid  (tlp_host_rx_valid),
      .host_rx_we     (tlp_host_rx_we),
      .host_rx_addr   (tlp_host_rx_addr),
      .host_rx_wdata  (tlp_host_rx_wdata),
      .host_rx_ready  (tlp_host_rx_ready),
      .host_tx_valid  (tlp_host_tx_valid),
      .host_tx_rdata  (tlp_host_tx_rdata)
    );
  end else begin
    assign link_up = 1'b0;
    assign pcie_txp = '0;
    assign pcie_txn = '1;
  end

  assign pcie_link_up = SIM_DIRECT ? 1'b0 : link_up;

  // Mux host requests: sim-direct vs TLP-decoded
  logic        mux_rx_valid, mux_rx_we;
  logic [31:0] mux_rx_addr, mux_rx_wdata;

  assign mux_rx_valid = SIM_DIRECT ? rx_valid : tlp_host_rx_valid;
  assign mux_rx_we    = SIM_DIRECT ? rx_we    : tlp_host_rx_we;
  assign mux_rx_addr  = SIM_DIRECT ? rx_addr  : tlp_host_rx_addr;
  assign mux_rx_wdata = SIM_DIRECT ? rx_wdata : tlp_host_rx_wdata;
  assign tlp_host_rx_ready = SIM_DIRECT ? 1'b0 : rx_ready;

  // ── MMIO decode ─────────────────────────────────────────────
  logic [31:0] csr_offset, sram_offset;
  assign csr_offset  = mux_rx_addr - CSR_BASE;
  assign sram_offset = mux_rx_addr - SRAM_BASE;

  logic is_csr, is_sram;
  assign is_csr  = mux_rx_valid && (mux_rx_addr >= CSR_BASE)  && (csr_offset < 32'h1000);
  assign is_sram = mux_rx_valid && (mux_rx_addr >= SRAM_BASE) && (sram_offset < 32'h200_0000);

  assign csr_cs    = is_csr;
  assign csr_we    = mux_rx_we;
  assign csr_addr  = csr_offset[7:2];
  assign csr_wdata = mux_rx_wdata;

  assign sram_req   = is_sram;
  assign sram_we    = mux_rx_we;
  assign sram_addr  = sram_offset[24:0];
  assign sram_wdata = {8{mux_rx_wdata}};

  assign rx_ready = (is_csr) || (is_sram && sram_ack);

  logic [31:0] read_data;
  assign read_data = is_csr ? csr_rdata : (is_sram ? sram_rdata[31:0] : 32'h0);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_valid <= 1'b0;
      tx_rdata <= '0;
      tlp_host_tx_valid <= 1'b0;
      tlp_host_tx_rdata <= '0;
    end else begin
      tx_valid <= mux_rx_valid && rx_ready;
      tx_rdata <= read_data;
      tlp_host_tx_valid <= mux_rx_valid && rx_ready;
      tlp_host_tx_rdata <= read_data;
    end
  end

endmodule
