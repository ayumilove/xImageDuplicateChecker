# -*- coding: utf-8 -*-
"""
增强相似度检测模块

支持旋转和分辨率变化的图片相似度检测
结合多种哈希算法和多尺度分析提高检测精度
"""

import os
import tempfile
from typing import List, Dict, Tuple, Optional
from PIL import Image
import numpy as np
from .hash_utils import calculate_dhash, calculate_phash, calculate_ahash, hamming_distance


class EnhancedSimilarityDetector:
    """
    增强相似度检测器
    支持旋转、缩放、分辨率变化的图片相似度检测
    """
    
    def __init__(self, 
                 angles: List[int] = None,
                 scales: List[float] = None,
                 hash_sizes: List[int] = None):
        """
        初始化增强相似度检测器
        
        Args:
            angles: 要检测的旋转角度列表，默认为[0, 90, 180, 270]
            scales: 要检测的缩放比例列表，默认为[0.5, 0.75, 1.0, 1.25, 1.5]
            hash_sizes: 哈希大小列表，用于多尺度分析，默认为[8, 16]
        """
        # 优化默认参数以提高性能
        self.angles = angles or [0, 90, 180, 270]  # 保持旋转检测
        self.scales = scales or [0.75, 1.0, 1.25]  # 减少缩放比例
        self.hash_sizes = hash_sizes or [8]  # 只使用一个哈希大小
    
    def calculate_multi_scale_hashes(self, image_path: str) -> List[Dict]:
        """
        计算图片在多个角度和尺度下的哈希值
        
        Args:
            image_path: 图片路径
            
        Returns:
            包含多个角度和尺度哈希值的列表
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        all_hashes = []
        
        try:
            img = Image.open(image_path)
            original_size = img.size
            
            for angle in self.angles:
                # 旋转图片
                if angle == 0:
                    rotated_img = img
                else:
                    rotated_img = img.rotate(angle, expand=True, fillcolor='white')
                
                for scale in self.scales:
                    # 缩放图片
                    if scale == 1.0:
                        scaled_img = rotated_img
                    else:
                        new_size = (int(rotated_img.size[0] * scale), 
                                   int(rotated_img.size[1] * scale))
                        if new_size[0] > 0 and new_size[1] > 0:
                            scaled_img = rotated_img.resize(new_size, Image.LANCZOS)
                        else:
                            continue
                    
                    # 为每个哈希大小计算哈希值（优化：直接从PIL图像计算）
                    for hash_size in self.hash_sizes:
                        try:
                            # 直接从PIL图像计算哈希值，避免临时文件
                            dhash = self._calculate_dhash_from_image(scaled_img, hash_size)
                            phash = self._calculate_phash_from_image(scaled_img, hash_size)
                            ahash = self._calculate_ahash_from_image(scaled_img, hash_size)
                            
                            # 计算额外的特征
                            features = self._extract_additional_features(scaled_img)
                            
                            all_hashes.append({
                                'angle': angle,
                                'scale': scale,
                                'hash_size': hash_size,
                                'dhash': dhash,
                                'phash': phash,
                                'ahash': ahash,
                                'features': features,
                                'image_size': scaled_img.size
                            })
                        except Exception as e:
                            # 如果计算失败，跳过这个组合
                            continue
        
        except Exception as e:
            raise ValueError(f"计算多尺度哈希时出错: {image_path}, 错误: {str(e)}")
        
        return all_hashes
    
    def _calculate_dhash_from_image(self, image: Image.Image, hash_size: int) -> str:
        """直接从PIL图像计算指定大小的dHash"""
        try:
            gray_img = image.convert('L')
            resized_img = gray_img.resize((hash_size + 1, hash_size), Image.LANCZOS)
            pixels = np.array(resized_img)
            diff = pixels[:, 1:] > pixels[:, :-1]
            binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _calculate_phash_from_image(self, image: Image.Image, hash_size: int) -> str:
        """直接从PIL图像计算指定大小的pHash"""
        try:
            gray_img = image.convert('L')
            resized_img = gray_img.resize((hash_size * 4, hash_size * 4), Image.LANCZOS)
            pixels = np.array(resized_img, dtype=np.float32)
            
            # 简化的DCT计算
            dct = np.zeros((hash_size, hash_size))
            for i in range(hash_size):
                for j in range(hash_size):
                    dct[i, j] = np.sum(pixels * 
                                     np.cos(np.pi * i * np.arange(hash_size * 4) / (hash_size * 4)) *
                                     np.cos(np.pi * j * np.arange(hash_size * 4).reshape(-1, 1) / (hash_size * 4)))
            
            dct_flat = dct.flatten()[1:]
            median = np.median(dct_flat)
            diff = dct_flat > median
            binary_hash = ''.join('1' if d else '0' for d in diff)
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                if i + 4 <= len(binary_hash):
                    hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _calculate_ahash_from_image(self, image: Image.Image, hash_size: int) -> str:
        """直接从PIL图像计算指定大小的aHash"""
        try:
            gray_img = image.convert('L')
            resized_img = gray_img.resize((hash_size, hash_size), Image.LANCZOS)
            pixels = np.array(resized_img)
            avg = np.mean(pixels)
            diff = pixels > avg
            binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                if i + 4 <= len(binary_hash):
                    hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _calculate_dhash_with_size(self, image_path: str, hash_size: int) -> str:
        """计算指定大小的dHash"""
        try:
            image = Image.open(image_path).convert('L')
            image = image.resize((hash_size + 1, hash_size), Image.LANCZOS)
            pixels = np.array(image)
            diff = pixels[:, 1:] > pixels[:, :-1]
            binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _calculate_phash_with_size(self, image_path: str, hash_size: int) -> str:
        """计算指定大小的pHash"""
        try:
            image = Image.open(image_path).convert('L')
            image = image.resize((hash_size * 4, hash_size * 4), Image.LANCZOS)
            pixels = np.array(image, dtype=np.float32)
            
            # 简化的DCT计算
            dct = np.zeros((hash_size, hash_size))
            for i in range(hash_size):
                for j in range(hash_size):
                    dct[i, j] = np.sum(pixels * 
                                     np.cos(np.pi * i * np.arange(hash_size * 4) / (hash_size * 4)) *
                                     np.cos(np.pi * j * np.arange(hash_size * 4).reshape(-1, 1) / (hash_size * 4)))
            
            dct_flat = dct.flatten()[1:]
            median = np.median(dct_flat)
            diff = dct_flat > median
            binary_hash = ''.join('1' if d else '0' for d in diff)
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                if i + 4 <= len(binary_hash):
                    hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _calculate_ahash_with_size(self, image_path: str, hash_size: int) -> str:
        """计算指定大小的aHash"""
        try:
            image = Image.open(image_path).convert('L')
            image = image.resize((hash_size, hash_size), Image.LANCZOS)
            pixels = np.array(image)
            avg = np.mean(pixels)
            diff = pixels > avg
            binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
            hex_hash = ''
            for i in range(0, len(binary_hash), 4):
                if i + 4 <= len(binary_hash):
                    hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
            return hex_hash
        except Exception:
            return "error"
    
    def _extract_additional_features(self, image: Image.Image) -> Dict:
        """
        提取额外的图片特征
        
        Args:
            image: PIL图片对象
            
        Returns:
            特征字典
        """
        try:
            # 转换为灰度图
            gray_img = image.convert('L')
            pixels = np.array(gray_img)
            
            features = {
                'aspect_ratio': image.size[0] / image.size[1] if image.size[1] > 0 else 1.0,
                'brightness': np.mean(pixels),
                'contrast': np.std(pixels),
                'entropy': self._calculate_entropy(pixels),
                'edge_density': self._calculate_edge_density(pixels)
            }
            
            return features
        except Exception:
            return {
                'aspect_ratio': 1.0,
                'brightness': 128.0,
                'contrast': 0.0,
                'entropy': 0.0,
                'edge_density': 0.0
            }
    
    def _calculate_entropy(self, pixels: np.ndarray) -> float:
        """计算图片熵值"""
        try:
            hist, _ = np.histogram(pixels, bins=256, range=(0, 256))
            hist = hist / hist.sum()
            hist = hist[hist > 0]  # 移除零值
            entropy = -np.sum(hist * np.log2(hist))
            return float(entropy)
        except Exception:
            return 0.0
    
    def _calculate_edge_density(self, pixels: np.ndarray) -> float:
        """计算边缘密度"""
        try:
            # 简单的Sobel边缘检测
            sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
            sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
            
            # 计算梯度
            grad_x = np.abs(np.convolve(pixels.flatten(), sobel_x.flatten(), mode='same'))
            grad_y = np.abs(np.convolve(pixels.flatten(), sobel_y.flatten(), mode='same'))
            
            edge_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            edge_density = np.mean(edge_magnitude)
            
            return float(edge_density)
        except Exception:
            return 0.0
    
    def compare_enhanced_similarity(self, 
                                  image1_path: str, 
                                  image2_path: str,
                                  dhash_threshold: int = 12,
                                  phash_threshold: int = 4,
                                  ahash_threshold: int = 4,
                                  feature_weight: float = 0.3) -> Dict:
        """
        使用增强方法比较两张图片的相似度
        
        Args:
            image1_path: 第一张图片路径
            image2_path: 第二张图片路径
            dhash_threshold: dHash阈值（放宽以适应分辨率变化）
            phash_threshold: pHash阈值（放宽以适应分辨率变化）
            ahash_threshold: aHash阈值（放宽以适应分辨率变化）
            feature_weight: 特征相似度权重
            
        Returns:
            详细的比较结果
        """
        hashes1 = self.calculate_multi_scale_hashes(image1_path)
        hashes2 = self.calculate_multi_scale_hashes(image2_path)
        
        best_match = None
        min_distances = {
            'dhash': float('inf'),
            'phash': float('inf'),
            'ahash': float('inf')
        }
        
        all_matches = []
        
        # 比较所有组合
        for h1 in hashes1:
            for h2 in hashes2:
                if (h1['dhash'] == "error" or h2['dhash'] == "error" or
                    h1['phash'] == "error" or h2['phash'] == "error" or
                    h1['ahash'] == "error" or h2['ahash'] == "error"):
                    continue
                
                try:
                    # 计算哈希距离
                    dhash_dist = hamming_distance(h1['dhash'], h2['dhash'])
                    phash_dist = hamming_distance(h1['phash'], h2['phash'])
                    ahash_dist = hamming_distance(h1['ahash'], h2['ahash'])
                    
                    # 计算特征相似度
                    feature_similarity = self._calculate_feature_similarity(h1['features'], h2['features'])
                    
                    # 综合评分（哈希距离越小越好，特征相似度越大越好）
                    hash_score = (dhash_dist + phash_dist + ahash_dist) / 3.0
                    feature_score = (1.0 - feature_similarity) * 64  # 转换为距离形式
                    combined_score = hash_score * (1 - feature_weight) + feature_score * feature_weight
                    
                    match_info = {
                        'angle1': h1['angle'],
                        'angle2': h2['angle'],
                        'scale1': h1['scale'],
                        'scale2': h2['scale'],
                        'hash_size': h1['hash_size'],
                        'dhash_distance': dhash_dist,
                        'phash_distance': phash_dist,
                        'ahash_distance': ahash_dist,
                        'feature_similarity': feature_similarity,
                        'combined_score': combined_score,
                        'size1': h1['image_size'],
                        'size2': h2['image_size']
                    }
                    
                    all_matches.append(match_info)
                    
                    # 更新最小距离
                    if dhash_dist < min_distances['dhash']:
                        min_distances['dhash'] = dhash_dist
                    if phash_dist < min_distances['phash']:
                        min_distances['phash'] = phash_dist
                    if ahash_dist < min_distances['ahash']:
                        min_distances['ahash'] = ahash_dist
                    
                    # 更新最佳匹配
                    if best_match is None or combined_score < best_match['combined_score']:
                        best_match = match_info
                
                except Exception:
                    continue
        
        # 排序所有匹配结果
        all_matches.sort(key=lambda x: x['combined_score'])
        
        # 判断相似度
        dhash_similar = min_distances['dhash'] <= dhash_threshold
        phash_similar = min_distances['phash'] <= phash_threshold
        ahash_similar = min_distances['ahash'] <= ahash_threshold
        
        # 特征相似度判断
        feature_similar = False
        if best_match and best_match['feature_similarity'] > 0.7:
            feature_similar = True
        
        # 综合判断（至少两种算法相似，或者特征高度相似）
        similar_count = sum([dhash_similar, phash_similar, ahash_similar])
        is_similar = similar_count >= 2 or (similar_count >= 1 and feature_similar)
        
        # 确定检测类型
        detection_type = self._determine_detection_type(best_match)
        
        return {
            'is_similar': is_similar,
            'detection_type': detection_type,
            'min_distances': min_distances,
            'best_match': best_match,
            'top_matches': all_matches[:5],  # 返回前5个最佳匹配
            'similar_algorithms': {
                'dhash': dhash_similar,
                'phash': phash_similar,
                'ahash': ahash_similar,
                'features': feature_similar
            },
            'similar_count': similar_count,
            'confidence': self._calculate_confidence(best_match, min_distances)
        }
    
    def _calculate_feature_similarity(self, features1: Dict, features2: Dict) -> float:
        """
        计算特征相似度
        
        Args:
            features1: 第一张图片的特征
            features2: 第二张图片的特征
            
        Returns:
            特征相似度（0-1之间，1表示完全相似）
        """
        try:
            # 计算各个特征的相似度
            aspect_ratio_sim = 1.0 - min(abs(features1['aspect_ratio'] - features2['aspect_ratio']) / max(features1['aspect_ratio'], features2['aspect_ratio']), 1.0)
            brightness_sim = 1.0 - min(abs(features1['brightness'] - features2['brightness']) / 255.0, 1.0)
            contrast_sim = 1.0 - min(abs(features1['contrast'] - features2['contrast']) / 128.0, 1.0)
            entropy_sim = 1.0 - min(abs(features1['entropy'] - features2['entropy']) / 8.0, 1.0)
            edge_sim = 1.0 - min(abs(features1['edge_density'] - features2['edge_density']) / 100.0, 1.0)
            
            # 加权平均
            weights = [0.15, 0.25, 0.25, 0.2, 0.15]  # 对比度和亮度权重较高
            similarities = [aspect_ratio_sim, brightness_sim, contrast_sim, entropy_sim, edge_sim]
            
            weighted_similarity = sum(w * s for w, s in zip(weights, similarities))
            return weighted_similarity
        except Exception:
            return 0.0
    
    def _determine_detection_type(self, best_match: Optional[Dict]) -> str:
        """
        确定检测类型
        
        Args:
            best_match: 最佳匹配信息
            
        Returns:
            检测类型描述
        """
        if not best_match:
            return "无匹配"
        
        angle_diff = abs(best_match['angle1'] - best_match['angle2'])
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        scale_diff = abs(best_match['scale1'] - best_match['scale2'])
        
        detection_parts = []
        
        if angle_diff > 0:
            detection_parts.append(f"旋转{angle_diff}°")
        
        if scale_diff > 0.1:
            scale_ratio = max(best_match['scale1'], best_match['scale2']) / min(best_match['scale1'], best_match['scale2'])
            detection_parts.append(f"缩放{scale_ratio:.1f}x")
        
        if best_match['size1'] != best_match['size2']:
            detection_parts.append("分辨率变化")
        
        if not detection_parts:
            return "完全相同"
        
        return "增强检测(" + "+".join(detection_parts) + ")"
    
    def _calculate_confidence(self, best_match: Optional[Dict], min_distances: Dict) -> float:
        """
        计算检测置信度
        
        Args:
            best_match: 最佳匹配信息
            min_distances: 最小距离
            
        Returns:
            置信度（0-1之间）
        """
        if not best_match:
            return 0.0
        
        try:
            # 基于哈希距离计算置信度
            max_distance = 64  # 最大可能的汉明距离
            hash_confidence = 1.0 - (best_match['dhash_distance'] + best_match['phash_distance'] + best_match['ahash_distance']) / (3 * max_distance)
            
            # 基于特征相似度计算置信度
            feature_confidence = best_match['feature_similarity']
            
            # 综合置信度
            combined_confidence = (hash_confidence * 0.7 + feature_confidence * 0.3)
            
            return max(0.0, min(1.0, combined_confidence))
        except Exception:
            return 0.0
    
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算两个哈希值的汉明距离
        
        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值
            
        Returns:
            汉明距离
        """
        if hash1 == "error" or hash2 == "error" or len(hash1) != len(hash2):
            return 999  # 返回一个很大的距离值
        
        try:
            return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        except Exception:
            return 999
    
    def _calculate_feature_similarity_from_dict(self, features1: Dict, features2: Dict) -> float:
        """
        从特征字典计算特征相似度
        
        Args:
            features1: 第一个图片的特征字典
            features2: 第二个图片的特征字典
            
        Returns:
            特征相似度 (0-1)
        """
        try:
            # 计算各个特征的相似度
            aspect_ratio_sim = 1.0 - abs(features1.get('aspect_ratio', 1.0) - features2.get('aspect_ratio', 1.0))
            brightness_sim = 1.0 - abs(features1.get('brightness', 0.5) - features2.get('brightness', 0.5))
            contrast_sim = 1.0 - abs(features1.get('contrast', 0.5) - features2.get('contrast', 0.5))
            entropy_sim = 1.0 - abs(features1.get('entropy', 5.0) - features2.get('entropy', 5.0)) / 10.0
            edge_density_sim = 1.0 - abs(features1.get('edge_density', 0.1) - features2.get('edge_density', 0.1))
            
            # 加权平均
            similarity = (aspect_ratio_sim * 0.3 + brightness_sim * 0.2 + 
                         contrast_sim * 0.2 + entropy_sim * 0.15 + edge_density_sim * 0.15)
            
            return max(0.0, min(1.0, similarity))
        except Exception:
            return 0.8  # 默认相似度
    
    def _fast_compare_with_precomputed_hashes(self, hashes1: List[Dict], hashes2: List[Dict],
                                            file1: str, file2: str,
                                            dhash_threshold: int = 12,
                                            phash_threshold: int = 4,
                                            ahash_threshold: int = 4,
                                            feature_weight: float = 0.3) -> Dict:
        """
        使用预计算的哈希值进行快速比较
        
        Args:
            hashes1: 第一个图片的多尺度哈希值
            hashes2: 第二个图片的多尺度哈希值
            file1: 第一个图片路径
            file2: 第二个图片路径
            dhash_threshold: dHash阈值
            phash_threshold: pHash阈值
            ahash_threshold: aHash阈值
            feature_weight: 特征权重
            
        Returns:
            比较结果字典
        """
        if not hashes1 or not hashes2:
            return None
        
        best_similarity = 0
        best_match = None
        best_rotation = 0
        best_scale = 1.0
        min_distances = {
            'dhash': float('inf'),
            'phash': float('inf'),
            'ahash': float('inf')
        }
        
        # 快速比较所有哈希组合
        for hash_data1 in hashes1:
            for hash_data2 in hashes2:
                # 计算哈希距离
                dhash_dist = self._hamming_distance(hash_data1['dhash'], hash_data2['dhash'])
                phash_dist = self._hamming_distance(hash_data1['phash'], hash_data2['phash'])
                ahash_dist = self._hamming_distance(hash_data1['ahash'], hash_data2['ahash'])
                
                # 更新最小距离
                min_distances['dhash'] = min(min_distances['dhash'], dhash_dist)
                min_distances['phash'] = min(min_distances['phash'], phash_dist)
                min_distances['ahash'] = min(min_distances['ahash'], ahash_dist)
                
                # 检查是否满足阈值
                hash_matches = 0
                if dhash_dist <= dhash_threshold:
                    hash_matches += 1
                if phash_dist <= phash_threshold:
                    hash_matches += 1
                if ahash_dist <= ahash_threshold:
                    hash_matches += 1
                
                # 至少需要2个哈希算法匹配
                if hash_matches >= 2:
                    # 计算相似度分数
                    hash_similarity = 1.0 - (dhash_dist + phash_dist + ahash_dist) / (64 + 64 + 64)
                    
                    if hash_similarity > best_similarity:
                         best_similarity = hash_similarity
                         # 简化特征相似度计算
                         feature_sim = 0.8  # 默认特征相似度
                         if 'features' in hash_data1 and 'features' in hash_data2:
                             try:
                                 feature_sim = self._calculate_feature_similarity_from_dict(
                                     hash_data1['features'], hash_data2['features']
                                 )
                             except:
                                 feature_sim = 0.8
                         
                         best_match = {
                             'dhash_distance': dhash_dist,
                             'phash_distance': phash_dist,
                             'ahash_distance': ahash_dist,
                             'hash_similarity': hash_similarity,
                             'feature_similarity': feature_sim
                         }
                         best_rotation = abs(hash_data1.get('angle', 0) - hash_data2.get('angle', 0))
                         best_scale = max(hash_data1.get('scale', 1.0), hash_data2.get('scale', 1.0)) / min(hash_data1.get('scale', 1.0), hash_data2.get('scale', 1.0))
        
        if best_match is None:
            return {
                'is_similar': False,
                'confidence': 0.0,
                'detection_type': '无匹配',
                'best_match': None
            }
        
        # 计算综合相似度
        combined_similarity = (1 - feature_weight) * best_similarity + feature_weight * best_match['feature_similarity']
        
        # 确定检测类型
        hash_distances = {
            'dhash': best_match['dhash_distance'],
            'phash': best_match['phash_distance'],
            'ahash': best_match['ahash_distance']
        }
        
        # 构建包含旋转和缩放信息的匹配数据用于检测类型判断
        match_with_transform = {
            **best_match,
            'angle1': 0,
            'angle2': best_rotation,
            'scale1': 1.0,
            'scale2': best_scale,
            'size1': (100, 100),  # 占位符
            'size2': (100, 100)   # 占位符
        }
        detection_type = self._determine_detection_type(match_with_transform)
        
        # 计算置信度
        confidence = self._calculate_confidence(match_with_transform, hash_distances)
        
        return {
            'is_similar': combined_similarity > 0.7,
            'confidence': confidence,
            'detection_type': detection_type,
            'best_match': {
                **best_match,
                'rotation_angle': best_rotation,
                'scale_factor': best_scale,
                'combined_similarity': combined_similarity
            }
        }


