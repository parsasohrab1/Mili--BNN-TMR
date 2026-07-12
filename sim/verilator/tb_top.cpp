// Verilator testbench — Full chip top-level smoke test

#include "Vmili_chip_top.h"
#include "verilated.h"

static const uint32_t MILI_CSR_BASE  = 0x40000000;
static const uint32_t MILI_REG_STATUS = 0x04;
static const uint32_t MILI_REG_INFER_CTRL = 0x24;
static const uint32_t MILI_REG_INFER_STAT = 0x28;
static const uint32_t MILI_REG_TMR_CTRL = 0x1C;

static void tick(Vmili_chip_top* dut) {
    dut->clk_sys = 0; dut->clk_io = 0; dut->eval();
    dut->clk_sys = 1; dut->clk_io = 1; dut->eval();
}

static uint32_t csr_read(Vmili_chip_top* dut, uint32_t offset) {
    dut->pcie_rx_valid = 1;
    dut->pcie_rx_we    = 0;
    dut->pcie_rx_addr  = MILI_CSR_BASE + offset;
    dut->pcie_rx_wdata = 0;
    tick(dut);
    dut->pcie_rx_valid = 0;
    tick(dut);
    return dut->pcie_tx_rdata;
}

static void csr_write(Vmili_chip_top* dut, uint32_t offset, uint32_t data) {
    dut->pcie_rx_valid = 1;
    dut->pcie_rx_we    = 1;
    dut->pcie_rx_addr  = MILI_CSR_BASE + offset;
    dut->pcie_rx_wdata = data;
    tick(dut);
    dut->pcie_rx_valid = 0;
    tick(dut);
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vmili_chip_top dut;

    dut.rst_n = 0;
    dut.pcie_rx_valid = 0;
    dut.pcie_refclk = 1;
    dut.pcie_rxp = 0;
    dut.pcie_rxn = 0xF;
    dut.spi_cs_n = 1;
    dut.uart_rx = 1;
    for (int i = 0; i < 10; i++) tick(&dut);
    dut.rst_n = 1;

    // Read STATUS — expect READY bit set
    uint32_t status = csr_read(&dut, MILI_REG_STATUS);
    if (!(status & 0x1)) {
        VL_PRINTF("FAIL: STATUS.READY not set (status=0x%08x)\n", status);
        return 1;
    }
    VL_PRINTF("STATUS = 0x%08x (READY OK)\n", status);

    // Enable TMR
    csr_write(&dut, MILI_REG_TMR_CTRL, 0x1);

    // Start inference
    csr_write(&dut, MILI_REG_INFER_CTRL, 0x1);

    int timeout = 100;
    uint32_t infer_stat = 0;
    while (--timeout > 0) {
        tick(&dut);
        infer_stat = csr_read(&dut, MILI_REG_INFER_STAT);
        if (infer_stat & 0x2) break; // DONE
    }

    if (!(infer_stat & 0x2)) {
        VL_PRINTF("FAIL: inference did not complete (stat=0x%08x)\n", infer_stat);
        return 1;
    }

    VL_PRINTF("INFER_STAT = 0x%08x (DONE, cycles=%u)\n",
              infer_stat, infer_stat >> 8);
    VL_PRINTF("Chip top smoke test PASSED\n");
    return 0;
}
