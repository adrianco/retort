cmake_minimum_required(VERSION 3.16)
project(book_collection_api LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(SQLite3 REQUIRED)

add_library(book_api book_api.cpp)
target_include_directories(book_api PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(book_api PUBLIC SQLite3::SQLite3)
target_compile_options(book_api PRIVATE -Wall -Wextra -Wpedantic)

add_executable(book_server main.cpp)
target_link_libraries(book_server PRIVATE book_api)

include(CTest)
if(BUILD_TESTING)
  add_executable(book_api_tests tests.cpp)
  target_link_libraries(book_api_tests PRIVATE book_api)
  add_test(NAME book_api_tests COMMAND book_api_tests)
endif()
