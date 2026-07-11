/**
 * STM32H7 Host Bridge Firmware — SPI slave to Mili BNN-TMR chip
 *
 * Protocol handler for PC/Python bridge over USB-UART.
 * Forwards commands to BNN chip via SPI1 + DMA.
 *
 * Build: add to STM32CubeIDE project with HAL SPI + DMA enabled.
 */

#include "mili_regs.h"
#include <stdint.h>
#include <string.h>

#define BRIDGE_SYNC0  'M'
#define BRIDGE_SYNC1  'I'

#define CMD_REG_RD   0x01
#define CMD_REG_WR   0x02
#define CMD_DMA_WR   0x03
#define CMD_DMA_RD   0x04
#define CMD_DPM      0x05
#define CMD_INFER    0x06

extern int  mili_spi_reg_read(uint32_t offset, uint32_t *val);
extern int  mili_spi_reg_write(uint32_t offset, uint32_t val);
extern int  mili_spi_dma_write(uint32_t sram_addr, const uint8_t *data, uint32_t len);
extern int  mili_spi_dma_read(uint32_t sram_addr, uint8_t *data, uint32_t len);
extern void mili_irq_enable(void);

static int bridge_tx(const uint8_t *data, uint32_t len)
{
    extern int host_uart_tx(const uint8_t *, uint32_t);
    return host_uart_tx(data, len);
}

static int bridge_rx(uint8_t *data, uint32_t len)
{
    extern int host_uart_rx(uint8_t *, uint32_t);
    return host_uart_rx(data, len);
}

static void bridge_reply(uint8_t cmd, const uint8_t *payload, uint32_t len)
{
    uint8_t hdr[7] = { BRIDGE_SYNC0, BRIDGE_SYNC1, cmd };
    memcpy(&hdr[3], &len, 4);
    bridge_tx(hdr, 7);
    if (len > 0)
        bridge_tx(payload, len);
}

void mili_host_bridge_init(void)
{
    mili_irq_enable();
}

void mili_host_bridge_poll(void)
{
    uint8_t sync[2];
    if (bridge_rx(sync, 2) != 0)
        return;
    if (sync[0] != BRIDGE_SYNC0 || sync[1] != BRIDGE_SYNC1)
        return;

    uint8_t cmd;
    uint32_t plen;
    bridge_rx(&cmd, 1);
    bridge_rx((uint8_t *)&plen, 4);

    uint8_t payload[4096];
    if (plen > sizeof(payload))
        return;
    if (plen > 0)
        bridge_rx(payload, plen);

    switch (cmd) {
    case CMD_REG_RD: {
        uint32_t offset, val;
        memcpy(&offset, payload, 4);
        mili_spi_reg_read(offset, &val);
        bridge_reply(cmd, (uint8_t *)&val, 4);
        break;
    }
    case CMD_REG_WR: {
        uint32_t offset, val;
        memcpy(&offset, payload, 4);
        memcpy(&val, payload + 4, 4);
        mili_spi_reg_write(offset, val);
        bridge_reply(cmd, NULL, 0);
        break;
    }
    case CMD_DMA_WR: {
        uint32_t addr, len;
        memcpy(&addr, payload, 4);
        memcpy(&len, payload + 4, 4);
        mili_spi_dma_write(addr, payload + 8, len);
        bridge_reply(cmd, NULL, 0);
        break;
    }
    case CMD_DMA_RD: {
        uint32_t addr, len;
        memcpy(&addr, payload, 4);
        memcpy(&len, payload + 4, 4);
        mili_spi_dma_read(addr, payload, len);
        bridge_reply(cmd, payload, len);
        break;
    }
    case CMD_DPM: {
        uint8_t mode = payload[0];
        mili_spi_reg_write(MILI_REG_DPM_CTRL, mode);
        uint8_t resp[6] = { 2, mode, 0, 0, 0, 0 };
        bridge_reply(cmd, resp, 6);
        break;
    }
    case CMD_INFER: {
        uint32_t batch;
        memcpy(&batch, payload, 4);
        mili_spi_reg_write(MILI_REG_BATCH_SIZE, batch);
        mili_spi_reg_write(MILI_REG_INFER_CTRL, MILI_INFER_START);
        bridge_reply(cmd, NULL, 0);
        break;
    }
    default:
        break;
    }
}

/* EXTI callback — forward IRQ to host */
void mili_infer_done_isr(void)
{
    uint8_t irq_msg[] = { BRIDGE_SYNC0, BRIDGE_SYNC1, 0xFF, 0, 0, 0, 1, 1 };
    bridge_tx(irq_msg, sizeof(irq_msg));
}
