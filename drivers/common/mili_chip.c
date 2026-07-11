/**
 * Mili BNN-TMR — Full C API implementation
 */

#include "../../api/cpp/include/mili_chip.h"
#include "mili_hal.h"
#include "mili_regs.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Platform HAL factories (defined per backend) */
extern const mili_hal_ops_t mili_sim_hal_ops;
extern int mili_sim_hal_init(void **ctx);

#ifdef MILI_HAL_FREERTOS
extern const mili_hal_ops_t mili_stm32h7_hal_ops;
extern int mili_stm32h7_hal_init(void **ctx);
#endif

#ifdef MILI_HAL_LINUX
extern const mili_hal_ops_t mili_pcie_hal_ops;
extern int mili_pcie_hal_init(void **ctx);
#endif

struct mili_chip {
    mili_interface_t       iface;
    const mili_hal_ops_t  *ops;
    void                  *hal_ctx;
    mili_power_mode_t      power_mode;
    uint32_t               model_addr;
    uint32_t               input_addr;
    uint32_t               output_addr;
    uint32_t               model_size;
    uint32_t               output_capacity;
    int8_t                *output_buf;
    bool                   model_loaded;
    mili_irq_callback_t    irq_cb;
    void                  *irq_user_data;
};

static int chip_wait_ready(mili_chip_t *chip)
{
    uint32_t status;
    for (int i = 0; i < 1000; i++) {
        if (mili_hal_reg_read(chip->hal_ctx, chip->ops,
                              MILI_REG_STATUS, &status) != MILI_HAL_OK)
            return MILI_ERR_IO;
        if (status & MILI_STATUS_READY)
            return MILI_OK;
    }
    return MILI_ERR_TIMEOUT;
}

static int chip_enable_irq(mili_chip_t *chip, uint32_t mask)
{
    return mili_hal_reg_write(chip->hal_ctx, chip->ops,
                              MILI_REG_IRQ_EN, mask);
}

static void chip_irq_dispatch(uint32_t irq_stat, void *user_data)
{
    mili_chip_t *chip = (mili_chip_t *)user_data;
    if (chip && chip->irq_cb)
        chip->irq_cb(irq_stat, chip->irq_user_data);
}

mili_chip_t *mili_chip_open(mili_interface_t iface)
{
    mili_chip_t *chip = calloc(1, sizeof(mili_chip_t));
    if (!chip)
        return NULL;

    chip->iface = iface;
    chip->power_mode = MILI_POWER_NORMAL;
    chip->model_addr = MILI_SRAM_ADDR(MILI_SRAM_MODEL_OFF);
    chip->input_addr = MILI_SRAM_ADDR(MILI_SRAM_INPUT_OFF);
    chip->output_addr = MILI_SRAM_ADDR(MILI_SRAM_OUTPUT_OFF);
    chip->output_capacity = 4096;
    chip->output_buf = malloc(chip->output_capacity);
    if (!chip->output_buf) {
        free(chip);
        return NULL;
    }

    int rc = MILI_ERR_IO;
    switch (iface) {
    case MILI_IFACE_SPI:
#ifdef MILI_HAL_FREERTOS
        rc = mili_stm32h7_hal_init(&chip->hal_ctx);
        chip->ops = &mili_stm32h7_hal_ops;
#else
        rc = mili_sim_hal_init(&chip->hal_ctx);
        chip->ops = &mili_sim_hal_ops;
#endif
        break;
    case MILI_IFACE_PCIE:
#ifdef MILI_HAL_LINUX
        rc = mili_pcie_hal_init(&chip->hal_ctx);
        chip->ops = &mili_pcie_hal_ops;
#else
        rc = mili_sim_hal_init(&chip->hal_ctx);
        chip->ops = &mili_sim_hal_ops;
#endif
        break;
    default:
        rc = MILI_ERR;
        break;
    }

    if (rc != MILI_HAL_OK) {
        free(chip->output_buf);
        free(chip);
        return NULL;
    }

    if (chip->ops->register_irq)
        chip->ops->register_irq(chip->hal_ctx, chip_irq_dispatch, chip);

    chip_enable_irq(chip, MILI_IRQ_INFER_DONE | MILI_IRQ_INFER_ERR);
    mili_hal_reg_write(chip->hal_ctx, chip->ops, MILI_REG_TMR_CTRL, MILI_TMR_EN);
    chip_wait_ready(chip);

    return chip;
}

void mili_chip_close(mili_chip_t *chip)
{
    if (!chip)
        return;
    free(chip->output_buf);
    free(chip);
}

void mili_chip_register_irq(mili_chip_t *chip,
                          mili_irq_callback_t cb, void *user_data)
{
    if (!chip)
        return;
    chip->irq_cb = cb;
    chip->irq_user_data = user_data;
}

int mili_chip_load_model(mili_chip_t *chip, const char *model_path)
{
    FILE *f;
    long fsize;
    uint8_t *buf;

    if (!chip || !model_path)
        return MILI_ERR;

    f = fopen(model_path, "rb");
    if (!f)
        return MILI_ERR_IO;

    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return MILI_ERR_IO;
    }
    fsize = ftell(f);
    if (fsize <= 0 || fsize > (long)MILI_SRAM_MODEL_SIZE) {
        fclose(f);
        return MILI_ERR;
    }
    rewind(f);

    buf = malloc((size_t)fsize);
    if (!buf) {
        fclose(f);
        return MILI_ERR;
    }
    if (fread(buf, 1, (size_t)fsize, f) != (size_t)fsize) {
        free(buf);
        fclose(f);
        return MILI_ERR_IO;
    }
    fclose(f);

    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_MODEL_ADDR, chip->model_addr) != MILI_HAL_OK) {
        free(buf);
        return MILI_ERR_IO;
    }

    if (mili_hal_dma_to_sram(chip->hal_ctx, chip->ops,
                             chip->model_addr, buf, (uint32_t)fsize) != MILI_HAL_OK) {
        free(buf);
        return MILI_ERR_DMA;
    }

    free(buf);
    chip->model_size = (uint32_t)fsize;
    chip->model_loaded = true;
    return MILI_OK;
}

