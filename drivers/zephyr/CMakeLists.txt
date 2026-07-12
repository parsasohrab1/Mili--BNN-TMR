if(CONFIG_MILI_BNN_TMR)

zephyr_library()
zephyr_library_sources(
  mili_zephyr.c
  ../common/mili_hal.c
)
zephyr_include_directories(
  .
  ../common
  ../../api/cpp/include
)

endif()
