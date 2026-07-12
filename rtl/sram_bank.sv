// Mili BNN-TMR — SRAM Storage Bank
// Uses memory-compiler macro (sram_macro) with ECC sideband

`include "mili_pkg.sv"

module sram_bank #(
  parameter int DATA_W  = mili_pkg::DATA_WIDTH,
  parameter int ECC_W   = mili_pkg::ECC_WIDTH * mili_pkg::SUBWORD_COUNT,
  parameter int ADDR_W  = mili_pkg::ADDR_WIDTH,
  parameter int DEPTH   = mili_pkg::SRAM_SIM_DEPTH,
  parameter int READ_LATENCY = 2
) (
  input  logic                   clk,
  input  logic                   cs,
  input  logic                   we,
  input  logic [ADDR_W-1:0]      addr,
  input  logic [DATA_W-1:0]      wdata,
  input  logic [ECC_W-1:0]       wECC,
  output logic [DATA_W-1:0]      rdata,
  output logic [ECC_W-1:0]       rECC,
  output logic                   rdata_valid
);

  sram_macro #(
    .DATA_W(DATA_W),
    .ECC_W(ECC_W),
    .ADDR_W(ADDR_W),
    .DEPTH(DEPTH),
    .READ_LATENCY(READ_LATENCY)
  ) u_macro (
    .clk         (clk),
    .cs          (cs),
    .we          (we),
    .addr        (addr),
    .wdata       (wdata),
    .wECC        (wECC),
    .rdata       (rdata),
    .rECC        (rECC),
    .rdata_valid (rdata_valid)
  );

endmodule
