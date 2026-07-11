// Mili BNN-TMR — I2C Slave Interface (config / PMIC)

module i2c_if #(
  parameter logic [6:0] SLAVE_ADDR = 7'h50
) (
  input  logic        clk,
  input  logic        rst_n,
  inout  wire         i2c_scl,
  inout  wire         i2c_sda,
  output logic        reg_cs,
  output logic        reg_we,
  output logic [5:0]  reg_addr,
  output logic [31:0] reg_wdata,
  input  logic [31:0] reg_rdata
);

  logic scl_in, sda_in, sda_out, sda_oe;
  assign scl_in     = i2c_scl;
  assign i2c_sda    = sda_oe ? sda_out : 1'bz;
  assign sda_in     = i2c_sda;

  logic [7:0]  rx_byte;
  logic [2:0]  bit_cnt;
  logic [6:0]  addr_match;
  logic [5:0]  byte_addr;
  logic        rw_bit;
  logic        ack_sda;

  typedef enum logic [2:0] {
    I2C_IDLE, I2C_ADDR, I2C_ACK1, I2C_REG_ADDR, I2C_ACK2,
    I2C_WRITE, I2C_ACK3, I2C_READ, I2C_ACK4
  } i2c_state_e;

  i2c_state_e state;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state    <= I2C_IDLE;
      sda_oe   <= 1'b0;
      sda_out  <= 1'b1;
      reg_cs   <= 1'b0;
      reg_we   <= 1'b0;
    end else begin
      reg_cs <= 1'b0;
      unique case (state)
        I2C_IDLE: begin
          if (!scl_in && !sda_in) // START condition
            state <= I2C_ADDR;
        end
        I2C_ADDR: begin
          if (scl_in) begin
            rx_byte <= {rx_byte[6:0], sda_in};
            if (bit_cnt == 3'd7) begin
              addr_match <= {rx_byte[6:0], sda_in};
              rw_bit     <= sda_in;
              state      <= I2C_ACK1;
              bit_cnt    <= '0;
            end else
              bit_cnt <= bit_cnt + 1'b1;
          end
        end
        I2C_ACK1: begin
          if (addr_match == SLAVE_ADDR) begin
            sda_oe  <= 1'b1;
            sda_out <= 1'b0; // ACK
            state   <= rw_bit ? I2C_READ : I2C_REG_ADDR;
          end else
            state <= I2C_IDLE;
        end
        I2C_REG_ADDR: begin
          if (scl_in) begin
            byte_addr <= {byte_addr[4:0], sda_in};
            if (bit_cnt == 3'd7) begin
              state   <= I2C_ACK2;
              bit_cnt <= '0;
            end else
              bit_cnt <= bit_cnt + 1'b1;
          end
        end
        I2C_ACK2: begin
          sda_oe  <= 1'b1;
          sda_out <= 1'b0;
          state   <= I2C_WRITE;
        end
        I2C_WRITE: begin
          if (scl_in) begin
            rx_byte <= {rx_byte[6:0], sda_in};
            if (bit_cnt == 3'd7) begin
              reg_cs    <= 1'b1;
              reg_we    <= 1'b1;
              reg_addr  <= byte_addr[5:0];
              reg_wdata <= {24'h0, rx_byte[6:0], sda_in};
              state     <= I2C_IDLE;
            end else
              bit_cnt <= bit_cnt + 1'b1;
          end
        end
        I2C_READ: begin
          reg_cs   <= 1'b1;
          sda_oe   <= 1'b1;
          sda_out  <= reg_rdata[7 - bit_cnt];
          if (scl_in)
            bit_cnt <= bit_cnt + 1'b1;
          if (bit_cnt == 3'd7)
            state <= I2C_IDLE;
        end
        default: state <= I2C_IDLE;
      endcase
    end
  end

endmodule
