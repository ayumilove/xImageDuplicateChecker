#ifndef HASH_ALGORITHMS_H
#define HASH_ALGORITHMS_H

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
 * 计算图片的差值哈希(dHash)
 * @param image_path 图片文件路径
 * @param hash_size 哈希大小，默认为8
 * @return 图片的dHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_dhash_c(const char* image_path, int hash_size);

/**
 * 计算图片的感知哈希(pHash)
 * @param image_path 图片文件路径
 * @param hash_size 哈希大小，默认为8
 * @return 图片的pHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_phash_c(const char* image_path, int hash_size);

/**
 * 计算图片的平均哈希(aHash)
 * @param image_path 图片文件路径
 * @param hash_size 哈希大小，默认为8
 * @return 图片的aHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_ahash_c(const char* image_path, int hash_size);

/**
 * 计算文件的MD5哈希值
 * @param file_path 文件路径
 * @return 文件的MD5哈希值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_file_hash_c(const char* file_path);

/**
 * 计算两个哈希值之间的汉明距离
 * @param hash1 第一个哈希值（十六进制字符串）
 * @param hash2 第二个哈希值（十六进制字符串）
 * @return 两个哈希值之间的汉明距离
 */
DLL_EXPORT int hamming_distance_c(const char* hash1, const char* hash2);

/**
 * 检测图片是否为纯色图片
 * @param image_path 图片文件路径
 * @param threshold 标准差阈值，低于此值被视为纯色图片
 * @return 如果是纯色图片返回1，否则返回0，错误返回-1
 */
DLL_EXPORT int is_pure_color_image_c(const char* image_path, float threshold);

/**
 * 计算图片在指定角度旋转后的差值哈希(dHash)
 * @param image_path 图片文件路径
 * @param angle 旋转角度（0, 90, 180, 270）
 * @param hash_size 哈希大小，默认为8
 * @return 旋转后图片的dHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_dhash_rotated_c(const char* image_path, int angle, int hash_size);

/**
 * 计算图片在指定角度旋转后的感知哈希(pHash)
 * @param image_path 图片文件路径
 * @param angle 旋转角度（0, 90, 180, 270）
 * @param hash_size 哈希大小，默认为8
 * @return 旋转后图片的pHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_phash_rotated_c(const char* image_path, int angle, int hash_size);

/**
 * 计算图片在指定角度旋转后的平均哈希(aHash)
 * @param image_path 图片文件路径
 * @param angle 旋转角度（0, 90, 180, 270）
 * @param hash_size 哈希大小，默认为8
 * @return 旋转后图片的aHash值（十六进制字符串），需要调用者释放内存
 */
DLL_EXPORT char* calculate_ahash_rotated_c(const char* image_path, int angle, int hash_size);

/**
 * 释放由库分配的字符串内存
 * @param str 要释放的字符串指针
 */
DLL_EXPORT void free_string_c(char* str);

#ifdef __cplusplus
}
#endif

#endif // HASH_ALGORITHMS_H