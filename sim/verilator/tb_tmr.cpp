// Verilator testbench — TMR Majority Voter test

#include "Vtmr_voter.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtmr_voter dut;

    // All agree
    dut.lane0 = 0xAAAA;
    dut.lane1 = 0xAAAA;
    dut.lane2 = 0xAAAA;
    dut.eval();
    if (dut.voted != 0xAAAA || dut.disagree) {
        VL_PRINTF("FAIL: unanimous vote\n");
        return 1;
    }

    // Lane2 disagrees (single fault — correctable)
    dut.lane2 = 0x5555;
    dut.eval();
    if (dut.voted != 0xAAAA || !dut.disagree) {
        VL_PRINTF("FAIL: majority should be 0xAAAA, disagree=%d\n", (int)dut.disagree);
        return 1;
    }

    // All disagree (uncorrectable at word level)
    dut.lane0 = 0x0001;
    dut.lane1 = 0x0002;
    dut.lane2 = 0x0004;
    dut.eval();
    if (!dut.disagree) {
        VL_PRINTF("FAIL: should detect disagreement\n");
        return 1;
    }

    VL_PRINTF("TMR voter test PASSED\n");
    return 0;
}
