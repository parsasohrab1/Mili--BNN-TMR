/**
 * Mili BNN-TMR Edge AI Accelerator - C/C++ API
 *
 * High-level interface for BNN inference on the systolic array
 * with TMR fault tolerance. Intended for integration with STM32H7
 * host via PCIe Gen4 or SPI.
 */

#ifndef MILI_CHIP_H
#define MILI_CHIP_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MILI_PE_COUNT       64
#define MILI_PE_ARRAY_DIM   8
#define MILI_MAX_POWER_W    50.0f
#define MILI_SRAM_MB        32

#define MILI_OK             0
#define MILI_ERR            -1
#define MILI_ERR_IO         -2
#define MILI_ERR_TIMEOUT    -3
#define MILI_ERR_DMA        -4

typedef enum {
    MILI_IFACE_PCIE = 0,
    MILI_IFACE_SPI  = 1,
} mili_interface_t;

typedef enum {
    MILI_POWER_SLEEP  = 0,
    MILI_POWER_IDLE   = 1,
    MILI_POWER_NORMAL = 2,
    MILI_POWER_TURBO  = 3,
} mili_power_mode_t;

typedef struct {
    mili_power_mode_t mode;
    uint32_t frequency_mhz;
    float power_w;
} mili_power_state_t;

typedef struct {
    int8_t  *output;
    uint32_t output_size;
    float    latency_ms;
    mili_power_mode_t power_mode;
    bool     tmr_corrected;
} mili_inference_result_t;

typedef void (*mili_irq_callback_t)(uint32_t irq_stat, void *user_data);

typedef struct mili_chip mili_chip_t;

/* Lifecycle */
mili_chip_t *mili_chip_open(mili_interface_t iface);
void         mili_chip_close(mili_chip_t *chip);

/* IRQ */
void mili_chip_register_irq(mili_chip_t *chip,
                            mili_irq_callback_t cb, void *user_data);

/* Model management */
int mili_chip_load_model(mili_chip_t *chip, const char *model_path);

/* Inference */
int mili_chip_infer(
    mili_chip_t *chip,
    const int8_t *input,
    uint32_t input_size,
    uint32_t batch_size,
    mili_inference_result_t *result
);

/* DMA (direct SRAM access) */
int mili_chip_dma_write(mili_chip_t *chip, uint32_t sram_addr,
                        const void *data, uint32_t len);
int mili_chip_dma_read(mili_chip_t *chip, uint32_t sram_addr,
                       void *data, uint32_t len);

/* Power management */
int mili_chip_get_power_state(mili_chip_t *chip, mili_power_state_t *state);
int mili_chip_set_power_mode(mili_chip_t *chip, mili_power_mode_t mode);

/* CSR access (test / debug) */
int mili_chip_reg_read(mili_chip_t *chip, uint32_t offset, uint32_t *value);
int mili_chip_reg_write(mili_chip_t *chip, uint32_t offset, uint32_t value);

#ifdef __cplusplus
}
#endif

#endif /* MILI_CHIP_H */
