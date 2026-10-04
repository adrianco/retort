cmake_minimum_required(VERSION 3.14)
project(brazilian_soccer_mcp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_library(soccer STATIC src/soccer.cpp src/mcp_server.cpp)
target_include_directories(soccer PUBLIC src)
if(NOT MSVC)
  target_compile_options(soccer PRIVATE -Wall -Wextra)
endif()

set(DATA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")

add_executable(brazilian_soccer_mcp src/main.cpp)
target_link_libraries(brazilian_soccer_mcp PRIVATE soccer)
target_compile_definitions(brazilian_soccer_mcp PRIVATE DEFAULT_DATA_DIR="${DATA_DIR}")

enable_testing()
add_executable(soccer_tests tests/test_soccer.cpp)
target_link_libraries(soccer_tests PRIVATE soccer)
target_compile_definitions(soccer_tests PRIVATE DEFAULT_DATA_DIR="${DATA_DIR}")
add_test(NAME soccer_tests COMMAND soccer_tests)
