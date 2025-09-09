#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复图片检测与查看器
集成了目录扫描、重复检测和结果查看功能的完整桌面应用

Copyright (c) 2024 xImageDuplicateChecker
Licensed under MIT License
Author: Xing
Version: 1.0.0
GitHub: https://github.com/ayumilove/xImageDuplicateChecker
"""

import tkinter as tk
from tkinter import filedialog, messagebox
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    pass  # 未安装ttkbootstrap，将使用标准tkinter
    from tkinter import ttk
import json
import os
from PIL import Image, ImageTk
import threading
import subprocess
import platform
import queue
import time
import webbrowser
from cpp_hash_lib.cpp_duplicate_checker import CppDuplicateChecker
from i18n import I18n
from memory_optimization_config import get_memory_optimized_config, print_memory_recommendations

# 初始化多语言支持
i18n = I18n()
_ = i18n.get_text

class IntegratedDuplicateApp:
    def __init__(self, root):
        self.root = root
        self.root.title(_("window_title"))
        self.root.geometry("1400x900")
        
        # 使用全局的多语言支持实例
        self.i18n = i18n
        
        # 设置窗口图标和最小尺寸
        self.root.minsize(1200, 800)
        
        # GitHub项目地址
        self.github_url = _("github_url")
        
        # 版权信息
        self.copyright_info = _("copyright")
        
        # 数据存储
        self.duplicate_data = []
        self.current_group_index = 0
        self.image_cache = {}
        self.loading_threads = 0
        self.max_concurrent_loads = 3
        self.load_queue = queue.Queue()
        self.queue_processor_running = False
        
        # 分页相关
        self.current_page = 0
        self.images_per_page = 20  # 每页显示20张图片
        self.total_pages = 0
        
        # 扫描相关
        self.scan_directory = ""
        self.is_scanning = False
        self.checker = None
        
        # 内存优化配置
        self.memory_config = get_memory_optimized_config()
        # 应用内存优化配置
        # 内存优化建议
        
        # 线程监控相关
        self.thread_monitor_enabled = True
        self.thread_stats = {
            'hash_threads': 0,
            'compare_threads': 0,
            'pure_color_threads': 0,
            'total_threads': 0,
            'active_tasks': 0,
            'completed_tasks': 0,
            'thread_pool_status': 'idle',
            'current_stage': 'idle'
        }
        self.monitor_update_timer = None
        self._last_log_message = ''  # 保存最近的日志消息
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建菜单栏
        self.setup_menu()
        
        # 创建主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 第一个标签页：扫描与检测
        self.scan_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scan_frame, text=_("tab_scan"))
        self.setup_scan_ui()
        
        # 第二个标签页：结果查看
        self.view_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.view_frame, text=_("tab_view"))
        self.setup_view_ui()
        
        # 第三个标签页：线程监控
        self.monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.monitor_frame, text="线程监控")
        self.setup_monitor_ui()
        
        # 底部版权信息栏
        copyright_frame = ttk.Frame(main_container)
        copyright_frame.pack(fill=tk.X, pady=(5, 0))
        
        copyright_label = ttk.Label(copyright_frame, text=self.copyright_info, 
                                   font=('Arial', 8), foreground='#6c757d')
        copyright_label.pack(side=tk.RIGHT)
        
        # 启动线程监控
        if self.thread_monitor_enabled:
            self.start_monitor_update()
        
    def setup_monitor_ui(self):
        """设置线程监控界面"""
        main_frame = ttk.Frame(self.monitor_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 监控控制区域
        control_frame = ttk.LabelFrame(main_frame, text="监控控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.monitor_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="启用线程监控", 
                       variable=self.monitor_enabled_var,
                       command=self.toggle_thread_monitor).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(control_frame, text="更新间隔: 500ms", 
                 font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT)
        
        # 线程池状态区域
        pool_frame = ttk.LabelFrame(main_frame, text="线程池状态", padding="10")
        pool_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：总体状态
        status_row1 = ttk.Frame(pool_frame)
        status_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_row1, text="线程池状态:").pack(side=tk.LEFT, padx=(0, 5))
        self.pool_status_label = ttk.Label(status_row1, text="空闲", foreground="green")
        self.pool_status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_row1, text="总线程数:").pack(side=tk.LEFT, padx=(0, 5))
        self.total_threads_label = ttk.Label(status_row1, text="0")
        self.total_threads_label.pack(side=tk.LEFT)
        
        # 第二行：任务状态
        status_row2 = ttk.Frame(pool_frame)
        status_row2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_row2, text="活跃任务:").pack(side=tk.LEFT, padx=(0, 5))
        self.active_tasks_label = ttk.Label(status_row2, text="0")
        self.active_tasks_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_row2, text="已完成任务:").pack(side=tk.LEFT, padx=(0, 5))
        self.completed_tasks_label = ttk.Label(status_row2, text="0")
        self.completed_tasks_label.pack(side=tk.LEFT)
        
        # 线程详情区域
        details_frame = ttk.LabelFrame(main_frame, text="线程详情", padding="10")
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 哈希计算线程
        hash_row = ttk.Frame(details_frame)
        hash_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(hash_row, text="哈希计算线程:").pack(side=tk.LEFT, padx=(0, 5))
        self.hash_threads_label = ttk.Label(hash_row, text="0")
        self.hash_threads_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.hash_progress = ttk.Progressbar(hash_row, mode='determinate', length=150)
        self.hash_progress.pack(side=tk.LEFT, padx=(0, 10))
        
        self.hash_progress_label = ttk.Label(hash_row, text="0%")
        self.hash_progress_label.pack(side=tk.LEFT)
        
        # 比较计算线程
        compare_row = ttk.Frame(details_frame)
        compare_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(compare_row, text="比较计算线程:").pack(side=tk.LEFT, padx=(0, 5))
        self.compare_threads_label = ttk.Label(compare_row, text="0")
        self.compare_threads_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.compare_progress = ttk.Progressbar(compare_row, mode='determinate', length=150)
        self.compare_progress.pack(side=tk.LEFT, padx=(0, 10))
        
        self.compare_progress_label = ttk.Label(compare_row, text="0%")
        self.compare_progress_label.pack(side=tk.LEFT)
        
        # 纯色检测线程
        pure_color_row = ttk.Frame(details_frame)
        pure_color_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(pure_color_row, text="纯色检测线程:").pack(side=tk.LEFT, padx=(0, 5))
        self.pure_color_threads_label = ttk.Label(pure_color_row, text="0")
        self.pure_color_threads_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.pure_color_progress = ttk.Progressbar(pure_color_row, mode='determinate', length=150)
        self.pure_color_progress.pack(side=tk.LEFT, padx=(0, 10))
        
        self.pure_color_progress_label = ttk.Label(pure_color_row, text="0%")
        self.pure_color_progress_label.pack(side=tk.LEFT)
        
        # 实时日志区域
        log_frame = ttk.LabelFrame(main_frame, text="线程活动日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.thread_log_text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.thread_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        thread_log_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.thread_log_text.yview)
        thread_log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.thread_log_text.configure(yscrollcommand=thread_log_scrollbar.set)
        
        # 清除日志按钮
        clear_frame = ttk.Frame(log_frame)
        clear_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(clear_frame, text="清除日志", command=self.clear_thread_log).pack(side=tk.RIGHT)
        
        # 状态信息
        status_info_frame = ttk.Frame(log_frame)
        status_info_frame.pack(fill=tk.X, pady=(5, 0))
        
        status_label = ttk.Label(status_info_frame, text=_("status_ready"), 
                                font=('Arial', 8), foreground='#28a745')
        status_label.pack(side=tk.LEFT)
        self.status_label = status_label
        
    def setup_menu(self):
        """设置菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_file"), menu=file_menu)
        file_menu.add_command(label=_("load_results"), command=self.load_json_file)
        file_menu.add_command(label=_("save_results"), command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="管理扫描进度", command=self.manage_scan_progress)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # 语言菜单
        language_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_language"), menu=language_menu)
        
        available_languages = i18n.get_available_languages()
        for lang_code, lang_name in available_languages.items():
            language_menu.add_command(
                label=lang_name,
                command=lambda code=lang_code: self.change_language(code)
            )
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_help"), menu=help_menu)
        help_menu.add_command(label=_("menu_github"), command=self.open_github)
        help_menu.add_separator()
        help_menu.add_command(label=_("menu_about"), command=self.show_about)
    
    def change_language(self, language_code):
        """切换语言"""
        if i18n.set_language(language_code):
            # 更新界面文本
            self.update_ui_texts()
            self.update_status(_("status_ready"), "success")
    
    def update_ui_texts(self):
        """更新界面文本"""
        # 更新窗口标题
        self.root.title(_("window_title"))
        
        # 更新版权信息
        self.copyright_info = _("copyright")
        
        # 重新创建界面（简单方法）
        # 在实际应用中，可以更精细地更新每个控件的文本
        messagebox.showinfo("Language Changed", "Language has been changed. Please restart the application to see all changes.")
    
    def open_github(self):
        """打开GitHub项目页面"""
        webbrowser.open("https://github.com/ayumilove/xImageDuplicateChecker")
        self.update_status("GitHub项目页面已打开", "info")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = f"""
重复图片检测与查看器 v1.0.0

一个开源的重复图片检测工具，支持：
• 多种哈希算法检测
• 旋转图片识别
• 纯色图片检测
• 直观的图形界面
• 多语言支持
• 断点续传功能

GitHub: {self.github_url}

© 2024 xImageDuplicateChecker
MIT License
        """
        messagebox.showinfo(_("menu_about"), about_text)
    
    def manage_scan_progress(self):
        """管理扫描进度"""
        try:
            from src.scan_progress import ScanProgress
            progress_manager = ScanProgress()
            incomplete_scans = progress_manager.list_incomplete_scans()
            
            if not incomplete_scans:
                messagebox.showinfo("扫描进度管理", "当前没有未完成的扫描。")
                return
            
            # 创建进度管理窗口
            progress_window = tk.Toplevel(self.root)
            progress_window.title("扫描进度管理")
            progress_window.geometry("600x400")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # 主框架
            main_frame = ttk.Frame(progress_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 说明标签
            info_label = ttk.Label(main_frame, text="以下是未完成的扫描，您可以选择清除它们：")
            info_label.pack(anchor=tk.W, pady=(0, 10))
            
            # 创建列表框显示未完成的扫描
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # 列表框和滚动条
            scan_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE)
            scan_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=scan_listbox.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            scan_listbox.configure(yscrollcommand=scrollbar.set)
            
            # 填充扫描信息
            scan_directories = []
            for scan_info in incomplete_scans:
                directory = scan_info.get('scan_directory', 'Unknown')
                timestamp = scan_info.get('timestamp', 'Unknown')
                completed_stages = scan_info.get('completed_stages', [])
                progress_percent = scan_info.get('progress_percent', 0)
                
                display_text = f"目录: {directory} | 时间: {timestamp} | 进度: {progress_percent:.1f}% | 已完成: {', '.join(completed_stages) if completed_stages else '无'}"
                scan_listbox.insert(tk.END, display_text)
                scan_directories.append(directory)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            def clear_selected():
                """清除选中的扫描进度"""
                selected_indices = scan_listbox.curselection()
                if not selected_indices:
                    messagebox.showwarning("警告", "请先选择要清除的扫描。")
                    return
                
                selected_directories = [scan_directories[i] for i in selected_indices]
                
                # 确认对话框
                if messagebox.askyesno("确认清除", f"确定要清除 {len(selected_directories)} 个扫描进度吗？\n\n此操作不可撤销。"):
                    cleared_count = 0
                    for directory in selected_directories:
                        try:
                            progress_manager.clear_progress(directory)
                            cleared_count += 1
                        except Exception as e:
                            self.log_message(f"清除扫描进度 {directory} 时出错: {str(e)}")
                    
                    messagebox.showinfo("清除完成", f"已成功清除 {cleared_count} 个扫描进度。")
                    progress_window.destroy()
            
            def clear_all():
                """清除所有扫描进度"""
                if messagebox.askyesno("确认清除", f"确定要清除所有 {len(scan_directories)} 个扫描进度吗？\n\n此操作不可撤销。"):
                    cleared_count = 0
                    for directory in scan_directories:
                        try:
                            progress_manager.clear_progress(directory)
                            cleared_count += 1
                        except Exception as e:
                            self.log_message(f"清除扫描进度 {directory} 时出错: {str(e)}")
                    
                    messagebox.showinfo("清除完成", f"已成功清除 {cleared_count} 个扫描进度。")
                    progress_window.destroy()
            
            # 按钮
            ttk.Button(button_frame, text="清除选中", command=clear_selected).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="清除全部", command=clear_all).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="关闭", command=progress_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("错误", f"管理扫描进度时出错: {str(e)}")
            self.log_message(f"管理扫描进度时出错: {str(e)}")
        
    def setup_scan_ui(self):
        """设置扫描界面"""
        main_frame = ttk.Frame(self.scan_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 目录选择区域
        dir_frame = ttk.LabelFrame(main_frame, text=_("dir_selection"), padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        try:
            ttk.Button(dir_frame, text=_("select_dir_btn"), command=self.select_directory, bootstyle="primary").pack(side=tk.LEFT, padx=(0, 10))
        except:
            ttk.Button(dir_frame, text=_("select_dir_btn"), command=self.select_directory).pack(side=tk.LEFT, padx=(0, 10))
            
        self.dir_label = ttk.Label(dir_frame, text=_("no_dir_selected"))
        self.dir_label.pack(side=tk.LEFT)
        
        # 参数设置区域
        params_frame = ttk.LabelFrame(main_frame, text=_("detection_params"), padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行参数
        row1 = ttk.Frame(params_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text=_("recursive_scan")).pack(side=tk.LEFT, padx=(0, 5))
        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, variable=self.recursive_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row1, text=_("detect_pure_color")).pack(side=tk.LEFT, padx=(0, 5))
        self.pure_color_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row1, variable=self.pure_color_var).pack(side=tk.LEFT)
        
        # 检测方式控制行
        detection_row = ttk.Frame(params_frame)
        detection_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(detection_row, text="完全一致检测").pack(side=tk.LEFT, padx=(0, 5))
        self.exact_match_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(detection_row, variable=self.exact_match_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(detection_row, text="感知哈希检测").pack(side=tk.LEFT, padx=(0, 5))
        self.perceptual_hash_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(detection_row, variable=self.perceptual_hash_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(detection_row, text="(dHash+pHash+aHash)", font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT)
        
        # 第二行参数
        row2 = ttk.Frame(params_frame)
        row2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row2, text=_("dhash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.dhash_var = tk.IntVar(value=12)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.dhash_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row2, text=_("phash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.phash_var = tk.IntVar(value=8)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.phash_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row2, text=_("ahash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.ahash_var = tk.IntVar(value=8)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.ahash_var).pack(side=tk.LEFT)
        
        # 第三行参数
        row3 = ttk.Frame(params_frame)
        row3.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row3, text=_("detect_rotation")).pack(side=tk.LEFT, padx=(0, 5))
        self.detect_rotation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, variable=self.detect_rotation_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text=_("rotation_note"), font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT)
        
        # 第四行参数 - 增强相似度检测
        row4 = ttk.Frame(params_frame)
        row4.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row4, text="增强相似度检测").pack(side=tk.LEFT, padx=(0, 5))
        self.enhanced_similarity_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row4, variable=self.enhanced_similarity_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row4, text="支持旋转+分辨率变化检测", font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row4, text="置信度阈值").pack(side=tk.LEFT, padx=(0, 5))
        self.confidence_var = tk.DoubleVar(value=0.6)
        ttk.Spinbox(row4, from_=0.1, to=1.0, increment=0.1, width=5, textvariable=self.confidence_var, format="%.1f").pack(side=tk.LEFT)
        
        # 第五行参数 - LSH索引优化
        row5 = ttk.Frame(params_frame)
        row5.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row5, text="启用LSH索引").pack(side=tk.LEFT, padx=(0, 5))
        self.enable_lsh_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row5, variable=self.enable_lsh_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row5, text="大规模数据加速", font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row5, text="LSH阈值").pack(side=tk.LEFT, padx=(0, 5))
        self.lsh_threshold_var = tk.IntVar(value=500000)
        ttk.Spinbox(row5, from_=10000, to=2000000, increment=10000, width=8, textvariable=self.lsh_threshold_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row5, text="哈希表数").pack(side=tk.LEFT, padx=(0, 5))
        self.lsh_tables_var = tk.IntVar(value=10)
        ttk.Spinbox(row5, from_=5, to=20, width=3, textvariable=self.lsh_tables_var).pack(side=tk.LEFT)
        
        # 控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        try:
            # 使用ttkbootstrap的按钮样式
            self.scan_button = ttk.Button(control_frame, text=_("start_scan_btn"), command=self.start_scan, bootstyle="success")
            self.stop_button = ttk.Button(control_frame, text=_("stop_scan_btn"), command=self.stop_scan, state=tk.DISABLED, bootstyle="danger")
        except:
            # 标准tkinter按钮
            self.scan_button = ttk.Button(control_frame, text=_("start_scan_btn"), command=self.start_scan)
            self.stop_button = ttk.Button(control_frame, text=_("stop_scan_btn"), command=self.stop_scan, state=tk.DISABLED)
            
        self.scan_button.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 进度条
        try:
            self.progress = ttk.Progressbar(control_frame, mode='indeterminate', bootstyle="info-striped")
        except:
            self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 日志输出区域
        log_frame = ttk.LabelFrame(main_frame, text=_("scan_log"), padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
    def setup_view_ui(self):
        """设置查看界面"""
        main_frame = ttk.Frame(self.view_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text=_("file_selection"), padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        try:
            # 使用ttkbootstrap的按钮样式
            ttk.Button(file_frame, text=_("select_json_btn"), command=self.load_json_file, bootstyle="primary").pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(file_frame, text=_("load_latest_btn"), command=self.load_latest_result, bootstyle="info").pack(side=tk.LEFT, padx=(0, 10))
        except:
            # 标准tkinter按钮
            ttk.Button(file_frame, text=_("select_json_btn"), command=self.load_json_file).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(file_frame, text=_("load_latest_btn"), command=self.load_latest_result).pack(side=tk.LEFT, padx=(0, 10))
            
        self.file_label = ttk.Label(file_frame, text=_("no_file_selected"))
        self.file_label.pack(side=tk.LEFT)
        
        # 统计信息区域
        self.stats_frame = ttk.LabelFrame(main_frame, text=_("statistics"), padding="5")
        self.stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.stats_label = ttk.Label(self.stats_frame, text="")
        self.stats_label.pack()
        
        # 左侧：组列表
        left_frame = ttk.LabelFrame(main_frame, text=_("duplicate_groups"), padding="5")
        left_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # 组列表
        self.group_listbox = tk.Listbox(left_frame, width=40)
        self.group_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.group_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.group_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.group_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 右侧：图片显示区域
        right_frame = ttk.LabelFrame(main_frame, text=_("image_preview"), padding="5")
        right_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # 创建滚动区域
        canvas = tk.Canvas(right_frame, bg="white")
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        v_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        canvas.configure(yscrollcommand=v_scrollbar.set)
        
        self.images_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.images_frame, anchor="nw")
        
        self.canvas = canvas
        self.images_frame.bind('<Configure>', self.on_frame_configure)
        
        # 鼠标滚轮绑定
        canvas.bind("<MouseWheel>", self.on_mousewheel)
        
    def select_directory(self):
        """选择扫描目录"""
        directory = filedialog.askdirectory(title=_("select_scan_dir_title"))
        if directory:
            self.scan_directory = directory
            self.dir_label.config(text=f"{_('selected')}: {directory}")
            self.update_status(_("dir_selected"), "success")
            
    def update_status(self, message, status_type="info"):
        """更新状态显示"""
        if hasattr(self, 'status_label'):
            # 根据状态类型设置颜色
            color_map = {
                "success": "#28a745",
                "info": "#17a2b8", 
                "warning": "#ffc107",
                "danger": "#dc3545",
                "secondary": "#6c757d"
            }
            color = color_map.get(status_type, "#6c757d")
            self.status_label.config(text=message, foreground=color)
            
    def log_message(self, message):
        """添加日志消息（优化版本，减少UI刷新）"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        # 移除频繁的update_idletasks调用，减少UI卡顿
        # self.root.update_idletasks()
        
    def start_scan(self):
        """开始扫描"""
        if not self.scan_directory:
            messagebox.showerror(_("error"), _("please_select_dir_first"))
            self.update_status(_("error_no_dir_selected"), "danger")
            return
            
        if not os.path.exists(self.scan_directory):
            messagebox.showerror(_("error"), _("dir_not_exist"))
            self.update_status(_("error_dir_not_exist"), "danger")
            return
        
        # 检查是否有未完成的扫描
        resume_scan = False
        try:
            from src.scan_progress import ScanProgress
            progress_manager = ScanProgress()
            incomplete_scans = progress_manager.list_incomplete_scans()
            
            for scan_info in incomplete_scans:
                if scan_info.get('scan_directory') == self.scan_directory:
                    # 发现未完成的扫描，询问用户是否继续
                    completed_stages = scan_info.get('completed_stages', [])
                    timestamp = scan_info.get('timestamp', 'Unknown')
                    progress_percent = scan_info.get('progress_percent', 0)
                    
                    message = f"发现未完成的扫描:\n\n"
                    message += f"扫描目录: {self.scan_directory}\n"
                    message += f"扫描时间: {timestamp}\n"
                    message += f"进度: {progress_percent:.1f}%\n"
                    message += f"已完成阶段: {', '.join(completed_stages) if completed_stages else '无'}\n\n"
                    message += "是否继续之前的扫描？\n\n"
                    message += "选择'是'将从中断处继续\n"
                    message += "选择'否'将开始新的扫描"
                    
                    result = messagebox.askyesno("发现未完成的扫描", message)
                    if result:
                        resume_scan = True
                        self.log_message(f"将继续之前的扫描 (进度: {progress_percent:.1f}%)")
                    else:
                        # 用户选择开始新扫描，清除旧的进度
                        progress_manager.clear_progress(self.scan_directory)
                        self.log_message("已清除之前的扫描进度，开始新的扫描")
                    break
        except Exception as e:
            self.log_message(f"检查扫描进度时出错: {str(e)}")
            
        # 更新UI状态
        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.update_status(_("scanning"), "info")
        
        # 清空日志（如果不是恢复扫描）
        if not resume_scan:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        # 在新线程中执行扫描
        threading.Thread(target=lambda: self.scan_thread(resume_scan), daemon=True).start()
        
    def scan_thread(self, resume=False):
        """扫描线程"""
        self.should_stop = False  # 重置停止标志
        # 记录扫描开始时间
        self.scan_start_time = time.time()
        try:
            if resume:
                self.log_message(f"继续扫描目录: {self.scan_directory}")
            else:
                self.log_message(f"{_('start_scanning_dir')}: {self.scan_directory}")
            
            # 首先测试C++库是否可用
            cpp_available = False
            try:
                from cpp_hash_lib.hash_wrapper import get_hash_lib
                hash_lib = get_hash_lib()
                # 显示C++库版本信息
                version = hash_lib.get_version()
                self.log_message(f"C++库版本: {version}")
                # 测试C++库功能
                test_result = hash_lib.hamming_distance("abcd", "abcd")
                if test_result == 0:
                    cpp_available = True
                    self.log_message("C++库初始化成功")
                else:
                    self.log_message("C++库初始化失败，回退到Python实现")
            except Exception as e:
                self.log_message(f"C++库不可用，回退到Python实现: {str(e)}")
            
            if not cpp_available:
                # 回退到Python实现
                from src.duplicate_checker import DuplicateChecker
                
                # 获取检测方式设置
                exact_match_enabled = self.exact_match_var.get()
                perceptual_hash_enabled = self.perceptual_hash_var.get()
                
                # 输出调试信息
                self.enhanced_real_time_log(f"Python实现检测方式设置: 完全一致检测={exact_match_enabled}, 感知哈希检测={perceptual_hash_enabled}")
                
                self.checker = DuplicateChecker(
                    phash_threshold=self.phash_var.get(),
                    dhash_threshold=self.dhash_var.get(),
                    ahash_threshold=self.ahash_var.get(),
                    enable_exact_match=exact_match_enabled,
                    enable_perceptual_hash=perceptual_hash_enabled,
                    output_dir="results",
                    detect_pure_color=self.pure_color_var.get(),
                    detect_rotation=self.detect_rotation_var.get()
                )
                self.checker.set_log_callback(self.enhanced_real_time_log)
                stats = self.checker.check_duplicates(
                    self.scan_directory, 
                    self.recursive_var.get()
                )
                self.log_message(f"[调试] Python实现check_duplicates返回值: {stats}")
                self.log_message(f"[调试] 返回值类型: {type(stats)}")
                if stats is None:
                    self.log_message("[错误] Python实现返回None，这不应该发生！")
                self._handle_scan_success(stats)
                return
            
            # 创建查重器，并设置实时日志回调（使用C++哈希库）
            try:
                # 获取检测方式设置
                exact_match_enabled = self.exact_match_var.get()
                perceptual_hash_enabled = self.perceptual_hash_var.get()
                
                # 输出调试信息
                self.enhanced_real_time_log(f"检测方式设置: 完全一致检测={exact_match_enabled}, 感知哈希检测={perceptual_hash_enabled}")
                
                self.checker = CppDuplicateChecker(
                    phash_threshold=self.phash_var.get(),
                    dhash_threshold=self.dhash_var.get(),
                    ahash_threshold=self.ahash_var.get(),
                    output_dir="results",
                    detect_pure_color=self.pure_color_var.get(),
                    detect_rotation=self.detect_rotation_var.get(),
                    enhanced_similarity=self.enhanced_similarity_var.get(),
                    confidence_threshold=self.confidence_var.get(),
                    enable_resume=True,  # 启用断点续传功能
                    enable_optimization=True,  # 启用优化算法
                    optimization_threshold=1000,  # 优化算法阈值
                    enable_ultra_fast=True,  # 启用超高速算法
                    ultra_fast_threshold=50000,  # 超高速算法阈值
                    enable_lsh=self.enable_lsh_var.get(),  # 启用LSH索引
                    lsh_threshold=self.lsh_threshold_var.get(),  # LSH阈值
                    lsh_num_tables=self.memory_config['lsh_num_hash_tables'],  # 使用内存优化配置
                    lsh_num_functions=self.memory_config['lsh_num_hash_functions'],  # 使用内存优化配置
                    enable_exact_match=exact_match_enabled,  # 启用完全一致检测
                    enable_perceptual_hash=perceptual_hash_enabled  # 启用感知哈希检测
                )
                
                # 设置实时日志回调
                self.checker.set_log_callback(self.enhanced_real_time_log)
                # 设置进度回调（如果需要的话）
                self.checker.set_progress_callback(None)  # 暂时设置为None，避免progress_callback错误
                
                # 执行查重
                if resume:
                    self.log_message("使用C++库继续图片查重...")
                else:
                    self.log_message("开始使用C++库进行图片查重...")
                    
                stats = self.checker.check_duplicates(
                    self.scan_directory, 
                    self.recursive_var.get(),
                    resume=resume
                )
                self.log_message(f"[调试] C++库check_duplicates返回值: {stats}")
                self.log_message(f"[调试] 返回值类型: {type(stats)}")
                if stats is None:
                    self.log_message("[错误] C++库返回None，这不应该发生！")
                self._handle_scan_success(stats)
                
            except Exception as e:
                error_msg = str(e)
                self.log_message(f"C++实现出错: {error_msg}")
                
                # 检查是否是用户主动停止
                if self.should_stop or "扫描已停止" in error_msg:
                    self.log_message("用户已停止扫描")
                    return
                
                self.log_message("尝试回退到Python实现...")
                # 回退到Python实现
                try:
                    from src.duplicate_checker import DuplicateChecker
                    
                    # 获取检测方式设置
                    exact_match_enabled = self.exact_match_var.get()
                    perceptual_hash_enabled = self.perceptual_hash_var.get()
                    
                    # 输出调试信息
                    self.enhanced_real_time_log(f"Python回退实现检测方式设置: 完全一致检测={exact_match_enabled}, 感知哈希检测={perceptual_hash_enabled}")
                    
                    self.checker = DuplicateChecker(
                        phash_threshold=self.phash_var.get(),
                        dhash_threshold=self.dhash_var.get(),
                        ahash_threshold=self.ahash_var.get(),
                        output_dir="results",
                        detect_pure_color=self.pure_color_var.get(),
                        detect_rotation=self.detect_rotation_var.get(),
                        enable_exact_match=exact_match_enabled,
                        enable_perceptual_hash=perceptual_hash_enabled
                    )
                    self.checker.set_log_callback(self.enhanced_real_time_log)
                    self.log_message("开始使用Python实现进行图片查重...")
                    stats = self.checker.check_duplicates(
                        self.scan_directory, 
                        self.recursive_var.get()
                    )
                    self._handle_scan_success(stats)
                except Exception as fallback_e:
                    self.log_message(f"Python实现也失败: {str(fallback_e)}")
                    raise fallback_e
                
        except Exception as e:
            self.log_message(f"{_('scan_failed')}: {str(e)}")
            import traceback
            self.log_message(f"详细错误信息: {traceback.format_exc()}")
        finally:
            # 恢复UI状态
            self.root.after(0, self.scan_finished)
    
    def _handle_scan_success(self, stats):
        """处理扫描成功的结果"""
        self.log_message(f"\n{_('scan_completed')}")
        
        # 计算扫描耗时
        scan_duration = 0
        if hasattr(self, 'scan_start_time'):
            scan_duration = time.time() - self.scan_start_time
        
        # 调试：显示接收到的stats内容
        self.log_message(f"[调试] 接收到的stats: {stats}")
        
        # 确保stats不为None
        if stats is None:
            stats = {'total_images': 0, 'duplicate_groups': 0, 'duplicate_images': 0}
            self.log_message("[调试] stats为None，使用默认值")
        
        # 显示详细的扫描汇总信息
        self.log_message("\n=== 扫描汇总 ===")
        self.log_message(f"扫描耗时: {scan_duration:.2f} 秒")
        self.log_message(f"{_('total_images')}: {stats.get('total_images', 0)}")
        self.log_message(f"实际处理: {stats.get('processed_images', stats.get('total_images', 0))} 个文件")
        self.log_message(f"{_('duplicate_groups')}: {stats.get('duplicate_groups', 0)}")
        self.log_message(f"{_('duplicate_images')}: {stats.get('duplicate_images', 0)}")
        
        # 显示纯色图片统计（如果有）
        if stats.get('pure_color_images', 0) > 0:
            self.log_message(f"纯色图片: {stats.get('pure_color_images', 0)}")
        
        # 显示重复原因统计（如果有）
        if 'reasons' in stats and stats['reasons']:
            self.log_message("\n重复原因统计:")
            for reason, count in stats['reasons'].items():
                self.log_message(f"  {reason}: {count} 组")
        
        # 显示文件状态统计（如果有）
        if 'file_status' in stats and stats['file_status']:
            self.log_message("\n文件状态统计:")
            for status, count in stats['file_status'].items():
                self.log_message(f"  {status}: {count} 个文件")
        
        # 计算可节省的存储空间（估算）
        duplicate_count = stats.get('duplicate_images', 0)
        if duplicate_count > 0:
            self.log_message(f"\n可删除重复文件: {duplicate_count} 个")
            self.log_message("注意: 删除前请仔细确认，避免误删重要文件")
        
        self.log_message("==================")
        
        # 自动加载结果
        self.root.after(0, self.load_latest_result)
            
    def real_time_log(self, message):
        """实时日志回调函数（优化版本）"""
        # 使用缓冲机制减少UI更新频率
        if not hasattr(self, '_main_log_buffer'):
            self._main_log_buffer = []
            self._last_main_log_update = 0
        
        self._main_log_buffer.append(message)
        
        # 进一步优化：每3秒或缓冲区满10条时更新一次UI
        current_time = time.time()
        if (current_time - self._last_main_log_update > 3.0) or len(self._main_log_buffer) >= 10:
            # 使用after方法确保在主线程中更新UI
            self.root.after(0, self._flush_main_log_buffer)
            self._last_main_log_update = current_time
    
    def _flush_main_log_buffer(self):
        """刷新主日志缓冲区到UI"""
        try:
            if hasattr(self, '_main_log_buffer') and self._main_log_buffer:
                for message in self._main_log_buffer:
                    self.log_message(message)
                self._main_log_buffer.clear()
        except Exception as e:
            pass  # 刷新主日志缓冲区时出错
            
    def scan_finished(self):
        """扫描完成后的UI更新"""
        self.is_scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.update_status(_("scan_completed"), "success")
        
    def stop_scan(self):
        """停止扫描"""
        self.is_scanning = False
        self.should_stop = True  # 设置停止标志
        self.log_message(_('user_stop_scan'))
        
        # 尝试停止checker
        if hasattr(self, 'checker') and self.checker:
            try:
                # 如果checker有停止方法，调用它
                if hasattr(self.checker, 'stop'):
                    self.checker.stop()
                    self.log_message("已向扫描器发送停止信号")
            except Exception as e:
                self.log_message(f"停止扫描器时出错: {str(e)}")
        
        # 刷新所有缓冲的日志
        self._flush_main_log_buffer()
        self._flush_log_buffer()
        
        self.update_status(_('scan_stopped'), "warning")
        # 延迟一点时间再调用scan_finished，给停止操作一些时间
        self.root.after(1000, self.scan_finished)
        
    def load_latest_result(self):
        """加载最新的扫描结果"""
        results_dir = "results"
        if not os.path.exists(results_dir):
            messagebox.showwarning(_("warning"), _("results_dir_not_exist"))
            return
            
        # 查找最新的JSON文件
        json_files = [f for f in os.listdir(results_dir) if f.endswith('.json') and 'duplicates' in f]
        if not json_files:
            messagebox.showwarning(_("warning"), _("no_result_files_found"))
            return
            
        # 按修改时间排序，获取最新的
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)
        latest_file = os.path.join(results_dir, json_files[0])
        
        self.load_json_from_path(latest_file)
        
    def load_json_file(self):
        """选择并加载JSON文件"""
        file_path = filedialog.askopenfilename(
            title=_("select_json_file_title"),
            filetypes=[(_("json_files"), "*.json"), (_("all_files"), "*.*")]
        )
        
        if file_path:
            self.load_json_from_path(file_path)
            
    def load_json_from_path(self, file_path=None):
        """从指定路径加载JSON文件"""
        if file_path is None:
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证JSON数据结构
            if not isinstance(data, list):
                raise ValueError("JSON文件格式错误：应该是一个数组")
            
            # 检查每个组是否包含必要的字段
            for i, group in enumerate(data):
                if not isinstance(group, dict):
                    raise ValueError(f"第{i+1}组数据格式错误：应该是一个对象")
                if 'reason' not in group:
                    # 为缺少reason字段的组添加默认值
                    group['reason'] = '未知原因'
                    self.log_message(f"警告：第{i+1}组缺少'reason'字段，已设置为默认值")
                if 'files' not in group:
                    raise ValueError(f"第{i+1}组缺少'files'字段")
                if not isinstance(group['files'], list):
                    raise ValueError(f"第{i+1}组的'files'字段应该是一个数组")
                
                # 兼容旧格式：将{'path': 'xxx'}格式转换为字符串
                converted_files = []
                has_old_format = False
                for file_item in group['files']:
                    if isinstance(file_item, dict) and 'file_path' in file_item:
                        # 新格式：{'file_path': 'xxx'}
                        converted_files.append(file_item['file_path'])
                        has_old_format = True
                    elif isinstance(file_item, str):
                        # 新格式：直接是字符串
                        converted_files.append(file_item)
                    else:
                        raise ValueError(f"第{i+1}组的文件路径格式错误：{file_item}")
                
                # 只在检测到旧格式时输出一次警告
                if has_old_format:
                    self.log_message(f"警告：第{i+1}组包含旧格式文件路径，已自动转换")
                
                group['files'] = converted_files
            
            self.duplicate_data = data
            self.file_label.config(text=f"{_('loaded')}: {os.path.basename(file_path)}")
            self.update_stats()
            self.update_group_list()
            self.update_status(f"{_('loaded_groups')}: {len(self.duplicate_data)}", "success")
            return True
            
        except FileNotFoundError:
            error_msg = f"文件不存在: {file_path}"
            messagebox.showerror(_("error"), f"{_('load_json_failed')}: {error_msg}")
            self.update_status(_("load_file_failed"), "danger")
            return False
        except json.JSONDecodeError as e:
            error_msg = f"JSON格式错误: {str(e)}"
            messagebox.showerror(_("error"), f"{_('load_json_failed')}: {error_msg}")
            self.update_status(_("load_file_failed"), "danger")
            return False
        except Exception as e:
            error_msg = str(e)
            messagebox.showerror(_("error"), f"{_('load_json_failed')}: {error_msg}")
            self.update_status(_("load_file_failed"), "danger")
            self.log_message(f"加载JSON文件时发生错误: {error_msg}")
            return False
            
    def save_results(self):
        """保存扫描结果"""
        if not hasattr(self, 'duplicate_data') or not self.duplicate_data:
            messagebox.showwarning(_("warning"), _("no_results_to_save"))
            return
            
        file_path = filedialog.asksaveasfilename(
            title=_("save_results_title"),
            defaultextension=".json",
            filetypes=[(_("json_files"), "*.json"), (_("all_files"), "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.duplicate_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo(_("success"), f"{_('results_saved_to')}: {file_path}")
                self.update_status(_("save_success"), "success")
            except Exception as e:
                messagebox.showerror(_("error"), f"{_('save_failed')}: {str(e)}")
                self.update_status(_("save_failed"), "danger")
            
    def update_stats(self):
        """更新统计信息"""
        if not self.duplicate_data:
            return
            
        total_groups = len(self.duplicate_data)
        total_images = sum(len(group.get('files', [])) for group in self.duplicate_data)
        
        # 安全地访问reason字段，提供默认值
        exact_groups = sum(1 for group in self.duplicate_data if group.get('reason', '') == '完全相同')
        similar_groups = sum(1 for group in self.duplicate_data if '相似' in group.get('reason', ''))
        pure_groups = sum(1 for group in self.duplicate_data if group.get('reason', '') == '纯色图片')
        
        stats_text = f"{_('total_groups')}: {total_groups} | {_('total_images')}: {total_images} | {_('exact_same')}: {exact_groups}{_('groups')} | {_('similar_images')}: {similar_groups}{_('groups')} | {_('pure_color_images')}: {pure_groups}{_('groups')}"
        self.stats_label.config(text=stats_text)
        
    def update_group_list(self):
        """更新组列表"""
        self.group_listbox.delete(0, tk.END)
        
        for i, group in enumerate(self.duplicate_data):
            reason = group.get('reason', '未知原因')
            files_count = len(group.get('files', []))
            group_text = f"{_('group')}{i+1}: {reason} ({files_count}{_('images')})"
            self.group_listbox.insert(tk.END, group_text)
            
    def on_group_select(self, event):
        """组选择事件"""
        selection = self.group_listbox.curselection()
        if not selection:
            return
            
        self.current_group_index = selection[0]
        self.current_page = 0  # 重置分页
        self.display_group_images()
        
    def display_group_images(self):
        """显示组内图片（分页显示）"""
        # 清空当前显示和重置状态
        for widget in self.images_frame.winfo_children():
            widget.destroy()
        
        # 重置加载线程计数
        self.loading_threads = 0
        
        # 清空加载队列
        while not self.load_queue.empty():
            try:
                self.load_queue.get_nowait()
                self.load_queue.task_done()
            except queue.Empty:
                break
        
        # 清理部分缓存以释放内存
        if len(self.image_cache) > 50:
            cache_items = list(self.image_cache.items())
            self.image_cache = dict(cache_items[-50:])
            
        if not self.duplicate_data or self.current_group_index >= len(self.duplicate_data):
            return
            
        group = self.duplicate_data[self.current_group_index]
        total_images = len(group['files'])
        
        # 计算分页信息
        self.total_pages = max(1, (total_images + self.images_per_page - 1) // self.images_per_page)
        
        # 确保当前页在有效范围内
        if self.current_page >= self.total_pages:
            self.current_page = 0
        
        # 显示组信息和分页信息
        info_text = f"{group['reason']} - {total_images}{_('images')}"
        if self.total_pages > 1:
            info_text += f" (第 {self.current_page + 1}/{self.total_pages} 页)"
        
        info_label = ttk.Label(self.images_frame, text=info_text, font=('Arial', 12, 'bold'))
        info_label.pack(pady=(0, 10))
        
        # 添加分页控件（如果需要）
        if self.total_pages > 1:
            self.create_pagination_controls()
        
        # 计算当前页要显示的图片范围
        start_idx = self.current_page * self.images_per_page
        end_idx = min(start_idx + self.images_per_page, total_images)
        
        # 显示当前页的图片
        for i in range(start_idx, end_idx):
            file_path = group['files'][i]
            self.create_image_widget(file_path, i)
            
        # 更新滚动区域
        self.images_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def create_pagination_controls(self):
        """创建分页控件"""
        pagination_frame = ttk.Frame(self.images_frame)
        pagination_frame.pack(pady=10, fill='x')
        
        # 上一页按钮
        prev_btn = ttk.Button(pagination_frame, text="上一页", 
                             command=self.prev_page,
                             state='normal' if self.current_page > 0 else 'disabled')
        prev_btn.pack(side='left', padx=5)
        
        # 页码信息
        page_info = ttk.Label(pagination_frame, 
                             text=f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页")
        page_info.pack(side='left', padx=20)
        
        # 下一页按钮
        next_btn = ttk.Button(pagination_frame, text="下一页", 
                             command=self.next_page,
                             state='normal' if self.current_page < self.total_pages - 1 else 'disabled')
        next_btn.pack(side='left', padx=5)
        
        # 跳转到页面
        jump_frame = ttk.Frame(pagination_frame)
        jump_frame.pack(side='right', padx=10)
        
        ttk.Label(jump_frame, text="跳转到第").pack(side='left')
        
        self.page_entry = ttk.Entry(jump_frame, width=5)
        self.page_entry.pack(side='left', padx=5)
        self.page_entry.bind('<Return>', self.jump_to_page)
        
        ttk.Label(jump_frame, text="页").pack(side='left')
        
        jump_btn = ttk.Button(jump_frame, text="跳转", command=self.jump_to_page)
        jump_btn.pack(side='left', padx=5)
        
    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_group_images()
            
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_group_images()
            
    def jump_to_page(self, event=None):
        """跳转到指定页面"""
        try:
            page_num = int(self.page_entry.get()) - 1  # 转换为0基索引
            if 0 <= page_num < self.total_pages:
                self.current_page = page_num
                self.display_group_images()
            else:
                messagebox.showwarning("警告", f"页码必须在 1 到 {self.total_pages} 之间")
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的页码")
        
    def create_image_widget(self, file_path, index):
        """创建图片组件"""
        # 创建图片容器
        img_frame = ttk.Frame(self.images_frame, relief="solid", borderwidth=1)
        img_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件名标签
        filename = os.path.basename(file_path)
        name_label = ttk.Label(img_frame, text=filename, font=('Arial', 10, 'bold'))
        name_label.pack(pady=(5, 0))
        
        # 图片标签（占位符）
        img_label = ttk.Label(img_frame, text=_("loading"), background="lightgray")
        img_label.pack(pady=5)
        
        # 哈希距离信息（如果有的话）
        self.add_hash_distance_info(img_frame, file_path, index)
        
        # 路径标签
        path_label = ttk.Label(img_frame, text=file_path, font=('Arial', 8), foreground="gray")
        path_label.pack(pady=(0, 5))
        
        # 按钮框架
        btn_frame = ttk.Frame(img_frame)
        btn_frame.pack(pady=(0, 5))
        
        # 复制路径按钮
        try:
            copy_btn = ttk.Button(btn_frame, text=f"📋 {_('copy_path')}", 
                                 command=lambda: self.copy_path(file_path), bootstyle="secondary-outline")
        except:
            copy_btn = ttk.Button(btn_frame, text=f"📋 {_('copy_path')}", 
                                 command=lambda: self.copy_path(file_path))
        copy_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 打开文件按钮
        try:
            open_btn = ttk.Button(btn_frame, text=f"🖼️ {_('open_file')}", 
                                 command=lambda: self.open_file(file_path), bootstyle="info-outline")
        except:
            open_btn = ttk.Button(btn_frame, text=f"🖼️ {_('open_file')}", 
                                 command=lambda: self.open_file(file_path))
        open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 打开文件夹按钮
        try:
            folder_btn = ttk.Button(btn_frame, text=f"📁 {_('open_folder')}", 
                                   command=lambda: self.open_folder(file_path), bootstyle="warning-outline")
        except:
            folder_btn = ttk.Button(btn_frame, text=f"📁 {_('open_folder')}", 
                                   command=lambda: self.open_folder(file_path))
        folder_btn.pack(side=tk.LEFT)
        
        # 将图片加载请求加入队列
        self.load_queue.put((file_path, img_label))
        
        # 启动队列处理器（如果还没有运行）
        if not self.queue_processor_running:
            self.queue_processor_running = True
            threading.Thread(target=self.process_load_queue, daemon=True).start()
    
    def add_hash_distance_info(self, parent_frame, file_path, index):
        """添加哈希距离信息显示"""
        if not self.duplicate_data or self.current_group_index >= len(self.duplicate_data):
            return
            
        group = self.duplicate_data[self.current_group_index]
        
        # 检查是否有距离信息
        if 'files_with_distances' not in group:
            return
            
        # 查找当前文件的距离信息
        distance_info = None
        for file_info in group['files_with_distances']:
            if file_info['file_path'] == file_path:
                distance_info = file_info
                break
                
        if distance_info and index > 0:  # 第一个文件（基准文件）不显示距离
            # 创建距离信息框架
            distance_frame = ttk.Frame(parent_frame)
            distance_frame.pack(pady=(0, 5))
            
            # 距离信息标签
            distance_text = f"{_('dhash_distance')}: {distance_info['dhash_distance']} | {_('phash_distance')}: {distance_info['phash_distance']} | {_('ahash_distance')}: {distance_info['ahash_distance']}"
            distance_label = ttk.Label(distance_frame, text=distance_text, 
                                     font=('Arial', 8), foreground="blue")
            distance_label.pack()
        elif index == 0:
            # 基准文件标识
            base_frame = ttk.Frame(parent_frame)
            base_frame.pack(pady=(0, 5))
            
            base_label = ttk.Label(base_frame, text=f"{_('base_image')} ({_('distance')}: 0)", 
                                 font=('Arial', 8), foreground="green")
            base_label.pack()
        
    def process_load_queue(self):
        """处理图片加载队列"""
        while True:
            try:
                file_path, img_label = self.load_queue.get(timeout=1)
                
                while self.loading_threads >= self.max_concurrent_loads:
                    time.sleep(0.1)
                
                self.loading_threads += 1
                threading.Thread(target=self.load_image_async, 
                                args=(file_path, img_label), daemon=True).start()
                
                self.load_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                pass  # 队列处理错误
                continue
    
    def load_image_async(self, file_path, img_label):
        """异步加载图片"""
        try:
            if not os.path.exists(file_path):
                self.root.after(0, lambda: self.safe_update_label(img_label, text=_("file_not_exist"), foreground="red"))
                return
                
            if file_path in self.image_cache:
                photo = self.image_cache[file_path]
                self.root.after(0, lambda: self.safe_update_image_label(img_label, photo))
                return
                
            with Image.open(file_path) as img:
                max_size = (200, 150)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                if len(self.image_cache) < 50:
                    self.image_cache[file_path] = photo
                
                self.root.after(0, lambda: self.safe_update_image_label(img_label, photo))
                
        except Exception as e:
            self.root.after(0, lambda: self.safe_update_label(img_label, text=f"{_('load_failed')}: {str(e)}", foreground="red"))
        finally:
            self.loading_threads = max(0, self.loading_threads - 1)
            
    def safe_update_image_label(self, img_label, photo):
        """安全更新图片标签"""
        try:
            if img_label.winfo_exists():
                img_label.config(image=photo, text="")
                img_label.image = photo
        except tk.TclError:
            pass
            
    def safe_update_label(self, img_label, text="", foreground="black"):
        """安全更新文本标签"""
        try:
            if img_label.winfo_exists():
                img_label.config(text=text, foreground=foreground)
        except tk.TclError:
            pass
        
    def on_frame_configure(self, event):
        """框架配置事件"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def on_mousewheel(self, event):
        """鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def copy_path(self, file_path):
        """复制文件路径"""
        self.root.clipboard_clear()
        self.root.clipboard_append(file_path)
        self.update_status(_("path_copied"), "success")
        # messagebox.showinfo("成功", "路径已复制到剪贴板")
        
    def open_file(self, file_path):
        """打开文件"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            self.update_status(_("file_opened"), "success")
        except Exception as e:
            messagebox.showerror(_("error"), f"{_('cannot_open_file')}: {str(e)}")
            self.update_status(_("open_file_failed"), "danger")
            
    def open_folder(self, file_path):
        """打开文件夹"""
        try:
            folder_path = os.path.dirname(file_path)
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
            self.update_status(_("folder_opened"), "success")
        except Exception as e:
            messagebox.showerror(_("error"), f"{_('cannot_open_folder')}: {str(e)}")
            self.update_status(_("open_folder_failed"), "danger")
    
    def toggle_thread_monitor(self):
        """切换线程监控状态"""
        self.thread_monitor_enabled = self.monitor_enabled_var.get()
        
        if self.thread_monitor_enabled:
            self.thread_log_message("线程监控已启用")
            self.start_monitor_update()
        else:
            self.thread_log_message("线程监控已禁用")
            self.stop_monitor_update()
    
    def start_monitor_update(self):
        """开始监控更新"""
        if self.thread_monitor_enabled:
            self.update_thread_status()
            # 进一步优化更新频率：扫描时2秒更新一次，空闲时5秒更新一次
            update_interval = 2000 if self.is_scanning else 5000
            self.monitor_update_timer = self.root.after(update_interval, self.start_monitor_update)
    
    def stop_monitor_update(self):
        """停止监控更新"""
        if self.monitor_update_timer:
            self.root.after_cancel(self.monitor_update_timer)
            self.monitor_update_timer = None
    
    def update_thread_status(self):
        """更新线程状态显示"""
        try:
            # 获取当前活跃线程数
            import threading
            active_threads = threading.active_count()
            
            if self.is_scanning and self.checker:
                # 扫描中状态
                self.thread_stats['thread_pool_status'] = 'running'
                self.thread_stats['total_threads'] = active_threads
                
                # 从CppDuplicateChecker获取真实的线程状态
                if hasattr(self.checker, 'get_thread_status'):
                    try:
                        checker_status = self.checker.get_thread_status()
                        
                        # 更新线程数据
                        self.thread_stats['hash_threads'] = checker_status.get('hash_threads', 0)
                        self.thread_stats['compare_threads'] = checker_status.get('compare_threads', 0)
                        self.thread_stats['pure_color_threads'] = checker_status.get('pure_color_threads', 0)
                        self.thread_stats['active_tasks'] = checker_status.get('active_tasks', 0)
                        self.thread_stats['completed_tasks'] = checker_status.get('completed_tasks', 0)
                        self.thread_stats['current_stage'] = checker_status.get('current_stage', 'unknown')
                        
                        # 记录线程状态变化
                        stage = self.thread_stats['current_stage']
                        if stage != getattr(self, '_last_stage', ''):
                            self.thread_log_message(f"阶段切换: {stage}")
                            self._last_stage = stage
                            
                    except Exception as e:
                        self.thread_log_message(f"获取检查器线程状态失败: {str(e)}")
                        # 回退到基于日志的估算
                        self._fallback_thread_estimation(active_threads)
                else:
                    # 回退到基于日志的估算
                    self._fallback_thread_estimation(active_threads)
            else:
                # 空闲状态
                self.thread_stats['thread_pool_status'] = 'idle'
                self.thread_stats['total_threads'] = active_threads
                self.thread_stats['hash_threads'] = 0
                self.thread_stats['compare_threads'] = 0
                self.thread_stats['pure_color_threads'] = 0
                self.thread_stats['active_tasks'] = 0
                self.thread_stats['completed_tasks'] = 0
                self.thread_stats['current_stage'] = 'idle'
            
            # 更新UI显示
            self.update_monitor_ui()
            
        except Exception as e:
            self.thread_log_message(f"更新线程状态时出错: {str(e)}")
    
    def _fallback_thread_estimation(self, active_threads):
        """基于日志的线程数估算（回退方案）"""
        # 检查最近的日志消息来判断当前阶段
        recent_log = getattr(self, '_last_log_message', '').lower()
        
        # 显示真实的工作线程数
        # 工作线程数 = 总活跃线程数 - 主线程 - UI线程
        work_threads = max(0, active_threads - 2)
        
        # 根据日志关键词判断当前主要阶段，显示真实线程数
        if ('比较' in recent_log or 'compare' in recent_log or
            '分组' in recent_log or 'group' in recent_log or
            '旋转' in recent_log or 'rotation' in recent_log or
            '相似' in recent_log or 'similarity' in recent_log or
            '感知哈希' in recent_log or 'perceptual' in recent_log):
            # 比较计算阶段 - C++实现最多使用8个线程
            self.thread_stats['hash_threads'] = 0
            self.thread_stats['compare_threads'] = work_threads
            self.thread_stats['pure_color_threads'] = 0
            self.thread_stats['current_stage'] = 'group_comparison'
        elif ('纯色' in recent_log or 'pure color' in recent_log or '检测纯色' in recent_log):
            # 纯色检测阶段 - C++实现最多使用4个线程
            self.thread_stats['hash_threads'] = 0
            self.thread_stats['compare_threads'] = 0
            self.thread_stats['pure_color_threads'] = work_threads
            self.thread_stats['current_stage'] = 'pure_color_detection'
        else:
            # 哈希计算阶段 - C++实现最多使用16个线程
            self.thread_stats['hash_threads'] = work_threads
            self.thread_stats['compare_threads'] = 0
            self.thread_stats['pure_color_threads'] = 0
            self.thread_stats['current_stage'] = 'hash_calculation'
    
    def update_monitor_ui(self):
        """更新监控界面显示"""
        try:
            # 检查是否需要更新UI（避免不必要的UI刷新）
            current_stats = {
                'status': self.thread_stats['thread_pool_status'],
                'stage': self.thread_stats.get('current_stage', 'idle'),
                'total_threads': self.thread_stats['total_threads'],
                'hash_threads': self.thread_stats['hash_threads'],
                'compare_threads': self.thread_stats['compare_threads'],
                'pure_color_threads': self.thread_stats.get('pure_color_threads', 0),
                'active_tasks': self.thread_stats['active_tasks'],
                'completed_tasks': self.thread_stats['completed_tasks']
            }
            
            # 如果状态没有变化，跳过UI更新
            if hasattr(self, '_last_ui_stats') and self._last_ui_stats == current_stats:
                return
            
            self._last_ui_stats = current_stats.copy()
            
            # 更新线程池状态
            status = current_stats['status']
            current_stage = current_stats['stage']
            
            if status == 'running':
                stage_text = {
                    'hash_calculation': '哈希计算中',
                    'group_comparison': '分组比较中', 
                    'pure_color_detection': '纯色检测中',
                    'unknown': '运行中'
                }.get(current_stage, '运行中')
                self.pool_status_label.config(text=stage_text, foreground="orange")
            elif status == 'idle':
                self.pool_status_label.config(text="空闲", foreground="green")
            else:
                self.pool_status_label.config(text="未知", foreground="gray")
            
            # 更新线程数
            self.total_threads_label.config(text=str(current_stats['total_threads']))
            self.hash_threads_label.config(text=str(current_stats['hash_threads']))
            self.compare_threads_label.config(text=str(current_stats['compare_threads']))
            self.pure_color_threads_label.config(text=str(current_stats['pure_color_threads']))
            
            # 更新任务数
            self.active_tasks_label.config(text=str(current_stats['active_tasks']))
            self.completed_tasks_label.config(text=str(current_stats['completed_tasks']))
            
            # 更新进度条（基于真实线程使用率）
            hash_threads = current_stats['hash_threads']
            compare_threads = current_stats['compare_threads']
            pure_color_threads = current_stats['pure_color_threads']
            
            # 哈希计算进度（最大16线程）
            if hash_threads > 0:
                hash_progress = min(100, (hash_threads / 16) * 100)
                self.hash_progress['value'] = hash_progress
                self.hash_progress_label.config(text=f"{hash_progress:.0f}%")
            else:
                self.hash_progress['value'] = 0
                self.hash_progress_label.config(text="0%")
            
            # 比较计算进度（最大8线程）
            if compare_threads > 0:
                compare_progress = min(100, (compare_threads / 8) * 100)
                self.compare_progress['value'] = compare_progress
                self.compare_progress_label.config(text=f"{compare_progress:.0f}%")
            else:
                self.compare_progress['value'] = 0
                self.compare_progress_label.config(text="0%")
            
            # 纯色检测进度（最大4线程）
            if pure_color_threads > 0:
                pure_color_progress = min(100, (pure_color_threads / 4) * 100)
                self.pure_color_progress['value'] = pure_color_progress
                self.pure_color_progress_label.config(text=f"{pure_color_progress:.0f}%")
            else:
                self.pure_color_progress['value'] = 0
                self.pure_color_progress_label.config(text="0%")
                
        except Exception as e:
            pass  # 更新监控UI时出错
    
    def thread_log_message(self, message):
        """记录线程活动日志（优化版本，减少UI更新频率）"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            # 使用缓冲机制，减少UI更新频率
            if not hasattr(self, '_log_buffer'):
                self._log_buffer = []
                self._last_log_update = 0
            
            self._log_buffer.append(log_entry)
            
            # 进一步优化：每5秒或缓冲区满20条时更新一次UI
            current_time = time.time()
            if (current_time - self._last_log_update > 5.0) or len(self._log_buffer) >= 20:
                self._flush_log_buffer()
                self._last_log_update = current_time
                
        except Exception as e:
            pass  # 记录线程日志时出错
    
    def _flush_log_buffer(self):
        """刷新日志缓冲区到UI"""
        try:
            if hasattr(self, '_log_buffer') and self._log_buffer:
                self.thread_log_text.config(state=tk.NORMAL)
                for entry in self._log_buffer:
                    self.thread_log_text.insert(tk.END, entry)
                self.thread_log_text.see(tk.END)
                self.thread_log_text.config(state=tk.DISABLED)
                self._log_buffer.clear()
        except Exception as e:
            pass  # 刷新日志缓冲区时出错
    
    def clear_thread_log(self):
        """清除线程日志"""
        try:
            self.thread_log_text.config(state=tk.NORMAL)
            self.thread_log_text.delete(1.0, tk.END)
            self.thread_log_text.config(state=tk.DISABLED)
            self.thread_log_message("日志已清除")
        except Exception as e:
            pass  # 清除线程日志时出错
    
    def enhanced_real_time_log(self, message):
        """增强的实时日志，同时记录到扫描日志和线程日志"""
        # 保存最近的日志消息用于线程状态判断
        self._last_log_message = message
        
        # 原有的扫描日志
        self.real_time_log(message)
        
        # 线程监控日志（添加去重机制）
        if self.thread_monitor_enabled:
            # 初始化去重集合
            if not hasattr(self, '_logged_messages'):
                self._logged_messages = set()
            
            # 检测线程相关的日志消息
            thread_keywords = ['线程', 'thread', '并行', '哈希计算', '分组比较', '批次', 
                             '纯色', '检测', '处理', '扫描', 'detecting', 'processing']
            
            # 创建消息的唯一标识（去除时间戳等变化部分）
            message_key = message
            # 移除时间戳和动态数字，保留核心信息
            import re
            message_key = re.sub(r'\d{2}:\d{2}:\d{2}', '', message_key)  # 移除时间戳
            message_key = re.sub(r'\d+\.\d+秒', 'X.X秒', message_key)  # 标准化耗时
            message_key = re.sub(r'\d+/\d+', 'X/Y', message_key)  # 标准化进度
            
            if any(keyword in message.lower() for keyword in thread_keywords):
                # 只记录新的消息，避免重复
                if message_key not in self._logged_messages:
                    self._logged_messages.add(message_key)
                    self.thread_log_message(f"[扫描] {message}")
                    
                    # 更新任务计数
                    if '完成' in message or 'completed' in message.lower():
                        self.thread_stats['completed_tasks'] += 1
                    elif '开始' in message or '处理' in message or 'start' in message.lower() or 'processing' in message.lower():
                        self.thread_stats['active_tasks'] += 1
                        
            # 定期清理去重集合，避免内存泄漏
            if len(self._logged_messages) > 1000:
                self._logged_messages.clear()

def main():
    try:
        # 尝试使用ttkbootstrap的superhero主题（深蓝色专业主题）
        import ttkbootstrap as ttk
        root = ttk.Window(themename="superhero")
        pass  # 使用ttkbootstrap superhero主题
    except ImportError:
        # 如果没有安装ttkbootstrap，使用标准tkinter
        root = tk.Tk()
        pass  # 使用标准tkinter主题
    
    app = IntegratedDuplicateApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()