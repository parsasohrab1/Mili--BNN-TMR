# Mili Bootloader — host test + STM32H7 build notes

CC       ?= gcc
CFLAGS   ?= -Wall -Wextra -std=c11 -I../drivers/common
BUILD    ?= build

.PHONY: host-test stm32 clean

host-test: $(BUILD)/bootloader_test
	./$(BUILD)/bootloader_test
	@echo "Bootloader host test PASSED"

$(BUILD)/bootloader_test: bootloader.c | $(BUILD)
	$(CC) $(CFLAGS) -DMILI_BOOT_HOST -DMILI_BOOT_HOST_TEST -o $@ bootloader.c

$(BUILD):
	mkdir -p $(BUILD)

stm32:
	@echo "STM32H7 build: use STM32CubeIDE or"
	@echo "  arm-none-eabi-gcc -DSTM32H743xx -T stm32h743vi.ld bootloader.c stm32_hal_stub.c"

clean:
	rm -rf $(BUILD)
