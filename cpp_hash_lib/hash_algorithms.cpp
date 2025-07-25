#include "hash_algorithms.h"
#include <cstring>
#include <cmath>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <vector>
#include <random>

#ifdef HAVE_OPENCV
#include <opencv2/opencv.hpp>
#endif

using namespace std;

string binary_to_hex(const string& binary) {
    string hex = "";
    for (size_t i = 0; i < binary.length(); i += 4) {
        string chunk = binary.substr(i, 4);
        if (chunk.length() < 4) {
            chunk.append(4 - chunk.length(), '0');
        }
        int value = stoi(chunk, nullptr, 2);
        hex += (value < 10) ? ('0' + value) : ('a' + value - 10);
    }
    return hex;
}

char* allocate_string(const string& str) {
    char* result = new char[str.length() + 1];
    strcpy(result, str.c_str());
    return result;
}

char* calculate_dhash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        // 添加调试信息
        if (!image_path) {
            return allocate_string("ERROR: Null image path");
        }
        
        // 先测试基本的 OpenCV 功能
        cv::Mat test_mat = cv::Mat::zeros(10, 10, CV_8UC1);
        if (test_mat.empty()) {
            return allocate_string("ERROR: Cannot create test matrix");
        }
        
        cv::Mat img = cv::imread(string(image_path), cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: Cannot load image");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string("ERROR: Invalid hash size");
        }
        
        cv::Mat resized;
        cv::resize(img, resized, cv::Size(hash_size + 1, hash_size));
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                int left = resized.at<uchar>(i, j);
                int right = resized.at<uchar>(i, j + 1);
                hash_binary += (left > right) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string(error_msg);
    } catch (...) {
        return allocate_string("ERROR: Unknown exception");
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

char* calculate_phash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string("ERROR: Null image path");
        }
        
        cv::Mat img = cv::imread(string(image_path), cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: Cannot load image");
        }
        
        if (hash_size <= 0 || hash_size > 32) {
            return allocate_string("ERROR: Invalid hash size");
        }
        
        cv::Mat resized;
        cv::resize(img, resized, cv::Size(32, 32));
        
        cv::Mat float_img;
        resized.convertTo(float_img, CV_32F);
        
        cv::Mat dct_img;
        cv::dct(float_img, dct_img);
        
        cv::Mat dct_low = dct_img(cv::Rect(0, 0, hash_size, hash_size));
        
        cv::Scalar mean_scalar = cv::mean(dct_low);
        double mean_val = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                if (i == 0 && j == 0) continue;
                hash_binary += (dct_low.at<float>(i, j) > mean_val) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const cv::Exception& e) {
        return allocate_string("ERROR: OpenCV exception");
    } catch (const std::exception& e) {
        return allocate_string("ERROR: Standard exception");
    } catch (...) {
        return allocate_string("ERROR: Unknown exception");
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

char* calculate_ahash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string("ERROR: Null image path");
        }
        
        cv::Mat img = cv::imread(string(image_path), cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: Cannot load image");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string("ERROR: Invalid hash size");
        }
        
        cv::Mat resized;
        cv::resize(img, resized, cv::Size(hash_size, hash_size));
        
        // 检测是否为纯色图片
        cv::Scalar mean_scalar, std_scalar;
        cv::meanStdDev(resized, mean_scalar, std_scalar);
        double std_dev = std_scalar[0];
        
        if (std_dev < 3.0) {
            return allocate_string("pure_color_image");
        }
        
        double avg = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (resized.at<uchar>(i, j) > avg) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const cv::Exception& e) {
        return allocate_string("ERROR: OpenCV exception");
    } catch (const std::exception& e) {
        return allocate_string("ERROR: Standard exception");
    } catch (...) {
        return allocate_string("ERROR: Unknown exception");
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

char* calculate_file_hash_c(const char* file_path) {
    try {
        if (!file_path) {
            return allocate_string("ERROR: Null file path");
        }
        
        ifstream file(file_path, ios::binary);
        if (!file.is_open()) {
            return allocate_string("ERROR: Cannot open file");
        }
        
        // 简单的文件哈希实现（使用文件大小和部分内容）
        file.seekg(0, ios::end);
        size_t file_size = file.tellg();
        file.seekg(0, ios::beg);
        
        // 读取文件开头、中间和结尾的数据
        vector<char> buffer(min(file_size, (size_t)1024));
        file.read(buffer.data(), buffer.size());
        
        // 生成简单哈希
        stringstream ss;
        ss << hex << file_size;
        for (size_t i = 0; i < buffer.size(); i += 16) {
            ss << hex << (unsigned char)buffer[i];
        }
        
        return allocate_string(ss.str());
    } catch (const std::exception& e) {
        return allocate_string("ERROR: File hash calculation failed");
    } catch (...) {
        return allocate_string("ERROR: Unknown exception in file hash");
    }
}

int hamming_distance_c(const char* hash1, const char* hash2) {
    if (strcmp(hash1, "pure_color_image") == 0 || strcmp(hash2, "pure_color_image") == 0) {
        return 64;
    }
    
    size_t len1 = strlen(hash1);
    size_t len2 = strlen(hash2);
    if (len1 != len2) {
        return -1;
    }
    
    int distance = 0;
    for (size_t i = 0; i < len1; i++) {
        int val1, val2;
        if (hash1[i] >= '0' && hash1[i] <= '9') {
            val1 = hash1[i] - '0';
        } else if (hash1[i] >= 'a' && hash1[i] <= 'f') {
            val1 = hash1[i] - 'a' + 10;
        } else {
            return -1;
        }
        
        if (hash2[i] >= '0' && hash2[i] <= '9') {
            val2 = hash2[i] - '0';
        } else if (hash2[i] >= 'a' && hash2[i] <= 'f') {
            val2 = hash2[i] - 'a' + 10;
        } else {
            return -1;
        }
        
        int xor_result = val1 ^ val2;
        while (xor_result) {
            distance += xor_result & 1;
            xor_result >>= 1;
        }
    }
    
    return distance;
}

int is_pure_color_image_c(const char* image_path, float threshold) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return -1;
        }
        
        cv::Mat img = cv::imread(string(image_path), cv::IMREAD_COLOR);
        if (img.empty()) {
            return -1;
        }
        
        // 获取图片尺寸
        if (img.rows < 10 || img.cols < 10) {
            return 1; // 太小的图片视为纯色
        }
        
        // 采样像素（对于大图片，不需要检查所有像素）
        int sample_size = min(100, img.rows * img.cols);
        vector<cv::Vec3b> pixels;
        
        random_device rd;
        mt19937 gen(rd());
        uniform_int_distribution<> dis_x(0, img.cols - 1);
        uniform_int_distribution<> dis_y(0, img.rows - 1);
        
        for (int i = 0; i < sample_size; i++) {
            int x = dis_x(gen);
            int y = dis_y(gen);
            pixels.push_back(img.at<cv::Vec3b>(y, x));
        }
        
        // 计算RGB通道的标准差
        vector<double> r_values, g_values, b_values;
        for (const auto& pixel : pixels) {
            b_values.push_back(pixel[0]); // BGR格式
            g_values.push_back(pixel[1]);
            r_values.push_back(pixel[2]);
        }
        
        // 计算标准差
        auto calc_std = [](const vector<double>& values) {
            double mean = 0;
            for (double v : values) mean += v;
            mean /= values.size();
            
            double variance = 0;
            for (double v : values) {
                variance += (v - mean) * (v - mean);
            }
            variance /= values.size();
            
            return sqrt(variance);
        };
        
        double r_std = calc_std(r_values);
        double g_std = calc_std(g_values);
        double b_std = calc_std(b_values);
        
        // 如果所有通道的标准差都小于阈值，认为是纯色图片
        return (r_std < threshold && g_std < threshold && b_std < threshold) ? 1 : 0;
    } catch (const cv::Exception& e) {
        return -1;
    } catch (const std::exception& e) {
        return -1;
    } catch (...) {
        return -1;
    }
