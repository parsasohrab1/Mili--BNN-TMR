/**
 * Mili BNN-TMR — Hardware Abstraction Layer
 *
 * Platform drivers implement these ops for SPI, PCIe, or simulator backends.
 */

#ifndef MILI_HAL_H
#define MILI_HAL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MILI_HAL_OK           0
#define MILI_HAL_ERR          -1
#define MILI_HAL_ERR_TIMEOUT  -2
#define MILI_HAL_ERR_DMA      -3

typedef void (*mili_irq_callback_t)(uint32_t irq_stat, void *user_data);

typedef struct mili_hal_ops {
    int (*read_reg)(void *ctx, uint32_t offset, uint32_t *value);
    int (*write_reg)(void *ctx, uint32_t offset, uint32_t value);
    int (*dma_write)(void *ctx, uint32_t sram_addr, const void *src, uint32_t len);
    int (*dma_read)(void *ctx, uint32_t sram_addr, void *dst, uint32_t len);
    int (*wait_irq)(void *ctx, uint32_t irq_mask, uint32_t timeout_ms);
    void (*register_irq)(void *ctx, mili_irq_callback_t cb, void *user_data);
} mili_hal_ops_t;

/* Register access helpers (CSR offsets from mili_regs.h) */
int mili_hal_reg_read(void *ctx, const mili_hal_ops_t *ops,
                      uint32_t offset, uint32_t *value);
int mili_hal_reg_write(void *ctx, const mili_hal_ops_t *ops,
                       uint32_t offset, uint32_t value);

/* DMA transfer to/from chip SRAM */
int mili_hal_dma_to_sram(void *ctx, const mili_hal_ops_t *ops,
                         uint32_t sram_addr, const void *src, uint32_t len);
int mili_hal_dma_from_sram(void *ctx, const mili_hal_ops_t *ops,
                           uint32_t sram_addr, void *dst, uint32_t len);

/* Wait for inference completion IRQ */
int mili_hal_wait_infer_done(void *ctx, const mili_hal_ops_t *ops,
                             uint32_t timeout_ms);

#ifdef __cplusplus
}
#endif

#endif /* MILI_HAL_H */
