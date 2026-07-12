// Mili BNN-TMR — PCIe TLP RX/TX (Memory Read/Write + Completion)

`include "mili_pkg.sv"

module pcie_tlp (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               link_up,
  // From PHY
  input  logic               phy_rx_valid,
  input  logic [31:0]        phy_rx_data,
  output logic               phy_rx_ready,
  output logic               phy_tx_valid,
  output logic [31:0]        phy_tx_data,
  input  logic               phy_tx_ready,
  // To MMIO bridge (legacy simplified host port)
  output logic               host_rx_valid,
  output logic               host_rx_we,
  output logic [31:0]        host_rx_addr,
  output logic [31:0]        host_rx_wdata,
  input  logic               host_rx_ready,
  input  logic               host_tx_valid,
  input  logic [31:0]        host_tx_rdata
);

  import pcie_pkg::*;

  typedef enum logic [1:0] {
    RX_IDLE,
    RX_HDR,
    RX_DATA,
    RX_WAIT
  } rx_state_e;

  rx_state_e rx_state;
  mem_tlp_t  rx_tlp;
  logic [1:0] rx_dw_cnt;

  assign phy_rx_ready = link_up && (rx_state != RX_WAIT);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rx_state       <= RX_IDLE;
      rx_dw_cnt      <= '0;
      host_rx_valid  <= 1'b0;
      host_rx_we     <= 1'b0;
      host_rx_addr   <= '0;
      host_rx_wdata  <= '0;
    end else begin
      host_rx_valid <= 1'b0;

      if (link_up && phy_rx_valid && phy_rx_ready) begin
        unique case (rx_state)
          RX_IDLE, RX_HDR: begin
            if (rx_dw_cnt == 2'd0) begin
              rx_tlp.fmt      <= phy_rx_data[31:29];
              rx_tlp.tlp_type <= phy_rx_data[28:24];
              rx_tlp.length   <= phy_rx_data[9:0];
              rx_dw_cnt       <= 2'd1;
              rx_state        <= RX_HDR;
            end else if (rx_dw_cnt == 2'd1) begin
              rx_tlp.addr_lo <= phy_rx_data;
              rx_dw_cnt      <= 2'd2;
              if (rx_tlp.fmt == FMT_3DW_DATA)
                rx_state <= RX_DATA;
              else
                rx_state <= RX_WAIT;
            end
          end
          RX_DATA: begin
            rx_tlp.data     <= phy_rx_data;
            host_rx_valid   <= 1'b1;
            host_rx_we      <= 1'b1;
            host_rx_addr    <= rx_tlp.addr_lo;
            host_rx_wdata   <= phy_rx_data;
            rx_state        <= RX_IDLE;
            rx_dw_cnt       <= '0;
          end
          RX_WAIT: begin
            host_rx_valid <= 1'b1;
            host_rx_we    <= 1'b0;
            host_rx_addr  <= rx_tlp.addr_lo;
            rx_state      <= RX_IDLE;
            rx_dw_cnt     <= '0;
          end
          default: rx_state <= RX_IDLE;
        endcase
      end

      if (host_rx_valid && !host_rx_ready)
        host_rx_valid <= 1'b1;
    end
  end

  // Completion TLP on read response
  logic pending_cpl;
  logic [31:0] cpl_data;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      phy_tx_valid <= 1'b0;
      phy_tx_data  <= '0;
      pending_cpl  <= 1'b0;
      cpl_data     <= '0;
    end else begin
      phy_tx_valid <= 1'b0;
      if (host_tx_valid && link_up && phy_tx_ready && !pending_cpl) begin
        pending_cpl <= 1'b1;
        cpl_data    <= host_tx_rdata;
      end
      if (pending_cpl && phy_tx_ready) begin
        phy_tx_valid <= 1'b1;
        phy_tx_data  <= cpl_data;
        pending_cpl  <= 1'b0;
      end
    end
  end

endmodule
