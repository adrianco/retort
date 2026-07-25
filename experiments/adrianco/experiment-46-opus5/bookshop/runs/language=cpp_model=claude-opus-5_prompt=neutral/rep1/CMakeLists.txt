cmake_minimum_required(VERSION 3.16)
project(books_api LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

add_library(books_core STATIC
  src/json.cpp
  src/book.cpp
  src/store.cpp
  src/http_server.cpp
  src/api.cpp
)
target_include_directories(books_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
# Newer CMake exports SQLite3::SQLite3; older releases only define SQLite::SQLite3.
if(TARGET SQLite3::SQLite3)
  target_link_libraries(books_core PUBLIC SQLite3::SQLite3 Threads::Threads)
else()
  target_link_libraries(books_core PUBLIC SQLite::SQLite3 Threads::Threads)
endif()
target_compile_options(books_core PRIVATE -Wall -Wextra -Wpedantic)

add_executable(books_api src/main.cpp)
target_link_libraries(books_api PRIVATE books_core)
target_compile_options(books_api PRIVATE -Wall -Wextra -Wpedantic)

enable_testing()

add_executable(books_tests
  tests/test_framework.cpp
  tests/http_client.cpp
  tests/test_json.cpp
  tests/test_book.cpp
  tests/test_http.cpp
  tests/test_store.cpp
  tests/test_api.cpp
)
target_include_directories(books_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(books_tests PRIVATE books_core)
target_compile_options(books_tests PRIVATE -Wall -Wextra)

add_test(NAME books_tests COMMAND books_tests)
set_tests_properties(books_tests PROPERTIES TIMEOUT 120)
