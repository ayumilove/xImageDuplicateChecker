# -*- coding: utf-8 -*-
"""
C++ 哈希算法库 Python 包

高性能的C++图像哈希算法库，为xImageDuplicateChecker项目提供核心算法实现。
"""

__version__ = "1.0.0"
__author__ = "xImageDuplicateChecker Team"
__description__ = "High-performance C++ image hashing library for duplicate detection"

# 导入主要功能
try:
    from .hash_wrapper import (
        calculate_dhash,
        calculate_phash,
        calculate_ahash,
        calculate_file_hash,
        hamming_distance,
        is_pure_color_image,
        HashLibraryWrapper,
        get_hash_lib
    )
    
    from .rotation_invariant_wrapper import (
        RotationInvariantHasher,
        batch_compare_with_rotation
    )
    
    # 标记C++库可用
    CPP_LIBRARY_AVAILABLE = True
    
except Exception as e:
    # 如果C++库不可用，提供错误信息
    CPP_LIBRARY_AVAILABLE = False
    _import_error = str(e)
    
    def _raise_import_error(*args, **kwargs):
        raise ImportError(
            f"C++ 哈希库不可用: {_import_error}\n"
            "请运行 'python build.py' 编译动态库，或检查依赖是否正确安装。"
        )
    
    # 创建占位符函数
    calculate_dhash = _raise_import_error
    calculate_phash = _raise_import_error
    calculate_ahash = _raise_import_error
    calculate_file_hash = _raise_import_error
    hamming_distance = _raise_import_error
    is_pure_color_image = _raise_import_error
    HashLibraryWrapper = _raise_import_error
    get_hash_lib = _raise_import_error
    RotationInvariantHasher = _raise_import_error
    batch_compare_with_rotation = _raise_import_error


# 导出的公共接口
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    'CPP_LIBRARY_AVAILABLE',
    
    # 核心哈希函数
    'calculate_dhash',
    'calculate_phash',
    'calculate_ahash',
    'calculate_file_hash',
    'hamming_distance',
    'is_pure_color_image',
    
    # 库封装类
    'HashLibraryWrapper',
    'get_hash_lib',
    
    # 旋转不变算法
    'RotationInvariantHasher',
    'batch_compare_with_rotation',
]


def get_library_info():
    """
    获取库信息
    
    Returns:
        dict: 包含库版本、状态等信息的字典
    """
    info = {
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'cpp_library_available': CPP_LIBRARY_AVAILABLE,
    }
    
    if CPP_LIBRARY_AVAILABLE:
        try:
            lib = get_hash_lib()
            info['library_loaded'] = True
            info['library_instance'] = str(lib)
        except Exception as e:
            info['library_loaded'] = False
            info['load_error'] = str(e)
    else:
        info['library_loaded'] = False
        info['import_error'] = _import_error if '_import_error' in globals() else 'Unknown error'
    
    return info


def check_installation():
    """
    检查安装状态并打印详细信息
    """
    print(f"C++ 哈希算法库 v{__version__}")
    print("=" * 50)
    
    info = get_library_info()
    
    print(f"库状态: {'✓ 可用' if info['cpp_library_available'] else '✗ 不可用'}")
    
    if info['cpp_library_available']:
        if info['library_loaded']:
            print("✓ 动态库加载成功")
            print(f"库实例: {info['library_instance']}")
        else:
            print("✗ 动态库加载失败")
            print(f"错误: {info['load_error']}")
    else:
        print("✗ 导入失败")
        print(f"错误: {info['import_error']}")
        print("\n解决方案:")
        print("1. 运行 'python build.py' 编译动态库")
        print("2. 检查依赖是否正确安装 (OpenCV, OpenSSL)")
        print("3. 确保编译器和CMake可用")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    # 当直接运行此模块时，显示安装状态
    check_installation()