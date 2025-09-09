#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSH (Locality Sensitive Hashing) 索引实现
用于加速图片查重的分组比较阶段

作者: AI Assistant
日期: 2024
"""

import numpy as np
import hashlib
import random
from typing import List, Dict, Set, Tuple, Any, Optional
from collections import defaultdict
import time
import json
import os

class LSHIndex:
    """
    局部敏感哈希索引，用于快速相似图片检索
    
    LSH的核心思想：
    - 相似的输入有更高概率被映射到相同的桶中
    - 通过多个哈希函数和多个哈希表提高召回率
    - 大幅减少需要精确比较的候选对数量
    """
    
    def __init__(self, 
                 num_hash_tables: int = 6,  # 减少哈希表数量以节省内存
                 num_hash_functions: int = 3,  # 减少哈希函数数量
                 hash_length: int = 64,
                 similarity_threshold: float = 0.85):
        """
        初始化LSH索引
        
        Args:
            num_hash_tables: 哈希表数量，越多召回率越高但速度越慢
            num_hash_functions: 每个哈希表的哈希函数数量
            hash_length: 输入哈希的位长度（dhash/phash/ahash通常是64位）
            similarity_threshold: 相似度阈值，用于确定LSH参数
        """
        self.num_hash_tables = num_hash_tables
        self.num_hash_functions = num_hash_functions
        self.hash_length = hash_length
        self.similarity_threshold = similarity_threshold
        
        # LSH哈希表：每个表是一个字典，键是LSH签名，值是文件列表
        self.hash_tables: List[Dict[str, List[Dict[str, Any]]]] = [
            defaultdict(list) for _ in range(num_hash_tables)
        ]
        
        # 随机投影矩阵：用于生成LSH哈希函数
        self.projection_matrices = self._generate_projection_matrices()
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'total_buckets': 0,
            'avg_bucket_size': 0,
            'max_bucket_size': 0,
            'index_time': 0,
            'query_time': 0,
            'candidate_reduction_ratio': 0,
            'memory_usage_mb': 0
        }
        
        # 内存管理
        self.max_bucket_size_limit = 5000  # 限制单个桶的最大大小
        self.enable_memory_optimization = True
        
    def _generate_projection_matrices(self) -> List[np.ndarray]:
        """
        生成随机投影矩阵用于LSH哈希函数
        
        Returns:
            投影矩阵列表，每个矩阵对应一个哈希表
        """
        matrices = []
        random.seed(42)  # 固定种子确保可重现性
        
        for i in range(self.num_hash_tables):
            # 每个哈希表有num_hash_functions个哈希函数
            # 每个哈希函数是一个长度为hash_length的随机向量
            matrix = np.random.randn(self.num_hash_functions, self.hash_length)
            matrices.append(matrix)
            
        return matrices
    
    def _hash_to_binary_vector(self, hash_hex: str) -> np.ndarray:
        """
        将十六进制哈希转换为二进制向量
        
        Args:
            hash_hex: 十六进制哈希字符串
            
        Returns:
            二进制向量 (numpy数组)
        """
        # 转换为整数然后转为二进制
        hash_int = int(hash_hex, 16)
        binary_str = format(hash_int, f'0{self.hash_length}b')
        
        # 转换为numpy数组，0->-1, 1->1 (便于计算)
        binary_vector = np.array([1 if bit == '1' else -1 for bit in binary_str], dtype=np.float32)
        return binary_vector
    
    def _compute_lsh_signature(self, binary_vector: np.ndarray, table_idx: int) -> str:
        """
        计算LSH签名
        
        Args:
            binary_vector: 输入的二进制向量
            table_idx: 哈希表索引
            
        Returns:
            LSH签名字符串
        """
        # 使用对应的投影矩阵
        projection_matrix = self.projection_matrices[table_idx]
        
        # 计算投影：matrix @ vector
        projections = projection_matrix @ binary_vector
        
        # 生成二进制签名：>0为1，<=0为0
        signature_bits = ['1' if p > 0 else '0' for p in projections]
        signature = ''.join(signature_bits)
        
        return signature
    
    def add_file(self, file_info: Dict[str, Any]) -> None:
        """
        将文件添加到LSH索引
        
        Args:
            file_info: 包含文件路径和哈希值的字典
                      必须包含: 'file_path', 'dhash', 'phash', 'ahash'
        """
        # 为每种哈希类型计算LSH签名
        for hash_type in ['dhash', 'phash', 'ahash']:
            if hash_type not in file_info:
                continue
                
            hash_hex = file_info[hash_type]
            binary_vector = self._hash_to_binary_vector(hash_hex)
            
            # 在每个哈希表中添加文件
            for table_idx in range(self.num_hash_tables):
                lsh_signature = self._compute_lsh_signature(binary_vector, table_idx)
                
                # 创建桶键：结合哈希类型和LSH签名
                bucket_key = f"{hash_type}_{lsh_signature}"
                
                # 添加到对应的桶中（带内存优化）
                bucket = self.hash_tables[table_idx][bucket_key]
                
                # 限制桶大小以防止内存爆炸
                if self.enable_memory_optimization and len(bucket) >= self.max_bucket_size_limit:
                    # 如果桶太大，随机移除一些旧条目
                    import random
                    bucket = bucket[:self.max_bucket_size_limit//2]  # 保留一半
                    self.hash_tables[table_idx][bucket_key] = bucket
                
                bucket.append(file_info)
    
    def build_index(self, file_hashes: List[Dict[str, Any]]) -> None:
        """
        批量构建LSH索引
        
        Args:
            file_hashes: 文件哈希列表
        """
        start_time = time.time()
        
        self.log(f"开始构建LSH索引，文件数量: {len(file_hashes)}")
        
        for i, file_info in enumerate(file_hashes):
            self.add_file(file_info)
            
            # 进度显示
            if (i + 1) % 1000 == 0:
                progress = (i + 1) / len(file_hashes) * 100
                self.log(f"LSH索引构建进度: {progress:.1f}% ({i + 1}/{len(file_hashes)})")
        
        # 更新统计信息
        self.stats['total_files'] = len(file_hashes)
        self.stats['index_time'] = time.time() - start_time
        self._update_bucket_stats()
        self._update_memory_stats()
        
        self.log(f"LSH索引构建完成，耗时: {self.stats['index_time']:.2f}秒")
        self.log(f"平均桶大小: {self.stats['avg_bucket_size']:.1f}，最大桶大小: {self.stats['max_bucket_size']}")
        self.log(f"索引内存使用: {self.stats['memory_usage_mb']:.1f} MB")
    
    def _update_bucket_stats(self) -> None:
        """
        更新桶统计信息
        """
        all_bucket_sizes = []
        total_buckets = 0
        
        for table in self.hash_tables:
            for bucket_key, files in table.items():
                if files:  # 非空桶
                    all_bucket_sizes.append(len(files))
                    total_buckets += 1
        
        if all_bucket_sizes:
            self.stats['total_buckets'] = total_buckets
            self.stats['avg_bucket_size'] = sum(all_bucket_sizes) / len(all_bucket_sizes)
            self.stats['max_bucket_size'] = max(all_bucket_sizes)
        else:
            self.stats['total_buckets'] = 0
            self.stats['avg_bucket_size'] = 0
            self.stats['max_bucket_size'] = 0
            
    def _update_memory_stats(self) -> None:
        """更新内存使用统计"""
        try:
            import sys
            total_size = 0
            
            # 计算哈希表占用的内存
            for table in self.hash_tables:
                total_size += sys.getsizeof(table)
                for bucket_key, files in table.items():
                    total_size += sys.getsizeof(bucket_key)
                    total_size += sys.getsizeof(files)
                    for file_info in files:
                        total_size += sys.getsizeof(file_info)
            
            # 计算投影矩阵占用的内存
            for matrix in self.projection_matrices:
                total_size += matrix.nbytes
            
            self.stats['memory_usage_mb'] = total_size / (1024 * 1024)
        except Exception:
            self.stats['memory_usage_mb'] = 0
        
    def query_candidates(self, file_info: Dict[str, Any]) -> Set[str]:
        """
        查询候选相似文件
        
        Args:
            file_info: 查询文件的信息
            
        Returns:
            候选文件路径集合
        """
        start_time = time.time()
        candidates = set()
        
        # 为每种哈希类型查询候选
        for hash_type in ['dhash', 'phash', 'ahash']:
            if hash_type not in file_info:
                continue
                
            hash_hex = file_info[hash_type]
            binary_vector = self._hash_to_binary_vector(hash_hex)
            
            # 在每个哈希表中查询
            for table_idx in range(self.num_hash_tables):
                lsh_signature = self._compute_lsh_signature(binary_vector, table_idx)
                bucket_key = f"{hash_type}_{lsh_signature}"
                
                # 获取桶中的候选文件
                bucket_files = self.hash_tables[table_idx].get(bucket_key, [])
                for candidate_file in bucket_files:
                    # 排除自己
                    if candidate_file['file_path'] != file_info['file_path']:
                        candidates.add(candidate_file['file_path'])
        
        self.stats['query_time'] += time.time() - start_time
        return candidates
    
    def get_all_candidate_pairs(self, file_hashes: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
        """
        获取所有候选相似文件对（优化版本）
        
        Args:
            file_hashes: 文件哈希列表
            
        Returns:
            候选文件对集合
        """
        self.log("开始生成候选文件对...")
        start_time = time.time()
        
        candidate_pairs = set()
        
        # 创建文件路径到索引的映射，用于快速查找
        path_to_index = {file_info['file_path']: i for i, file_info in enumerate(file_hashes)}
        
        # 优化：直接遍历所有桶，避免重复查询
        processed_pairs = set()
        
        for table_idx in range(self.num_hash_tables):
            for bucket_key, bucket_files in self.hash_tables[table_idx].items():
                if len(bucket_files) < 2:
                    continue  # 桶中文件少于2个，无法形成对
                
                # 在同一个桶中的文件两两配对
                for i in range(len(bucket_files)):
                    for j in range(i + 1, len(bucket_files)):
                        file1_path = bucket_files[i]['file_path']
                        file2_path = bucket_files[j]['file_path']
                        
                        # 确保文件对的顺序一致（避免重复）
                        if file1_path < file2_path:
                            pair = (file1_path, file2_path)
                        else:
                            pair = (file2_path, file1_path)
                        
                        # 避免重复添加相同的文件对
                        if pair not in processed_pairs:
                            candidate_pairs.add(pair)
                            processed_pairs.add(pair)
            
            # 进度显示（按哈希表进度）
            if (table_idx + 1) % 5 == 0 or table_idx == self.num_hash_tables - 1:
                progress = (table_idx + 1) / self.num_hash_tables * 100
                self.log(f"候选对生成进度: {progress:.1f}% (表 {table_idx + 1}/{self.num_hash_tables})")
        
        # 计算候选减少比例
        total_possible_pairs = len(file_hashes) * (len(file_hashes) - 1) // 2
        reduction_ratio = total_possible_pairs / len(candidate_pairs) if candidate_pairs else 1
        self.stats['candidate_reduction_ratio'] = reduction_ratio
        
        elapsed_time = time.time() - start_time
        self.log(f"候选对生成完成，耗时: {elapsed_time:.2f}秒")
        self.log(f"候选对数量: {len(candidate_pairs):,}，减少比例: {reduction_ratio:.1f}x")
        
        return candidate_pairs
    
    def save_index(self, filepath: str) -> None:
        """
        保存LSH索引到文件
        
        Args:
            filepath: 保存路径
        """
        index_data = {
            'num_hash_tables': self.num_hash_tables,
            'num_hash_functions': self.num_hash_functions,
            'hash_length': self.hash_length,
            'similarity_threshold': self.similarity_threshold,
            'projection_matrices': [matrix.tolist() for matrix in self.projection_matrices],
            'hash_tables': [dict(table) for table in self.hash_tables],
            'stats': self.stats
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"LSH索引已保存到: {filepath}")
    
    def load_index(self, filepath: str) -> bool:
        """
        从文件加载LSH索引
        
        Args:
            filepath: 索引文件路径
            
        Returns:
            是否加载成功
        """
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            self.num_hash_tables = index_data['num_hash_tables']
            self.num_hash_functions = index_data['num_hash_functions']
            self.hash_length = index_data['hash_length']
            self.similarity_threshold = index_data['similarity_threshold']
            
            # 恢复投影矩阵
            self.projection_matrices = [np.array(matrix) for matrix in index_data['projection_matrices']]
            
            # 恢复哈希表
            self.hash_tables = [defaultdict(list) for _ in range(self.num_hash_tables)]
            for i, table_data in enumerate(index_data['hash_tables']):
                for bucket_key, files in table_data.items():
                    self.hash_tables[i][bucket_key] = files
            
            self.stats = index_data.get('stats', {})
            
            self.log(f"LSH索引已从 {filepath} 加载")
            return True
            
        except Exception as e:
            self.log(f"加载LSH索引失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            统计信息字典
        """
        return self.stats.copy()


