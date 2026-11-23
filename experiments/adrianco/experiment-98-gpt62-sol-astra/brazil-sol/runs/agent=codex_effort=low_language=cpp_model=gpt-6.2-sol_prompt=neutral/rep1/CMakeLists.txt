cmake_minimum_required(VERSION 3.20)
project(brazilian_soccer_mcp LANGUAGES CXX)

find_package(Boost 1.75 CONFIG REQUIRED COMPONENTS json)
find_package(PkgConfig REQUIRED)
pkg_check_modules(UTF8PROC REQUIRED IMPORTED_TARGET libutf8proc)

add_executable(soccer_mcp main.cpp soccer.cpp)
target_compile_features(soccer_mcp PRIVATE cxx_std_20)
target_compile_options(soccer_mcp PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(soccer_mcp PRIVATE Boost::json PkgConfig::UTF8PROC)
target_compile_definitions(soccer_mcp PRIVATE SOCCER_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME soccer_mcp_scenarios COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test_mcp.py $<TARGET_FILE:soccer_mcp>)
  set_tests_properties(soccer_mcp_scenarios PROPERTIES TIMEOUT 20)
endif()
