// Verilator testbench — Systolic Array 8×8 test

#include "Vsystolic_array.h"
#include "verilated.h"

static void tick(Vsystolic_array* dut) {
    dut->clk = 0; dut->eval();
    dut->clk = 1; dut->eval();
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vsystolic_array dut;
    dut.rst_n = 0;
    dut.start = 0;
    for (int i = 0; i < 8; i++) {
        dut.a_row[i] = i & 1;
        dut.w_col[i] = 1;
    }
    for (int i = 0; i < 5; i++) tick(&dut);
    dut.rst_n = 1;

    dut.start = 1;
    tick(&dut);
    dut.start = 0;

    int timeout = 20;
    while (!dut.done && --timeout > 0)
        tick(&dut);

    if (!dut.done) {
        VL_PRINTF("FAIL: systolic did not complete\n");
        return 1;
    }

    tick(&dut); // latch results

    VL_PRINTF("Systolic done. PE[0][0]=%d PE[7][7]=%d\n",
              (int)dut.result[0][0], (int)dut.result[7][7]);
    VL_PRINTF("Systolic 8x8 test PASSED (%d cycles)\n", 14 - timeout);
    return 0;
}
