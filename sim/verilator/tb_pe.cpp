// Verilator testbench — PE unit test

#include "Vpe.h"
#include "verilated.h"

static void tick(Vpe* dut) {
    dut->clk = 0; dut->eval();
    dut->clk = 1; dut->eval();
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vpe dut;
    dut.rst_n = 0;
    dut.en = 0;
    dut.clear = 0;
    dut.a_in = 1;
    dut.w_in = 1;
    tick(&dut);
    dut.rst_n = 1;

    // +1 * +1 = +1
    dut.en = 1; dut.clear = 1; dut.a_in = 1; dut.w_in = 1;
    tick(&dut);
    dut.clear = 0;
    if (dut.acc_out != 1) {
        VL_PRINTF("FAIL: expected acc=1, got %d\n", (int)dut.acc_out);
        return 1;
    }

    // accumulate: +1 * -1 = -1 → acc = 0
    dut.a_in = 1; dut.w_in = 0;
    tick(&dut);
    if (dut.acc_out != 0) {
        VL_PRINTF("FAIL: expected acc=0, got %d\n", (int)dut.acc_out);
        return 1;
    }

    VL_PRINTF("PE test PASSED\n");
    return 0;
}
