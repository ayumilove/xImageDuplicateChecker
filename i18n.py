# -*- coding: utf-8 -*-
"""
多语言支持模块
支持中文和英文界面
"""

import json
import os

class I18n:
    def __init__(self):
        self.current_language = 'zh'  # 默认中文
        self.translations = {
            "zh": {
                # 窗口和标题
                "window_title": "重复图片检测与查看器",
                "github_url": "https://github.com/ayumilove/xImageDuplicateChecker",
                "copyright": "© 2024 xImageDuplicateChecker - 开源重复图片检测工具",
                
                # 标签页
                "tab_scan": "扫描与检测",
                "tab_view": "结果查看",
                
                # 扫描界面
                "dir_selection": "📂 目录选择",
                "select_dir_btn": "📁 选择扫描目录",
                "no_dir_selected": "未选择目录",
                "detection_params": "⚙️ 检测参数",
                "hash_algorithm": "哈希算法:",
                "similarity_threshold": "相似度阈值:",
                "min_file_size": "最小文件大小(KB):",
                "recursive_scan": "递归扫描:",
                "detect_pure_color": "检测纯色图片:",
                "dhash_threshold": "dHash阈值:",
                "phash_threshold": "pHash阈值:",
                "ahash_threshold": "aHash阈值:",
                "detect_rotation": "识别旋转图片:",
                "rotation_note": "(可识别90°/180°/270°旋转)",
                "operation_control": "🎮 操作控制",
                "start_scan_btn": "🔍 开始扫描",
                "stop_scan_btn": "⏹️ 停止扫描",
                "save_results_btn": "💾 保存结果",
                "load_results_btn": "📂 加载结果",
                "scan_log": "📋 扫描日志",
                
                # 查看界面
                "file_selection": "📁 文件选择",
                "select_json_btn": "📂 选择JSON文件",
                "load_latest_btn": "🔄 加载最新结果",
                "no_file_selected": "未选择文件",
                "statistics": "📊 统计信息",
                "duplicate_groups": "📋 重复组列表",
                "image_preview": "🖼️ 图片预览",
                
                # 菜单
                "menu_file": "文件",
                "menu_language": "语言",
                "menu_help": "帮助",
                "menu_github": "GitHub项目",
                "menu_about": "关于",
                "load_results": "加载结果",
                "save_results": "保存结果",
                
                # 状态信息
                "status_ready": "就绪",
                "selected": "已选择",
                "loaded": "已加载",
                "scanning": "正在扫描...",
                "scan_completed": "扫描完成",
                "scan_stopped": "扫描已停止",
                "loading": "加载中...",
                
                # 对话框标题
                "select_scan_dir_title": "选择要扫描的目录",
                "select_json_file_title": "选择查重结果JSON文件",
                "save_results_title": "保存查重结果",
                
                # 文件类型
                "json_files": "JSON文件",
                "all_files": "所有文件",
                
                # 统计信息
                "total_groups": "总组数",
                "total_images": "总图片数",
                "exact_same": "完全相同",
                "similar_images": "相似图片",
                "pure_color_images": "纯色图片",
                "groups": "组",
                "images": "张",
                "group": "组",
                "duplicate_images": "重复图片总数",
                "loaded_groups": "已加载组数",
                
                # 距离信息
                "dhash_distance": "dHash距离",
                "phash_distance": "pHash距离",
                "ahash_distance": "aHash距离",
                "base_image": "基准图片",
                "distance": "距离",
                
                # 按钮文本
                "copy_path": "复制路径",
                "open_file": "打开文件",
                "open_folder": "打开文件夹",
                
                # 扫描相关
                "start_scanning_dir": "开始扫描目录",
                "scan_error": "扫描过程中出错",
                "scan_failed": "扫描失败",
                "user_stop_scan": "用户请求停止扫描...",
                
                # 错误和警告消息
                "please_select_dir_first": "请先选择扫描目录",
                "dir_not_exist": "选择的目录不存在",
                "error_no_dir_selected": "错误：未选择目录",
                "error_dir_not_exist": "错误：目录不存在",
                "dir_selected": "目录已选择",
                "results_dir_not_exist": "results目录不存在",
                "no_result_files_found": "未找到重复检测结果文件",
                "load_json_failed": "加载JSON文件失败",
                "load_file_failed": "加载文件失败",
                "file_not_exist": "文件不存在",
                "load_failed": "加载失败",
                "no_results_to_save": "没有可保存的结果",
                "results_saved_to": "结果已保存到",
                "save_success": "结果保存成功",
                "save_failed": "保存失败",
                
                # 操作状态
                "path_copied": "路径已复制到剪贴板",
                "file_opened": "文件已打开",
                "folder_opened": "文件夹已打开",
                "cannot_open_file": "无法打开文件",
                "cannot_open_folder": "无法打开文件夹",
                "open_file_failed": "打开文件失败",
                "open_folder_failed": "打开文件夹失败",
                
                # 消息
                "error": "错误",
                "warning": "警告",
                "success": "成功",
                "info": "信息",
            },
            "en": {
                # Window and titles
                "window_title": "Duplicate Image Detector & Viewer",
                "github_url": "https://github.com/ayumilove/xImageDuplicateChecker",
                "copyright": "© 2024 xImageDuplicateChecker - Open Source Duplicate Image Detection Tool",
                
                # Tabs
                "tab_scan": "Scan & Detection",
                "tab_view": "Results View",
                
                # Scan interface
                "dir_selection": "📂 Directory Selection",
                "select_dir_btn": "📁 Select Scan Directory",
                "no_dir_selected": "No directory selected",
                "detection_params": "⚙️ Detection Parameters",
                "hash_algorithm": "Hash Algorithm:",
                "similarity_threshold": "Similarity Threshold:",
                "min_file_size": "Min File Size (KB):",
                "recursive_scan": "Recursive Scan:",
                "detect_pure_color": "Detect Pure Color:",
                "dhash_threshold": "dHash Threshold:",
                "phash_threshold": "pHash Threshold:",
                "ahash_threshold": "aHash Threshold:",
                "detect_rotation": "Detect Rotation:",
                "rotation_note": "(Detects 90°/180°/270° rotations)",
                "operation_control": "🎮 Operation Control",
                "start_scan_btn": "🔍 Start Scan",
                "stop_scan_btn": "⏹️ Stop Scan",
                "save_results_btn": "💾 Save Results",
                "load_results_btn": "📂 Load Results",
                "scan_log": "📋 Scan Log",
                
                # View interface
                "file_selection": "📁 File Selection",
                "select_json_btn": "📂 Select JSON File",
                "load_latest_btn": "🔄 Load Latest Results",
                "no_file_selected": "No file selected",
                "statistics": "📊 Statistics",
                "duplicate_groups": "📋 Duplicate Groups",
                "image_preview": "🖼️ Image Preview",
                
                # Menu
                "menu_file": "File",
                "menu_language": "Language",
                "menu_help": "Help",
                "menu_github": "GitHub Project",
                "menu_about": "About",
                "load_results": "Load Results",
                "save_results": "Save Results",
                
                # Status information
                "status_ready": "Ready",
                "selected": "Selected",
                "loaded": "Loaded",
                "scanning": "Scanning...",
                "scan_completed": "Scan Completed",
                "scan_stopped": "Scan Stopped",
                "loading": "Loading...",
                
                # Dialog titles
                "select_scan_dir_title": "Select Directory to Scan",
                "select_json_file_title": "Select Duplicate Detection JSON File",
                "save_results_title": "Save Duplicate Detection Results",
                
                # File types
                "json_files": "JSON Files",
                "all_files": "All Files",
                
                # Statistics
                "total_groups": "Total Groups",
                "total_images": "Total Images",
                "exact_same": "Exact Same",
                "similar_images": "Similar Images",
                "pure_color_images": "Pure Color Images",
                "groups": " groups",
                "images": " images",
                "group": "Group ",
                "duplicate_images": "Total Duplicate Images",
                "loaded_groups": "Loaded Groups",
                
                # Distance information
                "dhash_distance": "dHash Distance",
                "phash_distance": "pHash Distance",
                "ahash_distance": "aHash Distance",
                "base_image": "Base Image",
                "distance": "Distance",
                
                # Button text
                "copy_path": "Copy Path",
                "open_file": "Open File",
                "open_folder": "Open Folder",
                
                # Scan related
                "start_scanning_dir": "Start scanning directory",
                "scan_error": "Error during scanning",
                "scan_failed": "Scan failed",
                "user_stop_scan": "User requested to stop scanning...",
                
                # Error and warning messages
                "please_select_dir_first": "Please select a scan directory first",
                "dir_not_exist": "Selected directory does not exist",
                "error_no_dir_selected": "Error: No directory selected",
                "error_dir_not_exist": "Error: Directory does not exist",
                "dir_selected": "Directory selected",
                "results_dir_not_exist": "Results directory does not exist",
                "no_result_files_found": "No duplicate detection result files found",
                "load_json_failed": "Failed to load JSON file",
                "load_file_failed": "Failed to load file",
                "file_not_exist": "File does not exist",
                "load_failed": "Load failed",
                "no_results_to_save": "No results to save",
                "results_saved_to": "Results saved to",
                "save_success": "Results saved successfully",
                "save_failed": "Save failed",
                
                # Operation status
                "path_copied": "Path copied to clipboard",
                "file_opened": "File opened",
                "folder_opened": "Folder opened",
                "cannot_open_file": "Cannot open file",
                "cannot_open_folder": "Cannot open folder",
                "open_file_failed": "Failed to open file",
                "open_folder_failed": "Failed to open folder",
                
                # Messages
                "error": "Error",
                "warning": "Warning",
                "success": "Success",
                "info": "Info",
            }
        }
    
    def get_available_languages(self):
        """获取可用语言列表"""
        return {
            'zh': '中文',
            'en': 'English'
        }
    
    def set_language(self, language_code):
        """设置当前语言"""
        if language_code in self.translations:
            self.current_language = language_code
            return True
        return False
    
    def get_text(self, key, default=None):
        """获取翻译文本"""
        if default is None:
            default = key
        
        return self.translations.get(self.current_language, {}).get(key, default)
    
    def __call__(self, key, default=None):
        """使翻译对象可调用"""
        return self.get_text(key, default)

# 创建全局翻译实例
i18n = I18n()

# 创建便捷的翻译函数
_ = i18n