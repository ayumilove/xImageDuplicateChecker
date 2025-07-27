#include "hash_algorithms.h"
#include <cstring>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <stdexcept>

#ifdef HAVE_OPENCV
#include <opencv2/opencv.hpp>
#include <opencv2/imgproc.hpp>
#ifdef _WIN32
#include <windows.h>
#include <codecvt>
#include <locale>
#endif
#endif

#ifdef HAVE_OPENSSL
#include <openssl/md5.h>
#include <openssl/sha.h>
#endif

using namespace std;

#ifdef HAVE_OPENCV
#ifdef _WIN32
// Windows上处理UTF-8中文路径的辅助函数
cv::Mat imread_unicode(const string& filename, int flags = cv::IMREAD_COLOR) {
    try {
        // 将UTF-8字符串转换为宽字符
        std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
        std::wstring wide_filename = converter.from_bytes(filename);
        
        // 使用Windows API读取文件到内存，然后用OpenCV解码
        HANDLE hFile = CreateFileW(wide_filename.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hFile == INVALID_HANDLE_VALUE) {
            // 如果Unicode路径失败，尝试直接读取
            return cv::imread(filename, flags);
        }
        
        DWORD fileSize = GetFileSize(hFile, NULL);
        if (fileSize == INVALID_FILE_SIZE || fileSize == 0) {
            CloseHandle(hFile);
            return cv::Mat();
        }
        
        std::vector<uchar> buffer(fileSize);
        DWORD bytesRead;
        if (!ReadFile(hFile, buffer.data(), fileSize, &bytesRead, NULL) || bytesRead != fileSize) {
            CloseHandle(hFile);
            return cv::Mat();
        }
        
        CloseHandle(hFile);
        
        // 使用OpenCV从内存缓冲区解码图像
        cv::Mat img = cv::imdecode(buffer, flags);
        return img;
    } catch (...) {
        // 如果转换失败，尝试直接读取
        return cv::imread(filename, flags);
    }
}
#else
// 非Windows系统直接使用OpenCV的imread
cv::Mat imread_unicode(const string& filename, int flags = cv::IMREAD_COLOR) {
    return cv::imread(filename, flags);
}
#endif
#endif

string allocate_string(const string& str) {
    return str;
}

char* allocate_string_c(const string& str) {
    char* result = new char[str.length() + 1];
    strcpy(result, str.c_str());
    return result;
}

void free_string_c(char* str) {
    delete[] str;
}

string binary_to_hex(const string& binary) {
    stringstream ss;
    for (size_t i = 0; i < binary.length(); i += 4) {
        string nibble = binary.substr(i, 4);
        while (nibble.length() < 4) nibble += "0";
        
        int value = 0;
        for (int j = 0; j < 4; j++) {
            if (nibble[j] == '1') {
                value += (1 << (3 - j));
            }
        }
        
        ss << hex << value;
    }
    return ss.str();
}

