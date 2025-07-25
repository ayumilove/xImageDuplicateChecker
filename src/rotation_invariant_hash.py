# -*- coding: utf-8 -*-
"""
旋转不变哈希算法模块

提供旋转不变的图片哈希计算和比较功能
"""

import os
import tempfile
from typing import List, Dict, Tuple
from PIL import Image
from .hash_utils import calculate_dhash, calculate_phash, calculate_ahash, hamming_distance


class RotationInvariantHasher:
    """
    旋转不变哈希计算器
    """
    
    def __init__(self, angles: List[int] = None):
        """
        初始化旋转不变哈希计算器
        
        Args:
            angles: 要计算的旋转角度列表，默认为[0, 90, 180, 270]
        """
        self.angles = angles or [0, 90, 180, 270]
    
    def calculate_rotation_invariant_hashes(self, image_path: str) -> List[Dict]:
        """
        计算图片在多个角度下的哈希值
        
        Args:
            image_path: 图片路径
            
        Returns:
            包含多个角度哈希值的列表
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        hashes = []
        
        try:
            img = Image.open(image_path)
            
            for angle in self.angles:
                # 旋转图片
                if angle == 0:
                    rotated_img = img
                else:
                    rotated_img = img.rotate(angle, expand=True, fillcolor='white')
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_path = temp_file.name
                    rotated_img.save(temp_path)
                
                try:
                    # 计算哈希值
                    dhash = calculate_dhash(temp_path)
                    phash = calculate_phash(temp_path)
                    ahash = calculate_ahash(temp_path)
                    
                    hashes.append({
                        'angle': angle,
                        'dhash': dhash,
                        'phash': phash,
                        'ahash': ahash
                    })
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        except Exception as e:
            raise ValueError(f"计算旋转不变哈希时出错: {image_path}, 错误: {str(e)}")
        
        return hashes
    
    def compare_rotation_invariant(self, image1_path: str, image2_path: str, 
                                 dhash_threshold: int = 8, 
                                 phash_threshold: int = 2, 
                                 ahash_threshold: int = 2) -> Dict:
        """
        使用旋转不变方法比较两张图片
        
        Args:
            image1_path: 第一张图片路径
            image2_path: 第二张图片路径
            dhash_threshold: dHash阈值
            phash_threshold: pHash阈值
            ahash_threshold: aHash阈值
            
        Returns:
            比较结果字典
        """
        hashes1 = self.calculate_rotation_invariant_hashes(image1_path)
        hashes2 = self.calculate_rotation_invariant_hashes(image2_path)
        
        min_distances = {
            'dhash': float('inf'),
            'phash': float('inf'),
            'ahash': float('inf')
        }
        
        best_match = None
        
        # 比较所有角度组合，找到最小距离
        for h1 in hashes1:
            for h2 in hashes2:
                try:
                    dhash_dist = hamming_distance(h1['dhash'], h2['dhash'])
                    phash_dist = hamming_distance(h1['phash'], h2['phash'])
                    ahash_dist = hamming_distance(h1['ahash'], h2['ahash'])
                    
                    if dhash_dist < min_distances['dhash']:
                        min_distances['dhash'] = dhash_dist
                    if phash_dist < min_distances['phash']:
                        min_distances['phash'] = phash_dist
                    if ahash_dist < min_distances['ahash']:
                        min_distances['ahash'] = ahash_dist
                    
                    # 记录最佳匹配
                    total_dist = dhash_dist + phash_dist + ahash_dist
                    if best_match is None or total_dist < best_match['total_distance']:
                        best_match = {
                            'angle1': h1['angle'],
                            'angle2': h2['angle'],
                            'dhash_distance': dhash_dist,
                            'phash_distance': phash_dist,
                            'ahash_distance': ahash_dist,
                            'total_distance': total_dist
                        }
                except Exception:
                    # 如果计算距离失败，跳过这个组合
                    continue
        
        # 判断是否相似
        dhash_similar = min_distances['dhash'] < dhash_threshold
        phash_similar = min_distances['phash'] < phash_threshold
        ahash_similar = min_distances['ahash'] < ahash_threshold
        
        # 使用多重验证机制（至少两种算法判断为相似）
        similar_count = sum([dhash_similar, phash_similar, ahash_similar])
        is_similar = similar_count >= 2
        
        return {
            'is_similar': is_similar,
            'min_distances': min_distances,
            'best_match': best_match,
            'similar_algorithms': {
                'dhash': dhash_similar,
                'phash': phash_similar,
                'ahash': ahash_similar
            },
            'similar_count': similar_count
        }
    
    def find_rotation_angle(self, image1_path: str, image2_path: str) -> int:
        """
        找到两张图片之间的旋转角度
        
        Args:
            image1_path: 第一张图片路径
            image2_path: 第二张图片路径
            
        Returns:
            旋转角度（如果找到匹配），否则返回-1
        """
        result = self.compare_rotation_invariant(image1_path, image2_path)
        
        if result['is_similar'] and result['best_match']:
            angle_diff = abs(result['best_match']['angle1'] - result['best_match']['angle2'])
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            return angle_diff
        
        return -1


def batch_compare_with_rotation(image_files: List[str], 
                               dhash_threshold: int = 8,
                               phash_threshold: int = 2,
                               ahash_threshold: int = 2,
                               log_callback=None) -> List[Dict]:
    """
    批量比较图片，支持旋转识别（优化版本）
    
    Args:
        image_files: 图片文件列表
        dhash_threshold: dHash阈值
        phash_threshold: pHash阈值
        ahash_threshold: aHash阈值
        log_callback: 日志回调函数
        
    Returns:
        相似图片组列表
    """
    hasher = RotationInvariantHasher()
    similar_groups = []
    processed = set()
    
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    log(f"开始旋转不变图片比较，共 {len(image_files)} 个文件...")
    
    # 预计算所有图片的旋转哈希值
    log("正在预计算所有图片的旋转哈希值...")
    all_hashes = {}
    
    for i, file_path in enumerate(image_files):
        if i % 100 == 0 and i > 0:
            log(f"已预计算 {i}/{len(image_files)} 个文件的哈希值...")
        
        try:
            all_hashes[file_path] = hasher.calculate_rotation_invariant_hashes(file_path)
        except Exception as e:
            log(f"计算哈希值失败: {file_path}, 错误: {str(e)}")
            continue
    
    log(f"哈希值预计算完成，开始比较...")
    
    # 使用预计算的哈希值进行比较
    for i, file1 in enumerate(image_files):
        if file1 in processed or file1 not in all_hashes:
            continue
        
        if i % 50 == 0 and i > 0:
            log(f"已处理 {i}/{len(image_files)} 个文件...")
        
        similar_files = []
        rotation_info = []
        
        hashes1 = all_hashes[file1]
        
        for j, file2 in enumerate(image_files[i+1:], i+1):
            if file2 in processed or file2 not in all_hashes:
                continue
            
            try:
                hashes2 = all_hashes[file2]
                
                # 快速比较预计算的哈希值
                min_distances = {
                    'dhash': float('inf'),
                    'phash': float('inf'),
                    'ahash': float('inf')
                }
                
                best_match = None
                
                # 比较所有角度组合，找到最小距离
                for h1 in hashes1:
                    for h2 in hashes2:
                        try:
                            dhash_dist = hamming_distance(h1['dhash'], h2['dhash'])
                            phash_dist = hamming_distance(h1['phash'], h2['phash'])
                            ahash_dist = hamming_distance(h1['ahash'], h2['ahash'])
                            
                            if dhash_dist < min_distances['dhash']:
                                min_distances['dhash'] = dhash_dist
                            if phash_dist < min_distances['phash']:
                                min_distances['phash'] = phash_dist
                            if ahash_dist < min_distances['ahash']:
                                min_distances['ahash'] = ahash_dist
                            
                            # 记录最佳匹配
                            total_dist = dhash_dist + phash_dist + ahash_dist
                            if best_match is None or total_dist < best_match['total_distance']:
                                best_match = {
                                    'angle1': h1['angle'],
                                    'angle2': h2['angle'],
                                    'dhash_distance': dhash_dist,
                                    'phash_distance': phash_dist,
                                    'ahash_distance': ahash_dist,
                                    'total_distance': total_dist
                                }
                        except Exception:
                            continue
                
                # 判断是否相似
                dhash_similar = min_distances['dhash'] < dhash_threshold
                phash_similar = min_distances['phash'] < phash_threshold
                ahash_similar = min_distances['ahash'] < ahash_threshold
                
                # 使用多重验证机制（至少两种算法判断为相似）
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                is_similar = similar_count >= 2
                
                if is_similar:
                    similar_files.append(file2)
                    
                    # 记录旋转信息
                    if best_match:
                        angle_diff = abs(best_match['angle1'] - best_match['angle2'])
                        if angle_diff > 180:
                            angle_diff = 360 - angle_diff
                        
                        rotation_info.append({
                            'file': file2,
                            'rotation_angle': angle_diff,
                            'distances': min_distances
                        })
            
            except Exception as e:
                log(f"比较文件时出错: {file1} vs {file2}, 错误: {str(e)}")
                continue
        
        if similar_files:
            # 构建相似组
            all_files = [file1] + similar_files
            
            # 确定主要原因
            reasons = []
            if any(info['distances']['dhash'] < dhash_threshold for info in rotation_info):
                reasons.append("dHash")
            if any(info['distances']['phash'] < phash_threshold for info in rotation_info):
                reasons.append("pHash")
            if any(info['distances']['ahash'] < ahash_threshold for info in rotation_info):
                reasons.append("aHash")
            
            reason = "+".join(reasons) + "相似(支持旋转)"
            
            similar_group = {
                'reason': reason,
                'files': all_files,
                'rotation_info': rotation_info
            }
            
            similar_groups.append(similar_group)
            
            # 标记为已处理
            for file_path in all_files:
                processed.add(file_path)
    
    log(f"旋转不变比较完成，找到 {len(similar_groups)} 个相似组")
    return similar_groups