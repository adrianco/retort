cmake_minimum_required(VERSION 3.16)
project(brazilian_soccer_mcp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Core library shared by the server executable and the tests.
add_library(soccer_core STATIC
    src/json.cpp
    src/csv.cpp
    src/text.cpp
    src/dataset.cpp
    src/queries.cpp
    src/mcp_server.cpp
)
target_include_directories(soccer_core PUBLIC src)
target_compile_options(soccer_core PRIVATE $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra>)

# MCP server executable (stdio transport).
add_executable(brazilian_soccer_mcp src/main.cpp)
target_link_libraries(brazilian_soccer_mcp PRIVATE soccer_core)
target_compile_definitions(brazilian_soccer_mcp PRIVATE
    SOCCER_DEFAULT_DATA_DIR="${CMAKE_SOURCE_DIR}/data/kaggle")

# Unit and behaviour tests. Run with `ctest` or `./soccer_tests`.
enable_testing()
add_executable(soccer_tests
    tests/test_main.cpp
    tests/json_csv_tests.cpp
    tests/text_tests.cpp
    tests/query_tests.cpp
    tests/mcp_tests.cpp
)
target_link_libraries(soccer_tests PRIVATE soccer_core)
target_compile_definitions(soccer_tests PRIVATE
    SOCCER_DATA_DIR="${CMAKE_SOURCE_DIR}/data/kaggle")
add_test(NAME soccer_tests COMMAND soccer_tests)
