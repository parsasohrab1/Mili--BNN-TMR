// Mili BNN-TMR — SPI Slave Interface with DMA support
// Primary host link for STM32H7

module spi_if (
  input  logic        clk,
  input  logic        rst_n,
  // SPI pins
  input  logic        spi_sck,
  input  logic        spi_cs_n,
  input  logic        spi_mosi,
  output logic        spi_miso,
  // Register bus
  output logic        reg_cs,
  output logic        reg_we,
  output logic [5:0]  reg_addr,
  output logic [31:0] reg_wdata,
  input  logic [31:0] reg_rdata,
  // DMA
  output logic        dma_req,
  output logic        dma_we,
  output logic [24:0] dma_addr,
  output logic [31:0] dma_wdata,
  input  logic [31:0] dma_rdata,
  input  logic        dma_ack
);

  logic [5:0]  bit_cnt;
  logic [47:0] shift_reg;
  logic        active;
  logic        cmd_we;
  logic [31:0] cmd_addr;
  logic [31:0] cmd_data;

  typedef enum logic [1:0] { ST_CMD, ST_ADDR, ST_DATA, ST_RESP } spi_state_e;
  spi_state_e state;

  assign spi_miso = active ? shift_reg[47] : 1'b0;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state    <= ST_CMD;
      active   <= 1'b0;
      bit_cnt  <= '0;
      shift_reg<= '0;
      reg_cs   <= 1'b0;
      reg_we   <= 1'b0;
      dma_req  <= 1'b0;
    end else begin
      reg_cs  <= 1'b0;
      dma_req <= 1'b0;

      if (spi_cs_n) begin
        active  <= 1'b0;
        state   <= ST_CMD;
        bit_cnt <= '0;
      end else begin
        active <= 1'b1;
        if (spi_sck) begin // sample on rising edge (simplified)
          shift_reg <= {shift_reg[46:0], spi_mosi};
          bit_cnt   <= bit_cnt + 1'b1;

          if (bit_cnt == 5'd7) begin
            unique case (state)
              ST_CMD: begin
                cmd_we <= shift_reg[0];
                state  <= ST_ADDR;
                bit_cnt<= '0;
              end
              ST_ADDR: begin
                cmd_addr <= {shift_reg[23:0], spi_mosi, shift_reg[6:0]};
                state    <= cmd_we ? ST_DATA : ST_RESP;
                bit_cnt  <= '0;
              end
              ST_DATA: begin
                cmd_data <= {shift_reg[23:0], spi_mosi, shift_reg[6:0]};
                reg_cs   <= 1'b1;
                reg_we   <= 1'b1;
                reg_addr <= cmd_addr[7:2];
                reg_wdata<= cmd_data;
                state    <= ST_CMD;
                bit_cnt  <= '0;
              end
              ST_RESP: begin
                shift_reg[47:16] <= reg_rdata;
                state <= ST_CMD;
                bit_cnt <= '0;
              end
            endcase
          end
        end
      end
    end
  end

endmodule
