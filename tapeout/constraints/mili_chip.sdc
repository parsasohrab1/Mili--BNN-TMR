# Mili BNN-TMR — 14nm FinFET Timing Constraints (SDC)
# Target: 400 MHz (normal), 800 MHz (turbo)

create_clock -name clk_sys -period 2.500 [get_ports clk_sys]
create_clock -name clk_pcie -period 4.000 [get_ports pcie_refclk]

set_clock_uncertainty -setup 0.050 [get_clocks clk_sys]
set_clock_uncertainty -hold  0.020 [get_clocks clk_sys]

# I/O delays (BGA-484 package model)
set_input_delay  -clock clk_sys -max 0.400 [get_ports {spi_* pcie_rx_* i2c_* uart_*}]
set_input_delay  -clock clk_sys -min 0.100 [get_ports {spi_* pcie_rx_* i2c_* uart_*}]
set_output_delay -clock clk_sys -max 0.400 [get_ports {spi_* pcie_tx_* i2c_* uart_*}]
set_output_delay -clock clk_sys -min 0.100 [get_ports {spi_* pcie_tx_* i2c_* uart_*}]

# False paths
set_false_path -from [get_ports rst_n] -to [all_registers]
set_false_path -from [get_ports scan_en]

# Multicycle (DPM state transitions)
set_multicycle_path -setup 2 -from [get_clocks clk_sys] -to [get_cells u_dpm_ctrl/*]

# SRAM macro timing (32 MB embedded)
set_input_delay  -clock clk_sys -max 0.600 [get_ports sram_*]
set_output_delay -clock clk_sys -max 0.600 [get_ports sram_*]
