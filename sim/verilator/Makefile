# Mili BNN-TMR Verilator Simulation Makefile

VERILATOR   ?= verilator
BUILD_DIR   ?= build
RTL_DIR     := ../../rtl
SIM_DIR     := $(CURDIR)

VERILATOR_FLAGS = \
	--cc --exe --build -j 0 \
	--timing \
	-Wall -Wno-fatal \
	--top-module $(TOP) \
	-CFLAGS "-std=c++17 -O2" \
	-I$(RTL_DIR)

# ── Unit tests ────────────────────────────────────────────────
.PHONY: all pe systolic tmr triplex voter ecc dpm top clean help

all: pe systolic tmr triplex top

pe: TOP = pe
pe: TB = tb_pe.cpp
pe:
	@mkdir -p $(BUILD_DIR)/$@
	$(VERILATOR) $(VERILATOR_FLAGS) \
		-Mdir $(BUILD_DIR)/$@ \
		-o Vpe_sim \
		$(RTL_DIR)/mili_pkg.sv $(RTL_DIR)/pe.sv \
		$(SIM_DIR)/$(TB)
	$(BUILD_DIR)/$@/Vpe_sim

systolic: TOP = systolic_array
systolic: TB = tb_systolic.cpp
systolic:
	@mkdir -p $(BUILD_DIR)/$@
	$(VERILATOR) $(VERILATOR_FLAGS) \
		-Mdir $(BUILD_DIR)/$@ \
		-o Vsystolic_sim \
		$(RTL_DIR)/mili_pkg.sv $(RTL_DIR)/pe.sv $(RTL_DIR)/systolic_array.sv \
		$(SIM_DIR)/$(TB)
	$(BUILD_DIR)/$@/Vsystolic_sim

tmr: TOP = tmr_voter
tmr: TB = tb_tmr.cpp
tmr:
	@mkdir -p $(BUILD_DIR)/$@
	$(VERILATOR) $(VERILATOR_FLAGS) \
		-Mdir $(BUILD_DIR)/$@ \
		-o Vtmr_sim \
		$(RTL_DIR)/mili_pkg.sv $(RTL_DIR)/tmr_voter.sv \
		$(SIM_DIR)/$(TB)
	$(BUILD_DIR)/$@/Vtmr_sim

triplex: TOP = tmr_triplex
triplex: TB = tb_triplex.cpp
triplex:
	@mkdir -p $(BUILD_DIR)/$@
	$(VERILATOR) $(VERILATOR_FLAGS) \
		-Mdir $(BUILD_DIR)/$@ \
		-o Vtriplex_sim \
		$(RTL_DIR)/mili_pkg.sv $(RTL_DIR)/pe.sv $(RTL_DIR)/systolic_array.sv \
		$(RTL_DIR)/tmr_voter.sv $(RTL_DIR)/tmr_triplex.sv \
		$(SIM_DIR)/$(TB)
	$(BUILD_DIR)/$@/Vtriplex_sim

top: TOP = mili_chip_top
top: TB = tb_top.cpp
top:
	@mkdir -p $(BUILD_DIR)/$@
	$(VERILATOR) $(VERILATOR_FLAGS) \
		-Mdir $(BUILD_DIR)/$@ \
		-o Vtop_sim \
		-f filelist.f \
		$(SIM_DIR)/$(TB)
	$(BUILD_DIR)/$@/Vtop_sim

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "Targets: pe, systolic, tmr, triplex, top, all, clean"
