// Mili BNN-TMR — PCIe Gen4 Interface (MMIO bridge stub)
// Maps BAR0 accesses to internal CSR and SRAM

`include "mili_pkg.sv"

module pcie_if #(
  parameter int BAR_SIZE = 256 * 1024
) (
  input  logic               clk,
  input  logic               rst_n,
  // PCIe TLP-like simplified interface
  input  logic               rx_valid,
  input  logic               rx_we,
  input  logic [31:0]        rx_addr,
  input  logic [31:0]        rx_wdata,
  output logic               rx_ready,
  output logic               tx_valid,
  output logic [31:0]        tx_rdata,
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

  logic [31:0] csr_offset, sram_offset;
  assign csr_offset  = rx_addr - CSR_BASE;
  assign sram_offset = rx_addr - SRAM_BASE;

  logic is_csr, is_sram;
  assign is_csr  = rx_valid && (rx_addr >= CSR_BASE)  && (csr_offset < 32'h1000);
  assign is_sram = rx_valid && (rx_addr >= SRAM_BASE) && (sram_offset < 32'h200_0000);

  assign csr_cs    = is_csr;
  assign csr_we    = rx_we;
  assign csr_addr  = csr_offset[7:2];
  assign csr_wdata = rx_wdata;

  assign sram_req   = is_sram;
  assign sram_we    = rx_we;
  assign sram_addr  = sram_offset[24:0];
  assign sram_wdata = {8{rx_wdata}};

  assign rx_ready = (is_csr) || (is_sram && sram_ack);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_valid <= 1'b0;
      tx_rdata <= '0;
    end else begin
      tx_valid <= rx_valid && rx_ready;
      if (is_csr)
        tx_rdata <= csr_rdata;
      else if (is_sram)
        tx_rdata <= sram_rdata[31:0];
      else
        tx_rdata <= 32'h0;
    end
  end

endmodule
