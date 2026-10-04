cmake_minimum_required(VERSION 3.14)
project(books_api CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)

add_library(books_core STATIC src/json.cpp src/store.cpp src/app.cpp src/server.cpp)
target_include_directories(books_core PUBLIC src)
# Newer CMake renamed the imported target and deprecated the old name.
if(TARGET SQLite3::SQLite3)
  set(SQLITE_TARGET SQLite3::SQLite3)
else()
  set(SQLITE_TARGET SQLite::SQLite3)
endif()
target_link_libraries(books_core PUBLIC ${SQLITE_TARGET} Threads::Threads)
target_compile_options(books_core PRIVATE -Wall -Wextra)

add_executable(books_api src/main.cpp)
target_link_libraries(books_api PRIVATE books_core)

enable_testing()
add_executable(books_tests tests/tests.cpp)
target_link_libraries(books_tests PRIVATE books_core)
add_test(NAME books_tests COMMAND books_tests)
