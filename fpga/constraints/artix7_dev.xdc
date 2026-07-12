# Artix-7 DevKit constraints — Mili BNN-TMR chip emulator
# 100 MHz system clock, SPI to STM32H7, active-low reset

set_property PART $::env(PART) [current_project]

# Clock — 100 MHz board oscillator
create_clock -period 10.000 -name clk_sys [get_ports clk_sys]
create_clock -period 10.000 -name clk_io  [get_ports clk_io]

set_property PACKAGE_PIN E3  [get_ports clk_sys]
set_property PACKAGE_PIN D18 [get_ports clk_io]
set_property PACKAGE_PIN C12 [get_ports rst_n]

# SPI (MCU primary host interface)
set_property PACKAGE_PIN R14 [get_ports spi_sck]
set_property PACKAGE_PIN P14 [get_ports spi_cs_n]
set_property PACKAGE_PIN N16 [get_ports spi_mosi]
set_property PACKAGE_PIN M14 [get_ports spi_miso]

# IRQ to STM32
set_property PACKAGE_PIN L14 [get_ports irq]

# UART debug
set_property PACKAGE_PIN T14 [get_ports uart_tx]
set_property PACKAGE_PIN T15 [get_ports uart_rx]

# I/O standard
set_property IOSTANDARD LVCMOS33 [get_ports {clk_sys clk_io rst_n spi_* uart_* irq}]

# False paths — async SPI
set_false_path -from [get_ports spi_sck] -to [get_cells -hierarchical *u_spi*]

# Bitstream options
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
