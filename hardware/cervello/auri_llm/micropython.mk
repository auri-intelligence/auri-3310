# Stessa cosa per i port che usano make invece di CMake (unix, stm32...):
#   make USER_C_MODULES=../../hardware/cervello
AURI_LLM_MOD_DIR := $(USERMOD_DIR)

SRC_USERMOD += $(AURI_LLM_MOD_DIR)/auri_llm.c
CFLAGS_USERMOD += -I$(AURI_LLM_MOD_DIR)