#else
    return -1;
#endif
}

// 旋转图像的辅助函数
cv::Mat rotate_image(const cv::Mat& img, int angle) {
    cv::Mat rotated;
    cv::Point2f center(img.cols / 2.0, img.rows / 2.0);
    
    switch (angle) {
        case 0:
            return img.clone();
        case 90:
            cv::transpose(img, rotated);
            cv::flip(rotated, rotated, 1);
            break;
        case 180:
            cv::flip(img, rotated, -1);
            break;
        case 270:
            cv::transpose(img, rotated);
            cv::flip(rotated, rotated, 0);
            break;
        default:
            // 对于其他角度，使用仿射变换
            cv::Mat rotation_matrix = cv::getRotationMatrix2D(center, angle, 1.0);
            cv::warpAffine(img, rotated, rotation_matrix, img.size());
            break;
    }
    
    return rotated;
}

char* calculate_dhash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        cv::Mat img = cv::imread(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: 无法读取图片文件");
        }
        
        // 旋转图像
        cv::Mat rotated_img = rotate_image(img, angle);
        
        cv::Mat resized;
        cv::resize(rotated_img, resized, cv::Size(hash_size + 1, hash_size));
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (resized.at<uchar>(i, j) > resized.at<uchar>(i, j + 1)) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const exception& e) {
        return allocate_string("ERROR: " + string(e.what()));
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

char* calculate_phash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        cv::Mat img = cv::imread(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: 无法读取图片文件");
        }
        
        // 旋转图像
        cv::Mat rotated_img = rotate_image(img, angle);
        
        cv::Mat resized;
        cv::resize(rotated_img, resized, cv::Size(hash_size * 4, hash_size * 4));
        
        cv::Mat float_img;
        resized.convertTo(float_img, CV_32F);
        
        cv::Mat dct_img;
        cv::dct(float_img, dct_img);
        
        cv::Mat dct_low = dct_img(cv::Rect(1, 1, hash_size, hash_size));
        
        cv::Scalar mean_scalar = cv::mean(dct_low);
        double avg = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (dct_low.at<float>(i, j) > avg) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const exception& e) {
        return allocate_string("ERROR: " + string(e.what()));
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

char* calculate_ahash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        cv::Mat img = cv::imread(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string("ERROR: 无法读取图片文件");
        }
        
        // 旋转图像
        cv::Mat rotated_img = rotate_image(img, angle);
        
        cv::Mat resized;
        cv::resize(rotated_img, resized, cv::Size(hash_size, hash_size));
        
        // 检测是否为纯色图片
        cv::Scalar mean_scalar, std_scalar;
        cv::meanStdDev(resized, mean_scalar, std_scalar);
        double std_dev = std_scalar[0];
        
        if (std_dev < 3.0) {
            return allocate_string("pure_color_image");
        }
        
        double avg = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (resized.at<uchar>(i, j) > avg) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string(hex_hash);
    } catch (const exception& e) {
        return allocate_string("ERROR: " + string(e.what()));
    }
#else
    return allocate_string("ERROR: OpenCV not available");
#endif
}

void free_string_c(char* str) {
    if (str != nullptr) {
        delete[] str;
    }
}