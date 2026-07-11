# Design Compiler synthesis script — Mili BNN-TMR 14nm FinFET
# Usage: dc_shell -f synth.tcl

set TOP mili_chip_top
set RTL_DIR ../../rtl

read_file -format sverilog [list \
  ${RTL_DIR}/mili_pkg.sv \
  ${RTL_DIR}/pe.sv \
  ${RTL_DIR}/systolic_array.sv \
  ${RTL_DIR}/tmr_voter.sv \
  ${RTL_DIR}/tmr_triplex.sv \
  ${RTL_DIR}/ecc_codec.sv \
  ${RTL_DIR}/sram_bank.sv \
  ${RTL_DIR}/sram_ctrl.sv \
  ${RTL_DIR}/dpm_ctrl.sv \
  ${RTL_DIR}/reg_file.sv \
  ${RTL_DIR}/spi_if.sv \
  ${RTL_DIR}/pcie_if.sv \
  ${RTL_DIR}/i2c_if.sv \
  ${RTL_DIR}/uart_if.sv \
  ${RTL_DIR}/${TOP}.sv \
]

current_design $TOP
link

# 14nm FinFET libraries (placeholder — bind to foundry PDK)
# set_app_var target_library "tsmc14nf_stdcell_tt_0p85v_25c.db"
# set_app_var link_library "* $target_library sram_32mb_14nm.db"

source ../constraints/mili_chip.sdc

compile_ultra -gate_clock -retime

report_timing -max_paths 10 > reports/synth_timing.rpt
report_area > reports/synth_area.rpt
report_power > reports/synth_power.rpt

write -format verilog -hierarchy -output netlist/mili_chip_top_syn.v
write -format ddc -hierarchy -output netlist/mili_chip_top.ddc

puts "Synthesis complete: netlist/mili_chip_top_syn.v"
