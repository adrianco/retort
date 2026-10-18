cmake_minimum_required(VERSION 3.16)
project(book_api LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

add_library(bookapi STATIC
    src/json.cpp
    src/book_repository.cpp
    src/book_api.cpp
    src/http_server.cpp
)
target_include_directories(bookapi PUBLIC include)
target_link_libraries(bookapi PUBLIC SQLite3::SQLite3 Threads::Threads)
target_compile_options(bookapi PRIVATE -Wall -Wextra -Wpedantic)

add_executable(book_server src/main.cpp)
target_link_libraries(book_server PRIVATE bookapi)

enable_testing()
add_executable(book_tests
    tests/test_main.cpp
    tests/test_json.cpp
    tests/test_repository.cpp
    tests/test_api.cpp
    tests/test_http.cpp
)
target_include_directories(book_tests PRIVATE tests)
target_link_libraries(book_tests PRIVATE bookapi)
target_compile_options(book_tests PRIVATE -Wall -Wextra -Wpedantic)
add_test(NAME book_tests COMMAND book_tests)
