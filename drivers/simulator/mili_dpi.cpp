/**
 * Verilator DPI bridge — connects RTL mili_chip_top to simulator HAL
 *
 * Compile with Verilator testbench:
 *   verilator ... --dpi-hdr-only mili_dpi.cpp
 */

#include <cstdint>
#include <cstring>

extern "C" {
#include "mili_regs.h"

uint32_t mili_sim_csr_read(uint32_t offset);
void     mili_sim_csr_write(uint32_t offset, uint32_t value);
}

extern "C" uint32_t dpi_mili_csr_read(uint32_t offset)
{
    return mili_sim_csr_read(offset);
}

extern "C" void dpi_mili_csr_write(uint32_t offset, uint32_t value)
{
    mili_sim_csr_write(offset, value);
}

extern "C" void dpi_mili_dma_write(uint32_t sram_addr,
                                   const uint8_t *data, uint32_t len)
{
    static uint8_t sram[256 * 1024];
    uint32_t off = sram_addr - MILI_SRAM_BASE;
    if (off + len <= sizeof(sram))
        std::memcpy(sram + off, data, len);
}

extern "C" void dpi_mili_dma_read(uint32_t sram_addr,
                                  uint8_t *data, uint32_t len)
{
    static uint8_t sram[256 * 1024];
    uint32_t off = sram_addr - MILI_SRAM_BASE;
    if (off + len <= sizeof(sram))
        std::memcpy(data, sram + off, len);
}

extern "C" void dpi_mili_irq_notify(uint32_t irq_stat)
{
    (void)irq_stat;
    /* Forward to HAL IRQ handler in testbench */
}
