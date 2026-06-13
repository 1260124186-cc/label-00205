cmake_minimum_required(VERSION 3.15)
project(edge_sdk VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)
find_package(CURL REQUIRED)
find_package(nlohmann_json 3.2.0 QUIET)

if(NOT nlohmann_json_FOUND)
    find_package(PkgConfig QUIET)
    if(PkgConfig_FOUND)
        pkg_check_modules(JSONCPP QUIET jsoncpp)
    endif()
endif()

add_library(edge_sdk STATIC edge_sdk.cpp)
target_include_directories(edge_sdk PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(edge_sdk PRIVATE Threads::Threads CURL::libcurl)

if(nlohmann_json_FOUND)
    target_link_libraries(edge_sdk PRIVATE nlohmann_json::nlohmann_json)
    target_compile_definitions(edge_sdk PRIVATE HAS_NLOHMANN_JSON)
endif()

if(JSONCPP_FOUND)
    target_include_directories(edge_sdk PRIVATE ${JSONCPP_INCLUDE_DIRS})
    target_link_libraries(edge_sdk PRIVATE ${JSONCPP_LIBRARIES})
    target_compile_definitions(edge_sdk PRIVATE HAS_JSONCPP)
endif()

if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/example.cpp)
    add_executable(edge_example example.cpp)
    target_link_libraries(edge_example PRIVATE edge_sdk)
endif()