#ifdef _WIN32
// Windows上处理UTF-8中文路径的文件读取函数
vector<char> read_file_unicode(const string& filename) {
    try {
        // 将UTF-8字符串转换为宽字符
        std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
        std::wstring wide_filename = converter.from_bytes(filename);
        
        // 使用Windows API读取文件
        HANDLE hFile = CreateFileW(wide_filename.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (hFile == INVALID_HANDLE_VALUE) {
            return vector<char>();
        }
        
        DWORD fileSize = GetFileSize(hFile, NULL);
        if (fileSize == INVALID_FILE_SIZE || fileSize == 0) {
            CloseHandle(hFile);
            return vector<char>();
        }
        
        vector<char> buffer(fileSize);
        DWORD bytesRead;
        if (!ReadFile(hFile, buffer.data(), fileSize, &bytesRead, NULL) || bytesRead != fileSize) {
            CloseHandle(hFile);
            return vector<char>();
        }
        
        CloseHandle(hFile);
        return buffer;
    } catch (...) {
        return vector<char>();
    }
}
#endif

char* calculate_file_hash_c(const char* file_path) {
    try {
        if (!file_path) {
            return allocate_string_c("ERROR: Null file path");
        }
        
#ifdef _WIN32
        // Windows上使用Unicode文件读取
        vector<char> file_data = read_file_unicode(string(file_path));
        if (file_data.empty()) {
            return allocate_string_c("ERROR: Cannot open file");
        }
        
        streamsize file_size = file_data.size();
#else
        // 非Windows系统使用标准文件读取
        ifstream file(file_path, ios::binary | ios::ate);
        if (!file.is_open()) {
            return allocate_string_c("ERROR: Cannot open file");
        }
        
        streamsize file_size = file.tellg();
#endif
        
        if (file_size == 0) {
            return allocate_string_c("0");
        }
        
        vector<char> buffer;
        const size_t chunk_size = 8192;
        const size_t max_chunks = 8;
        
        size_t chunks_to_read = min(max_chunks, (size_t)((file_size + chunk_size - 1) / chunk_size));
        size_t step = max((size_t)1, (size_t)(file_size / chunk_size / chunks_to_read));
        
#ifdef _WIN32
        // Windows上从内存数据中采样
        for (size_t i = 0; i < chunks_to_read; i++) {
            size_t pos = i * step * chunk_size;
            if (pos >= file_data.size()) break;
            
            size_t read_size = min(chunk_size, file_data.size() - pos);
            buffer.insert(buffer.end(), file_data.begin() + pos, file_data.begin() + pos + read_size);
        }
#else
        // 非Windows系统从文件流中采样
        file.seekg(0, ios::beg);
        
        for (size_t i = 0; i < chunks_to_read; i++) {
            size_t pos = i * step * chunk_size;
            if (pos >= file_size) break;
            
            file.seekg(pos);
            size_t read_size = min(chunk_size, (size_t)(file_size - pos));
            
            vector<char> chunk(read_size);
            file.read(chunk.data(), read_size);
            buffer.insert(buffer.end(), chunk.begin(), chunk.end());
        }
#endif
        
        string size_str = to_string(file_size);
        buffer.insert(buffer.end(), size_str.begin(), size_str.end());
        
        uint64_t hash1 = 0x9e3779b9;
        uint64_t hash2 = 0x85ebca6b;
        
        for (char c : buffer) {
            hash1 = ((hash1 << 5) + hash1) + (unsigned char)c;
            hash2 = ((hash2 << 7) + hash2) ^ (unsigned char)c;
        }
        
        stringstream ss;
        ss << hex << hash1 << hash2;
        return allocate_string_c(ss.str());
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
}

int hamming_distance_c(const char* hash1, const char* hash2) {
    if (!hash1 || !hash2) {
        return -1;
    }
    
    string h1(hash1);
    string h2(hash2);
    
    if (h1.length() != h2.length()) {
        return -1;
    }
    
    int distance = 0;
    for (size_t i = 0; i < h1.length(); i++) {
        if (h1[i] != h2[i]) {
            distance++;
        }
    }
    
    return distance;
}

int is_pure_color_image_c(const char* image_path, float threshold) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return false;
        }
        
        cv::Mat img = imread_unicode(string(image_path), cv::IMREAD_COLOR);
        if (img.empty()) {
            return false;
        }
        
        vector<cv::Point> sample_points;
        int step = max(1, min(img.rows, img.cols) / 10);
        
        for (int i = step; i < img.rows; i += step) {
            for (int j = step; j < img.cols; j += step) {
                sample_points.push_back(cv::Point(j, i));
            }
        }
        
        if (sample_points.empty()) {
            sample_points.push_back(cv::Point(img.cols/2, img.rows/2));
        }
        
        vector<double> r_values, g_values, b_values;
        
        for (const auto& point : sample_points) {
            cv::Vec3b pixel = img.at<cv::Vec3b>(point.y, point.x);
            b_values.push_back(pixel[0]);
            g_values.push_back(pixel[1]);
            r_values.push_back(pixel[2]);
        }
        
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
        
        return (r_std < threshold && g_std < threshold && b_std < threshold) ? 1 : 0;
    } catch (...) {
        return -1;
    }
#else
    return -1;
#endif
}

#ifdef HAVE_OPENCV
cv::Mat rotate_image(const cv::Mat& img, int angle) {
    cv::Mat rotated;
    
    angle = ((angle % 360) + 360) % 360;
    
    switch (angle) {
        case 0:
            rotated = img.clone();
            break;
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
            cv::Point2f center(img.cols / 2.0f, img.rows / 2.0f);
            cv::Mat rotation_matrix = cv::getRotationMatrix2D(center, angle, 1.0);
            cv::warpAffine(img, rotated, rotation_matrix, img.size(), cv::INTER_LINEAR, cv::BORDER_REFLECT);
            break;
    }
    
    return rotated;
}
#endif

