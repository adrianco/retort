cmake_minimum_required(VERSION 3.20)
project(books_api LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Boost 1.84 REQUIRED COMPONENTS json unit_test_framework)
find_package(SQLite3 REQUIRED)

# Core logic: validation, storage and HTTP routing. No sockets here, so it is
# directly testable.
add_library(books_core
  src/book.cpp
  src/repository.cpp
  src/api.cpp
)
target_include_directories(books_core PUBLIC src)
target_link_libraries(books_core PUBLIC Boost::headers Boost::json SQLite::SQLite3)

# HTTP server (Boost.Beast) wrapping the core handler.
add_executable(books_server src/main.cpp)
target_link_libraries(books_server PRIVATE books_core)

enable_testing()
add_executable(books_tests tests/api_tests.cpp)
target_compile_definitions(books_tests PRIVATE BOOST_TEST_DYN_LINK)
target_link_libraries(books_tests PRIVATE books_core Boost::unit_test_framework)
add_test(NAME books_tests COMMAND books_tests)
