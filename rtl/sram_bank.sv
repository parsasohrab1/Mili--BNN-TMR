// Mili BNN-TMR — SRAM Storage Bank
// Parameterized depth; use SRAM_SIM_DEPTH for fast Verilator runs

`include "mili_pkg.sv"

module sram_bank #(
  parameter int DATA_W  = mili_pkg::DATA_WIDTH,
  parameter int ECC_W   = mili_pkg::ECC_WIDTH * mili_pkg::SUBWORD_COUNT,
  parameter int ADDR_W  = mili_pkg::ADDR_WIDTH,
  parameter int DEPTH   = mili_pkg::SRAM_SIM_DEPTH
) (
  input  logic                   clk,
  input  logic                   cs,
  input  logic                   we,
  input  logic [ADDR_W-1:0]      addr,
  input  logic [DATA_W-1:0]      wdata,
  input  logic [ECC_W-1:0]       wECC,
  output logic [DATA_W-1:0]      rdata,
  output logic [ECC_W-1:0]       rECC
);

  localparam int MEM_ADDR_W = $clog2(DEPTH);

  logic [DATA_W-1:0]  mem_data  [DEPTH];
  logic [ECC_W-1:0]   mem_ecc   [DEPTH];

  logic [MEM_ADDR_W-1:0] mem_addr;
  assign mem_addr = addr[MEM_ADDR_W-1:0];

  always_ff @(posedge clk) begin
    if (cs && we)
      mem_data[mem_addr] <= wdata;
    if (cs && we)
      mem_ecc[mem_addr]  <= wECC;
  end

  assign rdata = cs ? mem_data[mem_addr] : '0;
  assign rECC  = cs ? mem_ecc[mem_addr]  : '0;

endmodule
