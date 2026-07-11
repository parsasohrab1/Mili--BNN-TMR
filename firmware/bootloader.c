/**
 * Mili BNN-TMR — Chip Bootloader Firmware
 *
 * UART (115200) and SPI slave protocol for field updates.
 * Protocol:
 *   'B' 'N' '1'  — enter bootloader
 *   'W' <addr4> <len4> <data...>  — write SRAM
 *   'G' <addr4> <len4>           — read SRAM (responds with data)
 *   'J' <addr4>                  — jump to application
 *   'E'                          — erase model region
 */

#include "mili_regs.h"

#include <stdint.h>
#include <string.h>

#define BOOT_MAGIC_0  'B'
#define BOOT_MAGIC_1  'N'
#define BOOT_MAGIC_2  '1'

#define CMD_WRITE     'W'
#define CMD_READ      'G'
#define CMD_JUMP      'J'
#define CMD_ERASE     'E'

#define BOOT_UART_BAUD 115200u
#define BOOT_SPI_CS    0

typedef enum {
    BOOT_IFACE_UART = 0,
    BOOT_IFACE_SPI  = 1,
} boot_iface_t;

typedef struct {
    boot_iface_t iface;
    uint8_t     *sram_base;
    uint32_t     sram_size;
    uint32_t     app_entry;
    volatile int running;
} boot_ctx_t;

static boot_ctx_t g_boot;

/* Platform I/O — implemented per target (STM32 / simulator) */
extern int  boot_uart_rx_byte(uint8_t *byte);
extern int  boot_uart_tx(const uint8_t *data, uint32_t len);
extern int  boot_spi_rx(uint8_t *data, uint32_t len);
extern int  boot_spi_tx(const uint8_t *data, uint32_t len);
extern void boot_jump_to_app(uint32_t entry);

static int boot_read_bytes(uint8_t *buf, uint32_t len)
{
    for (uint32_t i = 0; i < len; i++) {
        int rc = (g_boot.iface == BOOT_IFACE_UART)
                     ? boot_uart_rx_byte(&buf[i])
                     : (boot_spi_rx(&buf[i], 1) == 1 ? 0 : -1);
        if (rc != 0)
            return -1;
    }
    return 0;
}

static int boot_write_bytes(const uint8_t *buf, uint32_t len)
{
    return (g_boot.iface == BOOT_IFACE_UART)
               ? boot_uart_tx(buf, len)
               : boot_spi_tx(buf, len);
}

static uint32_t boot_read_u32(void)
{
    uint8_t b[4];
    boot_read_bytes(b, 4);
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
           ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
}

static int boot_cmd_write(void)
{
    uint32_t addr = boot_read_u32();
    uint32_t len  = boot_read_u32();
    uint32_t offset = addr - MILI_SRAM_BASE;

    if (offset + len > g_boot.sram_size)
        return -1;

    return boot_read_bytes(g_boot.sram_base + offset, len);
}

static int boot_cmd_read(void)
{
    uint32_t addr = boot_read_u32();
    uint32_t len  = boot_read_u32();
    uint32_t offset = addr - MILI_SRAM_BASE;

    if (offset + len > g_boot.sram_size)
        return -1;

    return boot_write_bytes(g_boot.sram_base + offset, len);
}

static int boot_cmd_erase(void)
{
    memset(g_boot.sram_base + MILI_SRAM_MODEL_OFF, 0xFF, MILI_SRAM_MODEL_SIZE);
    return 0;
}

static void boot_process_cmd(uint8_t cmd)
{
    switch (cmd) {
    case CMD_WRITE: boot_cmd_write(); break;
    case CMD_READ:  boot_cmd_read();  break;
    case CMD_ERASE: boot_cmd_erase(); break;
    case CMD_JUMP:
        g_boot.app_entry = boot_read_u32();
        g_boot.running = 0;
        break;
    default:
        break;
    }
}

static int boot_check_magic(void)
{
    uint8_t m[3];
    if (boot_read_bytes(m, 3) != 0)
        return 0;
    return (m[0] == BOOT_MAGIC_0 && m[1] == BOOT_MAGIC_1 && m[2] == BOOT_MAGIC_2);
}

int mili_bootloader_init(boot_iface_t iface, uint8_t *sram, uint32_t sram_size)
{
    g_boot.iface     = iface;
    g_boot.sram_base = sram;
    g_boot.sram_size = sram_size;
    g_boot.app_entry = MILI_SRAM_BASE;
    g_boot.running   = 1;
    return 0;
}

void mili_bootloader_run(void)
{
    const uint8_t ack[] = "MILI-BOOT-v1\r\n";
    boot_write_bytes(ack, sizeof(ack) - 1);

    while (g_boot.running) {
        if (!boot_check_magic())
            continue;
        uint8_t cmd;
        if (boot_read_bytes(&cmd, 1) != 0)
            continue;
        boot_process_cmd(cmd);
    }

    boot_jump_to_app(g_boot.app_entry);
}

/* Simulator stubs for host testing */
#ifdef MILI_BOOT_HOST
static uint8_t g_host_sram[MILI_SRAM_SIZE];

int boot_uart_rx_byte(uint8_t *byte)  { (void)byte; return -1; }
int boot_uart_tx(const uint8_t *d, uint32_t n) { (void)d; (void)n; return (int)n; }
int boot_spi_rx(uint8_t *d, uint32_t n)  { (void)d; (void)n; return (int)n; }
int boot_spi_tx(const uint8_t *d, uint32_t n) { (void)d; (void)n; return (int)n; }
void boot_jump_to_app(uint32_t entry) { (void)entry; g_boot.running = 0; }

int main(void)
{
    mili_bootloader_init(BOOT_IFACE_SPI, g_host_sram, sizeof(g_host_sram));
    g_boot.running = 0; /* exit immediately in host test */
    return 0;
}
#endif
