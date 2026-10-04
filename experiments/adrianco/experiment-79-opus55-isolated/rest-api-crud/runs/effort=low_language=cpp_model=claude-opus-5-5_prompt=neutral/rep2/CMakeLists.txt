cmake_minimum_required(VERSION 3.14)
project(book_api CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(SQLite3 REQUIRED)
find_package(Threads REQUIRED)
# CMake >= 4.3 renamed the imported target; older versions only have SQLite::SQLite3.
if(TARGET SQLite3::SQLite3)
  set(SQLITE_TARGET SQLite3::SQLite3)
else()
  set(SQLITE_TARGET SQLite::SQLite3)
endif()

add_library(book_core STATIC src/store.cpp src/app.cpp src/http_server.cpp)
target_include_directories(book_core PUBLIC src)
target_link_libraries(book_core PUBLIC ${SQLITE_TARGET} Threads::Threads)
target_compile_options(book_core PRIVATE -Wall -Wextra)

add_executable(book_api src/main.cpp)
target_link_libraries(book_api PRIVATE book_core)

enable_testing()
add_executable(book_tests tests/test_main.cpp)
target_link_libraries(book_tests PRIVATE book_core)
add_test(NAME book_tests COMMAND book_tests)
