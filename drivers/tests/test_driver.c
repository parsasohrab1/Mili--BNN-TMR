/**
 * Mili BNN-TMR — Driver integration tests (FPGA emulator / simulator)
 */

#include "mili_chip.h"
#include "mili_regs.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

static volatile int g_irq_fired = 0;

static void test_irq_handler(uint32_t irq_stat, void *user_data)
{
    (void)user_data;
    if (irq_stat & MILI_IRQ_INFER_DONE)
        g_irq_fired = 1;
}

static void write_dummy_mili(const char *path)
{
    FILE *f = fopen(path, "wb");
    const char magic[] = "MILI";
    uint32_t hdr[13] = {0};
    memcpy(hdr, magic, 4);
    hdr[1] = 1;    /* version */
    hdr[2] = 1;    /* layers */
    fwrite(hdr, 1, 64, f);
    uint8_t layer[32] = {0};
    fwrite(layer, 1, 32, f);
    fclose(f);
}

static int test_chip_open_close(void)
{
    mili_chip_t *chip = mili_chip_open(MILI_IFACE_SPI);
    assert(chip != NULL);
    mili_chip_close(chip);
    printf("  [PASS] open/close\n");
    return 0;
}

static int test_dma_transfer(void)
{
    mili_chip_t *chip = mili_chip_open(MILI_IFACE_SPI);
    assert(chip != NULL);

    uint8_t tx[256], rx[256];
    for (int i = 0; i < 256; i++)
        tx[i] = (uint8_t)i;

    int rc = mili_chip_dma_write(chip, MILI_SRAM_ADDR(MILI_SRAM_INPUT_OFF),
                                 tx, sizeof(tx));
    assert(rc == MILI_OK);

    memset(rx, 0, sizeof(rx));
    rc = mili_chip_dma_read(chip, MILI_SRAM_ADDR(MILI_SRAM_INPUT_OFF),
                            rx, sizeof(rx));
    assert(rc == MILI_OK);
    assert(memcmp(tx, rx, sizeof(tx)) == 0);

    mili_chip_close(chip);
    printf("  [PASS] DMA write/read\n");
    return 0;
}

static int test_power_mode(void)
{
    mili_chip_t *chip = mili_chip_open(MILI_IFACE_SPI);
    mili_power_state_t state;

    assert(mili_chip_set_power_mode(chip, MILI_POWER_TURBO) == MILI_OK);
    assert(mili_chip_get_power_state(chip, &state) == MILI_OK);
    assert(state.mode == MILI_POWER_TURBO);
    assert(state.frequency_mhz == 800);

    mili_chip_close(chip);
    printf("  [PASS] power mode\n");
    return 0;
}

static int test_load_and_infer(const char *model_path)
{
    mili_chip_t *chip = mili_chip_open(MILI_IFACE_SPI);
    mili_inference_result_t result;
    int8_t input[784];

    mili_chip_register_irq(chip, test_irq_handler, NULL);
    assert(mili_chip_load_model(chip, model_path) == MILI_OK);

    memset(input, 0, sizeof(input));
    result.output_size = 10;
    assert(mili_chip_infer(chip, input, sizeof(input), 1, &result) == MILI_OK);
    assert(result.output != NULL);
    assert(result.latency_ms >= 0.0f);
    assert(g_irq_fired == 1);

    mili_chip_close(chip);
    printf("  [PASS] load model + infer + IRQ\n");
    return 0;
}

int main(int argc, char **argv)
{
    const char *model = (argc > 1) ? argv[1] : "test_model.mili";

    printf("Mili BNN-TMR Driver Integration Tests\n");
    printf("======================================\n");

    write_dummy_mili(model);

    test_chip_open_close();
    test_dma_transfer();
    test_power_mode();
    test_load_and_infer(model);

    printf("\nAll driver tests PASSED.\n");
    return 0;
}