char* calculate_dhash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
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
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}

char* calculate_phash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 32) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
        }
        
        cv::Mat resized;
        cv::resize(img, resized, cv::Size(hash_size, hash_size));
        
        cv::Mat float_img;
        resized.convertTo(float_img, CV_32F);
        
        cv::Mat dct_img;
        cv::dct(float_img, dct_img);
        
        cv::Scalar sum_scalar = cv::sum(dct_img(cv::Rect(0, 0, 8, 8)));
        double avg = sum_scalar[0] / 64.0;
        
        string hash_binary = "";
        for (int i = 0; i < 8; i++) {
            for (int j = 0; j < 8; j++) {
                hash_binary += (dct_img.at<float>(i, j) > avg) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}

char* calculate_ahash_c(const char* image_path, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
        }
        
        cv::Mat resized;
        cv::resize(img, resized, cv::Size(hash_size, hash_size));
        
        cv::Scalar mean_scalar = cv::mean(resized);
        double mean_val = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (resized.at<uchar>(i, j) > mean_val) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}

char* calculate_dhash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
        }
        
        cv::Mat rotated_img = rotate_image(img, angle);
        if (rotated_img.empty()) {
            return allocate_string_c("ERROR: Failed to rotate image");
        }
        
        cv::Mat resized;
        int dct_size = hash_size;
        cv::resize(rotated_img, resized, cv::Size(dct_size + 1, dct_size));
        
        string hash_binary = "";
        for (int i = 0; i < dct_size; i++) {
            for (int j = 0; j < dct_size; j++) {
                int left = resized.at<uchar>(i, j);
                int right = resized.at<uchar>(i, j + 1);
                hash_binary += (left > right) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}

char* calculate_phash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 32) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
        }
        
        cv::Mat rotated_img = rotate_image(img, angle);
        if (rotated_img.empty()) {
            return allocate_string_c("ERROR: Failed to rotate image");
        }
        
        cv::Mat resized;
        int dct_size = hash_size;
        cv::resize(rotated_img, resized, cv::Size(dct_size, dct_size));
        
        cv::Mat float_img;
        resized.convertTo(float_img, CV_32F);
        
        cv::Mat dct_img;
        cv::dct(float_img, dct_img);
        
        cv::Scalar sum_scalar = cv::sum(dct_img(cv::Rect(0, 0, 8, 8)));
        double avg = sum_scalar[0] / 64.0;
        
        string hash_binary = "";
        for (int i = 0; i < 8; i++) {
            for (int j = 0; j < 8; j++) {
                hash_binary += (dct_img.at<float>(i, j) > avg) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}

char* calculate_ahash_rotated_c(const char* image_path, int angle, int hash_size) {
#ifdef HAVE_OPENCV
    try {
        if (!image_path) {
            return allocate_string_c("ERROR: Null image path");
        }
        
        if (hash_size <= 0 || hash_size > 64) {
            return allocate_string_c("ERROR: Invalid hash size");
        }
        
        cv::Mat img = imread_unicode(image_path, cv::IMREAD_GRAYSCALE);
        if (img.empty()) {
            return allocate_string_c("ERROR: Cannot load image");
        }
        
        cv::Mat rotated_img = rotate_image(img, angle);
        if (rotated_img.empty()) {
            return allocate_string_c("ERROR: Failed to rotate image");
        }
        
        cv::Mat resized;
        cv::resize(rotated_img, resized, cv::Size(hash_size, hash_size));
        
        cv::Scalar mean_scalar = cv::mean(resized);
        double mean_val = mean_scalar[0];
        
        string hash_binary = "";
        for (int i = 0; i < hash_size; i++) {
            for (int j = 0; j < hash_size; j++) {
                hash_binary += (resized.at<uchar>(i, j) > mean_val) ? "1" : "0";
            }
        }
        
        string hex_hash = binary_to_hex(hash_binary);
        return allocate_string_c(hex_hash);
    } catch (const cv::Exception& e) {
        string error_msg = "ERROR: OpenCV exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (const std::exception& e) {
        string error_msg = "ERROR: Standard exception: " + string(e.what());
        return allocate_string_c(error_msg);
    } catch (...) {
        return allocate_string_c("ERROR: Unknown exception");
    }
#else
    return allocate_string_c("ERROR: OpenCV not available");
#endif
}
