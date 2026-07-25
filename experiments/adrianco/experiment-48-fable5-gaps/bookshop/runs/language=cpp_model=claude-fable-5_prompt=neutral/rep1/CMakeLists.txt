cmake_minimum_required(VERSION 3.16)
project(book_api CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

add_library(book_core
    src/book_store.cpp
    src/api.cpp
)
target_include_directories(book_core PUBLIC third_party)
target_link_libraries(book_core PUBLIC SQLite::SQLite3 Threads::Threads)

add_executable(book_api src/main.cpp)
target_link_libraries(book_api PRIVATE book_core)

enable_testing()
add_executable(book_tests tests/test_api.cpp)
target_link_libraries(book_tests PRIVATE book_core)
add_test(NAME api_tests COMMAND book_tests)
