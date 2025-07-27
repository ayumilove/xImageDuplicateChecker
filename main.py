#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
xImageDuplicateChecker - 图片查重工具

基于文件哈希和感知哈希的图片查重工具，可以检测完全相同和视觉上相似的图片。
"""

import argparse
import os
import sys

from cpp_hash_lib.cpp_duplicate_checker import CppDuplicateChecker


def parse_args():
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description="xImageDuplicateChecker - 图片查重工具")
    
    parser.add_argument(
        "directory", 
        help="要扫描的图片目录"
    )
    
    parser.add_argument(
        "-r", "--recursive", 
        action="store_true", 
        help="递归扫描子目录"
    )
    
    parser.add_argument(
        "-p", "--phash-threshold", 
        type=int, 
        default=5, 
        help="pHash相似度阈值，默认为5"
    )
    
    parser.add_argument(
        "-d", "--dhash-threshold", 
        type=int, 
        default=5, 
        help="dHash相似度阈值，默认为5"
    )
    
    parser.add_argument(
        "-a", "--ahash-threshold", 
        type=int, 
        default=3, 
        help="aHash相似度阈值，默认为5（降低以进一步减少误判）"
    )
    
    parser.add_argument(
        "--no-pure-color-detection", 
        action="store_true", 
        help="禁用纯色图片检测"
    )
    
    parser.add_argument(
        "-o", "--output", 
        default="results", 
        help="结果输出目录，默认为'results'"
    )
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    args = parse_args()
    
    # 检查目录是否存在
    if not os.path.exists(args.directory):
        print(f"错误: 目录不存在: {args.directory}")
        return 1
    
    # 创建查重器
    checker = CppDuplicateChecker(
        phash_threshold=args.phash_threshold,
        dhash_threshold=args.dhash_threshold,
        ahash_threshold=args.ahash_threshold,
        output_dir=args.output,
        detect_pure_color=not args.no_pure_color_detection
    )
    
    # 执行查重
    try:
        checker.check_duplicates(args.directory, args.recursive)
        return 0
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())