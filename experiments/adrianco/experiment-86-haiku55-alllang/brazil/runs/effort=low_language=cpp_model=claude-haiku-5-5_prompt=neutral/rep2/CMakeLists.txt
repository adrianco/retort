cmake_minimum_required(VERSION 3.16)
project(brazilian_soccer_mcp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_library(soccer_core STATIC
  src/json.cpp
  src/csv.cpp
  src/text.cpp
  src/team.cpp
  src/data_store.cpp
  src/queries.cpp
  src/tools.cpp
  src/mcp_server.cpp
)
target_include_directories(soccer_core PUBLIC src)
target_compile_options(soccer_core PRIVATE -Wall -Wextra -Wpedantic)

add_executable(brazilian_soccer_mcp src/main.cpp)
target_link_libraries(brazilian_soccer_mcp PRIVATE soccer_core)

enable_testing()
add_executable(soccer_tests
  tests/test_main.cpp
  tests/test_core.cpp
  tests/test_data.cpp
  tests/test_server.cpp
)
target_link_libraries(soccer_tests PRIVATE soccer_core)
target_compile_definitions(soccer_tests PRIVATE DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")
add_test(NAME soccer_tests COMMAND soccer_tests)
