#include <zephyr/kernel.h>
#include <zephyr/device.h>

#define MILI_NODE DT_COMPAT_GET_ANY_STATUS_OKAY(mili_bnn_tmr)

int main(void)
{
	const struct device *mili = DEVICE_DT_GET(MILI_NODE);
	if (!device_is_ready(mili)) {
		return 1;
	}
	printk("mili-bnn-tmr zephyr app ready\n");
	return 0;
}
