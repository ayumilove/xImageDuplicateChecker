#ifndef DUPLICATE_ANALYZER_H
#define DUPLICATE_ANALYZER_H

#include <vector>
#include <string>
#include <map>
#include <set>
#include <functional>

#ifdef _WIN32
    #ifdef BUILDING_DLL
        #define DLL_EXPORT __declspec(dllexport)
    #else
        #define DLL_EXPORT __declspec(dllimport)
    #endif
#else
    #define DLL_EXPORT
#endif

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 重复图片组结构
 */
struct DuplicateGroup {
    char* reason;           // 重复原因
    char** files;          // 文件路径数组
    int file_count;        // 文件数量
    int* dhash_distances;  // dHash距离数组
    int* phash_distances;  // pHash距离数组
    int* ahash_distances;  // aHash距离数组
};

/**
 * 分析结果结构
 */
struct AnalysisResult {
    DuplicateGroup* groups;     // 重复组数组
    int group_count;           // 重复组数量
    int total_images;          // 总图片数量
    int duplicate_images;      // 重复图片数量
    int pure_color_images;     // 纯色图片数量
    char* error_message;       // 错误信息（如果有）
};

/**
 * 分析参数结构
 */
struct AnalysisParams {
    int phash_threshold;       // pHash阈值
    int dhash_threshold;       // dHash阈值
    int ahash_threshold;       // aHash阈值
    bool detect_pure_color;    // 是否检测纯色图片
    bool detect_rotation;      // 是否检测旋转
    bool recursive_scan;       // 是否递归扫描
    float pure_color_threshold; // 纯色检测阈值
};

/**
 * 日志回调函数类型
 */
typedef void (*LogCallback)(const char* message);

/**
 * 分析指定目录中的重复图片
 * @param directory 要分析的目录路径
 * @param params 分析参数
 * @param log_callback 日志回调函数（可选）
 * @return 分析结果，需要调用 free_analysis_result 释放内存
 */
DLL_EXPORT AnalysisResult* analyze_duplicates_c(const char* directory, 
                                                const AnalysisParams* params,
                                                LogCallback log_callback);

/**
 * 分析指定文件列表中的重复图片
 * @param file_paths 文件路径数组
 * @param file_count 文件数量
 * @param params 分析参数
 * @param log_callback 日志回调函数（可选）
 * @return 分析结果，需要调用 free_analysis_result 释放内存
 */
DLL_EXPORT AnalysisResult* analyze_file_list_c(const char** file_paths,
                                               int file_count,
                                               const AnalysisParams* params,
                                               LogCallback log_callback);

/**
 * 扫描目录获取所有图片文件
 * @param directory 目录路径
 * @param recursive 是否递归扫描
 * @param file_count 输出参数：文件数量
 * @return 文件路径数组，需要调用 free_file_list 释放内存
 */
DLL_EXPORT char** scan_directory_c(const char* directory, 
                                   bool recursive, 
                                   int* file_count);

/**
 * 释放分析结果内存
 * @param result 要释放的分析结果
 */
DLL_EXPORT void free_analysis_result_c(AnalysisResult* result);

/**
 * 释放文件列表内存
 * @param file_list 文件列表
 * @param file_count 文件数量
 */
DLL_EXPORT void free_file_list_c(char** file_list, int file_count);

/**
 * 创建默认分析参数
 * @return 默认分析参数
 */
DLL_EXPORT AnalysisParams create_default_params_c();

#ifdef __cplusplus
}
#endif

#endif // DUPLICATE_ANALYZER_H