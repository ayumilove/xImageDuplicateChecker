cmake_minimum_required(VERSION 3.12)
project(HashAlgorithms)

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 设置编译选项
if(WIN32)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    add_definitions(-DBUILDING_DLL)
endif()

# 设置 OpenCV 路径
set(OpenCV_DIR "C:/opencv/build")
set(CMAKE_PREFIX_PATH "C:/opencv/build")

# 查找OpenCV (可选)
find_package(OpenCV QUIET)
if(OpenCV_FOUND)
    message(STATUS "Found OpenCV version: ${OpenCV_VERSION}")
    message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")
    message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
    include_directories(${OpenCV_INCLUDE_DIRS})
    add_definitions(-DHAVE_OPENCV)
else()
    message(WARNING "OpenCV not found! Building without OpenCV support.")
    message(STATUS "Searched in: ${OpenCV_DIR}")
endif()

# 查找OpenSSL (可选)
find_package(OpenSSL QUIET)
if(OPENSSL_FOUND)
    message(STATUS "Found OpenSSL version: ${OPENSSL_VERSION}")
    include_directories(${OPENSSL_INCLUDE_DIR})
    add_definitions(-DHAVE_OPENSSL)
else()
    message(WARNING "OpenSSL not found! Building without OpenSSL support.")
endif()

# 添加源文件
set(SOURCES
    hash_algorithms.cpp
)

set(HEADERS
    hash_algorithms.h
)

# 创建动态库
add_library(hash_algorithms SHARED ${SOURCES} ${HEADERS})

# 链接库
set(LINK_LIBS)
if(OpenCV_FOUND)
    list(APPEND LINK_LIBS ${OpenCV_LIBS})
endif()
if(OPENSSL_FOUND)
    list(APPEND LINK_LIBS ${OPENSSL_LIBRARIES})
endif()

if(LINK_LIBS)
    target_link_libraries(hash_algorithms ${LINK_LIBS})
endif()

# 设置输出目录
set_target_properties(hash_algorithms PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
)

# Windows特定设置
if(WIN32)
    set_target_properties(hash_algorithms PROPERTIES
        OUTPUT_NAME "hash_algorithms"
        SUFFIX ".dll"
    )
endif()

# Linux特定设置
if(UNIX AND NOT APPLE)
    set_target_properties(hash_algorithms PROPERTIES
        OUTPUT_NAME "hash_algorithms"
        SUFFIX ".so"
    )
endif()

# 安装规则
install(TARGETS hash_algorithms
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES ${HEADERS}
    DESTINATION include
)

# 打印构建信息
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
message(STATUS "OpenSSL libraries: ${OPENSSL_LIBRARIES}")