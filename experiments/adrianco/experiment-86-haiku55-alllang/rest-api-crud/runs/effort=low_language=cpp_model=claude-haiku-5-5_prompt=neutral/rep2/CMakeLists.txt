cmake_minimum_required(VERSION 3.16)
project(book_api LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Threads REQUIRED)
find_package(SQLite3 REQUIRED)

include(FetchContent)
FetchContent_Declare(
  httplib
  GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
  GIT_TAG v0.18.7
  GIT_SHALLOW TRUE
)
FetchContent_Declare(
  json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(httplib json)

# Core library: storage, validation and HTTP routing.
add_library(book_core
  src/database.cpp
  src/validation.cpp
  src/api.cpp
)
target_include_directories(book_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(book_core
  PUBLIC httplib::httplib nlohmann_json::nlohmann_json
  PRIVATE SQLite3::SQLite3 Threads::Threads
)

add_executable(book_api src/main.cpp)
target_link_libraries(book_api PRIVATE book_core)

enable_testing()
add_executable(book_api_tests tests/test_books.cpp)
target_link_libraries(book_api_tests PRIVATE book_core)
add_test(NAME book_api_tests COMMAND book_api_tests)
