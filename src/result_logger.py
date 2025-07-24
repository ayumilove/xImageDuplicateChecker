# -*- coding: utf-8 -*-
"""
结果记录模块

提供将重复图片信息记录到本地文件的功能
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class ResultLogger:
    """
    结果记录器，用于将重复图片信息记录到本地文件
    """
    
    def __init__(self, output_dir: str = "results"):
        """
        初始化结果记录器
        
        Args:
            output_dir: 输出目录，默认为"results"
        """
        self.output_dir = output_dir
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _get_timestamp(self) -> str:
        """
        获取当前时间戳字符串
        
        Returns:
            格式化的时间戳字符串
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_to_csv(self, duplicate_groups: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        将重复图片组保存为CSV文件
        
        Args:
            duplicate_groups: 重复图片组列表，每组包含重复原因和文件列表
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            filename = f"duplicates_{self._get_timestamp()}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['group_id', 'duplicate_reason', 'file_path']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for group_id, group in enumerate(duplicate_groups, 1):
                reason = group.get('reason', '未知')
                files = group.get('files', [])
                
                for file_path in files:
                    writer.writerow({
                        'group_id': group_id,
                        'duplicate_reason': reason,
                        'file_path': file_path
                    })
        
        return filepath
    
    def save_to_json(self, duplicate_groups: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        将重复图片组保存为JSON文件
        
        Args:
            duplicate_groups: 重复图片组列表，每组包含重复原因和文件列表
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            filename = f"duplicates_{self._get_timestamp()}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 为每个组添加组ID
        result = []
        for group_id, group in enumerate(duplicate_groups, 1):
            group_with_id = group.copy()
            group_with_id['group_id'] = group_id
            result.append(group_with_id)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(result, jsonfile, ensure_ascii=False, indent=2)
        
        return filepath
    
    def save_summary(self, stats: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存查重统计摘要
        
        Args:
            stats: 统计信息字典
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            filename = f"summary_{self._get_timestamp()}.txt"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"图片查重统计摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"总处理图片数: {stats.get('total_images', 0)}\n")
            f.write(f"重复图片组数: {stats.get('duplicate_groups', 0)}\n")
            f.write(f"重复图片总数: {stats.get('duplicate_images', 0)}\n")
            
            # 添加纯色图片统计
            if 'pure_color_images' in stats and stats['pure_color_images'] > 0:
                f.write(f"纯色图片数: {stats.get('pure_color_images', 0)}\n")
            
            f.write("\n")
            
            # 按重复原因统计
            f.write("按重复原因统计:\n")
            reasons = stats.get('reasons', {})
            for reason, count in reasons.items():
                f.write(f"  - {reason}: {count}组\n")
            
            f.write("\n" + "=" * 50 + "\n")
        
        return filepath