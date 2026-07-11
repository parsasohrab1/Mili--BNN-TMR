// Mili BNN-TMR — UART Debug / Bootloader Interface
// 115200 baud, 8N1 (simplified transmitter/receiver)

module uart_if #(
  parameter int CLK_FREQ   = 100_000_000,
  parameter int BAUD_RATE  = 115_200
) (
  input  logic        clk,
  input  logic        rst_n,
  output logic        uart_tx,
  input  logic        uart_rx,
  // Debug register peek/poke
  output logic        reg_cs,
  output logic        reg_we,
  output logic [5:0]  reg_addr,
  output logic [31:0] reg_wdata,
  input  logic [31:0] reg_rdata
);

  localparam int BAUD_DIV = CLK_FREQ / BAUD_RATE;

  // TX state machine
  logic [15:0] tx_cnt;
  logic [3:0]  tx_bit;
  logic [7:0]  tx_data;
  logic        tx_busy;
  logic        tx_start;

  typedef enum logic [1:0] { TX_IDLE, TX_START, TX_DATA, TX_STOP } tx_state_e;
  tx_state_e tx_state;

  assign uart_tx = (tx_state == TX_IDLE) ? 1'b1 :
                   (tx_state == TX_START) ? 1'b0 :
                   (tx_state == TX_DATA)  ? tx_data[tx_bit] : 1'b1;

  // RX (simplified — detect start bit)
  logic [7:0] rx_data;
  logic       rx_valid;
  logic [15:0] rx_cnt;
  logic [3:0]  rx_bit;
  logic        rx_sync;

  typedef enum logic [1:0] { RX_IDLE, RX_START, RX_DATA, RX_STOP } rx_state_e;
  rx_state_e rx_state;

  // TX FSM
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_state <= TX_IDLE;
      tx_cnt   <= '0;
      tx_bit   <= '0;
      tx_busy  <= 1'b0;
    end else begin
      unique case (tx_state)
        TX_IDLE: begin
          if (tx_start) begin
            tx_state <= TX_START;
            tx_cnt   <= BAUD_DIV[15:0];
            tx_busy  <= 1'b1;
          end
        end
        TX_START: begin
          if (tx_cnt == 0) begin
            tx_state <= TX_DATA;
            tx_bit   <= '0;
            tx_cnt   <= BAUD_DIV[15:0];
          end else
            tx_cnt <= tx_cnt - 1'b1;
        end
        TX_DATA: begin
          if (tx_cnt == 0) begin
            if (tx_bit == 4'd7)
              tx_state <= TX_STOP;
            else
              tx_bit <= tx_bit + 1'b1;
            tx_cnt <= BAUD_DIV[15:0];
          end else
            tx_cnt <= tx_cnt - 1'b1;
        end
        TX_STOP: begin
          if (tx_cnt == 0) begin
            tx_state <= TX_IDLE;
            tx_busy  <= 1'b0;
          end else
            tx_cnt <= tx_cnt - 1'b1;
        end
      endcase
    end
  end

  // RX FSM
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rx_state  <= RX_IDLE;
      rx_valid  <= 1'b0;
      rx_sync   <= 1'b1;
    end else begin
      rx_valid <= 1'b0;
      rx_sync  <= uart_rx;
      unique case (rx_state)
        RX_IDLE: begin
          if (!uart_rx) begin
            rx_state <= RX_START;
            rx_cnt   <= BAUD_DIV[15:0] / 2;
          end
        end
        RX_START: begin
          if (rx_cnt == 0) begin
            rx_state <= RX_DATA;
            rx_bit   <= '0;
            rx_cnt   <= BAUD_DIV[15:0];
          end else
            rx_cnt <= rx_cnt - 1'b1;
        end
        RX_DATA: begin
          if (rx_cnt == 0) begin
            rx_data[rx_bit] <= uart_rx;
            if (rx_bit == 4'd7)
              rx_state <= RX_STOP;
            else
              rx_bit <= rx_bit + 1'b1;
            rx_cnt <= BAUD_DIV[15:0];
          end else
            rx_cnt <= rx_cnt - 1'b1;
        end
        RX_STOP: begin
          if (rx_cnt == 0) begin
            rx_valid <= 1'b1;
            rx_state <= RX_IDLE;
          end else
            rx_cnt <= rx_cnt - 1'b1;
        end
      endcase
    end
  end

  // Simple command parser: 'R' + addr → read reg, 'W' + addr + data → write
  logic [1:0] cmd_state;
  logic [5:0] cmd_addr;
  logic [31:0] cmd_data;
  logic [1:0] data_byte_cnt;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cmd_state    <= 2'd0;
      reg_cs       <= 1'b0;
      reg_we       <= 1'b0;
      tx_start     <= 1'b0;
    end else begin
      reg_cs   <= 1'b0;
      tx_start <= 1'b0;
      if (rx_valid) begin
        unique case (cmd_state)
          2'd0: begin
            if (rx_data == "R") cmd_state <= 2'd1;
            else if (rx_data == "W") cmd_state <= 2'd2;
          end
          2'd1: begin // read: next byte is reg addr
            reg_cs   <= 1'b1;
            reg_addr <= rx_data[5:0];
            cmd_state<= 2'd0;
          end
          2'd2: begin // write: collect addr then data
            cmd_addr <= rx_data[5:0];
            cmd_state<= 2'd3;
          end
          2'd3: begin
            cmd_data <= {cmd_data[23:0], rx_data};
            data_byte_cnt <= data_byte_cnt + 1'b1;
            if (data_byte_cnt == 2'd3) begin
              reg_cs    <= 1'b1;
              reg_we    <= 1'b1;
              reg_addr  <= cmd_addr;
              reg_wdata <= {cmd_data[23:0], rx_data};
              cmd_state <= 2'd0;
              data_byte_cnt <= '0;
            end
          end
        endcase
      end
    end
  end

endmodule
