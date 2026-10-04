cmake_minimum_required(VERSION 3.14)
project(books_api CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

add_library(books_core src/json.cpp src/store.cpp src/api.cpp src/http_server.cpp)
target_include_directories(books_core PUBLIC src)
target_compile_options(books_core PRIVATE -Wall -Wextra)
if(TARGET SQLite3::SQLite3)
  target_link_libraries(books_core PUBLIC SQLite3::SQLite3 Threads::Threads)
else()
  target_link_libraries(books_core PUBLIC SQLite::SQLite3 Threads::Threads)
endif()

add_executable(books_server src/main.cpp)
target_link_libraries(books_server PRIVATE books_core)

enable_testing()
add_executable(books_tests tests/test_api.cpp)
target_link_libraries(books_tests PRIVATE books_core)
add_test(NAME books_tests COMMAND books_tests)