class LSHOptimizedDuplicateChecker:
    """
    基于LSH索引的优化查重器
    """
    
    def __init__(self, 
                 lsh_num_tables: int = 10,
                 lsh_num_functions: int = 4,
                 similarity_threshold: float = 0.85,
                 log_callback=None):
        """
        初始化LSH优化查重器
        
        Args:
            lsh_num_tables: LSH哈希表数量
            lsh_num_functions: 每个表的哈希函数数量
            similarity_threshold: 相似度阈值
            log_callback: 日志回调函数
        """
        self.lsh_index = LSHIndex(
            num_hash_tables=lsh_num_tables,
            num_hash_functions=lsh_num_functions,
            similarity_threshold=similarity_threshold
        )
        self.similarity_threshold = similarity_threshold
        self.log_callback = log_callback
        
    def log(self, message: str):
        """
        输出日志信息
        
        Args:
            message: 日志消息
        """
        if self.log_callback:
            self.log_callback(message)
        
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算汉明距离
        
        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值
            
        Returns:
            汉明距离
        """
        return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')
    
    def is_similar(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> bool:
        """
        判断两个文件是否相似
        
        Args:
            file1: 第一个文件信息
            file2: 第二个文件信息
            
        Returns:
            是否相似
        """
        # 计算三种哈希的汉明距离
        dhash_dist = self.hamming_distance(file1['dhash'], file2['dhash'])
        phash_dist = self.hamming_distance(file1['phash'], file2['phash'])
        ahash_dist = self.hamming_distance(file1['ahash'], file2['ahash'])
        
        # 相似性判定：至少两种哈希相似
        threshold = int(64 * (1 - self.similarity_threshold))
        similar_count = sum([
            dhash_dist <= threshold,
            phash_dist <= threshold,
            ahash_dist <= threshold
        ])
        
        return similar_count >= 2
    
    def find_duplicates_with_lsh(self, file_hashes: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        使用LSH索引查找重复文件
        
        Args:
            file_hashes: 文件哈希列表
            
        Returns:
            相似文件组列表
        """
        self.log(f"开始使用LSH索引查找重复文件，文件数量: {len(file_hashes)}")
        
        # 构建LSH索引
        self.lsh_index.build_index(file_hashes)
        
        # 获取候选文件对
        candidate_pairs = self.lsh_index.get_all_candidate_pairs(file_hashes)
        
        # 创建文件路径到文件信息的映射
        file_map = {f['file_path']: f for f in file_hashes}
        
        # 精确比较候选对
        self.log("开始精确比较候选文件对...")
        start_time = time.time()
        
        similar_pairs = []
        for i, (path1, path2) in enumerate(candidate_pairs):
            file1 = file_map[path1]
            file2 = file_map[path2]
            
            if self.is_similar(file1, file2):
                similar_pairs.append((file1, file2))
            
            # 进度显示
            if (i + 1) % 10000 == 0:
                progress = (i + 1) / len(candidate_pairs) * 100
                self.log(f"精确比较进度: {progress:.1f}% ({i + 1}/{len(candidate_pairs)})")
        
        comparison_time = time.time() - start_time
        self.log(f"精确比较完成，耗时: {comparison_time:.2f}秒")
        self.log(f"找到相似文件对: {len(similar_pairs)} 个")
        
        # 将相似文件对组织成组
        similar_groups = self._group_similar_files(similar_pairs)
        
        # 输出统计信息
        lsh_stats = self.lsh_index.get_stats()
        total_possible_pairs = len(file_hashes) * (len(file_hashes) - 1) // 2
        
        self.log(f"\nLSH优化查重完成:")
        self.log(f"  - 总文件数: {len(file_hashes):,}")
        self.log(f"  - 理论比较次数: {total_possible_pairs:,}")
        self.log(f"  - 实际比较次数: {len(candidate_pairs):,}")
        self.log(f"  - 减少比例: {lsh_stats['candidate_reduction_ratio']:.1f}x")
        self.log(f"  - 索引构建时间: {lsh_stats['index_time']:.2f}秒")
        self.log(f"  - 精确比较时间: {comparison_time:.2f}秒")
        self.log(f"  - 找到相似组: {len(similar_groups)} 个")
        
        return similar_groups
    
    def _group_similar_files(self, similar_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
        """
        将相似文件对组织成组
        
        Args:
            similar_pairs: 相似文件对列表
            
        Returns:
            相似文件组列表
        """
        # 使用并查集算法组织相似文件
        file_groups = {}
        group_id = 0
        
        for file1, file2 in similar_pairs:
            path1, path2 = file1['file_path'], file2['file_path']
            
            group1 = file_groups.get(path1)
            group2 = file_groups.get(path2)
            
            if group1 is None and group2 is None:
                # 创建新组
                file_groups[path1] = group_id
                file_groups[path2] = group_id
                group_id += 1
            elif group1 is None:
                # 将file1加入file2的组
                file_groups[path1] = group2
            elif group2 is None:
                # 将file2加入file1的组
                file_groups[path2] = group1
            elif group1 != group2:
                # 合并两个组
                old_group = group2
                new_group = group1
                for path, gid in file_groups.items():
                    if gid == old_group:
                        file_groups[path] = new_group
        
        # 组织成最终格式
        groups = defaultdict(list)
        file_map = {}
        
        for file1, file2 in similar_pairs:
            file_map[file1['file_path']] = file1
            file_map[file2['file_path']] = file2
        
        for path, gid in file_groups.items():
            groups[gid].append(file_map[path])
        
        # 过滤单个文件的组
        result = [group for group in groups.values() if len(group) > 1]
        
        return result


if __name__ == "__main__":
    pass