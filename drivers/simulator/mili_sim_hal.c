/**
 * Mili BNN-TMR — Simulator HAL (FPGA emulator / host testing)
 *
 * Memory-mapped register file backed by simulated chip state.
 * Connects to Verilator RTL via optional DPI bridge.
 */

#include "mili_hal.h"
#include "mili_regs.h"

#include <stdlib.h>
#include <string.h>

#define MILI_SIM_CSR_WORDS  32
#define MILI_SIM_SRAM_SIZE  (256u * 1024u)

typedef struct {
    uint32_t            csr[MILI_SIM_CSR_WORDS];
    uint8_t            *sram;
    mili_irq_callback_t irq_cb;
    void               *irq_user;
    volatile uint32_t   irq_pending;
} mili_sim_ctx_t;

static mili_sim_ctx_t g_sim;

static int sim_read_reg(void *ctx, uint32_t offset, uint32_t *value)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    uint32_t idx = offset / 4u;
    if (idx >= MILI_SIM_CSR_WORDS)
        return MILI_HAL_ERR;
    *value = sim->csr[idx];
    return MILI_HAL_OK;
}

static int sim_write_reg(void *ctx, uint32_t offset, uint32_t value)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    uint32_t idx = offset / 4u;
    if (idx >= MILI_SIM_CSR_WORDS)
        return MILI_HAL_ERR;

    sim->csr[idx] = value;

    /* STATUS: always ready */
    sim->csr[MILI_REG_STATUS / 4] = MILI_STATUS_READY | MILI_STATUS_SRAM_RDY | MILI_STATUS_TMR_ACT;

    /* INFER_START → simulate completion */
    if (offset == MILI_REG_INFER_CTRL && (value & MILI_INFER_START)) {
        uint32_t batch = sim->csr[MILI_REG_BATCH_SIZE / 4];
        if (batch == 0)
            batch = 1;
        uint32_t cycles = 14u * 10u * batch;
        sim->csr[MILI_REG_INFER_STAT / 4] = MILI_INFER_DONE | (cycles << MILI_INFER_CYCLE_SHIFT);
        sim->irq_pending |= MILI_IRQ_INFER_DONE;
        if (sim->irq_cb)
            sim->irq_cb(MILI_IRQ_INFER_DONE, sim->irq_user);
    }

    /* DPM_CTRL */
    if (offset == MILI_REG_DPM_CTRL) {
        uint32_t mode = value & MILI_DPM_MODE_MASK;
        uint32_t freq = (mode == MILI_DPM_TURBO) ? 800u :
                        (mode == MILI_DPM_IDLE)  ? 100u :
                        (mode == MILI_DPM_SLEEP) ? 0u : 400u;
        sim->csr[MILI_REG_DPM_STAT / 4] = mode | (freq << MILI_DPM_CUR_FREQ_SHIFT);
    }

    return MILI_HAL_OK;
}

static int sim_dma_write(void *ctx, uint32_t sram_addr, const void *src, uint32_t len)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    uint32_t offset = sram_addr - MILI_SRAM_BASE;
    if (!src || offset + len > MILI_SIM_SRAM_SIZE)
        return MILI_HAL_ERR;
    memcpy(sim->sram + offset, src, len);
    return MILI_HAL_OK;
}

static int sim_dma_read(void *ctx, uint32_t sram_addr, void *dst, uint32_t len)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    uint32_t offset = sram_addr - MILI_SRAM_BASE;
    if (!dst || offset + len > MILI_SIM_SRAM_SIZE)
        return MILI_HAL_ERR;
    memcpy(dst, sim->sram + offset, len);
    return MILI_HAL_OK;
}

static int sim_wait_irq(void *ctx, uint32_t irq_mask, uint32_t timeout_ms)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    (void)timeout_ms;
    if (sim->irq_pending & irq_mask) {
        sim->irq_pending &= ~irq_mask;
        return MILI_HAL_OK;
    }
    return MILI_HAL_OK; /* simulator completes instantly */
}

static void sim_register_irq(void *ctx, mili_irq_callback_t cb, void *user_data)
{
    mili_sim_ctx_t *sim = (mili_sim_ctx_t *)ctx;
    sim->irq_cb = cb;
    sim->irq_user = user_data;
}

const mili_hal_ops_t mili_sim_hal_ops = {
    .read_reg     = sim_read_reg,
    .write_reg    = sim_write_reg,
    .dma_write    = sim_dma_write,
    .dma_read     = sim_dma_read,
    .wait_irq     = sim_wait_irq,
    .register_irq = sim_register_irq,
};

int mili_sim_hal_init(void **ctx)
{
    memset(&g_sim, 0, sizeof(g_sim));
    g_sim.sram = calloc(1, MILI_SIM_SRAM_SIZE);
    if (!g_sim.sram)
        return MILI_HAL_ERR;
    g_sim.csr[MILI_REG_STATUS / 4] = MILI_STATUS_READY | MILI_STATUS_SRAM_RDY;
    g_sim.csr[MILI_REG_DPM_STAT / 4] = MILI_DPM_NORMAL | (400u << MILI_DPM_CUR_FREQ_SHIFT);
    *ctx = &g_sim;
    return MILI_HAL_OK;
}

/* Expose CSR/SRAM for Verilator DPI */
uint32_t mili_sim_csr_read(uint32_t offset)
{
    uint32_t val = 0;
    sim_read_reg(&g_sim, offset, &val);
    return val;
}

void mili_sim_csr_write(uint32_t offset, uint32_t value)
{
    sim_write_reg(&g_sim, offset, value);
}
