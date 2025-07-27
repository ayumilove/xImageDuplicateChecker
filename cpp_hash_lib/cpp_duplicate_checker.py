# -*- coding: utf-8 -*-
"""
基于C++哈希库的图片查重器

使用C++实现的哈希算法来提高性能
"""

import os
import time
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Set, Optional

from .hash_wrapper import (
    calculate_file_hash, 
    calculate_dhash, 
    calculate_phash, 
    calculate_ahash,
    hamming_distance,
    is_pure_color_image
)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.result_logger import ResultLogger


class CppDuplicateChecker:
    """
    基于C++哈希库的图片查重器
    """
    
    def __init__(self, 
                 phash_threshold: int = 2,
                 dhash_threshold: int = 8,
                 ahash_threshold: int = 2,
                 output_dir: str = "results",
                 detect_pure_color: bool = True,
                 detect_rotation: bool = False,
                 enhanced_similarity: bool = False,
                 confidence_threshold: float = 0.6):
        """
        初始化图片查重器
        
        Args:
            phash_threshold: pHash感知哈希相似度阈值，默认为2
            dhash_threshold: dHash感知哈希相似度阈值，默认为8
            ahash_threshold: aHash感知哈希相似度阈值，默认为2
            output_dir: 结果输出目录，默认为"results"
            detect_pure_color: 是否检测并标记纯色图片，默认为True
            detect_rotation: 是否启用旋转识别功能，默认为False
            enhanced_similarity: 是否启用增强相似度检测（支持旋转+分辨率变化），默认为False
            confidence_threshold: 增强检测的置信度阈值，默认为0.6
        """
        self.phash_threshold = phash_threshold
        self.dhash_threshold = dhash_threshold
        self.ahash_threshold = ahash_threshold
        self.detect_pure_color = detect_pure_color
        self.detect_rotation = detect_rotation
        self.enhanced_similarity = enhanced_similarity
        self.confidence_threshold = confidence_threshold
        self.logger = ResultLogger(output_dir)
        
        # 日志回调函数
        self.log_callback = None
        
        # 停止标志
        self.should_stop = False
        
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
    
    def stop(self):
        """
        停止扫描
        """
        self.should_stop = True
        self.log("收到停止信号，正在停止扫描...")
    
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
                        # 标准化路径分隔符，确保C++库能正确处理
                        file_path = os.path.join(root, file)
                        # 在Windows上统一使用反斜杠，避免混合分隔符问题
                        normalized_path = os.path.normpath(file_path)
                        image_files.append(normalized_path)
        else:
            for file in os.listdir(directory):
                if os.path.isfile(os.path.join(directory, file)) and \
                   os.path.splitext(file)[1].lower() in image_extensions:
                    # 标准化路径分隔符，确保C++库能正确处理
                    file_path = os.path.join(directory, file)
                    normalized_path = os.path.normpath(file_path)
                    image_files.append(normalized_path)
        
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
        error_count = 0
        max_errors = min(10, len(image_files) // 10)  # 最多允许10%的错误
        
        self.log(f"正在使用C++库计算 {len(image_files)} 个文件的哈希值...")
        for i, file_path in enumerate(image_files):
            if self.should_stop:
                self.log("扫描已停止")
                break
                
            if i % 50 == 0 and i > 0:  # 更频繁的进度更新
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                file_hash = calculate_file_hash(file_path)
                if file_hash:  # 确保哈希值有效
                    file_hash_map[file_hash].append(file_path)
                    error_count = 0  # 重置错误计数
                else:
                    self.log(f"文件哈希计算返回空值: {file_path}")
                    error_count += 1
            except Exception as e:
                error_count += 1
                self.log(f"处理文件时出错: {file_path}, 错误: {str(e)}")
                
                # 如果错误太多，抛出异常
                if error_count > max_errors:
                    raise Exception(f"C++库连续出错过多({error_count}次)，可能存在问题: {str(e)}")
        
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
            
        self.log("正在使用C++库检测纯色图片...")
        pure_color_images = []
        error_count = 0
        max_errors = min(10, len(image_files) // 10)  # 最多允许10%的错误
        
        for i, file_path in enumerate(image_files):
            if self.should_stop:
                self.log("扫描已停止")
                break
                
            if i % 50 == 0 and i > 0:  # 更频繁的进度更新
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                if is_pure_color_image(file_path):
                    pure_color_images.append(file_path)
                    self.stats['pure_color_images'] += 1
                error_count = 0  # 重置错误计数
            except Exception as e:
                error_count += 1
                self.log(f"检测纯色图片时出错: {file_path}, 错误: {str(e)}")
                
                # 如果错误太多，抛出异常
                if error_count > max_errors:
                    raise Exception(f"C++库连续出错过多({error_count}次)，可能存在问题: {str(e)}")
        
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
        # 计算所有图片的感知哈希
        self.log(f"正在使用C++库计算 {len(image_files)} 个文件的感知哈希...")
        
        # 存储每个文件的dhash和phash
        file_hashes = []
        error_count = 0
        max_errors = min(10, len(image_files) // 10)  # 最多允许10%的错误
        
        for i, file_path in enumerate(image_files):
            if self.should_stop:
                self.log("扫描已停止")
                break
                
            if i % 50 == 0 and i > 0:  # 更频繁的进度更新
                self.log(f"已处理 {i}/{len(image_files)} 个文件...")
            
            try:
                dhash = calculate_dhash(file_path)
                phash = calculate_phash(file_path)
                ahash = calculate_ahash(file_path)
                
                # 验证哈希值有效性
                if dhash and phash and ahash:
                    file_hashes.append({
                        'path': file_path,
                        'dhash': dhash,
                        'phash': phash,
                        'ahash': ahash
                    })
                    error_count = 0  # 重置错误计数
                else:
                    self.log(f"感知哈希计算返回空值: {file_path}")
                    error_count += 1
            except Exception as e:
                error_count += 1
                self.log(f"计算感知哈希时出错: {file_path}, 错误: {str(e)}")
                
                # 如果错误太多，抛出异常
                if error_count > max_errors:
                    raise Exception(f"C++库连续出错过多({error_count}次)，可能存在问题: {str(e)}")
        
        # 查找相似图片组
        similar_groups = []
        processed = set()  # 已处理的文件
        
        # 如果启用增强相似度检测，使用增强检测器
        if self.enhanced_similarity:
            self.log("正在使用增强相似度检测（支持旋转+分辨率变化）...")
            try:
                from src.enhanced_similarity_detector import batch_compare_with_enhanced_similarity
                
                # 使用增强相似度检测进行批量比较
                image_paths = [item['path'] for item in file_hashes]
                enhanced_groups = batch_compare_with_enhanced_similarity(
                    image_paths,
                    dhash_threshold=self.dhash_threshold + 4,  # 放宽阈值以适应分辨率变化
                    phash_threshold=self.phash_threshold + 2,
                    ahash_threshold=self.ahash_threshold + 2,
                    confidence_threshold=self.confidence_threshold,
                    log_callback=self.log
                )
                
                # 转换格式以保持兼容性
                for group in enhanced_groups:
                    similar_group = {
                        'reason': group['reason'],
                        'files': group['files'],
                        'files_with_distances': [],
                        'detection_info': group.get('detection_info', []),
                        'avg_confidence': group.get('avg_confidence', 0.0)
                    }
                    similar_groups.append(similar_group)
                    
                    # 标记为已处理
                    for file_path in group['files']:
                        processed.add(file_path)
                        
            except ImportError as e:
                self.log(f"增强相似度检测模块导入失败，回退到旋转检测: {str(e)}")
                # 回退到旋转检测
                self.enhanced_similarity = False
            except Exception as e:
                self.log(f"增强相似度检测出错，回退到旋转检测: {str(e)}")
                # 回退到旋转检测
                self.enhanced_similarity = False
        
        # 如果启用旋转检测但未启用增强检测，使用旋转不变哈希
        if self.detect_rotation and not self.enhanced_similarity:
            self.log("正在使用旋转不变哈希查找相似图片组...")
            try:
                from src.rotation_invariant_hash import batch_compare_with_rotation
                
                # 使用旋转不变哈希进行批量比较
                image_paths = [item['path'] for item in file_hashes]
                rotation_groups = batch_compare_with_rotation(
                    image_paths,
                    dhash_threshold=self.dhash_threshold,
                    phash_threshold=self.phash_threshold,
                    ahash_threshold=self.ahash_threshold,
                    log_callback=self.log
                )
                
                # 转换格式以保持兼容性
                for group in rotation_groups:
                    similar_group = {
                        'reason': group['reason'] + '(旋转检测)',
                        'files': group['files'],
                        'files_with_distances': group.get('files_with_distances', [])
                    }
                    similar_groups.append(similar_group)
                    
                    # 标记为已处理
                    for file_path in group['files']:
                        processed.add(file_path)
                        
            except ImportError as e:
                self.log(f"旋转检测模块导入失败，回退到标准检测: {str(e)}")
                # 回退到标准检测
                self.detect_rotation = False
            except Exception as e:
                self.log(f"旋转检测出错，回退到标准检测: {str(e)}")
                # 回退到标准检测
                self.detect_rotation = False
        
        # 如果没有启用旋转检测或旋转检测失败，使用标准方法
        if not self.detect_rotation:
            self.log("正在查找相似图片组...")
            for i, file1 in enumerate(file_hashes):
                if self.should_stop:
                    self.log("扫描已停止")
                    break
                    
                if file1['path'] in processed:
                    continue
                
                if i % 50 == 0 and i > 0:  # 更频繁的进度更新
                    self.log(f"已处理 {i}/{len(file_hashes)} 个文件...")
                
                similar_files = []
                reason = ""
                
                for j, file2 in enumerate(file_hashes):
                    # 更频繁的停止检查
                    if j % 100 == 0 and self.should_stop:
                        self.log("扫描已停止")
                        break
                        
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
                        reason = "+".join(reasons) + "相似(C++)"  # 标记为C++实现
                
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
        self.log("\n步骤1: 使用C++库检查完全相同的重复图片")
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
        self.log(f"\n步骤2: 使用C++库检测纯色图片 (共 {len(unique_images)} 个唯一文件)")
        pure_color_images = self.check_pure_color_images(unique_images)
        
        # 从图片列表中移除纯色图片
        if pure_color_images:
            unique_images = [img for img in unique_images if img not in set(pure_color_images)]
        
        # 步骤3: 检查感知上相似的图片
        self.log(f"\n步骤3: 使用C++库检查感知上相似的图片 (共 {len(unique_images)} 个唯一文件)")
        similar_groups = self.check_perceptual_duplicates(unique_images)
        
        # 生成结果
        all_duplicate_groups = []
        
        # 添加完全相同的重复组
        for file_hash, files in exact_duplicates.items():
            all_duplicate_groups.append({
                'reason': '完全相同(C++)',
                'files': files
            })
        
        # 添加纯色图片组（如果有）
        if self.pure_color_images:
            all_duplicate_groups.append({
                'reason': '纯色图片(C++)',
                'files': self.pure_color_images
            })
            self.stats['reasons']['纯色图片(C++)'] = 1
            if not self.stats['duplicate_groups']:
                self.stats['duplicate_groups'] = 1
        
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
        
        # 计算总耗时
        total_time = time.time() - start_time
        self.log(f"\n查重完成！总耗时: {total_time:.2f} 秒")
        self.log(f"使用C++库处理了 {self.stats['total_images']} 个图片文件")
        self.log(f"发现 {self.stats['duplicate_groups']} 个重复组，包含 {self.stats['duplicate_images']} 个重复图片")
        
        return self.stats