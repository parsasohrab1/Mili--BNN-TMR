/**
 * Mili BNN-TMR — Memory-Mapped Register Map
 *
 * CSR base: 0x4000_0000
 * SRAM base: 0x8000_0000 (32 MB)
 * PCIe BAR0: 0x6000_0000 (256 KB window into CSR+SRAM)
 */

#ifndef MILI_REGS_H
#define MILI_REGS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Address Map ─────────────────────────────────────────────── */
#define MILI_CSR_BASE           0x40000000u
#define MILI_SRAM_BASE          0x80000000u
#define MILI_SRAM_SIZE          (32u * 1024u * 1024u)
#define MILI_SRAM_END           (MILI_SRAM_BASE + MILI_SRAM_SIZE - 1u)
#define MILI_PCIE_BAR0_BASE     0x60000000u
#define MILI_PCIE_BAR0_SIZE     (256u * 1024u)

/* SRAM layout offsets (from MILI_SRAM_BASE) */
#define MILI_SRAM_MODEL_OFF     0x0000000u
#define MILI_SRAM_MODEL_SIZE    (28u * 1024u * 1024u)
#define MILI_SRAM_INPUT_OFF     0x1C00000u
#define MILI_SRAM_INPUT_SIZE    (2u * 1024u * 1024u)
#define MILI_SRAM_OUTPUT_OFF    0x1E00000u
#define MILI_SRAM_OUTPUT_SIZE   (2u * 1024u * 1024u)

/* ── CSR Offsets ─────────────────────────────────────────────── */
#define MILI_REG_CTRL           0x00u
#define MILI_REG_STATUS         0x04u
#define MILI_REG_IRQ_EN         0x08u
#define MILI_REG_IRQ_STAT       0x0Cu
#define MILI_REG_DPM_CTRL       0x10u
#define MILI_REG_DPM_STAT       0x14u
#define MILI_REG_CLK_CFG        0x18u
#define MILI_REG_TMR_CTRL       0x1Cu
#define MILI_REG_TMR_STAT       0x20u
#define MILI_REG_INFER_CTRL     0x24u
#define MILI_REG_INFER_STAT     0x28u
#define MILI_REG_INPUT_ADDR     0x2Cu
#define MILI_REG_OUTPUT_ADDR    0x30u
#define MILI_REG_MODEL_ADDR     0x34u
#define MILI_REG_BATCH_SIZE     0x38u
#define MILI_REG_PE_STAT        0x3Cu
#define MILI_REG_ECC_STAT       0x40u
#define MILI_REG_TEMP_STAT      0x44u
#define MILI_REG_DMA_CTRL       0x48u
#define MILI_REG_DMA_SRC        0x4Cu
#define MILI_REG_DMA_DST        0x50u
#define MILI_REG_DMA_LEN        0x54u
#define MILI_REG_DMA_STAT       0x58u

/* ── DMA_CTRL (0x48) ─────────────────────────────────────────── */
#define MILI_DMA_START          (1u << 0)
#define MILI_DMA_DIR_WR         (1u << 1)   /* 0=read from chip, 1=write to chip */
#define MILI_DMA_BUSY           (1u << 2)
#define MILI_DMA_DONE           (1u << 3)
#define MILI_DMA_ERR            (1u << 4)

/* ── CTRL (0x00) ───────────────────────────────────────────── */
#define MILI_CTRL_EN            (1u << 0)
#define MILI_CTRL_SOFT_RST      (1u << 1)
#define MILI_CTRL_SRAM_INIT     (1u << 2)

/* ── STATUS (0x04) ───────────────────────────────────────────── */
#define MILI_STATUS_READY       (1u << 0)
#define MILI_STATUS_ERR         (1u << 1)
#define MILI_STATUS_SRAM_RDY    (1u << 2)
#define MILI_STATUS_TMR_ACT     (1u << 3)

/* ── IRQ ─────────────────────────────────────────────────────── */
#define MILI_IRQ_INFER_DONE     (1u << 0)
#define MILI_IRQ_INFER_ERR      (1u << 1)
#define MILI_IRQ_TMR_ERR        (1u << 2)
#define MILI_IRQ_ECC_CORR       (1u << 3)
#define MILI_IRQ_ECC_UNCORR     (1u << 4)
#define MILI_IRQ_DPM_DONE       (1u << 5)

/* ── DPM_CTRL (0x10) ─────────────────────────────────────────── */
#define MILI_DPM_MODE_SHIFT     0u
#define MILI_DPM_MODE_MASK      0x03u
#define MILI_DPM_AUTO           (1u << 4)

#define MILI_DPM_SLEEP          0u
#define MILI_DPM_IDLE           1u
#define MILI_DPM_NORMAL         2u
#define MILI_DPM_TURBO          3u

/* ── DPM_STAT (0x14) ─────────────────────────────────────────── */
#define MILI_DPM_BUSY           (1u << 4)
#define MILI_DPM_CUR_FREQ_SHIFT 8u
#define MILI_DPM_CUR_FREQ_MASK  0xFFFu

/* ── CLK_CFG (0x18) ──────────────────────────────────────────── */
#define MILI_CLK_FREQ_SHIFT     0u
#define MILI_CLK_FREQ_MASK      0xFFFu
#define MILI_CLK_GATE_EN        (1u << 16)

/* ── TMR_CTRL (0x1C) ─────────────────────────────────────────── */
#define MILI_TMR_EN             (1u << 0)
#define MILI_TMR_FAULT_INJECT   (1u << 1)
#define MILI_TMR_FAULT_LANE_SHIFT 2u
#define MILI_TMR_FAULT_LANE_MASK  0x03u

/* ── TMR_STAT (0x20) ─────────────────────────────────────────── */
#define MILI_TMR_DISAGREE       (1u << 0)
#define MILI_TMR_ERR_CNT_SHIFT  8u
#define MILI_TMR_ERR_CNT_MASK   0xFFFFu

/* ── INFER_CTRL (0x24) ───────────────────────────────────────── */
#define MILI_INFER_START        (1u << 0)
#define MILI_INFER_ABORT        (1u << 1)

/* ── INFER_STAT (0x28) ───────────────────────────────────────── */
#define MILI_INFER_BUSY         (1u << 0)
#define MILI_INFER_DONE         (1u << 1)
#define MILI_INFER_ERR          (1u << 2)
#define MILI_INFER_CYCLE_SHIFT  8u
#define MILI_INFER_CYCLE_MASK   0xFFFFFFu

/* ── ECC_STAT (0x40) ─────────────────────────────────────────── */
#define MILI_ECC_CORR_CNT_SHIFT 0u
#define MILI_ECC_CORR_CNT_MASK  0xFFFFu
#define MILI_ECC_UNCORR_CNT_SHIFT 16u
#define MILI_ECC_UNCORR_CNT_MASK  0xFFFFu

/* ── Helper macros ───────────────────────────────────────────── */
#define MILI_REG_ADDR(offset)   (MILI_CSR_BASE + (offset))
#define MILI_SRAM_ADDR(offset)  (MILI_SRAM_BASE + (offset))

#define MILI_DPM_SET_MODE(val)  (((val) & MILI_DPM_MODE_MASK) << MILI_DPM_MODE_SHIFT)
#define MILI_DPM_GET_MODE(reg)  (((reg) >> MILI_DPM_MODE_SHIFT) & MILI_DPM_MODE_MASK)

#ifdef __cplusplus
}
#endif

#endif /* MILI_REGS_H */
