# Modulo utente per MicroPython (port ESP32 e altri port con CMake).
# Si usa cosi', dalla cartella ports/esp32 di MicroPython:
#   idf.py -D MICROPY_BOARD=ESP32_GENERIC_S3 -D MICROPY_BOARD_VARIANT=SPIRAM_OCT \
#          -D USER_C_MODULES=Z:/Shared/.../hardware/cervello/auri_llm/micropython.cmake build
add_library(usermod_auri_llm INTERFACE)

target_sources(usermod_auri_llm INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/auri_llm.c
)

target_include_directories(usermod_auri_llm INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_auri_llm)
