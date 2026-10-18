# ============================================================================
# CMakeLists.txt - Build for the Brazilian Soccer MCP server and its tests.
# Context: C++17, no third-party dependencies. Produces:
#   brazil_soccer_mcp  - the stdio MCP server executable
#   brazil_soccer_tests - BDD-style test executable (run via ctest)
# ============================================================================
cmake_minimum_required(VERSION 3.16)
project(BrazilSoccerMCP LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_library(brazil_soccer_core STATIC
  src/json.cpp
  src/csv.cpp
  src/text.cpp
  src/dataset.cpp
  src/loader.cpp
  src/queries.cpp
  src/tools.cpp
  src/mcp_server.cpp
)
target_include_directories(brazil_soccer_core PUBLIC src)
target_compile_options(brazil_soccer_core PRIVATE $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall -Wextra>)

add_executable(brazil_soccer_mcp src/main.cpp)
target_link_libraries(brazil_soccer_mcp PRIVATE brazil_soccer_core)

enable_testing()
add_executable(brazil_soccer_tests tests/test_main.cpp)
target_link_libraries(brazil_soccer_tests PRIVATE brazil_soccer_core)
target_compile_definitions(brazil_soccer_tests PRIVATE
  BRAZIL_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")
add_test(NAME brazil_soccer_tests COMMAND brazil_soccer_tests)