int mili_chip_infer(mili_chip_t *chip,
                    const int8_t *input,
                    uint32_t input_size,
                    uint32_t batch_size,
                    mili_inference_result_t *result)
{
    uint32_t infer_stat, dpm_stat;
    int rc;

    if (!chip || !input || !result)
        return MILI_ERR;
    if (!chip->model_loaded)
        return MILI_ERR;

    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_INPUT_ADDR, chip->input_addr) != MILI_HAL_OK)
        return MILI_ERR_IO;
    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_OUTPUT_ADDR, chip->output_addr) != MILI_HAL_OK)
        return MILI_ERR_IO;
    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_BATCH_SIZE, batch_size) != MILI_HAL_OK)
        return MILI_ERR_IO;

    if (mili_hal_dma_to_sram(chip->hal_ctx, chip->ops,
                             chip->input_addr, input,
                             input_size) != MILI_HAL_OK)
        return MILI_ERR_DMA;

    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_INFER_CTRL, MILI_INFER_START) != MILI_HAL_OK)
        return MILI_ERR_IO;

    rc = mili_hal_wait_infer_done(chip->hal_ctx, chip->ops, 10000);
    if (rc != MILI_HAL_OK)
        return (rc == MILI_HAL_ERR_TIMEOUT) ? MILI_ERR_TIMEOUT : MILI_ERR;

    if (result->output_size > chip->output_capacity)
        result->output_size = chip->output_capacity;

    if (mili_hal_dma_from_sram(chip->hal_ctx, chip->ops,
                               chip->output_addr, chip->output_buf,
                               result->output_size) != MILI_HAL_OK)
        return MILI_ERR_DMA;

    result->output = chip->output_buf;

    mili_hal_reg_read(chip->hal_ctx, chip->ops, MILI_REG_INFER_STAT, &infer_stat);
    mili_hal_reg_read(chip->hal_ctx, chip->ops, MILI_REG_DPM_STAT, &dpm_stat);

    uint32_t cycles = (infer_stat >> MILI_INFER_CYCLE_SHIFT) & MILI_INFER_CYCLE_MASK;
    uint32_t freq = (dpm_stat >> MILI_DPM_CUR_FREQ_SHIFT) & MILI_DPM_CUR_FREQ_MASK;
    if (freq == 0)
        freq = 400;
    result->latency_ms = (float)cycles / (float)freq / 1000.0f;
    result->power_mode = (mili_power_mode_t)(dpm_stat & MILI_DPM_MODE_MASK);
    result->tmr_corrected = false;

    return MILI_OK;
}

int mili_chip_get_power_state(mili_chip_t *chip, mili_power_state_t *state)
{
    uint32_t dpm_stat;
    if (!chip || !state)
        return MILI_ERR;

    if (mili_hal_reg_read(chip->hal_ctx, chip->ops,
                          MILI_REG_DPM_STAT, &dpm_stat) != MILI_HAL_OK)
        return MILI_ERR_IO;

    state->mode = (mili_power_mode_t)(dpm_stat & MILI_DPM_MODE_MASK);
    state->frequency_mhz = (dpm_stat >> MILI_DPM_CUR_FREQ_SHIFT) & MILI_DPM_CUR_FREQ_MASK;

    switch (state->mode) {
    case MILI_POWER_SLEEP: state->power_w = 0.01f; break;
    case MILI_POWER_IDLE:  state->power_w = 5.0f;  break;
    case MILI_POWER_TURBO: state->power_w = 48.0f; break;
    default:               state->power_w = 30.0f; break;
    }
    return MILI_OK;
}

int mili_chip_set_power_mode(mili_chip_t *chip, mili_power_mode_t mode)
{
    uint32_t ctrl;
    if (!chip)
        return MILI_ERR;

    ctrl = MILI_DPM_SET_MODE(mode);
    if (mili_hal_reg_write(chip->hal_ctx, chip->ops,
                           MILI_REG_DPM_CTRL, ctrl) != MILI_HAL_OK)
        return MILI_ERR_IO;

    chip->power_mode = mode;
    return MILI_OK;
}

int mili_chip_dma_write(mili_chip_t *chip, uint32_t sram_addr,
                        const void *data, uint32_t len)
{
    if (!chip)
        return MILI_ERR;
    return (mili_hal_dma_to_sram(chip->hal_ctx, chip->ops,
                                 sram_addr, data, len) == MILI_HAL_OK)
               ? MILI_OK : MILI_ERR_DMA;
}

int mili_chip_dma_read(mili_chip_t *chip, uint32_t sram_addr,
                       void *data, uint32_t len)
{
    if (!chip)
        return MILI_ERR;
    return (mili_hal_dma_from_sram(chip->hal_ctx, chip->ops,
                                   sram_addr, data, len) == MILI_HAL_OK)
               ? MILI_OK : MILI_ERR_DMA;
}
