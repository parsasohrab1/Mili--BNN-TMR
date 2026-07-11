/**
 * Mili BNN-TMR — STM32H7 SPI + DMA HAL (FreeRTOS)
 *
 * Targets STM32H743 as host processor. Uses SPI1 + DMA1 Stream
 * for register access and bulk SRAM transfers to the BNN accelerator.
 *
 * Build with: -DMILI_HAL_FREERTOS and STM32 HAL libraries linked.
 * Host test build uses stub transport (falls back to memcpy).
 */

#include "mili_hal.h"
#include "mili_regs.h"

#include <stdlib.h>
#include <string.h>

#ifdef MILI_HAL_FREERTOS
#include "stm32h7xx_hal.h"
extern SPI_HandleTypeDef hspi1;
extern DMA_HandleTypeDef hdma_spi1_tx;
extern DMA_HandleTypeDef hdma_spi1_rx;
#endif

#define MILI_SPI_TIMEOUT_MS  5000u
#define MILI_DMA_CHUNK       4096u

typedef struct {
    volatile uint32_t irq_pending;
    mili_irq_callback_t irq_cb;
    void               *irq_user;
#ifdef MILI_HAL_FREERTOS
    SPI_HandleTypeDef  *spi;
#endif
} mili_stm32_ctx_t;

static mili_stm32_ctx_t g_stm32;

/* SPI protocol: [CMD:1][ADDR:4][LEN:4][PAYLOAD...] */
#define SPI_CMD_REG_RD  0x01u
#define SPI_CMD_REG_WR  0x02u
#define SPI_CMD_DMA_WR  0x03u
#define SPI_CMD_DMA_RD  0x04u

static int stm32_spi_xfer(const uint8_t *tx, uint8_t *rx, uint32_t len)
{
#ifdef MILI_HAL_FREERTOS
    if (HAL_SPI_TransmitReceive(g_stm32.spi, (uint8_t *)tx, rx, len,
                                MILI_SPI_TIMEOUT_MS) != HAL_OK)
        return MILI_HAL_ERR;
    return MILI_HAL_OK;
#else
    (void)rx;
    (void)tx;
    (void)len;
    return MILI_HAL_OK; /* host stub */
#endif
}

static int stm32_reg_access(uint8_t cmd, uint32_t offset,
                          uint32_t *value, bool is_write)
{
    uint8_t tx[12];
    uint8_t rx[12];
    tx[0] = cmd;
    tx[1] = (uint8_t)(offset);
    tx[2] = (uint8_t)(offset >> 8);
    tx[3] = (uint8_t)(offset >> 16);
    tx[4] = (uint8_t)(offset >> 24);
    if (is_write) {
        tx[5] = (uint8_t)(*value);
        tx[6] = (uint8_t)(*value >> 8);
        tx[7] = (uint8_t)(*value >> 16);
        tx[8] = (uint8_t)(*value >> 24);
    }
    if (stm32_spi_xfer(tx, rx, is_write ? 9u : 5u) != MILI_HAL_OK)
        return MILI_HAL_ERR;
    if (!is_write) {
        *value = (uint32_t)rx[5] | ((uint32_t)rx[6] << 8) |
                 ((uint32_t)rx[7] << 16) | ((uint32_t)rx[8] << 24);
    }
    return MILI_HAL_OK;
}

static int stm32_dma_chunk(uint8_t cmd, uint32_t sram_addr,
                           const void *src, void *dst, uint32_t len)
{
    uint8_t hdr[9];
    hdr[0] = cmd;
    memcpy(&hdr[1], &sram_addr, 4);
    memcpy(&hdr[5], &len, 4);
    if (stm32_spi_xfer(hdr, NULL, 9) != MILI_HAL_OK)
        return MILI_HAL_ERR;

#ifdef MILI_HAL_FREERTOS
    if (cmd == SPI_CMD_DMA_WR) {
        if (HAL_SPI_Transmit_DMA(g_stm32.spi, (uint8_t *)src, len) != HAL_OK)
            return MILI_HAL_ERR;
        while (HAL_SPI_GetState(g_stm32.spi) != HAL_SPI_STATE_READY)
            ;
    } else {
        if (HAL_SPI_Receive_DMA(g_stm32.spi, (uint8_t *)dst, len) != HAL_OK)
            return MILI_HAL_ERR;
        while (HAL_SPI_GetState(g_stm32.spi) != HAL_SPI_STATE_READY)
            ;
    }
#else
    if (cmd == SPI_CMD_DMA_WR && src && dst == NULL)
        (void)src;
    else if (cmd == SPI_CMD_DMA_RD && dst)
        memset(dst, 0, len);
#endif
    return MILI_HAL_OK;
}

