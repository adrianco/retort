cmake_minimum_required(VERSION 3.16)
project(book_api)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
pkg_check_modules(SQLITE3 REQUIRED sqlite3)
pkg_check_modules(CURL REQUIRED libcurl)

# Find pthreads
find_package(Threads REQUIRED)

# Add executable
add_executable(book_api
    src/main.cpp
    src/server.cpp
    src/handler.cpp
    src/database.cpp
    src/model.cpp
)

# Include directories
target_include_directories(book_api PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${SQLITE3_INCLUDE_DIRS}
    ${CURL_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(book_api
    ${SQLITE3_LIBRARIES}
    ${CURL_LIBRARIES}
    Threads::Threads
)

# Add test executable
add_executable(book_api_tests
    tests/test_database_main.cpp
    tests/test_database.cpp
    src/database.cpp
    src/model.cpp
)

target_include_directories(book_api_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${SQLITE3_INCLUDE_DIRS}
)

target_link_libraries(book_api_tests
    ${SQLITE3_LIBRARIES}
    Threads::Threads
)

# Add server test executable
add_executable(book_api_server_tests
    tests/test_main.cpp
    tests/test_server.cpp
)

target_include_directories(book_api_server_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${SQLITE3_INCLUDE_DIRS}
    ${CURL_INCLUDE_DIRS}
)

target_link_libraries(book_api_server_tests
    ${SQLITE3_LIBRARIES}
    ${CURL_LIBRARIES}
    Threads::Threads
)

# Enable testing
enable_testing()
add_test(NAME DatabaseTests COMMAND book_api_tests)
add_test(NAME ServerTests COMMAND book_api_server_tests)
