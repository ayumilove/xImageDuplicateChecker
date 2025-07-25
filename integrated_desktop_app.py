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
    print("警告: 未安装ttkbootstrap，将使用标准tkinter")
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
from src.duplicate_checker import DuplicateChecker
from i18n import I18n

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
        
        # 扫描相关
        self.scan_directory = ""
        self.is_scanning = False
        self.checker = None
        
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
        
        # 底部版权信息栏
        copyright_frame = ttk.Frame(main_container)
        copyright_frame.pack(fill=tk.X, pady=(5, 0))
        
        copyright_label = ttk.Label(copyright_frame, text=self.copyright_info, 
                                   font=('Arial', 8), foreground='#6c757d')
        copyright_label.pack(side=tk.RIGHT)
        
        # 状态信息
        status_label = ttk.Label(copyright_frame, text=_("status_ready"), 
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

GitHub: {self.github_url}

© 2024 xImageDuplicateChecker
MIT License
        """
        messagebox.showinfo(_("menu_about"), about_text)
        
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
        
        # 第二行参数
        row2 = ttk.Frame(params_frame)
        row2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row2, text=_("dhash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.dhash_var = tk.IntVar(value=8)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.dhash_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row2, text=_("phash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.phash_var = tk.IntVar(value=2)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.phash_var).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(row2, text=_("ahash_threshold")).pack(side=tk.LEFT, padx=(0, 5))
        self.ahash_var = tk.IntVar(value=2)
        ttk.Spinbox(row2, from_=1, to=20, width=5, textvariable=self.ahash_var).pack(side=tk.LEFT)
        
        # 第三行参数
        row3 = ttk.Frame(params_frame)
        row3.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row3, text=_("detect_rotation")).pack(side=tk.LEFT, padx=(0, 5))
        self.detect_rotation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, variable=self.detect_rotation_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row3, text=_("rotation_note"), font=('Arial', 8), foreground='#6c757d').pack(side=tk.LEFT)
        
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
        """添加日志消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
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
            
        # 更新UI状态
        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.update_status(_("scanning"), "info")
        
        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 在新线程中执行扫描
        threading.Thread(target=self.scan_thread, daemon=True).start()
        
    def scan_thread(self):
        """扫描线程"""
        try:
            self.log_message(f"{_('start_scanning_dir')}: {self.scan_directory}")
            
            # 创建查重器，并设置实时日志回调
            self.checker = DuplicateChecker(
                phash_threshold=self.phash_var.get(),
                dhash_threshold=self.dhash_var.get(),
                ahash_threshold=self.ahash_var.get(),
                output_dir="results",
                detect_pure_color=self.pure_color_var.get(),
                detect_rotation=self.detect_rotation_var.get()
            )
            
            # 设置实时日志回调
            self.checker.set_log_callback(self.real_time_log)
            
            try:
                # 执行查重
                stats = self.checker.check_duplicates(
                    self.scan_directory, 
                    self.recursive_var.get()
                )
                
                self.log_message(f"\n{_('scan_completed')}")
                self.log_message(f"{_('total_images')}: {stats.get('total_images', 0)}")
                self.log_message(f"{_('duplicate_groups')}: {stats.get('duplicate_groups', 0)}")
                self.log_message(f"{_('duplicate_images')}: {stats.get('duplicate_images', 0)}")
                
                # 自动加载结果
                self.root.after(0, self.load_latest_result)
                
            except Exception as e:
                self.log_message(f"{_('scan_error')}: {str(e)}")
                
        except Exception as e:
            self.log_message(f"{_('scan_failed')}: {str(e)}")
        finally:
            # 恢复UI状态
            self.root.after(0, self.scan_finished)
            
    def real_time_log(self, message):
        """实时日志回调函数"""
        # 使用after方法确保在主线程中更新UI
        self.root.after(0, lambda: self.log_message(message))
            
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
        self.log_message(_("user_stop_scan"))
        self.update_status(_("scan_stopped"), "warning")
        self.scan_finished()
        
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
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.duplicate_data = json.load(f)
            
            self.file_label.config(text=f"{_('loaded')}: {os.path.basename(file_path)}")
            self.update_stats()
            self.update_group_list()
            self.update_status(f"{_('loaded_groups')}: {len(self.duplicate_data)}", "success")
            
        except Exception as e:
            messagebox.showerror(_("error"), f"{_('load_json_failed')}: {str(e)}")
            self.update_status(_("load_file_failed"), "danger")
            
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
        total_images = sum(len(group['files']) for group in self.duplicate_data)
        exact_groups = sum(1 for group in self.duplicate_data if group['reason'] == '完全相同')
        similar_groups = sum(1 for group in self.duplicate_data if '相似' in group['reason'])
        pure_groups = sum(1 for group in self.duplicate_data if group['reason'] == '纯色图片')
        
        stats_text = f"{_('total_groups')}: {total_groups} | {_('total_images')}: {total_images} | {_('exact_same')}: {exact_groups}{_('groups')} | {_('similar_images')}: {similar_groups}{_('groups')} | {_('pure_color_images')}: {pure_groups}{_('groups')}"
        self.stats_label.config(text=stats_text)
        
    def update_group_list(self):
        """更新组列表"""
        self.group_listbox.delete(0, tk.END)
        
        for i, group in enumerate(self.duplicate_data):
            group_text = f"{_('group')}{i+1}: {group['reason']} ({len(group['files'])}{_('images')})"
            self.group_listbox.insert(tk.END, group_text)
            
    def on_group_select(self, event):
        """组选择事件"""
        selection = self.group_listbox.curselection()
        if not selection:
            return
            
        self.current_group_index = selection[0]
        self.display_group_images()
        
    def display_group_images(self):
        """显示组内图片"""
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
        if len(self.image_cache) > 30:
            cache_items = list(self.image_cache.items())
            self.image_cache = dict(cache_items[-30:])
            
        if not self.duplicate_data or self.current_group_index >= len(self.duplicate_data):
            return
            
        group = self.duplicate_data[self.current_group_index]
        
        # 显示组信息
        info_label = ttk.Label(self.images_frame, text=f"{group['reason']} - {len(group['files'])}{_('images')}", 
                              font=('Arial', 12, 'bold'))
        info_label.pack(pady=(0, 10))
        
        # 显示图片
        for i, file_path in enumerate(group['files']):
            self.create_image_widget(file_path, i)
            
        # 更新滚动区域
        self.images_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
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
            if file_info['path'] == file_path:
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
                print(f"队列处理错误: {e}")
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

def main():
    try:
        # 尝试使用ttkbootstrap的superhero主题（深蓝色专业主题）
        import ttkbootstrap as ttk
        root = ttk.Window(themename="superhero")
        print("使用ttkbootstrap superhero主题")
    except ImportError:
        # 如果没有安装ttkbootstrap，使用标准tkinter
        root = tk.Tk()
        print("使用标准tkinter主题")
    
    app = IntegratedDuplicateApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()