static int stm32_read_reg(void *ctx, uint32_t offset, uint32_t *value)
{
    (void)ctx;
    return stm32_reg_access(SPI_CMD_REG_RD, offset, value, false);
}

static int stm32_write_reg(void *ctx, uint32_t offset, uint32_t value)
{
    (void)ctx;
    return stm32_reg_access(SPI_CMD_REG_WR, offset, &value, true);
}

static int stm32_dma_write(void *ctx, uint32_t sram_addr,
                           const void *src, uint32_t len)
{
    (void)ctx;
    const uint8_t *p = (const uint8_t *)src;
    uint32_t remaining = len;
    uint32_t addr = sram_addr;
    while (remaining > 0) {
        uint32_t chunk = (remaining > MILI_DMA_CHUNK) ? MILI_DMA_CHUNK : remaining;
        if (stm32_dma_chunk(SPI_CMD_DMA_WR, addr, p, NULL, chunk) != MILI_HAL_OK)
            return MILI_HAL_ERR;
        p += chunk;
        addr += chunk;
        remaining -= chunk;
    }
    return MILI_HAL_OK;
}

static int stm32_dma_read(void *ctx, uint32_t sram_addr,
                          void *dst, uint32_t len)
{
    (void)ctx;
    uint8_t *p = (uint8_t *)dst;
    uint32_t remaining = len;
    uint32_t addr = sram_addr;
    while (remaining > 0) {
        uint32_t chunk = (remaining > MILI_DMA_CHUNK) ? MILI_DMA_CHUNK : remaining;
        if (stm32_dma_chunk(SPI_CMD_DMA_RD, addr, NULL, p, chunk) != MILI_HAL_OK)
            return MILI_HAL_ERR;
        p += chunk;
        addr += chunk;
        remaining -= chunk;
    }
    return MILI_HAL_OK;
}

static int stm32_wait_irq(void *ctx, uint32_t irq_mask, uint32_t timeout_ms)
{
    mili_stm32_ctx_t *s = (mili_stm32_ctx_t *)ctx;
    for (uint32_t t = 0; t < timeout_ms; t++) {
        if (s->irq_pending & irq_mask) {
            s->irq_pending &= ~irq_mask;
            return MILI_HAL_OK;
        }
#ifdef MILI_HAL_FREERTOS
        vTaskDelay(pdMS_TO_TICKS(1));
#else
        /* host stub: poll CSR */
        uint32_t irq_stat;
        stm32_read_reg(ctx, MILI_REG_IRQ_STAT, &irq_stat);
        if (irq_stat & irq_mask)
            return MILI_HAL_OK;
#endif
    }
    return MILI_HAL_ERR_TIMEOUT;
}

static void stm32_register_irq(void *ctx, mili_irq_callback_t cb, void *user_data)
{
    mili_stm32_ctx_t *s = (mili_stm32_ctx_t *)ctx;
    s->irq_cb = cb;
    s->irq_user = user_data;
}

/* Called from EXTI ISR when MILI_IRQ pin asserts */
void mili_stm32h7_irq_handler(void)
{
    uint32_t irq_stat = MILI_IRQ_INFER_DONE;
    g_stm32.irq_pending |= irq_stat;
    if (g_stm32.irq_cb)
        g_stm32.irq_cb(irq_stat, g_stm32.irq_user);
}

const mili_hal_ops_t mili_stm32h7_hal_ops = {
    .read_reg     = stm32_read_reg,
    .write_reg    = stm32_write_reg,
    .dma_write    = stm32_dma_write,
    .dma_read     = stm32_dma_read,
    .wait_irq     = stm32_wait_irq,
    .register_irq = stm32_register_irq,
};

int mili_stm32h7_hal_init(void **ctx)
{
    memset(&g_stm32, 0, sizeof(g_stm32));
#ifdef MILI_HAL_FREERTOS
    g_stm32.spi = &hspi1;
#endif
    *ctx = &g_stm32;
    return MILI_HAL_OK;
}
