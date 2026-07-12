# Vivado batch synthesis — Mili BNN-TMR Artix-7 DevKit
# argv: <part> <build_dir> <project_name>

set part     [lindex $argv 0]
set builddir [lindex $argv 1]
set projname [lindex $argv 2]

set rtl_dir [file normalize [file join [file dirname [info script]] .. rtl]]
set flist   [file normalize [file join [file dirname [info script]] filelist.f]]

file mkdir $builddir
cd $builddir

create_project $projname . -part $part -force

# Read RTL filelist
set fh [open $flist r]
while {[gets $fh line] >= 0} {
  set t [string trim $line]
  if {$t eq "" || [string match "#*" $t]} { continue }
  set path [file normalize [file join [file dirname $flist] $t]]
  read_verilog -sv $path
}
close $fh

# Top + constraints
set_property top mili_chip_top [current_fileset]
read_xdc [file normalize [file join [file dirname [info script]] constraints artix7_dev.xdc]]

# Synthesis strategy tuned for Artix-7
synth_design -top mili_chip_top -part $part -directive RuntimeOptimized

# Place & route
opt_design
place_design -directive RuntimeOptimized
phys_opt_design
route_design -directive RuntimeOptimized

# Bitstream
write_bitstream -force ${projname}.bit
write_checkpoint -force ${projname}.dcp

# Utilization report
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt

puts "FPGA synthesis complete: ${builddir}/${projname}.bit"
