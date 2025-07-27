# -*- coding: utf-8 -*-
"""
xImageDuplicateChecker - 图像查重工具

一个高效的Python图像查重工具，支持多种重复检测算法。
"""

__version__ = "1.0.0"
__author__ = "Xing"
__email__ = "awuxing@gmail.com"
__description__ = "一个高效的Python图像查重工具"

from .duplicate_checker import DuplicateChecker
from .hash_utils import (
    calculate_file_hash,
    calculate_dhash,
    calculate_phash,
    calculate_ahash,
    is_pure_color_image
)
from .result_logger import ResultLogger

# 导入C++实现的查重器
try:
    from ..cpp_hash_lib.cpp_duplicate_checker import CppDuplicateChecker
    __all__ = [
        "DuplicateChecker",
        "CppDuplicateChecker",  # C++实现版本
        "calculate_file_hash",
        "calculate_dhash",
        "calculate_phash",
        "calculate_ahash",
        "is_pure_color_image",
        "ResultLogger"
    ]
except ImportError:
    # 如果C++库不可用，只导出Python版本
    __all__ = [
        "DuplicateChecker",
        "calculate_file_hash",
        "calculate_dhash",
        "calculate_phash",
        "calculate_ahash",
        "is_pure_color_image",
        "ResultLogger"
    ]