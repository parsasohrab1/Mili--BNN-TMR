# Mili BNN-TMR Driver Build System
#
# Host simulator tests (no embedded toolchain required):
#   make test
#
# FreeRTOS/STM32 build:
#   make TARGET=stm32h7 MILI_HAL_FREERTOS=1
#
# Linux PCIe module:
#   make -C linux KDIR=/lib/modules/$(uname -r)/build

CC       ?= gcc
CFLAGS   ?= -Wall -Wextra -std=c11 -Icommon -I../api/cpp/include
LDFLAGS  ?=

COMMON_SRCS = common/mili_hal.c common/mili_chip.c
SIM_SRCS    = simulator/mili_sim_hal.c
TEST_SRCS   = tests/test_driver.c

.PHONY: all test clean linux

all: test

test: build/test_driver
	./build/test_driver

build/test_driver: $(COMMON_SRCS) $(SIM_SRCS) $(TEST_SRCS) | build
	$(CC) $(CFLAGS) -o $@ $(COMMON_SRCS) $(SIM_SRCS) $(TEST_SRCS) $(LDFLAGS)

build/bootloader: ../firmware/bootloader.c | build
	$(CC) $(CFLAGS) -Icommon -DMILI_BOOT_HOST -o $@ ../firmware/bootloader.c

build:
	mkdir -p build

linux:
	$(MAKE) -C linux KDIR=$(KDIR)

clean:
	rm -rf build
	$(MAKE) -C linux clean 2>/dev/null || true
