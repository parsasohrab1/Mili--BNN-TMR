// Mili BNN-TMR — 32 MB SRAM memory-compiler wrapper
// Synthesis: define MILI_USE_SRAM_MACRO and bind foundry .lib/.lef
// Simulation: behavioral model with configurable read latency

`include "mili_pkg.sv"

module sram_macro #(
  parameter int DATA_W  = mili_pkg::DATA_WIDTH,
  parameter int ECC_W   = mili_pkg::ECC_WIDTH * mili_pkg::SUBWORD_COUNT,
  parameter int ADDR_W  = mili_pkg::ADDR_WIDTH,
  parameter int DEPTH   = mili_pkg::SRAM_SIM_DEPTH,
  parameter int READ_LATENCY = 2   // macro tCD + routing (ns → cycles @ 400 MHz)
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

  localparam int MEM_ADDR_W = $clog2(DEPTH);

`ifdef MILI_USE_SRAM_MACRO
  // Foundry 14nm 32 MB SRAM macro (blackbox for synthesis)
  /* verilator lint_off PINMISSING */
  sram_32mb_14nm #(
    .DATA_W(DATA_W), .ADDR_W(MEM_ADDR_W)
  ) u_macro (
    .clk   (clk),
    .csb   (~cs),
    .web   (~we),
    .addr  (addr[MEM_ADDR_W-1:0]),
    .din   ({wECC, wdata}),
    .dout  ({rECC, rdata})
  );
  /* verilator lint_on PINMISSING */
  assign rdata_valid = cs && !we;
`else
  logic [DATA_W-1:0]  mem_data [DEPTH];
  logic [ECC_W-1:0]   mem_ecc  [DEPTH];
  logic [MEM_ADDR_W-1:0] mem_addr;

  logic [DATA_W-1:0]  pipe_data [READ_LATENCY];
  logic [ECC_W-1:0]   pipe_ecc  [READ_LATENCY];
  logic               pipe_valid[READ_LATENCY];

  assign mem_addr = addr[MEM_ADDR_W-1:0];

  always_ff @(posedge clk) begin
    if (cs && we) begin
      mem_data[mem_addr] <= wdata;
      mem_ecc[mem_addr]  <= wECC;
    end
  end

  integer i;
  always_ff @(posedge clk) begin
    pipe_data[0]  <= mem_data[mem_addr];
    pipe_ecc[0]   <= mem_ecc[mem_addr];
    pipe_valid[0] <= cs && !we;
    for (i = 1; i < READ_LATENCY; i++) begin
      pipe_data[i]  <= pipe_data[i-1];
      pipe_ecc[i]   <= pipe_ecc[i-1];
      pipe_valid[i] <= pipe_valid[i-1];
    end
  end

  assign rdata       = pipe_valid[READ_LATENCY-1] ? pipe_data[READ_LATENCY-1] : '0;
  assign rECC        = pipe_valid[READ_LATENCY-1] ? pipe_ecc[READ_LATENCY-1]  : '0;
  assign rdata_valid = pipe_valid[READ_LATENCY-1];
`endif

endmodule
