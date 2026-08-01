cmake_minimum_required(VERSION 3.16)
project(brazilian_soccer_mcp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(soccer_core soccer.cpp)
target_include_directories(soccer_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(brazilian-soccer-mcp main.cpp)
target_link_libraries(brazilian-soccer-mcp PRIVATE soccer_core)

enable_testing()
add_executable(soccer_tests tests.cpp)
target_link_libraries(soccer_tests PRIVATE soccer_core)
add_test(NAME soccer_tests COMMAND soccer_tests ${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle)
