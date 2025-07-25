# -*- coding: utf-8 -*-
"""
C++ 旋转不变哈希算法的Python封装

提供与原有rotation_invariant_hash.py相同的接口，但使用C++动态库实现
"""

import ctypes
import os
from typing import List, Tuple, Dict, Any, Optional
from hash_wrapper import get_hash_lib


class RotationInvariantHasher:
    """
    旋转不变哈希计算器
    
    使用C++实现的哈希算法来计算图片在不同旋转角度下的哈希值
    """
    
    def __init__(self, hash_size: int = 8):
        """
        初始化旋转不变哈希计算器
        
        Args:
            hash_size: 哈希大小，默认为8
        """
        self.hash_size = hash_size
        self.hash_lib = get_hash_lib()
        self._setup_function_signatures()
        
        # 旋转角度列表
        self.rotation_angles = [0, 90, 180, 270]
    
    def _setup_function_signatures(self):
        """
        设置C++库函数签名
        """
        # 设置旋转哈希函数签名
        self.hash_lib.lib.calculate_dhash_rotated_c.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        self.hash_lib.lib.calculate_dhash_rotated_c.restype = ctypes.c_void_p
        
        self.hash_lib.lib.calculate_phash_rotated_c.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        self.hash_lib.lib.calculate_phash_rotated_c.restype = ctypes.c_void_p
        
        self.hash_lib.lib.calculate_ahash_rotated_c.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        self.hash_lib.lib.calculate_ahash_rotated_c.restype = ctypes.c_void_p
    
    def calculate_rotation_hashes(self, image_path: str) -> Dict[str, Dict[int, str]]:
        """
        计算图片在不同旋转角度下的所有哈希值
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            包含所有旋转角度哈希值的字典
            格式: {
                'dhash': {0: 'hash0', 90: 'hash90', 180: 'hash180', 270: 'hash270'},
                'phash': {0: 'hash0', 90: 'hash90', 180: 'hash180', 270: 'hash270'},
                'ahash': {0: 'hash0', 90: 'hash90', 180: 'hash180', 270: 'hash270'}
            }
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        rotation_hashes = {
            'dhash': {},
            'phash': {},
            'ahash': {}
        }
        
        # 使用C++库计算所有旋转角度的哈希值
        try:
            # 计算所有旋转角度的哈希值
            for angle in self.rotation_angles:
                # 使用C++库的旋转哈希函数
                dhash = self._calculate_rotated_hash('dhash', image_path, angle)
                phash = self._calculate_rotated_hash('phash', image_path, angle)
                ahash = self._calculate_rotated_hash('ahash', image_path, angle)
                
                rotation_hashes['dhash'][angle] = dhash
                rotation_hashes['phash'][angle] = phash
                rotation_hashes['ahash'][angle] = ahash
            
        except Exception as e:
            raise RuntimeError(f"计算旋转哈希失败: {e}")
        
        return rotation_hashes
    
    def _calculate_rotated_hash(self, hash_type: str, image_path: str, angle: int) -> str:
        """
        计算指定角度旋转后的哈希值
        
        Args:
            hash_type: 哈希类型 ('dhash', 'phash', 'ahash')
            image_path: 图片路径
            angle: 旋转角度
            
        Returns:
            哈希值字符串
        """
        image_path_bytes = image_path.encode('utf-8')
        
        if hash_type == 'dhash':
            result_ptr = self.hash_lib.lib.calculate_dhash_rotated_c(image_path_bytes, angle, self.hash_size)
        elif hash_type == 'phash':
            result_ptr = self.hash_lib.lib.calculate_phash_rotated_c(image_path_bytes, angle, self.hash_size)
        elif hash_type == 'ahash':
            result_ptr = self.hash_lib.lib.calculate_ahash_rotated_c(image_path_bytes, angle, self.hash_size)
        else:
            raise ValueError(f"不支持的哈希类型: {hash_type}")
        
        if not result_ptr:
            raise RuntimeError(f"计算{hash_type}旋转哈希失败")
        
        # 转换C字符串为Python字符串
        hash_str = ctypes.string_at(result_ptr).decode('utf-8')
        
        # 释放C++分配的内存
        self.hash_lib.lib.free_string_c(result_ptr)
        
        return hash_str
    
    def compare_rotation_invariant(self, image1_path: str, image2_path: str, 
                                 dhash_threshold: int = 5, 
                                 phash_threshold: int = 10, 
                                 ahash_threshold: int = 5) -> Tuple[bool, Dict[str, Any]]:
        """
        比较两张图片是否相似（考虑旋转不变性）
        
        Args:
            image1_path: 第一张图片路径
            image2_path: 第二张图片路径
            dhash_threshold: dHash相似度阈值
            phash_threshold: pHash相似度阈值
            ahash_threshold: aHash相似度阈值
            
        Returns:
            (是否相似, 详细信息字典)
        """
        try:
            # 计算两张图片的旋转哈希值
            hashes1 = self.calculate_rotation_hashes(image1_path)
            hashes2 = self.calculate_rotation_hashes(image2_path)
            
            best_match = {
                'is_similar': False,
                'rotation_angle': None,
                'similar_algorithms': [],
                'distances': {},
                'min_distances': {}
            }
            
            # 比较所有旋转角度组合
            for angle1 in self.rotation_angles:
                for angle2 in self.rotation_angles:
                    # 计算当前角度组合下的距离
                    dhash_dist = self.hash_lib.hamming_distance(
                        hashes1['dhash'][angle1], 
                        hashes2['dhash'][angle2]
                    )
                    phash_dist = self.hash_lib.hamming_distance(
                        hashes1['phash'][angle1], 
                        hashes2['phash'][angle2]
                    )
                    ahash_dist = self.hash_lib.hamming_distance(
                        hashes1['ahash'][angle1], 
                        hashes2['ahash'][angle2]
                    )
                    
                    # 检查是否满足相似度条件
                    similar_algorithms = []
                    if dhash_dist <= dhash_threshold:
                        similar_algorithms.append('dhash')
                    if phash_dist <= phash_threshold:
                        similar_algorithms.append('phash')
                    if ahash_dist <= ahash_threshold:
                        similar_algorithms.append('ahash')
                    
                    # 如果至少有两种算法判断为相似，则认为图片相似
                    if len(similar_algorithms) >= 2:
                        rotation_angle = (angle2 - angle1) % 360
                        
                        # 更新最佳匹配结果
                        if not best_match['is_similar'] or len(similar_algorithms) > len(best_match['similar_algorithms']):
                            best_match.update({
                                'is_similar': True,
                                'rotation_angle': rotation_angle,
                                'similar_algorithms': similar_algorithms,
                                'distances': {
                                    'dhash': dhash_dist,
                                    'phash': phash_dist,
                                    'ahash': ahash_dist
                                },
                                'angle1': angle1,
                                'angle2': angle2
                            })
            
            # 如果没有找到相似匹配，记录最小距离
            if not best_match['is_similar']:
                min_distances = {'dhash': float('inf'), 'phash': float('inf'), 'ahash': float('inf')}
                for angle1 in self.rotation_angles:
                    for angle2 in self.rotation_angles:
                        dhash_dist = self.hash_lib.hamming_distance(
                            hashes1['dhash'][angle1], 
                            hashes2['dhash'][angle2]
                        )
                        phash_dist = self.hash_lib.hamming_distance(
                            hashes1['phash'][angle1], 
                            hashes2['phash'][angle2]
                        )
                        ahash_dist = self.hash_lib.hamming_distance(
                            hashes1['ahash'][angle1], 
                            hashes2['ahash'][angle2]
                        )
                        
                        min_distances['dhash'] = min(min_distances['dhash'], dhash_dist)
                        min_distances['phash'] = min(min_distances['phash'], phash_dist)
                        min_distances['ahash'] = min(min_distances['ahash'], ahash_dist)
                
                best_match['min_distances'] = min_distances
            
            return best_match['is_similar'], best_match
            
        except Exception as e:
            raise RuntimeError(f"旋转不变比较失败: {e}")


def batch_compare_with_rotation(image_paths: List[str], 
                              dhash_threshold: int = 5, 
                              phash_threshold: int = 10, 
                              ahash_threshold: int = 5,
                              progress_callback=None) -> List[List[Dict[str, Any]]]:
    """
    批量比较图片相似性（支持旋转不变）
    
    Args:
        image_paths: 图片路径列表
        dhash_threshold: dHash相似度阈值
        phash_threshold: pHash相似度阈值
        ahash_threshold: aHash相似度阈值
        progress_callback: 进度回调函数
        
    Returns:
        相似图片组列表，每组包含相似图片的详细信息
    """
    if not image_paths:
        return []
    
    hasher = RotationInvariantHasher()
    similar_groups = []
    processed_images = set()
    
    total_comparisons = len(image_paths) * (len(image_paths) - 1) // 2
    current_comparison = 0
    
    for i, image1_path in enumerate(image_paths):
        if image1_path in processed_images:
            continue
        
        current_group = [{
            'path': image1_path,
            'rotation_angle': 0,
            'similar_reason': 'original'
        }]
        
        for j, image2_path in enumerate(image_paths[i+1:], i+1):
            if image2_path in processed_images:
                continue
            
            current_comparison += 1
            
            # 更新进度
            if progress_callback:
                progress = (current_comparison / total_comparisons) * 100
                progress_callback(f"比较图片 {i+1}/{len(image_paths)}: {os.path.basename(image1_path)} vs {os.path.basename(image2_path)}", progress)
            
            try:
                is_similar, match_info = hasher.compare_rotation_invariant(
                    image1_path, image2_path,
                    dhash_threshold, phash_threshold, ahash_threshold
                )
                
                if is_similar:
                    current_group.append({
                        'path': image2_path,
                        'rotation_angle': match_info.get('rotation_angle', 0),
                        'similar_reason': ', '.join(match_info.get('similar_algorithms', [])),
                        'distances': match_info.get('distances', {})
                    })
                    processed_images.add(image2_path)
                    
            except Exception as e:
                # 记录错误但继续处理其他图片
                if progress_callback:
                    progress_callback(f"比较失败: {e}", None)
                continue
        
        # 如果组中有多于一张图片，则添加到相似组列表
        if len(current_group) > 1:
            similar_groups.append(current_group)
        
        processed_images.add(image1_path)
    
    return similar_groups


if __name__ == "__main__":
    # 测试代码
    try:
        hasher = RotationInvariantHasher()
        print("C++ 旋转不变哈希库初始化成功！")
        print(f"哈希器实例: {hasher}")
    except Exception as e:
        print(f"初始化C++ 旋转不变哈希库失败: {e}")
        print("请确保已正确编译动态库文件。")