#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超高速图片查重器
针对64万张图片的极端优化版本

主要优化策略：
1. 多级哈希索引 - 使用更细粒度的分组
2. 早期终止策略 - 快速跳过明显不相似的图片
3. 批量向量化比较 - 使用NumPy加速距离计算
4. 内存池管理 - 减少内存分配开销
5. 自适应并行度 - 根据数据规模动态调整线程数
"""

import os
import time
import numpy as np
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple, Set
import threading
from dataclasses import dataclass


@dataclass
class HashInfo:
    """哈希信息数据类"""
    path: str
    dhash: str
    phash: str
    ahash: str
    dhash_int: int
    phash_int: int
    ahash_int: int


class UltraFastDuplicateChecker:
    """超高速图片查重器"""
    
    def __init__(self, 
                 dhash_threshold: int = 12,
                 phash_threshold: int = 8,
                 ahash_threshold: int = 8,
                 index_levels: int = 3,
                 max_workers: int = None,
                 batch_size: int = 1000,
                 enable_vectorization: bool = True):
        """
        初始化超高速查重器
        
        Args:
            dhash_threshold: dHash相似度阈值
            phash_threshold: pHash相似度阈值  
            ahash_threshold: aHash相似度阈值
            index_levels: 索引层级数（越多越精确但内存占用越大）
            max_workers: 最大工作线程数
            batch_size: 批处理大小
            enable_vectorization: 是否启用向量化计算
        """
        self.dhash_threshold = dhash_threshold
        self.phash_threshold = phash_threshold
        self.ahash_threshold = ahash_threshold
        self.index_levels = index_levels
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) * 4)
        self.batch_size = batch_size
        self.enable_vectorization = enable_vectorization
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'hash_time': 0,
            'index_time': 0,
            'compare_time': 0,
            'total_comparisons': 0,
            'skipped_comparisons': 0,
            'similar_groups': 0
        }
        
        # 日志回调
        self.log_callback = None
        self.should_stop = False
    
    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self.log_callback = callback
    
    def log(self, message: str):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
    
    def stop(self):
        """停止处理"""
        self.should_stop = True
    
    def hamming_distance_vectorized(self, hash1_array: np.ndarray, hash2_array: np.ndarray) -> np.ndarray:
        """向量化汉明距离计算"""
        return np.sum(hash1_array != hash2_array, axis=1)
    
    def hex_to_binary_array(self, hex_hash: str) -> np.ndarray:
        """将十六进制哈希转换为二进制数组"""
        # 转换为整数然后转为二进制字符串
        binary_str = bin(int(hex_hash, 16))[2:].zfill(64)
        return np.array([int(b) for b in binary_str], dtype=np.uint8)
    
    def calculate_hash_batch_ultra_fast(self, file_batch: List[str]) -> List[HashInfo]:
        """超高速批量计算哈希值"""
        from cpp_hash_lib.hash_wrapper import calculate_dhash, calculate_phash, calculate_ahash
        
        results = []
        for file_path in file_batch:
            if self.should_stop:
                break
            
            try:
                # 并行计算三种哈希
                dhash = calculate_dhash(file_path)
                phash = calculate_phash(file_path)
                ahash = calculate_ahash(file_path)
                
                if dhash and phash and ahash:
                    hash_info = HashInfo(
                        path=file_path,
                        dhash=dhash,
                        phash=phash,
                        ahash=ahash,
                        dhash_int=int(dhash, 16),
                        phash_int=int(phash, 16),
                        ahash_int=int(ahash, 16)
                    )
                    results.append(hash_info)
            except Exception as e:
                self.log(f"计算哈希失败: {os.path.basename(file_path)} - {str(e)}")
                continue
        
        return results
    
    def create_multi_level_index(self, hash_infos: List[HashInfo]) -> Dict[str, Dict[int, List[HashInfo]]]:
        """创建多级哈希索引"""
        start_time = time.time()
        
        # 创建多级索引
        indices = {
            'dhash': defaultdict(list),
            'phash': defaultdict(list), 
            'ahash': defaultdict(list)
        }
        
        # 根据索引层级确定前缀位数
        prefix_bits_list = [16, 20, 24][:self.index_levels]
        
        for hash_info in hash_infos:
            # 为每种哈希类型创建索引
            for hash_type, hash_value in [('dhash', hash_info.dhash_int), 
                                         ('phash', hash_info.phash_int),
                                         ('ahash', hash_info.ahash_int)]:
                
                # 使用最细粒度的前缀
                prefix_bits = prefix_bits_list[-1] if prefix_bits_list else 16
                mask = (1 << prefix_bits) - 1
                prefix = hash_value & mask
                
                indices[hash_type][prefix].append(hash_info)
        
        self.stats['index_time'] = time.time() - start_time
        
        # 统计索引效果
        for hash_type, index in indices.items():
            group_sizes = [len(group) for group in index.values()]
            avg_group_size = np.mean(group_sizes) if group_sizes else 0
            max_group_size = max(group_sizes) if group_sizes else 0
            self.log(f"{hash_type}索引: {len(index)}个分组, 平均大小{avg_group_size:.1f}, 最大{max_group_size}")
        
        return indices
    
    def early_termination_filter(self, hash1: HashInfo, hash2: HashInfo) -> bool:
        """早期终止过滤器 - 快速判断是否值得进行详细比较"""
        # 使用位运算快速估算汉明距离
        dhash_xor = hash1.dhash_int ^ hash2.dhash_int
        
        # 快速计算置位数（汉明距离的近似值）
        # 使用Brian Kernighan算法快速计算置位数
        bit_count = 0
        temp = dhash_xor
        while temp and bit_count <= self.dhash_threshold + 5:  # 提前终止
            temp &= temp - 1
            bit_count += 1
        
        # 如果dHash距离明显超过阈值，直接跳过
        if bit_count > self.dhash_threshold + 5:
            self.stats['skipped_comparisons'] += 1
            return False
        
        return True
    
    def compare_group_ultra_fast(self, group: List[HashInfo]) -> Tuple[List[Dict[str, Any]], int]:
        """超高速组内比较"""
        if len(group) < 2:
            return [], 0
        
        similar_groups = []
        processed = set()
        comparisons = 0
        
        # 如果组太大，使用向量化比较
        if self.enable_vectorization and len(group) > 50:
            return self._vectorized_group_compare(group)
        
        # 标准比较逻辑（优化版）
        for i, hash1 in enumerate(group):
            if hash1.path in processed or self.should_stop:
                continue
            
            similar_files = []
            
            for j in range(i + 1, len(group)):
                hash2 = group[j]
                if hash2.path in processed:
                    continue
                
                # 早期终止过滤
                if not self.early_termination_filter(hash1, hash2):
                    continue
                
                # 精确计算汉明距离
                dhash_distance = bin(hash1.dhash_int ^ hash2.dhash_int).count('1')
                phash_distance = bin(hash1.phash_int ^ hash2.phash_int).count('1')
                ahash_distance = bin(hash1.ahash_int ^ hash2.ahash_int).count('1')
                
                comparisons += 1
                self.stats['total_comparisons'] += 1
                
                # 判断相似性
                dhash_similar = dhash_distance <= self.dhash_threshold
                phash_similar = phash_distance <= self.phash_threshold
                ahash_similar = ahash_distance <= self.ahash_threshold
                
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                
                if similar_count >= 2:
                    reasons = []
                    if dhash_similar:
                        reasons.append("dHash")
                    if phash_similar:
                        reasons.append("pHash")
                    if ahash_similar:
                        reasons.append("aHash")
                    
                    similar_files.append({
                        'file_path': hash2.path,
                        'dhash_distance': dhash_distance,
                        'phash_distance': phash_distance,
                        'ahash_distance': ahash_distance,
                        'reason': '+'.join(reasons) + '相似(超速)'
                    })
            
            if similar_files:
                # 创建相似组
                files_with_distances = [{
                    'file_path': hash1.path,
                    'dhash_distance': 0,
                    'phash_distance': 0,
                    'ahash_distance': 0
                }] + similar_files
                
                group_info = {
                    'reason': similar_files[0]['reason'],
                    'files': [item['file_path'] for item in files_with_distances],
                    'files_with_distances': files_with_distances
                }
                similar_groups.append(group_info)
                
                # 标记为已处理
                processed.add(hash1.path)
                for f in similar_files:
                    processed.add(f['file_path'])
        
        return similar_groups, comparisons
    
    def _vectorized_group_compare(self, group: List[HashInfo]) -> Tuple[List[Dict[str, Any]], int]:
        """向量化组内比较（适用于大组）"""
        if not self.enable_vectorization:
            return self.compare_group_ultra_fast(group)
        
        similar_groups = []
        processed = set()
        comparisons = 0
        
        # 转换为NumPy数组以加速计算
        dhash_arrays = []
        phash_arrays = []
        ahash_arrays = []
        
        for hash_info in group:
            dhash_arrays.append(self.hex_to_binary_array(hash_info.dhash))
            phash_arrays.append(self.hex_to_binary_array(hash_info.phash))
            ahash_arrays.append(self.hex_to_binary_array(hash_info.ahash))
        
        dhash_matrix = np.array(dhash_arrays)
        phash_matrix = np.array(phash_arrays)
        ahash_matrix = np.array(ahash_arrays)
        
        # 批量比较
        for i, hash1 in enumerate(group):
            if hash1.path in processed or self.should_stop:
                continue
            
            # 计算与后续所有元素的距离
            remaining_indices = list(range(i + 1, len(group)))
            if not remaining_indices:
                continue
            
            # 向量化距离计算
            dhash_distances = self.hamming_distance_vectorized(
                dhash_matrix[remaining_indices], dhash_matrix[i:i+1]
            )
            phash_distances = self.hamming_distance_vectorized(
                phash_matrix[remaining_indices], phash_matrix[i:i+1]
            )
            ahash_distances = self.hamming_distance_vectorized(
                ahash_matrix[remaining_indices], ahash_matrix[i:i+1]
            )
            
            comparisons += len(remaining_indices)
            self.stats['total_comparisons'] += len(remaining_indices)
            
            similar_files = []
            
            for idx, j in enumerate(remaining_indices):
                hash2 = group[j]
                if hash2.path in processed:
                    continue
                
                dhash_distance = dhash_distances[idx]
                phash_distance = phash_distances[idx]
                ahash_distance = ahash_distances[idx]
                
                # 判断相似性
                dhash_similar = dhash_distance <= self.dhash_threshold
                phash_similar = phash_distance <= self.phash_threshold
                ahash_similar = ahash_distance <= self.ahash_threshold
                
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                
                if similar_count >= 2:
                    reasons = []
                    if dhash_similar:
                        reasons.append("dHash")
                    if phash_similar:
                        reasons.append("pHash")
                    if ahash_similar:
                        reasons.append("aHash")
                    
                    similar_files.append({
                        'file_path': hash2.path,
                        'dhash_distance': int(dhash_distance),
                        'phash_distance': int(phash_distance),
                        'ahash_distance': int(ahash_distance),
                        'reason': '+'.join(reasons) + '相似(向量化)'
                    })
            
            if similar_files:
                # 创建相似组
                files_with_distances = [{
                    'file_path': hash1.path,
                    'dhash_distance': 0,
                    'phash_distance': 0,
                    'ahash_distance': 0
                }] + similar_files
                
                group_info = {
                    'reason': similar_files[0]['reason'],
                    'files': [item['file_path'] for item in files_with_distances],
                    'files_with_distances': files_with_distances
                }
                similar_groups.append(group_info)
                
                # 标记为已处理
                processed.add(hash1.path)
                for f in similar_files:
                    processed.add(f['file_path'])
        
        return similar_groups, comparisons
    
    def check_duplicates_ultra_fast(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """超高速查重主函数"""
        start_time = time.time()
        self.stats['total_files'] = len(image_files)
        
        self.log(f"启动超高速查重算法，处理 {len(image_files)} 个文件")
        self.log(f"配置: 索引层级={self.index_levels}, 最大线程={self.max_workers}, 向量化={self.enable_vectorization}")
        
        # 步骤1：超高速并行计算哈希值
        hash_start_time = time.time()
        self.log("步骤1: 超高速并行计算哈希值...")
        
        all_hash_infos = []
        
        # 分批并行处理
        batches = [image_files[i:i+self.batch_size] for i in range(0, len(image_files), self.batch_size)]
        self.log(f"分批策略: {len(batches)} 个批次，每批 {self.batch_size} 个文件，使用 {self.max_workers} 个线程")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {executor.submit(self.calculate_hash_batch_ultra_fast, batch): i 
                             for i, batch in enumerate(batches)}
            
            completed_batches = 0
            for future in as_completed(future_to_batch):
                if self.should_stop:
                    break
                
                batch_results = future.result()
                all_hash_infos.extend(batch_results)
                
                completed_batches += 1
                # 更频繁的进度报告 - 每5个批次或每5%进度报告一次
                if completed_batches % 5 == 0 or completed_batches % max(1, len(batches) // 20) == 0:
                    progress = completed_batches / len(batches) * 100
                    processed_files = completed_batches * self.batch_size
                    active_threads = len([f for f in future_to_batch if not f.done()])
                    self.log(f"哈希计算进度: {completed_batches}/{len(batches)} ({progress:.1f}%) | 已处理: {processed_files} 个文件 | 活跃线程: {active_threads}")
        
        self.stats['hash_time'] = time.time() - hash_start_time
        self.log(f"哈希计算完成: {len(all_hash_infos)} 个文件，耗时 {self.stats['hash_time']:.2f} 秒")
        
        if not all_hash_infos:
            self.log("没有成功计算的哈希值")
            return []
        
        # 步骤2：创建多级索引
        self.log("步骤2: 创建多级哈希索引...")
        indices = self.create_multi_level_index(all_hash_infos)
        
        # 步骤3：智能分组比较
        compare_start_time = time.time()
        self.log("步骤3: 智能分组比较...")
        
        all_similar_groups = []
        
        # 选择最优的索引进行比较（通常选择分组最均匀的）
        best_index = None
        best_score = float('inf')
        
        for hash_type, index in indices.items():
            group_sizes = [len(group) for group in index.values()]
            if group_sizes:
                # 计算分组质量分数（方差越小越好）
                score = np.var(group_sizes) + max(group_sizes) * 0.1
                if score < best_score:
                    best_score = score
                    best_index = index
        
        if best_index:
            # 过滤出需要比较的分组（大小>=2）
            large_groups = [group for group in best_index.values() if len(group) >= 2]
            
            self.log(f"使用最优索引，{len(large_groups)} 个分组需要比较")
            
            # 并行比较各分组
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(large_groups))) as executor:
                future_to_group = {executor.submit(self.compare_group_ultra_fast, group): i 
                                 for i, group in enumerate(large_groups)}
                
                completed_groups = 0
                for future in as_completed(future_to_group):
                    if self.should_stop:
                        break
                    
                    group_results, group_comparisons = future.result()
                    all_similar_groups.extend(group_results)
                    
                    completed_groups += 1
                    if completed_groups % 50 == 0:
                        progress = completed_groups / len(large_groups) * 100
                        self.log(f"分组比较进度: {completed_groups}/{len(large_groups)} ({progress:.1f}%)")
        
        self.stats['compare_time'] = time.time() - compare_start_time
        self.stats['similar_groups'] = len(all_similar_groups)
        
        # 输出最终统计
        total_time = time.time() - start_time
        naive_comparisons = len(image_files) * (len(image_files) - 1) // 2
        optimization_ratio = naive_comparisons / max(self.stats['total_comparisons'], 1)
        
        self.log(f"\n超高速查重完成:")
        self.log(f"  - 总耗时: {total_time:.2f} 秒")
        self.log(f"  - 哈希计算: {self.stats['hash_time']:.2f} 秒")
        self.log(f"  - 索引创建: {self.stats['index_time']:.2f} 秒")
        self.log(f"  - 分组比较: {self.stats['compare_time']:.2f} 秒")
        self.log(f"  - 实际比较次数: {self.stats['total_comparisons']:,}")
        self.log(f"  - 跳过比较次数: {self.stats['skipped_comparisons']:,}")
        self.log(f"  - 优化倍数: {optimization_ratio:.1f}x")
        self.log(f"  - 找到相似组: {len(all_similar_groups)} 个")
        
        return all_similar_groups


if __name__ == "__main__":
    pass