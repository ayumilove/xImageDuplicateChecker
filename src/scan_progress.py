# -*- coding: utf-8 -*-
"""
扫描进度管理模块

提供扫描进度的保存和恢复功能，支持断点续传
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path


class ScanProgress:
    """
    扫描进度管理器，用于保存和恢复扫描进度
    """
    
    def __init__(self, progress_dir: str = "progress"):
        """
        初始化进度管理器
        
        Args:
            progress_dir: 进度文件保存目录
        """
        self.progress_dir = progress_dir
        
        # 确保进度目录存在
        if not os.path.exists(progress_dir):
            os.makedirs(progress_dir)
    
    def _get_progress_file_path(self, scan_directory: str) -> str:
        """
        获取指定扫描目录的进度文件路径
        
        Args:
            scan_directory: 扫描目录路径
            
        Returns:
            进度文件路径
        """
        # 将目录路径转换为安全的文件名
        safe_name = scan_directory.replace(':', '_').replace('\\', '_').replace('/', '_')
        safe_name = safe_name.replace(' ', '_').replace('..', '_')
        return os.path.join(self.progress_dir, f"scan_progress_{safe_name}.json")
    
    def save_progress(self, 
                     scan_directory: str,
                     scan_config: Dict[str, Any],
                     current_stage: str,
                     processed_files: Set[str],
                     completed_stages: List[str],
                     file_hash_results: Dict[str, str] = None,
                     phash_results: Dict[str, Dict[str, str]] = None,
                     duplicate_groups: List[Dict[str, Any]] = None,
                     pure_color_images: List[str] = None,
                     stats: Dict[str, Any] = None,
                     group_comparison_progress: Dict[str, Any] = None) -> str:
        """
        保存扫描进度
        
        Args:
            scan_directory: 扫描目录
            scan_config: 扫描配置
            current_stage: 当前扫描阶段
            processed_files: 已处理的文件集合
            completed_stages: 已完成的阶段列表
            file_hash_results: 文件哈希结果
            phash_results: 感知哈希结果
            duplicate_groups: 已发现的重复组
            pure_color_images: 纯色图片列表
            stats: 统计信息
            group_comparison_progress: 分组比较进度
            
        Returns:
            进度文件路径
        """
        progress_file = self._get_progress_file_path(scan_directory)
        
        progress_data = {
            'scan_directory': scan_directory,
            'scan_config': scan_config,
            'current_stage': current_stage,
            'processed_files': list(processed_files),
            'completed_stages': completed_stages,
            'file_hash_results': file_hash_results or {},
            'phash_results': phash_results or {},
            'duplicate_groups': duplicate_groups or [],
            'pure_color_images': pure_color_images or [],
            'stats': stats or {},
            'group_comparison_progress': group_comparison_progress or {},
            'timestamp': datetime.now().isoformat(),
            'last_update': time.time()
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        return progress_file
    
    def load_progress(self, scan_directory: str) -> Optional[Dict[str, Any]]:
        """
        加载扫描进度
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            进度数据字典，如果没有找到则返回None
        """
        progress_file = self._get_progress_file_path(scan_directory)
        
        if not os.path.exists(progress_file):
            return None
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # 验证进度文件的有效性
            if not self._validate_progress_data(progress_data):
                return None
            
            return progress_data
        except Exception as e:
            print(f"加载进度文件失败: {e}")
            return None
    
    def _validate_progress_data(self, progress_data: Dict[str, Any]) -> bool:
        """
        验证进度数据的有效性
        
        Args:
            progress_data: 进度数据
            
        Returns:
            是否有效
        """
        required_fields = [
            'scan_directory', 'scan_config', 'current_stage',
            'processed_files', 'completed_stages', 'timestamp'
        ]
        
        for field in required_fields:
            if field not in progress_data:
                return False
        
        # 检查时间戳是否过期（超过7天认为过期）
        try:
            last_update = progress_data.get('last_update', 0)
            if time.time() - last_update > 7 * 24 * 3600:  # 7天
                return False
        except:
            return False
        
        return True
    
    def has_incomplete_scan(self, scan_directory: str) -> bool:
        """
        检查是否有未完成的扫描
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            是否有未完成的扫描
        """
        progress_data = self.load_progress(scan_directory)
        if not progress_data:
            return False
        
        # 检查是否已完成所有阶段
        completed_stages = progress_data.get('completed_stages', [])
        all_stages = ['scan_files', 'file_hash', 'pure_color', 'perceptual_hash', 'similarity_check']
        
        return len(completed_stages) < len(all_stages)
    
    def get_progress_info(self, scan_directory: str) -> Optional[Dict[str, Any]]:
        """
        获取进度信息摘要
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            进度信息摘要
        """
        progress_data = self.load_progress(scan_directory)
        if not progress_data:
            return None
        
        completed_stages = progress_data.get('completed_stages', [])
        current_stage = progress_data.get('current_stage', '')
        processed_files = progress_data.get('processed_files', [])
        stats = progress_data.get('stats', {})
        timestamp = progress_data.get('timestamp', '')
        
        all_stages = ['scan_files', 'file_hash', 'pure_color', 'perceptual_hash', 'similarity_check']
        progress_percent = (len(completed_stages) / len(all_stages)) * 100
        
        return {
            'scan_directory': scan_directory,
            'current_stage': current_stage,
            'completed_stages': completed_stages,
            'progress_percent': progress_percent,
            'processed_files_count': len(processed_files),
            'stats': stats,
            'timestamp': timestamp,
            'stage_names': {
                'scan_files': '扫描文件',
                'file_hash': '计算文件哈希',
                'pure_color': '检测纯色图片',
                'perceptual_hash': '计算感知哈希',
                'similarity_check': '相似度检查'
            }
        }
    
    def clear_progress(self, scan_directory: str) -> bool:
        """
        清除指定目录的进度文件
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            是否成功清除
        """
        progress_file = self._get_progress_file_path(scan_directory)
        
        try:
            if os.path.exists(progress_file):
                os.remove(progress_file)
                return True
            return True
        except Exception as e:
            print(f"清除进度文件失败: {e}")
            return False
    
    def list_incomplete_scans(self) -> List[Dict[str, Any]]:
        """
        列出所有未完成的扫描
        
        Returns:
            未完成扫描的信息列表
        """
        incomplete_scans = []
        
        if not os.path.exists(self.progress_dir):
            return incomplete_scans
        
        for filename in os.listdir(self.progress_dir):
            if filename.startswith('scan_progress_') and filename.endswith('.json'):
                progress_file = os.path.join(self.progress_dir, filename)
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                    
                    if self._validate_progress_data(progress_data):
                        scan_directory = progress_data.get('scan_directory', '')
                        if self.has_incomplete_scan(scan_directory):
                            info = self.get_progress_info(scan_directory)
                            if info:
                                incomplete_scans.append(info)
                except Exception as e:
                    print(f"读取进度文件失败 {filename}: {e}")
        
        return incomplete_scans