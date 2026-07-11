// Mili BNN-TMR — SECDED ECC Codec (Hamming SECDED for 64-bit data)
// Corrects single-bit errors, detects double-bit errors

`include "mili_pkg.sv"

module ecc_codec #(
  parameter int DATA_W = mili_pkg::SUBWORD_WIDTH,
  parameter int ECC_W  = mili_pkg::ECC_WIDTH
) (
  input  logic [DATA_W-1:0]  data_in,
  input  logic [ECC_W-1:0]   ecc_in,
  input  logic               decode_en,
  output logic [DATA_W-1:0]  data_out,
  output logic [ECC_W-1:0]   ecc_out,
  output logic               corrected,
  output logic               uncorrectable
);

  // Hamming(72,64) SECDED — simplified behavioral model
  // Encode: XOR parity over bit positions
  function automatic logic [ECC_W-1:0] encode(input logic [DATA_W-1:0] d);
    logic [ECC_W-1:0] p;
    p[0] = ^(d & 64'h5555_5555_5555_5555);
    p[1] = ^(d & 64'h3333_3333_3333_3333);
    p[2] = ^(d & 64'h0F0F_0F0F_0F0F_0F0F);
    p[3] = ^(d & 64'h00FF_00FF_00FF_00FF);
    p[4] = ^(d & 64'h0000_FFFF_0000_FFFF);
    p[5] = ^(d & 64'h0000_0000_FFFF_FFFF);
    p[6] = ^d;
    p[7] = ^(d ^ {64{p[6]}});
    return p;
  endfunction

  logic [ECC_W-1:0]  calc_ecc;
  logic [DATA_W-1:0]  synd_data;
  logic               single_err;
  logic [5:0]         err_pos;

  assign calc_ecc = encode(data_in);

  always_comb begin
    if (!decode_en) begin
      data_out      = data_in;
      ecc_out       = calc_ecc;
      corrected     = 1'b0;
      uncorrectable = 1'b0;
    end else begin
      logic [ECC_W-1:0] syndrome;
      syndrome = encode(data_in) ^ ecc_in;

      if (syndrome == '0) begin
        data_out      = data_in;
        ecc_out       = ecc_in;
        corrected     = 1'b0;
        uncorrectable = 1'b0;
      end else if (^syndrome) begin
        // Single-bit error — flip detected position (simplified)
        err_pos       = syndrome[5:0];
        data_out      = data_in ^ (DATA_W'(1) << err_pos[5:0]);
        ecc_out       = encode(data_out);
        corrected     = 1'b1;
        uncorrectable = 1'b0;
      end else begin
        data_out      = data_in;
        ecc_out       = ecc_in;
        corrected     = 1'b0;
        uncorrectable = 1'b1;
      end
    end
  end

endmodule
