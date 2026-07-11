// Verilator testbench for tmr_triplex fault injection

#include <cstdio>
#include <cstdlib>
#include "Vtmr_triplex.h"
#include "verilated.h"

static void tick(Vtmr_triplex* top) {
    top->clk = 0;
    top->eval();
    top->clk = 1;
    top->eval();
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtmr_triplex top;

    top.rst_n = 0;
    top.tmr_en = 1;
    top.fault_inject = 0;
    top.fault_lane = 0;
    top.start = 0;
    for (int i = 0; i < 4; i++) tick(&top);
    top.rst_n = 1;

    // Feed simple test vectors
    for (int r = 0; r < 8; r++) {
        top.a_row[r] = (r + 1) & 0xFF;
    }
    for (int c = 0; c < 8; c++) {
        top.w_col[c] = 1;
    }

    // Run without fault
    top.fault_inject = 0;
    top.start = 1;
    tick(&top);
    top.start = 0;

    int timeout = 5000;
    while (!top.done && --timeout > 0) tick(&top);
    if (!top.done) {
        fprintf(stderr, "FAIL: triplex timeout (no fault)\n");
        return 1;
    }
    if (top.disagree) {
        fprintf(stderr, "FAIL: unexpected disagree without fault\n");
        return 1;
    }

    // Reset and run with fault on lane 1
    top.rst_n = 0;
    tick(&top);
    top.rst_n = 1;

    top.fault_inject = 1;
    top.fault_lane = 1;
    top.start = 1;
    tick(&top);
    top.start = 0;

    timeout = 5000;
    while (!top.done && --timeout > 0) tick(&top);
    if (!top.done) {
        fprintf(stderr, "FAIL: triplex timeout (with fault)\n");
        return 1;
    }
    if (!top.disagree) {
        fprintf(stderr, "FAIL: expected disagree with fault inject\n");
        return 1;
    }
    if (top.err_count == 0) {
        fprintf(stderr, "FAIL: expected err_count > 0\n");
        return 1;
    }

    printf("PASS: tmr_triplex fault injection (err_count=%u)\n", top.err_count);
    return 0;
}
