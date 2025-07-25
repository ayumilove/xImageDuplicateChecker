# -*- coding: utf-8 -*-
"""
C++ 哈希算法库的Python封装

提供与原有Python实现相同的接口，但使用C++动态库实现
"""

import ctypes
import os
import platform
from typing import Optional


class HashLibraryWrapper:
    """
    C++ 哈希算法库的Python封装类
    """
    
    def __init__(self, lib_path: Optional[str] = None):
        """
        初始化哈希库封装
        
        Args:
            lib_path: 动态库路径，如果为None则自动检测
        """
        self.lib = None
        self._load_library(lib_path)
        self._setup_function_signatures()
    
    def _load_library(self, lib_path: Optional[str] = None):
        """
        加载动态库
        
        Args:
            lib_path: 动态库路径
        """
        if lib_path is None:
            # 自动检测库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            if platform.system() == "Windows":
                lib_name = "hash_algorithms.dll"
                possible_paths = [
                    os.path.join(current_dir, "build", "bin", lib_name),
                    os.path.join(current_dir, "build", "Release", lib_name),
                    os.path.join(current_dir, "build", "Debug", lib_name),
                    os.path.join(current_dir, lib_name)
                ]
            else:
                lib_name = "libhash_algorithms.so"
                possible_paths = [
                    os.path.join(current_dir, "build", "lib", lib_name),
                    os.path.join(current_dir, lib_name)
                ]
            
            lib_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    lib_path = path
                    break
            
            if lib_path is None:
                raise FileNotFoundError(f"无法找到动态库文件。请确保已编译库文件，或手动指定路径。")
        
        try:
            self.lib = ctypes.CDLL(lib_path)
        except OSError as e:
            raise RuntimeError(f"无法加载动态库 {lib_path}: {e}")
    
    def _setup_function_signatures(self):
        """
        设置函数签名
        """
        # calculate_dhash_c - 返回指针而不是自动转换的字符串
        self.lib.calculate_dhash_c.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.calculate_dhash_c.restype = ctypes.c_void_p
        
        # calculate_phash_c
        self.lib.calculate_phash_c.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.calculate_phash_c.restype = ctypes.c_void_p
        
        # calculate_ahash_c
        self.lib.calculate_ahash_c.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.calculate_ahash_c.restype = ctypes.c_void_p
        
        # calculate_file_hash_c
        self.lib.calculate_file_hash_c.argtypes = [ctypes.c_char_p]
        self.lib.calculate_file_hash_c.restype = ctypes.c_void_p
        
        # hamming_distance_c
        self.lib.hamming_distance_c.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.hamming_distance_c.restype = ctypes.c_int
        
        # is_pure_color_image_c
        self.lib.is_pure_color_image_c.argtypes = [ctypes.c_char_p, ctypes.c_float]
        self.lib.is_pure_color_image_c.restype = ctypes.c_int
        
        # free_string_c
        self.lib.free_string_c.argtypes = [ctypes.c_void_p]
        self.lib.free_string_c.restype = None
    
    def _call_and_free(self, func, *args):
        """
        调用C函数并自动释放返回的字符串内存
        
        Args:
            func: C函数
            *args: 函数参数
            
        Returns:
            解码后的字符串
        """
        result_ptr = func(*args)
        if result_ptr:
            try:
                result = ctypes.string_at(result_ptr).decode('utf-8')
                return result
            finally:
                self.lib.free_string_c(result_ptr)
        return None
    
    def calculate_dhash(self, image_path: str, hash_size: int = 8) -> str:
        """
        计算图片的差值哈希(dHash)
        
        Args:
            image_path: 图片文件路径
            hash_size: 哈希大小，默认为8
            
        Returns:
            图片的dHash值（十六进制字符串）
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        result = self._call_and_free(
            self.lib.calculate_dhash_c,
            image_path.encode('utf-8'),
            hash_size
        )
        
        if result and result.startswith("ERROR:"):
            raise ValueError(result)
        
        return result
    
    def calculate_phash(self, image_path: str, hash_size: int = 8) -> str:
        """
        计算图片的感知哈希(pHash)
        
        Args:
            image_path: 图片文件路径
            hash_size: 哈希大小，默认为8
            
        Returns:
            图片的pHash值（十六进制字符串）
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        result = self._call_and_free(
            self.lib.calculate_phash_c,
            image_path.encode('utf-8'),
            hash_size
        )
        
        if result and result.startswith("ERROR:"):
            raise ValueError(result)
        
        return result
    
    def calculate_ahash(self, image_path: str, hash_size: int = 8) -> str:
        """
        计算图片的平均哈希(aHash)
        
        Args:
            image_path: 图片文件路径
            hash_size: 哈希大小，默认为8
            
        Returns:
            图片的aHash值（十六进制字符串）
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        result = self._call_and_free(
            self.lib.calculate_ahash_c,
            image_path.encode('utf-8'),
            hash_size
        )
        
        if result and result.startswith("ERROR:"):
            raise ValueError(result)
        
        return result
    
    def calculate_file_hash(self, file_path: str) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件的MD5哈希值
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        result = self._call_and_free(
            self.lib.calculate_file_hash_c,
            file_path.encode('utf-8')
        )
        
        if result and result.startswith("ERROR:"):
            raise ValueError(result)
        
        return result
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算两个哈希值之间的汉明距离
        
        Args:
            hash1: 第一个哈希值（十六进制字符串）
            hash2: 第二个哈希值（十六进制字符串）
            
        Returns:
            两个哈希值之间的汉明距离
        """
        result = self.lib.hamming_distance_c(
            hash1.encode('utf-8'),
            hash2.encode('utf-8')
        )
        
        if result < 0:
            raise ValueError(f"哈希值格式错误或长度不匹配: {hash1} vs {hash2}")
        
        return result
    
    def is_pure_color_image(self, image_path: str, threshold: float = 3.0) -> bool:
        """
        检测图片是否为纯色图片
        
        Args:
            image_path: 图片文件路径
            threshold: 标准差阈值，低于此值被视为纯色图片
            
        Returns:
            如果是纯色图片返回True，否则返回False
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        result = self.lib.is_pure_color_image_c(
            image_path.encode('utf-8'),
            ctypes.c_float(threshold)
        )
        
        if result < 0:
            raise ValueError(f"无法处理图片: {image_path}")
        
        return result == 1


# 全局实例
_hash_lib_instance = None


def get_hash_lib():
    """
    获取哈希库实例（单例模式）
    
    Returns:
        HashLibraryWrapper实例
    """
    global _hash_lib_instance
    if _hash_lib_instance is None:
        _hash_lib_instance = HashLibraryWrapper()
    return _hash_lib_instance


# 提供与原有代码兼容的函数接口
def calculate_dhash(image_path: str, hash_size: int = 8) -> str:
    """计算图片的差值哈希(dHash)"""
    return get_hash_lib().calculate_dhash(image_path, hash_size)


def calculate_phash(image_path: str, hash_size: int = 8) -> str:
    """计算图片的感知哈希(pHash)"""
    return get_hash_lib().calculate_phash(image_path, hash_size)


def calculate_ahash(image_path: str, hash_size: int = 8) -> str:
    """计算图片的平均哈希(aHash)"""
    return get_hash_lib().calculate_ahash(image_path, hash_size)


def calculate_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希值"""
    return get_hash_lib().calculate_file_hash(file_path)


def hamming_distance(hash1: str, hash2: str) -> int:
    """计算两个哈希值之间的汉明距离"""
    return get_hash_lib().hamming_distance(hash1, hash2)


def is_pure_color_image(image_path: str, threshold: float = 3.0) -> bool:
    """检测图片是否为纯色图片"""
    return get_hash_lib().is_pure_color_image(image_path, threshold)


if __name__ == "__main__":
    # 测试代码
    try:
        lib = get_hash_lib()
        print("C++ 哈希库加载成功！")
        print(f"库实例: {lib}")
    except Exception as e:
        print(f"加载C++ 哈希库失败: {e}")
        print("请确保已正确编译动态库文件。")