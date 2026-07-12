# Mili BNN-TMR — Tape-out flow (requires foundry PDK + EDA tools)
# Usage:
#   make synth    # Design Compiler / Genus
#   make pnr      # Innovus place & route
#   make signoff  # DRC/LVS/STA reports
#   make gds      # streamOut GDSII

ROOT     := $(CURDIR)/..
SYNTH    := $(ROOT)/tapeout/synthesis/synth.tcl
PNR      := $(ROOT)/tapeout/pnr/place_route.tcl
SIGNOFF  := $(ROOT)/tapeout/signoff
GDS_OUT  := $(ROOT)/tapeout/gds/mili_chip_top.gds

.PHONY: synth pnr signoff gds all check-tools

all: signoff gds

check-tools:
	@which dc_shell >/dev/null 2>&1 || echo "WARN: dc_shell not in PATH"
	@which innovus >/dev/null 2>&1 || echo "WARN: innovus not in PATH"

synth: check-tools
	@mkdir -p netlist reports
	cd synthesis && dc_shell -f synth.tcl

pnr: synth
	@mkdir -p gds reports
	cd pnr && innovus -init place_route.tcl

signoff:
	@test -f $(SIGNOFF)/drc_report.txt || (echo "Missing DRC report"; exit 1)
	@test -f $(SIGNOFF)/lvs_report.txt || (echo "Missing LVS report"; exit 1)
	@test -f $(SIGNOFF)/timing_report.json || (echo "Missing timing report"; exit 1)
	@echo "Signoff artifacts present."

gds:
	@if [ -f $(GDS_OUT) ]; then echo "GDS: $(GDS_OUT)"; else echo "Run 'make pnr' to generate GDS"; fi
