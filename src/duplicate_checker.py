# -*- coding: utf-8 -*-
"""
图片查重核心模块

实现基于文件哈希和感知哈希的图片查重功能
"""

import os
import time
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Set, Optional

from .hash_utils import (
    calculate_file_hash, 
    calculate_dhash, 
    calculate_phash, 
    calculate_ahash,
    hamming_distance,
    is_pure_color_image
)
from .result_logger import ResultLogger
from .rotation_invariant_hash import batch_compare_with_rotation


class DuplicateChecker:
    """
    图片查重器，用于检测重复图片
    """
    
    def __init__(self, 
                 phash_threshold: int = 2,
                 dhash_threshold: int = 8,
                 ahash_threshold: int = 2,  # 大幅降低aHash阈值至2，减少误判
                 output_dir: str = "results",
                 detect_pure_color: bool = True,
                 detect_rotation: bool = False):
        """
        初始化图片查重器
        
        Args:
            phash_threshold: pHash感知哈希相似度阈值，默认为2（降低以提高准确性）
            dhash_threshold: dHash感知哈希相似度阈值，默认为8
            ahash_threshold: aHash感知哈希相似度阈值，默认为2（大幅降低以减少误判）
            output_dir: 结果输出目录，默认为"results"
            detect_pure_color: 是否检测并标记纯色图片，默认为True
            detect_rotation: 是否启用旋转识别功能，默认为False
        """
        self.phash_threshold = phash_threshold
        self.dhash_threshold = dhash_threshold
        self.ahash_threshold = ahash_threshold
        self.detect_pure_color = detect_pure_color
        self.detect_rotation = detect_rotation
        self.logger = ResultLogger(output_dir)
        
        # 日志回调函数
        self.log_callback = None
        
        # 存储结果
        self.file_hash_groups = defaultdict(list)  # 文件哈希 -> 文件列表
        self.phash_groups = []  # 感知哈希相似组
        self.pure_color_images = []  # 纯色图片列表
        
        # 统计信息
        self.stats = {
            'total_images': 0,
            'duplicate_groups': 0,
            'duplicate_images': 0,
            'pure_color_images': 0,
            'reasons': defaultdict(int)
        }
    
    def set_log_callback(self, callback):
        """
        设置日志回调函数
        
        Args:
            callback: 日志回调函数，接收一个字符串参数
        """
        self.log_callback = callback
    
    def log(self, message):
        """
        输出日志信息
        
        Args:
            message: 日志消息
        """
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """
        扫描目录获取所有图片文件
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录，默认为True
            
        Returns:
            图片文件路径列表
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
        image_files = []
        
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        image_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if os.path.isfile(os.path.join(directory, file)) and \
                   os.path.splitext(file)[1].lower() in image_extensions:
                    image_files.append(os.path.join(directory, file))
        
        return image_files
    
    def check_exact_duplicates(self, image_files: List[str]) -> Dict[str, List[str]]:
        """
        检查完全相同的重复图片（基于文件哈希）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            哈希值 -> 文件列表的字典
        """
        file_hash_map = defaultdict(list)
        
        self.log(f"正在计算 {len(image_files)} 个文件的哈希值...")
        for i, file_path in enumerate(image_files):
            if i % 100 == 0 and i > 0:
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                file_hash = calculate_file_hash(file_path)
                file_hash_map[file_hash].append(file_path)
            except Exception as e:
                self.log(f"处理文件时出错: {file_path}, 错误: {str(e)}")
        
        # 只保留有重复的组
        duplicate_groups = {h: files for h, files in file_hash_map.items() if len(files) > 1}
        
        # 更新统计信息
        self.file_hash_groups = duplicate_groups
        if duplicate_groups:
            self.stats['reasons']['完全相同'] = len(duplicate_groups)
            self.stats['duplicate_groups'] += len(duplicate_groups)
            self.stats['duplicate_images'] += sum(len(files) - 1 for files in duplicate_groups.values())
        
        return duplicate_groups
    
    def check_pure_color_images(self, image_files: List[str]) -> List[str]:
        """
        检测纯色图片
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            纯色图片列表
        """
        if not self.detect_pure_color:
            return []
            
        self.log("正在检测纯色图片...")
        pure_color_images = []
        
        for i, file_path in enumerate(image_files):
            if i % 100 == 0 and i > 0:
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                if is_pure_color_image(file_path):
                    pure_color_images.append(file_path)
                    self.stats['pure_color_images'] += 1
            except Exception as e:
                self.log(f"检测纯色图片时出错: {file_path}, 错误: {str(e)}")
        
        self.pure_color_images = pure_color_images
        return pure_color_images
    
    def check_perceptual_duplicates(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        检查感知上相似的图片（基于感知哈希）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            相似图片组列表
        """
        # 如果启用了旋转识别，使用旋转不变算法
        if self.detect_rotation:
            self.log(f"使用旋转不变算法检测相似图片 (共 {len(image_files)} 个文件)...")
            similar_groups = batch_compare_with_rotation(
                image_files,
                dhash_threshold=self.dhash_threshold,
                phash_threshold=self.phash_threshold,
                ahash_threshold=self.ahash_threshold,
                log_callback=self.log_callback
            )
            
            # 更新统计信息
            self.phash_groups = similar_groups
            if similar_groups:
                for group in similar_groups:
                    reason = group['reason']
                    self.stats['reasons'][reason] = self.stats['reasons'].get(reason, 0) + 1
                
                self.stats['duplicate_groups'] += len(similar_groups)
                self.stats['duplicate_images'] += sum(len(group['files']) - 1 for group in similar_groups)
            
            return similar_groups
        
        # 使用传统算法
        # 计算所有图片的感知哈希
        self.log(f"正在计算 {len(image_files)} 个文件的感知哈希...")
        
        # 存储每个文件的dhash和phash
        file_hashes = []
        
        for i, file_path in enumerate(image_files):
            if i % 100 == 0 and i > 0:
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                dhash = calculate_dhash(file_path)
                phash = calculate_phash(file_path)
                ahash = calculate_ahash(file_path)
                
                file_hashes.append({
                    'path': file_path,
                    'dhash': dhash,
                    'phash': phash,
                    'ahash': ahash
                })
            except Exception as e:
                self.log(f"计算感知哈希时出错: {file_path}, 错误: {str(e)}")
        
        # 查找相似图片组
        similar_groups = []
        processed = set()  # 已处理的文件
        
        self.log("正在查找相似图片组...")
        for i, file1 in enumerate(file_hashes):
            if file1['path'] in processed:
                continue
            
            if i % 100 == 0 and i > 0:
                self.log(f"已处理 {i}/{len(file_hashes)} 个文件...")
            
            similar_files = []
            reason = ""
            
            for file2 in file_hashes:
                if file1['path'] == file2['path'] or file2['path'] in processed:
                    continue
                
                # 计算dhash距离
                dhash_distance = hamming_distance(file1['dhash'], file2['dhash'])
                
                # 计算phash距离
                phash_distance = hamming_distance(file1['phash'], file2['phash'])
                
                # 计算ahash距离
                ahash_distance = hamming_distance(file1['ahash'], file2['ahash'])
                
                # 判断是否相似 - 使用多重验证机制，至少两种算法都判断为相似
                dhash_similar = dhash_distance < self.dhash_threshold
                phash_similar = phash_distance < self.phash_threshold
                ahash_similar = ahash_distance < self.ahash_threshold
                
                # 计算相似的算法数量
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                
                # 至少需要两种算法都判断为相似才认为是重复
                if similar_count >= 2:
                    similar_files.append({
                        'path': file2['path'],
                        'dhash_distance': dhash_distance,
                        'phash_distance': phash_distance,
                        'ahash_distance': ahash_distance
                    })
                    # 确定主要原因
                    reasons = []
                    if dhash_similar:
                        reasons.append("dHash")
                    if phash_similar:
                        reasons.append("pHash")
                    if ahash_similar:
                        reasons.append("aHash")
                    reason = "+".join(reasons) + "相似"
            
            if similar_files:
                # 构建文件列表，包含哈希距离信息
                files_with_distances = [{
                    'path': file1['path'],
                    'dhash_distance': 0,  # 基准文件距离为0
                    'phash_distance': 0,
                    'ahash_distance': 0
                }]
                files_with_distances.extend(similar_files)
                
                similar_group = {
                    'reason': reason,
                    'files': [item['path'] for item in files_with_distances],  # 保持向后兼容
                    'files_with_distances': files_with_distances  # 新增：包含距离信息的文件列表
                }
                similar_groups.append(similar_group)
                
                # 标记为已处理
                processed.add(file1['path'])
                for file_info in similar_files:
                    processed.add(file_info['path'])
        
        # 更新统计信息
        self.phash_groups = similar_groups
        if similar_groups:
            for group in similar_groups:
                reason = group['reason']
                self.stats['reasons'][reason] = self.stats['reasons'].get(reason, 0) + 1
            
            self.stats['duplicate_groups'] += len(similar_groups)
            self.stats['duplicate_images'] += sum(len(group['files']) - 1 for group in similar_groups)
        
        return similar_groups
    
    def check_duplicates(self, directory: str, recursive: bool = True) -> Dict[str, Any]:
        """
        执行完整的图片查重流程
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录，默认为True
            
        Returns:
            查重结果统计信息
        """
        start_time = time.time()
        
        # 扫描目录获取所有图片文件
        self.log(f"正在扫描目录: {directory}")
        image_files = self.scan_directory(directory, recursive)
        self.log(f"找到 {len(image_files)} 个图片文件")
        
        self.stats['total_images'] = len(image_files)
        
        # 步骤1: 检查完全相同的重复图片
        self.log("\n步骤1: 检查完全相同的重复图片")
        exact_duplicates = self.check_exact_duplicates(image_files)
        
        # 从图片列表中移除完全相同的重复图片（只保留每组的第一个）
        unique_images = []
        processed_files = set()
        
        for files in exact_duplicates.values():
            unique_images.append(files[0])
            for file_path in files:
                processed_files.add(file_path)
        
        for file_path in image_files:
            if file_path not in processed_files:
                unique_images.append(file_path)
        
        # 步骤2: 检测纯色图片
        self.log(f"\n步骤2: 检测纯色图片 (共 {len(unique_images)} 个唯一文件)")
        pure_color_images = self.check_pure_color_images(unique_images)
        
        # 从图片列表中移除纯色图片
        if pure_color_images:
            unique_images = [img for img in unique_images if img not in set(pure_color_images)]
        
        # 步骤3: 检查感知上相似的图片
        self.log(f"\n步骤3: 检查感知上相似的图片 (共 {len(unique_images)} 个唯一文件)")
        similar_groups = self.check_perceptual_duplicates(unique_images)
        
        # 生成结果
        all_duplicate_groups = []
        
        # 添加完全相同的重复组
        for file_hash, files in exact_duplicates.items():
            all_duplicate_groups.append({
                'reason': '完全相同',
                'files': files
            })
        
        # 添加纯色图片组（如果有）
        if self.pure_color_images:
            all_duplicate_groups.append({
                'reason': '纯色图片',
                'files': self.pure_color_images
            })
            self.stats['reasons']['纯色图片'] = 1
            if not self.stats['duplicate_groups']:
                self.stats['duplicate_groups'] = 1
            else:
                self.stats['duplicate_groups'] += 1
        
        # 添加感知相似的重复组
        all_duplicate_groups.extend(similar_groups)
        
        # 保存结果
        if all_duplicate_groups:
            csv_path = self.logger.save_to_csv(all_duplicate_groups)
            json_path = self.logger.save_to_json(all_duplicate_groups)
            summary_path = self.logger.save_summary(self.stats)
            
            self.log(f"\n查重结果已保存到:")
            self.log(f"- CSV: {csv_path}")
            self.log(f"- JSON: {json_path}")
            self.log(f"- 摘要: {summary_path}")
        else:
            self.log("\n未发现重复图片")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        self.log(f"\n查重完成，耗时: {elapsed_time:.2f}秒")
        self.log(f"总处理图片数: {self.stats['total_images']}")
        self.log(f"重复图片组数: {self.stats['duplicate_groups']}")
        self.log(f"重复图片总数: {self.stats['duplicate_images']}")
        if self.pure_color_images:
            self.log(f"纯色图片数: {self.stats['pure_color_images']}")
        
        return self.stats