/**
 * Mili BNN-TMR — Zephyr RTOS Driver
 *
 * Add to Zephyr project:
 *   CONFIG_MILI_BNN_TMR=y
 *
 * Device tree binding: compatible = "mili,bnn-tmr"
 */

#include "mili_hal.h"
#include "mili_regs.h"

#ifdef __ZEPHYR__
#include <zephyr/device.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>

#define DT_DRV_COMPAT mili_bnn_tmr

struct mili_zephyr_data {
    const struct device *spi_dev;
    struct spi_config    spi_cfg;
    struct k_sem         irq_sem;
    mili_irq_callback_t  irq_cb;
    void                *irq_user;
};

static int zephyr_reg_xfer(const struct device *dev, uint32_t offset,
                           uint32_t *val, bool write)
{
    struct mili_zephyr_data *data = dev->data;
    uint8_t tx[9] = { write ? 0x02u : 0x01u };
    uint8_t rx[9] = {0};

    sys_put_le32(offset, &tx[1]);
    if (write)
        sys_put_le32(*val, &tx[5]);

    struct spi_buf tx_buf = { .buf = tx, .len = write ? 9u : 5u };
    struct spi_buf rx_buf = { .buf = rx, .len = write ? 9u : 9u };
    struct spi_buf_set txs = { .buffers = &tx_buf, .count = 1 };
    struct spi_buf_set rxs = { .buffers = &rx_buf, .count = 1 };

    if (spi_transceive_dt(&(data->spi_cfg), &txs, &rxs) != 0)
        return MILI_HAL_ERR;
    if (!write)
        *val = sys_get_le32(&rx[5]);
    return MILI_HAL_OK;
}

static int zephyr_read_reg(void *ctx, uint32_t offset, uint32_t *value)
{
    return zephyr_reg_xfer((const struct device *)ctx, offset, value, false);
}

static int zephyr_write_reg(void *ctx, uint32_t offset, uint32_t value)
{
    return zephyr_reg_xfer((const struct device *)ctx, offset, &value, true);
}

static int zephyr_dma_write(void *ctx, uint32_t sram_addr,
                            const void *src, uint32_t len)
{
    const struct device *dev = ctx;
    struct mili_zephyr_data *data = dev->data;
    uint8_t hdr[9] = { 0x03u };
    sys_put_le32(sram_addr, &hdr[1]);
    sys_put_le32(len, &hdr[5]);

    struct spi_buf hdr_buf = { .buf = hdr, .len = 9 };
    struct spi_buf data_buf = { .buf = (void *)src, .len = len };
    struct spi_buf bufs[2] = { hdr_buf, data_buf };
    struct spi_buf_set tx = { .buffers = bufs, .count = 2 };

    return (spi_write_dt(&data->spi_cfg, &tx) == 0) ? MILI_HAL_OK : MILI_HAL_ERR;
}

static int zephyr_dma_read(void *ctx, uint32_t sram_addr,
                           void *dst, uint32_t len)
{
    const struct device *dev = ctx;
    struct mili_zephyr_data *data = dev->data;
    uint8_t hdr[9] = { 0x04u };
    sys_put_le32(sram_addr, &hdr[1]);
    sys_put_le32(len, &hdr[5]);

    struct spi_buf hdr_buf = { .buf = hdr, .len = 9 };
    struct spi_buf data_buf = { .buf = dst, .len = len };
    struct spi_buf tx_bufs[1] = { hdr_buf };
    struct spi_buf rx_bufs[2] = { { .buf = hdr, .len = 9 }, data_buf };
    struct spi_buf_set txs = { .buffers = tx_bufs, .count = 1 };
    struct spi_buf_set rxs = { .buffers = rx_bufs, .count = 2 };

    return (spi_transceive_dt(&data->spi_cfg, &txs, &rxs) == 0)
               ? MILI_HAL_OK : MILI_HAL_ERR;
}

static int zephyr_wait_irq(void *ctx, uint32_t irq_mask, uint32_t timeout_ms)
{
    const struct device *dev = ctx;
    struct mili_zephyr_data *data = dev->data;
    (void)irq_mask;
    return (k_sem_take(&data->irq_sem, K_MSEC(timeout_ms)) == 0)
               ? MILI_HAL_OK : MILI_HAL_ERR_TIMEOUT;
}

static void zephyr_register_irq(void *ctx, mili_irq_callback_t cb, void *user_data)
{
    struct mili_zephyr_data *data = ((const struct device *)ctx)->data;
    data->irq_cb = cb;
    data->irq_user = user_data;
}

static void mili_zephyr_isr(const struct device *dev)
{
    struct mili_zephyr_data *data = dev->data;
    k_sem_give(&data->irq_sem);
    if (data->irq_cb)
        data->irq_cb(MILI_IRQ_INFER_DONE, data->irq_user);
}

static int mili_zephyr_init(const struct device *dev)
{
    struct mili_zephyr_data *data = dev->data;
    k_sem_init(&data->irq_sem, 0, 1);
    return 0;
}

static const mili_hal_ops_t zephyr_hal_ops = {
    .read_reg     = zephyr_read_reg,
    .write_reg    = zephyr_write_reg,
    .dma_write    = zephyr_dma_write,
    .dma_read     = zephyr_dma_read,
    .wait_irq     = zephyr_wait_irq,
    .register_irq = zephyr_register_irq,
};

#define MILI_ZEPHYR_INIT(n) \
    static struct mili_zephyr_data mili_data_##n; \
    DEVICE_DT_INST_DEFINE(n, mili_zephyr_init, NULL, \
                          &mili_data_##n, NULL, POST_KERNEL, \
                          CONFIG_KERNEL_INIT_PRIORITY_DEVICE, NULL);

DT_INST_FOREACH_STATUS_OKAY(MILI_ZEPHYR_INIT)

#endif /* __ZEPHYR__ */

/* Host stub when not building inside Zephyr */
#ifndef __ZEPHYR__
const mili_hal_ops_t mili_zephyr_hal_ops;
#endif
