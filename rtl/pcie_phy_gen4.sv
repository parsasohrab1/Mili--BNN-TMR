// Mili BNN-TMR — PCIe Gen4 behavioral PHY (LTSSM + lane model)
// Production: replace with hard PHY macro (e.g. Synopsys DWC PCIe Gen4)

`include "mili_pkg.sv"

module pcie_phy_gen4 #(
  parameter int LANES = pcie_pkg::PCIE_LANES
) (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               refclk,       // 100 MHz PCIe refclk
  input  logic [LANES-1:0]   rxp,
  input  logic [LANES-1:0]   rxn,
  output logic [LANES-1:0]   txp,
  output logic [LANES-1:0]   txn,
  output logic               link_up,
  output logic [2:0]         ltssm_state,
  // DWORD stream to/from TLP layer
  input  logic               tx_valid,
  input  logic [31:0]        tx_data,
  output logic               tx_ready,
  output logic               rx_valid,
  output logic [31:0]        rx_data,
  input  logic               rx_ready
);

  typedef enum logic [2:0] {
    LTSSM_DETECT   = 3'd0,
    LTSSM_POLLING  = 3'd1,
    LTSSM_CONFIG   = 3'd2,
    LTSSM_L0       = 3'd3,
    LTSSM_RECOVERY = 3'd4
  } ltssm_e;

  ltssm_e state;
  logic [7:0] train_cnt;

  assign txp = {LANES{1'b0}};
  assign txn = {LANES{1'b1}};

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state      <= LTSSM_DETECT;
      train_cnt  <= '0;
      link_up    <= 1'b0;
    end else begin
      case (state)
        LTSSM_DETECT: begin
          train_cnt <= train_cnt + 1'b1;
          if (train_cnt > 8'd4)
            state <= LTSSM_POLLING;
        end
        LTSSM_POLLING: begin
          train_cnt <= train_cnt + 1'b1;
          if (train_cnt > 8'd12)
            state <= LTSSM_CONFIG;
        end
        LTSSM_CONFIG: begin
          train_cnt <= train_cnt + 1'b1;
          if (train_cnt > 8'd20) begin
            state   <= LTSSM_L0;
            link_up <= 1'b1;
          end
        end
        LTSSM_L0: link_up <= 1'b1;
        default: state <= LTSSM_DETECT;
      endcase
    end
  end

  assign ltssm_state = state;

  // Loopback DWORD pipe when link is up (behavioral serdes bypass)
  assign tx_ready = link_up;
  assign rx_valid = link_up && tx_valid;
  assign rx_data  = tx_data;

endmodule
