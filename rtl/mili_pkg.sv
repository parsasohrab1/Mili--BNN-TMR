// Mili BNN-TMR — Global parameters and type definitions

package mili_pkg;

  parameter int PE_ROWS        = 8;
  parameter int PE_COLS        = 8;
  parameter int PE_COUNT       = PE_ROWS * PE_COLS;
  parameter int ACC_WIDTH      = 32;
  parameter int DATA_WIDTH     = 256;
  parameter int SUBWORD_WIDTH  = 64;
  parameter int SUBWORD_COUNT  = DATA_WIDTH / SUBWORD_WIDTH;
  parameter int ECC_WIDTH      = 8;
  parameter int ADDR_WIDTH       = 25;   // 32 MB
  parameter int SRAM_DEPTH       = 1 << ADDR_WIDTH; // production
  parameter int SRAM_SIM_DEPTH   = 4096; // fast simulation
  parameter int CLK_FREQ_NORM    = 400;
  parameter int CLK_FREQ_TURBO   = 800;
  parameter int CLK_FREQ_IDLE    = 100;

  typedef enum logic [1:0] {
    PWR_SLEEP  = 2'b00,
    PWR_IDLE   = 2'b01,
    PWR_NORMAL = 2'b10,
    PWR_TURBO  = 2'b11
  } pwr_mode_e;

  typedef enum logic [1:0] {
    ST_IDLE    = 2'b00,
    ST_LOAD    = 2'b01,
    ST_COMPUTE = 2'b10,
    ST_STORE   = 2'b11
  } infer_state_e;

  // BNN sign encoding: 0 → -1, 1 → +1
  function automatic logic signed [ACC_WIDTH-1:0] bnn_sign(input logic bit_val);
    return bit_val ? ACC_WIDTH'(1) : ACC_WIDTH'(-1);
  endfunction

  function automatic logic majority3(input logic a, b, c);
    return (a & b) | (a & c) | (b & c);
  endfunction

endpackage
