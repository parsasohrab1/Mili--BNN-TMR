// Mili BNN-TMR — SRAM Controller with ECC
// 256-bit wide, 32 MB address space, SECDED per 64-bit sub-word

`include "mili_pkg.sv"

module sram_ctrl #(
  parameter int DATA_W  = mili_pkg::DATA_WIDTH,
  parameter int ADDR_W  = mili_pkg::ADDR_WIDTH,
  parameter int ECC_W   = mili_pkg::ECC_WIDTH,
  parameter int SUB_CNT = mili_pkg::SUBWORD_COUNT,
  parameter int DEPTH   = mili_pkg::SRAM_SIM_DEPTH
) (
  input  logic                   clk,
  input  logic                   rst_n,
  input  logic                   req,
  input  logic                   we,
  input  logic [ADDR_W-1:0]      addr,
  input  logic [DATA_W-1:0]      wdata,
  output logic [DATA_W-1:0]      rdata,
  output logic                   ack,
  output logic                   ready,
  output logic [15:0]            ecc_corr_cnt,
  output logic [15:0]            ecc_uncorr_cnt
);

  logic [DATA_W-1:0]              bank_rdata;
  logic [ECC_W*SUB_CNT-1:0]       bank_recc, bank_wecc;
  logic [DATA_W-1:0]              decoded_data;
  logic                           any_corrected, any_uncorr;

  sram_bank #(.DATA_W(DATA_W), .ECC_W(ECC_W*SUB_CNT), .ADDR_W(ADDR_W), .DEPTH(DEPTH)) u_bank (
    .clk   (clk),
    .cs    (req),
    .we    (we),
    .addr  (addr),
    .wdata (wdata),
    .wECC  (bank_wecc),
    .rdata (bank_rdata),
    .rECC  (bank_recc)
  );

  // Per-subword ECC encode on write, decode on read
  logic corrected_vec [SUB_CNT];
  logic uncorr_vec    [SUB_CNT];

  genvar s;
  generate
    for (s = 0; s < SUB_CNT; s++) begin : gen_ecc
      logic [ECC_W-1:0] enc_ecc;

      ecc_codec u_enc (
        .data_in       (we ? wdata[s*64 +: 64] : bank_rdata[s*64 +: 64]),
        .ecc_in        (bank_recc[s*ECC_W +: ECC_W]),
        .decode_en     (req && !we),
        .data_out      (decoded_data[s*64 +: 64]),
        .ecc_out       (enc_ecc),
        .corrected     (corrected_vec[s]),
        .uncorrectable (uncorr_vec[s])
      );

      assign bank_wecc[s*ECC_W +: ECC_W] = enc_ecc;
    end
  endgenerate

  assign any_corrected = |corrected_vec;
  assign any_uncorr    = |uncorr_vec;

  logic pending;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pending       <= 1'b0;
      ack           <= 1'b0;
      rdata         <= '0;
      ecc_corr_cnt  <= '0;
      ecc_uncorr_cnt<= '0;
    end else begin
      ack <= 1'b0;
      if (req && !pending) begin
        pending <= 1'b1;
      end else if (pending) begin
        ack     <= 1'b1;
        pending <= 1'b0;
        rdata   <= decoded_data;
        if (any_corrected)
          ecc_corr_cnt <= ecc_corr_cnt + 16'd1;
        if (any_uncorr)
          ecc_uncorr_cnt <= ecc_uncorr_cnt + 16'd1;
      end
    end
  end

  assign ready = 1'b1;

endmodule
