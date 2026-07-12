/**
 * Mili BNN-TMR — Linux PCIe Kernel Module (Linux RT)
 *
 * Build:
 *   make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
 *
 * Load:
 *   sudo insmod mili_pcie.ko
 *   echo "mili" > /sys/class/mili_bnn/mili0/device/load_model ...
 */

#include "mili_hal.h"
#include "mili_regs.h"

#ifdef __KERNEL__
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/interrupt.h>
#include <linux/wait.h>
#include <linux/mm.h>

#define MILI_PCI_VENDOR 0x1FAE
#define MILI_PCI_DEVICE 0xBNN1
#define MILI_BAR0       0

struct mili_pcie_dev {
    struct pci_dev  *pdev;
    void __iomem    *bar0;
    wait_queue_head_t irq_wq;
    volatile uint32_t irq_pending;
    mili_irq_callback_t irq_cb;
    void            *irq_user;
    int              irq;
};

static struct mili_pcie_dev *g_mili_pdev;

static uint32_t pcie_map_addr(uint32_t addr, uint32_t *bar_off)
{
    if (addr >= MILI_SRAM_BASE && addr <= MILI_SRAM_END) {
        *bar_off = 0x10000u + (addr - MILI_SRAM_BASE);
        return 0;
    }
    if (addr >= MILI_CSR_BASE) {
        *bar_off = addr - MILI_CSR_BASE;
        return 0;
    }
    return 1;
}

static int pcie_read_reg(void *ctx, uint32_t offset, uint32_t *value)
{
    struct mili_pcie_dev *dev = ctx;
    if (offset >= MILI_PCIE_BAR0_SIZE)
        return MILI_HAL_ERR;
    *value = readl(dev->bar0 + offset);
    return MILI_HAL_OK;
}

static int pcie_write_reg(void *ctx, uint32_t offset, uint32_t value)
{
    struct mili_pcie_dev *dev = ctx;
    if (offset >= MILI_PCIE_BAR0_SIZE)
        return MILI_HAL_ERR;
    writel(value, dev->bar0 + offset);
    return MILI_HAL_OK;
}

static int pcie_dma_write(void *ctx, uint32_t sram_addr,
                          const void *src, uint32_t len)
{
    struct mili_pcie_dev *dev = ctx;
    uint32_t bar_off;
    if (pcie_map_addr(sram_addr, &bar_off))
        return MILI_HAL_ERR;
    if (bar_off + len > MILI_PCIE_BAR0_SIZE)
        return MILI_HAL_ERR;
    memcpy_toio(dev->bar0 + bar_off, src, len);
    return MILI_HAL_OK;
}

static int pcie_dma_read(void *ctx, uint32_t sram_addr,
                         void *dst, uint32_t len)
{
    struct mili_pcie_dev *dev = ctx;
    uint32_t bar_off;
    if (pcie_map_addr(sram_addr, &bar_off))
        return MILI_HAL_ERR;
    if (bar_off + len > MILI_PCIE_BAR0_SIZE)
        return MILI_HAL_ERR;
    memcpy_fromio(dst, dev->bar0 + bar_off, len);
    return MILI_HAL_OK;
}

static int pcie_wait_irq(void *ctx, uint32_t irq_mask, uint32_t timeout_ms)
{
    struct mili_pcie_dev *dev = ctx;
    long rc = wait_event_interruptible_timeout(
        dev->irq_wq,
        (dev->irq_pending & irq_mask) != 0,
        msecs_to_jiffies(timeout_ms));
    if (rc <= 0)
        return MILI_HAL_ERR_TIMEOUT;
    dev->irq_pending &= ~irq_mask;
    return MILI_HAL_OK;
}

static void pcie_register_irq(void *ctx, mili_irq_callback_t cb, void *user_data)
{
    struct mili_pcie_dev *dev = ctx;
    dev->irq_cb = cb;
    dev->irq_user = user_data;
}

static irqreturn_t mili_pcie_irq_handler(int irq, void *dev_id)
{
    struct mili_pcie_dev *dev = dev_id;
    uint32_t irq_stat = readl(dev->bar0 + MILI_REG_IRQ_STAT);
    dev->irq_pending |= irq_stat;
    writel(irq_stat, dev->bar0 + MILI_REG_IRQ_STAT); /* W1C */
    wake_up_interruptible(&dev->irq_wq);
    if (dev->irq_cb)
        dev->irq_cb(irq_stat, dev->irq_user);
    return IRQ_HANDLED;
}

const mili_hal_ops_t mili_pcie_hal_ops = {
    .read_reg     = pcie_read_reg,
    .write_reg    = pcie_write_reg,
    .dma_write    = pcie_dma_write,
    .dma_read     = pcie_dma_read,
    .wait_irq     = pcie_wait_irq,
    .register_irq = pcie_register_irq,
};

int mili_pcie_hal_init(void **ctx)
{
    if (!g_mili_pdev)
        return MILI_HAL_ERR;
    *ctx = g_mili_pdev;
    return MILI_HAL_OK;
}

static int mili_pcie_probe(struct pci_dev *pdev, const struct pci_device_id *id)
{
    struct mili_pcie_dev *dev;
    int rc;

    dev = devm_kzalloc(&pdev->dev, sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;

    rc = pci_enable_device(pdev);
    if (rc)
        return rc;

    pci_set_master(pdev);
    dev->bar0 = pci_iomap(pdev, MILI_BAR0, MILI_PCIE_BAR0_SIZE);
    if (!dev->bar0)
        return -ENOMEM;

    init_waitqueue_head(&dev->irq_wq);
    dev->pdev = pdev;
    g_mili_pdev = dev;

    /* Enable MSI/MSI-X when available */
    pci_alloc_irq_vectors(pdev, 1, 1, PCI_IRQ_MSI | PCI_IRQ_LEGACY);
    dev->irq = pci_irq_vector(pdev, 0);
    if (dev->irq < 0)
        dev->irq = pdev->irq;

    rc = request_irq(dev->irq, mili_pcie_irq_handler, IRQF_SHARED,
                     "mili-bnn", dev);
    if (rc)
        return rc;

    pci_set_drvdata(pdev, dev);
    return 0;
}

static void mili_pcie_remove(struct pci_dev *pdev)
{
    struct mili_pcie_dev *dev = pci_get_drvdata(pdev);
    free_irq(dev->irq, dev);
    pci_free_irq_vectors(pdev);
    pci_iounmap(pdev, dev->bar0);
    pci_disable_device(pdev);
    g_mili_pdev = NULL;
}

static const struct pci_device_id mili_pci_ids[] = {
    { PCI_DEVICE(MILI_PCI_VENDOR, MILI_PCI_DEVICE) },
    { 0 }
};
MODULE_DEVICE_TABLE(pci, mili_pci_ids);

static struct pci_driver mili_pcie_driver = {
    .name     = "mili-bnn-tmr",
    .id_table = mili_pci_ids,
    .probe    = mili_pcie_probe,
    .remove   = mili_pcie_remove,
};

module_pci_driver(mili_pcie_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Mili BNN-TMR Edge AI Accelerator PCIe driver");

#endif /* __KERNEL__ */
