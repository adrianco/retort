cmake_minimum_required(VERSION 3.16)
project(brazilian_soccer_mcp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_library(soccer_core STATIC
  src/csv.cpp
  src/text.cpp
  src/db.cpp
  src/tools.cpp
  src/server.cpp
)
target_include_directories(soccer_core PUBLIC src)
target_compile_options(soccer_core PRIVATE -Wall -Wextra)

add_executable(soccer_mcp_server src/main.cpp)
target_link_libraries(soccer_mcp_server PRIVATE soccer_core)

enable_testing()

add_executable(test_unit tests/test_unit.cpp)
target_link_libraries(test_unit PRIVATE soccer_core)
add_test(NAME unit COMMAND test_unit ${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle)

add_executable(test_mcp_protocol tests/test_mcp_protocol.cpp)
target_link_libraries(test_mcp_protocol PRIVATE soccer_core)
add_test(NAME mcp_protocol COMMAND test_mcp_protocol
         $<TARGET_FILE:soccer_mcp_server> ${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle)
