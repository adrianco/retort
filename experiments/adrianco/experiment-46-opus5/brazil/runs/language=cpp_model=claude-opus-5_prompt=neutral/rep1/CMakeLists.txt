cmake_minimum_required(VERSION 3.16)
project(brazilian_soccer_mcp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

if(MSVC)
  add_compile_options(/W4 /utf-8)
else()
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

add_library(bsmcp_core STATIC
  src/json.cpp
  src/csv.cpp
  src/text_utils.cpp
  src/team_registry.cpp
  src/dataset.cpp
  src/query_engine.cpp
  src/query_tools_matches.cpp
  src/query_tools_players.cpp
  src/query_tools_competitions.cpp
  src/query_tools_stats.cpp
  src/mcp_server.cpp
)
target_include_directories(bsmcp_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

# Baked-in default location of the CSV corpus so the binary works from any cwd.
target_compile_definitions(bsmcp_core PRIVATE
  BSMCP_DEFAULT_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")

add_executable(bsmcp src/main.cpp)
target_link_libraries(bsmcp PRIVATE bsmcp_core)

enable_testing()

add_executable(bsmcp_tests
  tests/test_main.cpp
  tests/test_json.cpp
  tests/test_csv.cpp
  tests/test_text_utils.cpp
  tests/test_team_registry.cpp
  tests/test_dataset.cpp
  tests/test_match_queries.cpp
  tests/test_team_queries.cpp
  tests/test_player_queries.cpp
  tests/test_competition_queries.cpp
  tests/test_statistics.cpp
  tests/test_mcp_protocol.cpp
  tests/test_performance.cpp
  tests/test_sample_questions.cpp
)
target_link_libraries(bsmcp_tests PRIVATE bsmcp_core)
target_include_directories(bsmcp_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_compile_definitions(bsmcp_tests PRIVATE
  BSMCP_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data/kaggle")

add_test(NAME bdd_suite COMMAND bsmcp_tests)
