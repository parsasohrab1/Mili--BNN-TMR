# Innovus Place & Route script — Mili BNN-TMR BGA-484
# Usage: innovus -init place_route.tcl

set TOP mili_chip_top
set NETLIST netlist/mili_chip_top_syn.v
set SDC ../constraints/mili_chip.sdc
set LEF "tech/tsmc14nf.lef macros/sram_32mb.lef"
set GDS_OUT gds/mili_chip_top.gds

# Floorplan (die 6.5 × 6.5 mm for BGA-484)
floorPlan -site core -d 6500 6500 50 50 50 50

# Power grid
addRing -spacing 5 -width 5 -layer {M9 M8} -nets {VDD VSS}
addStripe -layer M8 -width 5 -spacing 5 -start 50 -nets {VDD VSS}

# Place macros (SRAM banks)
placeInstance sram_macro_0 500 500
placeInstance sram_macro_1 3500 500

placeDesign -prePlaceOpt
refinePlace
optDesign -preCTS
clockDesign -specFile ../constraints/cts.spec
optDesign -postCTS
routeDesign
optDesign -postRoute
addFiller -cell FILL8 FILL4 FILL2 FILL1

# Signoff exports
verify_drc -report signoff/drc_report.txt
verify_lvs -report signoff/lvs_report.txt
streamOut $GDS_OUT

puts "P&R complete: $GDS_OUT"
