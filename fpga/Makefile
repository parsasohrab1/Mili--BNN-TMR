# Mili DevKit — Artix-7 FPGA synthesis flow
# Target: XC7A200T-FBG484 (per integration/board/dev_board.yaml)
#
# Usage (requires Vivado 2022+):
#   make synth          # generate bitstream
#   make export         # copy .bit to build/

PART     ?= xc7a200tfbg484-2
BUILD    ?= build
VIVADO   ?= vivado
PROJECT  := mili_fpga_devkit

RTL_FLIST := filelist.f
XDC       := constraints/artix7_dev.xdc
TCL       := vivado_synth.tcl

.PHONY: all synth export check clean

all: synth

check:
	@which $(VIVADO) >/dev/null 2>&1 || (echo "Vivado not in PATH"; exit 1)

synth: check
	@mkdir -p $(BUILD)
	$(VIVADO) -mode batch -source $(TCL) -tclargs $(PART) $(BUILD) $(PROJECT)

export: synth
	@test -f $(BUILD)/$(PROJECT).bit && cp $(BUILD)/$(PROJECT).bit $(BUILD)/mili_devkit_artix7.bit
	@echo "Bitstream: $(BUILD)/mili_devkit_artix7.bit"

clean:
	rm -rf $(BUILD) .Xil *.jou *.log
