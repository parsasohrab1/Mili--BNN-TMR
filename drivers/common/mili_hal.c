/**
 * Mili BNN-TMR — HAL register and DMA helpers
 */

#include "mili_hal.h"
#include "mili_regs.h"

int mili_hal_reg_read(void *ctx, const mili_hal_ops_t *ops,
                      uint32_t offset, uint32_t *value)
{
    if (!ops || !ops->read_reg || !value)
        return MILI_HAL_ERR;
    return ops->read_reg(ctx, offset, value);
}

int mili_hal_reg_write(void *ctx, const mili_hal_ops_t *ops,
                       uint32_t offset, uint32_t value)
{
    if (!ops || !ops->write_reg)
        return MILI_HAL_ERR;
    return ops->write_reg(ctx, offset, value);
}

int mili_hal_dma_to_sram(void *ctx, const mili_hal_ops_t *ops,
                         uint32_t sram_addr, const void *src, uint32_t len)
{
    if (!ops || !ops->dma_write || !src || len == 0)
        return MILI_HAL_ERR;
    return ops->dma_write(ctx, sram_addr, src, len);
}

int mili_hal_dma_from_sram(void *ctx, const mili_hal_ops_t *ops,
                           uint32_t sram_addr, void *dst, uint32_t len)
{
    if (!ops || !ops->dma_read || !dst || len == 0)
        return MILI_HAL_ERR;
    return ops->dma_read(ctx, sram_addr, dst, len);
}

int mili_hal_wait_infer_done(void *ctx, const mili_hal_ops_t *ops,
                             uint32_t timeout_ms)
{
    uint32_t stat;
    int rc;

    if (!ops)
        return MILI_HAL_ERR;

    if (ops->wait_irq) {
        rc = ops->wait_irq(ctx, MILI_IRQ_INFER_DONE, timeout_ms);
        if (rc == MILI_HAL_OK)
            return MILI_HAL_OK;
    }

    /* Polling fallback */
    for (uint32_t t = 0; t < timeout_ms; t++) {
        rc = mili_hal_reg_read(ctx, ops, MILI_REG_INFER_STAT, &stat);
        if (rc != MILI_HAL_OK)
            return rc;
        if (stat & MILI_INFER_DONE)
            return MILI_HAL_OK;
        if (stat & MILI_INFER_ERR)
            return MILI_HAL_ERR;
    }
    return MILI_HAL_ERR_TIMEOUT;
}
