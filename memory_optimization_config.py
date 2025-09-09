#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存优化配置
用于管理图片查重程序的内存使用

作者: AI Assistant
日期: 2024
"""

import psutil
from typing import Dict, Any

class MemoryOptimizationConfig:
    """
    内存优化配置类
    根据系统内存大小自动调整参数
    """
    
    def __init__(self):
        self.total_memory_gb = psutil.virtual_memory().total / (1024**3)
        self.available_memory_gb = psutil.virtual_memory().available / (1024**3)
        
    def get_config_for_memory_size(self) -> Dict[str, Any]:
        """
        根据系统内存大小返回优化配置
        
        Returns:
            配置字典
        """
        if self.total_memory_gb >= 32:
            return self._get_high_memory_config()
        elif self.total_memory_gb >= 16:
            return self._get_medium_memory_config()
        elif self.total_memory_gb >= 8:
            return self._get_low_memory_config()
        else:
            return self._get_minimal_memory_config()
    
    def _get_high_memory_config(self) -> Dict[str, Any]:
        """高内存配置 (32GB+)"""
        return {
            'max_cache_size': 5000,
            'memory_threshold': 75,
            'memory_critical_threshold': 85,
            'memory_check_interval': 100,
            'gc_interval': 2000,
            'lsh_num_hash_tables': 8,
            'lsh_num_hash_functions': 4,
            'lsh_max_bucket_size': 8000,
            'batch_size': 1000,
            'max_workers': 8,
            'enable_memory_optimization': False,
            'description': '高内存配置：适用于32GB+内存系统'
        }
    
    def _get_medium_memory_config(self) -> Dict[str, Any]:
        """中等内存配置 (16-32GB) - 激进优化版本"""
        return {
            'max_cache_size': 1500,  # 进一步减少缓存
            'memory_threshold': 60,  # 更低的内存阈值
            'memory_critical_threshold': 70,  # 更低的临界阈值
            'memory_check_interval': 25,  # 更频繁的内存检查
            'gc_interval': 500,  # 更频繁的垃圾回收
            'lsh_num_hash_tables': 4,  # 减少LSH哈希表
            'lsh_num_hash_functions': 2,  # 减少哈希函数
            'lsh_max_bucket_size': 2000,  # 减少桶大小
            'batch_size': 200,  # 减少批处理大小
            'max_workers': 4,  # 减少工作线程
            'enable_memory_optimization': True,
            'description': '中等内存配置：适用于16-32GB内存系统（激进优化）'
        }
    
    def _get_low_memory_config(self) -> Dict[str, Any]:
        """低内存配置 (8-16GB)"""
        return {
            'max_cache_size': 1500,
            'memory_threshold': 65,
            'memory_critical_threshold': 75,
            'memory_check_interval': 50,
            'gc_interval': 1000,
            'lsh_num_hash_tables': 4,
            'lsh_num_hash_functions': 2,
            'lsh_max_bucket_size': 3000,
            'batch_size': 200,
            'max_workers': 4,
            'enable_memory_optimization': True,
            'description': '低内存配置：适用于8-16GB内存系统'
        }
    
    def _get_minimal_memory_config(self) -> Dict[str, Any]:
        """最小内存配置 (<8GB)"""
        return {
            'max_cache_size': 500,
            'memory_threshold': 60,
            'memory_critical_threshold': 70,
            'memory_check_interval': 25,
            'gc_interval': 500,
            'lsh_num_hash_tables': 3,
            'lsh_num_hash_functions': 2,
            'lsh_max_bucket_size': 1000,
            'batch_size': 100,
            'max_workers': 2,
            'enable_memory_optimization': True,
            'description': '最小内存配置：适用于<8GB内存系统'
        }
    
    def print_system_info(self):
        """打印系统内存信息"""
        print(f"系统总内存: {self.total_memory_gb:.1f} GB")
        print(f"可用内存: {self.available_memory_gb:.1f} GB")
        print(f"内存使用率: {psutil.virtual_memory().percent:.1f}%")
        
        config = self.get_config_for_memory_size()
        print(f"推荐配置: {config['description']}")
        
    def get_recommended_file_limit(self) -> int:
        """根据内存大小推荐文件处理上限"""
        if self.total_memory_gb >= 32:
            return 200000  # 20万文件
        elif self.total_memory_gb >= 16:
            return 100000  # 10万文件
        elif self.total_memory_gb >= 8:
            return 50000   # 5万文件
        else:
            return 20000   # 2万文件

def get_memory_optimized_config() -> Dict[str, Any]:
    """
    获取内存优化配置的便捷函数
    
    Returns:
        优化配置字典
    """
    optimizer = MemoryOptimizationConfig()
    return optimizer.get_config_for_memory_size()

def print_memory_recommendations():
    """
    打印内存优化建议
    """
    optimizer = MemoryOptimizationConfig()
    optimizer.print_system_info()
    
    config = optimizer.get_config_for_memory_size()
    file_limit = optimizer.get_recommended_file_limit()
    
    print("\n内存优化建议:")
    print(f"- 推荐最大处理文件数: {file_limit:,} 个")
    print(f"- 缓存大小限制: {config['max_cache_size']} 个文件")
    print(f"- LSH哈希表数量: {config['lsh_num_hash_tables']}")
    print(f"- 批处理大小: {config['batch_size']}")
    print(f"- 最大工作线程: {config['max_workers']}")
    
    if optimizer.available_memory_gb < 4:
        print("\n⚠️  警告: 可用内存不足4GB，建议:")
        print("   1. 关闭其他程序释放内存")
        print("   2. 分批处理文件")
        print("   3. 考虑升级内存")

if __name__ == "__main__":
    print_memory_recommendations()