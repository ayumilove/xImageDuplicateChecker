#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际化(i18n)支持模块
提供多语言界面支持
"""

import json
import os
from typing import Dict, Any

class I18n:
    def __init__(self, default_language='zh_CN'):
        self.current_language = default_language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """加载所有语言翻译文件"""
        # 中文翻译
        self.translations['zh_CN'] = {
            # 窗口标题
            'window_title': '重复图片检测与查看器 v1.0.0',
            'github_url': 'https://github.com/ayumilove/xImageDuplicateChecker',
            
            # 标签页
            'tab_scan': '🔍 扫描与检测',
            'tab_view': '📊 结果查看',
            
            # 扫描界面
            'dir_selection': '📂 目录选择',
            'select_dir_btn': '📁 选择扫描目录',
            'no_dir_selected': '未选择目录',
            'detection_params': '⚙️ 检测参数',
            'recursive_scan': '递归扫描:',
            'detect_pure_color': '检测纯色图片:',
            'dhash_threshold': 'dHash阈值:',
            'phash_threshold': 'pHash阈值:',
            'ahash_threshold': 'aHash阈值:',
            'rotation_detection': '旋转识别:',
            'rotation_tip': '(可识别90°/180°/270°旋转)',
            'start_scan': '🚀 开始扫描',
            'stop_scan': '⏹️ 停止扫描',
            'scan_log': '📋 扫描日志',
            
            # 查看界面
            'file_selection': '📁 文件选择',
            'load_results': '📂 加载结果文件',
            'group_navigation': '📑 分组导航',
            'prev_group': '⬅️ 上一组',
            'next_group': '➡️ 下一组',
            'group_info': '分组信息',
            'image_preview': '🖼️ 图片预览',
            'file_operations': '📋 文件操作',
            'copy_path': '📋 复制路径',
            'open_file': '📁 打开文件',
            'open_folder': '📂 打开文件夹',
            'delete_file': '🗑️ 删除文件',
            
            # 菜单
            'menu_file': '文件',
            'menu_language': '语言',
            'menu_help': '帮助',
            'menu_about': '关于',
            'menu_github': 'GitHub项目',
            
            # 状态信息
            'status_ready': '就绪',
            'status_scanning': '扫描中...',
            'status_loading': '加载中...',
            'status_completed': '完成',
            
            # 消息
            'select_directory_first': '请先选择扫描目录',
            'scan_completed': '扫描完成',
            'scan_stopped': '扫描已停止',
            'file_copied': '文件路径已复制到剪贴板',
            'file_opened': '文件已打开',
            'folder_opened': '文件夹已打开',
            'file_deleted': '文件已删除',
            'no_results_loaded': '未加载结果文件',
            'no_groups_found': '未找到重复组',
            'load_results_first': '请先加载结果文件',
            
            # 版权信息
            'copyright': '© 2024 xImageDuplicateChecker | MIT License | 开源项目',
        }
        
        # 英文翻译
        self.translations['en_US'] = {
            # 窗口标题
            'window_title': 'Duplicate Image Detector & Viewer v1.0.0',
            'github_url': 'https://github.com/your-username/xImageDuplicateChecker',
            
            # 标签页
            'tab_scan': '🔍 Scan & Detect',
            'tab_view': '📊 View Results',
            
            # 扫描界面
            'dir_selection': '📂 Directory Selection',
            'select_dir_btn': '📁 Select Scan Directory',
            'no_dir_selected': 'No directory selected',
            'detection_params': '⚙️ Detection Parameters',
            'recursive_scan': 'Recursive Scan:',
            'detect_pure_color': 'Detect Pure Color:',
            'dhash_threshold': 'dHash Threshold:',
            'phash_threshold': 'pHash Threshold:',
            'ahash_threshold': 'aHash Threshold:',
            'rotation_detection': 'Rotation Detection:',
            'rotation_tip': '(Detect 90°/180°/270° rotation)',
            'start_scan': '🚀 Start Scan',
            'stop_scan': '⏹️ Stop Scan',
            'scan_log': '📋 Scan Log',
            
            # 查看界面
            'file_selection': '📁 File Selection',
            'load_results': '📂 Load Results File',
            'group_navigation': '📑 Group Navigation',
            'prev_group': '⬅️ Previous',
            'next_group': '➡️ Next',
            'group_info': 'Group Information',
            'image_preview': '🖼️ Image Preview',
            'file_operations': '📋 File Operations',
            'copy_path': '📋 Copy Path',
            'open_file': '📁 Open File',
            'open_folder': '📂 Open Folder',
            'delete_file': '🗑️ Delete File',
            
            # 菜单
            'menu_file': 'File',
            'menu_language': 'Language',
            'menu_help': 'Help',
            'menu_about': 'About',
            'menu_github': 'GitHub Project',
            
            # 状态信息
            'status_ready': 'Ready',
            'status_scanning': 'Scanning...',
            'status_loading': 'Loading...',
            'status_completed': 'Completed',
            
            # 消息
            'select_directory_first': 'Please select a scan directory first',
            'scan_completed': 'Scan completed',
            'scan_stopped': 'Scan stopped',
            'file_copied': 'File path copied to clipboard',
            'file_opened': 'File opened',
            'folder_opened': 'Folder opened',
            'file_deleted': 'File deleted',
            'no_results_loaded': 'No results file loaded',
            'no_groups_found': 'No duplicate groups found',
            'load_results_first': 'Please load results file first',
            
            # 版权信息
            'copyright': '© 2024 xImageDuplicateChecker | MIT License | Open Source Project',
        }
    
    def set_language(self, language_code: str):
        """设置当前语言"""
        if language_code in self.translations:
            self.current_language = language_code
            return True
        return False
    
    def get_text(self, key: str, default: str = None) -> str:
        """获取翻译文本"""
        if self.current_language in self.translations:
            return self.translations[self.current_language].get(key, default or key)
        return default or key
    
    def get_available_languages(self) -> Dict[str, str]:
        """获取可用语言列表"""
        return {
            'zh_CN': '中文 (简体)',
            'en_US': 'English'
        }
    
    def get_current_language(self) -> str:
        """获取当前语言代码"""
        return self.current_language

# 全局i18n实例
i18n = I18n()

# 便捷函数
def _(key: str, default: str = None) -> str:
    """获取翻译文本的便捷函数"""
    return i18n.get_text(key, default)