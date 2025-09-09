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
    
    log(f"开始旋转不变图片比较，共 {len(image_files)} 个文件...")
    
    # 预计算所有图片的旋转哈希值（使用多线程）
    log("正在使用多线程预计算所有图片的旋转哈希值...")
    all_hashes = {}
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    
    def calculate_hash_batch(file_batch, batch_index):
        """批量计算旋转哈希值"""
        batch_results = {}
        for i, file_path in enumerate(file_batch):
            try:
                batch_results[file_path] = hasher.calculate_rotation_invariant_hashes(file_path)
                # 更频繁的进度更新
                if (i + 1) % 10 == 0:
                    log(f"批次{batch_index+1}: 已处理 {i+1}/{len(file_batch)} 个文件...")
            except Exception as e:
                log(f"计算哈希值失败: {file_path}, 错误: {str(e)}")
                continue
        return batch_results
    
    # 分批并行处理 - 使用更小的批次以获得更好的进度反馈
    batch_size = max(50, len(image_files) // 32)  # 32个批次，每批次至少50个文件
    batches = [image_files[i:i+batch_size] for i in range(0, len(image_files), batch_size)]
    
    log(f"将 {len(image_files)} 个文件分为 {len(batches)} 个批次，每批次约 {batch_size} 个文件")
    
    # 创建线程池进行并行计算
    with ThreadPoolExecutor(max_workers=min(8, len(batches))) as executor:
        # 提交所有批次任务
        future_to_batch = {executor.submit(calculate_hash_batch, batch, i): i for i, batch in enumerate(batches)}
        
        processed_count = 0
        completed_batches = 0
        for future in as_completed(future_to_batch):
            try:
                batch_results = future.result()
                all_hashes.update(batch_results)
                processed_count += len(batch_results)
                completed_batches += 1
                
                # 更频繁的进度更新
                progress_percent = (processed_count / len(image_files)) * 100
                log(f"已预计算 {processed_count}/{len(image_files)} 个文件的哈希值... ({progress_percent:.1f}%, 完成批次: {completed_batches}/{len(batches)})")
                    
            except Exception as e:
                log(f"批次处理失败: {str(e)}")
    
    log(f"哈希值预计算完成，开始多线程比较...")
    log(f"总共需要比较 {len(image_files)} 个文件，预计比较次数: {len(image_files) * (len(image_files) - 1) // 2}")
    
    # 多线程比较函数
    def compare_file_batch(file_indices_batch):
        """批量比较文件的函数"""
        batch_similar_groups = []
        batch_processed = set()
        
        for i in file_indices_batch:
            file1 = image_files[i]
            if file1 in processed or file1 not in all_hashes:
                continue
            
            similar_files = []
            rotation_info = []
            hashes1 = all_hashes[file1]
            
            # 只与后续文件比较，避免重复
            for j in range(i + 1, len(image_files)):
                file2 = image_files[j]
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
                    
                    # 优化的角度组合比较：先进行快速筛选
                    # 首先比较0度角度的哈希值，如果已经相似则无需旋转检测
                    base_h1 = next((h for h in hashes1 if h['angle'] == 0), hashes1[0])
                    base_h2 = next((h for h in hashes2 if h['angle'] == 0), hashes2[0])
                    
                    # 快速检查：先比较基础角度
                    base_dhash_dist = hamming_distance(base_h1['dhash'], base_h2['dhash'])
                    base_phash_dist = hamming_distance(base_h1['phash'], base_h2['phash'])
                    base_ahash_dist = hamming_distance(base_h1['ahash'], base_h2['ahash'])
                    
                    min_distances['dhash'] = base_dhash_dist
                    min_distances['phash'] = base_phash_dist
                    min_distances['ahash'] = base_ahash_dist
                    
                    best_match = {
                        'angle1': base_h1['angle'],
                        'angle2': base_h2['angle'],
                        'dhash_distance': base_dhash_dist,
                        'phash_distance': base_phash_dist,
                        'ahash_distance': base_ahash_dist,
                        'total_distance': base_dhash_dist + base_phash_dist + base_ahash_dist
                    }
                    
                    # 如果基础角度已经足够相似，跳过旋转检测
                    base_similar_count = sum([
                        base_dhash_dist < dhash_threshold,
                        base_phash_dist < phash_threshold,
                        base_ahash_dist < ahash_threshold
                    ])
                    
                    # 只有在基础角度不够相似时才进行旋转检测
                    if base_similar_count < 2:
                        # 进行完整的旋转不变比较
                        for h1 in hashes1:
                            for h2 in hashes2:
                                # 跳过已经比较过的基础角度组合
                                if h1['angle'] == base_h1['angle'] and h2['angle'] == base_h2['angle']:
                                    continue
                                
                                try:
                                    dhash_dist = hamming_distance(h1['dhash'], h2['dhash'])
                                    phash_dist = hamming_distance(h1['phash'], h2['phash'])
                                    ahash_dist = hamming_distance(h1['ahash'], h2['ahash'])
                                    
                                    # 早期退出：如果当前组合明显不如已有最佳匹配，跳过
                                    current_total = dhash_dist + phash_dist + ahash_dist
                                    if current_total >= best_match['total_distance'] * 1.5:
                                        continue
                                    
                                    if dhash_dist < min_distances['dhash']:
                                        min_distances['dhash'] = dhash_dist
                                    if phash_dist < min_distances['phash']:
                                        min_distances['phash'] = phash_dist
                                    if ahash_dist < min_distances['ahash']:
                                        min_distances['ahash'] = ahash_dist
                                    
                                    # 更新最佳匹配
                                    if current_total < best_match['total_distance']:
                                        best_match = {
                                            'angle1': h1['angle'],
                                            'angle2': h2['angle'],
                                            'dhash_distance': dhash_dist,
                                            'phash_distance': phash_dist,
                                            'ahash_distance': ahash_dist,
                                            'total_distance': current_total
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
                
                batch_similar_groups.append(similar_group)
                
                # 标记所有相似文件为已处理
                for file in all_files:
                    batch_processed.add(file)
        
        return batch_similar_groups, batch_processed
    
    # 使用多线程进行比较
    # 将文件索引分批处理，每批处理一定数量的文件
    batch_size = max(10, len(image_files) // 16)  # 16个批次，每批次至少10个文件
    file_indices = list(range(len(image_files)))
    index_batches = [file_indices[i:i+batch_size] for i in range(0, len(file_indices), batch_size)]
    
    log(f"将 {len(image_files)} 个文件分为 {len(index_batches)} 个比较批次，每批次约 {batch_size} 个文件")
    
    # 添加线程锁保护共享变量
    import threading
    rotation_lock = threading.Lock()
    
    # 创建线程池进行并行比较
    with ThreadPoolExecutor(max_workers=min(6, len(index_batches))) as executor:
        # 提交所有批次任务
        future_to_batch = {executor.submit(compare_file_batch, batch): i for i, batch in enumerate(index_batches)}
        
        completed_batches = 0
        total_comparisons = 0
        
        for future in as_completed(future_to_batch):
            try:
                batch_similar_groups, batch_processed = future.result()
                
                # 使用线程锁保护共享变量的修改
                with rotation_lock:
                    similar_groups.extend(batch_similar_groups)
                    processed.update(batch_processed)
                    completed_batches += 1
                
                progress_percent = (completed_batches / len(index_batches)) * 100
                log(f"旋转不变比较进度: {completed_batches}/{len(index_batches)} 个批次 ({progress_percent:.1f}%)，已找到 {len(similar_groups)} 个相似组")
                
            except Exception as e:
                log(f"批次比较失败: {str(e)}")
    
    log(f"旋转不变比较完成！")
    log(f"找到 {len(similar_groups)} 个相似组")
    log(f"平均每个相似组包含 {sum(len(group['files']) for group in similar_groups) / len(similar_groups):.1f} 个文件" if similar_groups else "未找到相似文件")
    return similar_groups