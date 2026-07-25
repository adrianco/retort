cmake_minimum_required(VERSION 3.16)
project(book_api CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)
find_package(SQLite3 REQUIRED)

# Vendored single-header dependencies (httplib, nlohmann/json).
set(THIRD_PARTY ${CMAKE_CURRENT_SOURCE_DIR}/third_party)

# Shared library with the store + handler logic, reused by app and tests.
add_library(book_core STATIC
    src/book_store.cpp
    src/handlers.cpp
)
target_include_directories(book_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${THIRD_PARTY}
)
target_link_libraries(book_core PUBLIC SQLite3::SQLite3)

# Server executable.
add_executable(book_api src/main.cpp)
target_link_libraries(book_api PRIVATE book_core Threads::Threads)

# Tests.
enable_testing()
add_executable(book_tests tests/test_main.cpp)
target_link_libraries(book_tests PRIVATE book_core Threads::Threads)
add_test(NAME book_tests COMMAND book_tests)