def batch_compare_with_enhanced_similarity(image_files: List[str],
                                         dhash_threshold: int = 12,
                                         phash_threshold: int = 4,
                                         ahash_threshold: int = 4,
                                         feature_weight: float = 0.3,
                                         confidence_threshold: float = 0.6,
                                         log_callback=None) -> List[Dict]:
    """
    批量比较图片，支持旋转和分辨率变化检测（优化版本）
    
    Args:
        image_files: 图片文件列表
        dhash_threshold: dHash阈值
        phash_threshold: pHash阈值
        ahash_threshold: aHash阈值
        feature_weight: 特征权重
        confidence_threshold: 置信度阈值
        log_callback: 日志回调函数
        
    Returns:
        相似图片组列表
    """
    import time
    start_time = time.time()
    
    detector = EnhancedSimilarityDetector()
    similar_groups = []
    processed = set()
    
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            print(message)
    
    total_files = len(image_files)
    total_comparisons = (total_files * (total_files - 1)) // 2
    
    log(f"开始增强相似度检测，共 {total_files} 个文件，预计 {total_comparisons} 次比较...")
    log("注意：增强检测计算量较大，每次比较需要多个尺度和角度组合")
    
    # 预先计算所有图片的哈希值以提高效率
    log("正在预计算所有图片的多尺度哈希值...")
    log(f"每个图片将计算 {len(detector.angles)} 个角度 × {len(detector.scales)} 个缩放 × {len(detector.hash_sizes)} 个哈希大小 = {len(detector.angles) * len(detector.scales) * len(detector.hash_sizes)} 个哈希组合")
    all_hashes = {}
    for i, file_path in enumerate(image_files):
        try:
            # 更频繁的进度报告
            log(f"预计算进度: {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%) - 处理: {os.path.basename(file_path)}")
            all_hashes[file_path] = detector.calculate_multi_scale_hashes(file_path)
            log(f"  完成，生成了 {len(all_hashes[file_path])} 个哈希组合")
        except Exception as e:
            log(f"预计算哈希失败: {file_path}, 错误: {str(e)}")
            all_hashes[file_path] = []
    
    log("预计算完成，开始比较...")
    
    comparison_count = 0
    for i, file1 in enumerate(image_files):
        if file1 in processed:
            continue
        
        # 报告当前处理的主文件
        elapsed = time.time() - start_time
        log(f"处理主文件 {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%): {os.path.basename(file1)} - 已用时 {elapsed:.1f}秒")
        
        similar_files = []
        detection_info = []
        
        for j, file2 in enumerate(image_files[i+1:], i+1):
            if file2 in processed:
                continue
            
            comparison_count += 1
            
            # 更频繁的比较进度报告 - 每5次比较或重要比较时报告
            if comparison_count % 5 == 0 or j == len(image_files) - 1:
                progress = comparison_count / total_comparisons * 100
                elapsed = time.time() - start_time
                estimated_total = elapsed / (comparison_count / total_comparisons) if comparison_count > 0 else 0
                remaining = estimated_total - elapsed
                log(f"  比较进度: {comparison_count}/{total_comparisons} ({progress:.1f}%) - 当前对比: {os.path.basename(file1)} vs {os.path.basename(file2)} - 预计剩余 {remaining:.0f}秒")
            
            try:
                # 使用预计算的哈希值进行快速比较
                result = detector._fast_compare_with_precomputed_hashes(
                    all_hashes.get(file1, []), all_hashes.get(file2, []),
                    file1, file2, dhash_threshold, phash_threshold, 
                    ahash_threshold, feature_weight
                )
                
                if result and result['is_similar'] and result['confidence'] >= confidence_threshold:
                    similar_files.append(file2)
                    detection_info.append({
                        'file': file2,
                        'detection_type': result['detection_type'],
                        'confidence': result['confidence'],
                        'best_match': result['best_match']
                    })
                    
                    # 详细的相似图片发现日志
                    rotation_info = ""
                    if result['best_match'] and 'rotation_angle' in result['best_match']:
                        rotation_angle = result['best_match']['rotation_angle']
                        if rotation_angle > 0:
                            rotation_info = f" (旋转角度: {rotation_angle}°)"
                    
                    scale_info = ""
                    if result['best_match'] and 'scale_factor' in result['best_match']:
                        scale_factor = result['best_match']['scale_factor']
                        if abs(scale_factor - 1.0) > 0.1:
                            scale_info = f" (缩放比例: {scale_factor:.2f})"
                    
                    log(f"  ✓ 找到相似图片: {os.path.basename(file1)} <-> {os.path.basename(file2)}")
                    log(f"    检测类型: {result['detection_type']}, 置信度: {result['confidence']:.3f}{rotation_info}{scale_info}")
            
            except Exception as e:
                log(f"比较文件时出错: {file1} vs {file2}, 错误: {str(e)}")
                continue
        
        if similar_files:
            all_files = [file1] + similar_files
            
            # 构建检测原因
            detection_types = [info['detection_type'] for info in detection_info]
            unique_types = list(set(detection_types))
            reason = "增强检测(" + "+".join(unique_types) + ")"
            
            similar_group = {
                'reason': reason,
                'files': all_files,
                'detection_info': detection_info,
                'avg_confidence': sum(info['confidence'] for info in detection_info) / len(detection_info)
            }
            
            similar_groups.append(similar_group)
            
            # 详细的相似组发现日志
            log(f"\n🎯 发现相似组 #{len(similar_groups)}: {len(all_files)} 个文件")
            log(f"  主文件: {os.path.basename(file1)}")
            for info in detection_info:
                log(f"  相似文件: {os.path.basename(info['file'])} (置信度: {info['confidence']:.3f}, 类型: {info['detection_type']})")
            log(f"  平均置信度: {similar_group['avg_confidence']:.3f}")
            log(f"  检测原因: {reason}\n")
            
            # 标记为已处理
            for file_path in all_files:
                processed.add(file_path)
        else:
            log(f"  未找到与 {os.path.basename(file1)} 相似的图片")
    
    elapsed = time.time() - start_time
    log(f"增强相似度检测完成！总用时 {elapsed:.1f}秒，找到 {len(similar_groups)} 个相似组")
    return similar_groups