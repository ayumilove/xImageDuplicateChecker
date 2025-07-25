#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复图片桌面查看器
使用tkinter GUI界面，无需web服务器
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from PIL import Image, ImageTk
import threading
import subprocess
import platform
import queue
import time

class DuplicateImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("重复图片查看器 - 桌面版")
        self.root.geometry("1200x800")
        
        self.duplicate_data = []
        self.current_group_index = 0
        self.image_cache = {}
        self.loading_threads = 0
        self.max_concurrent_loads = 3  # 限制同时加载的图片数量
        self.load_queue = queue.Queue()  # 图片加载队列
        self.queue_processor_running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(file_frame, text="选择JSON文件", command=self.load_json_file).pack(side=tk.LEFT, padx=(0, 10))
        self.file_label = ttk.Label(file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT)
        
        # 统计信息区域
        self.stats_frame = ttk.LabelFrame(main_frame, text="统计信息", padding="5")
        self.stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.stats_label = ttk.Label(self.stats_frame, text="")
        self.stats_label.pack()
        
        # 左侧：组列表
        left_frame = ttk.LabelFrame(main_frame, text="重复组列表", padding="5")
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
        right_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="5")
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
        
    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def load_json_file(self):
        file_path = filedialog.askopenfilename(
            title="选择查重结果JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.duplicate_data = json.load(f)
            
            self.file_label.config(text=f"已加载: {os.path.basename(file_path)}")
            self.update_stats()
            self.update_group_list()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载JSON文件失败: {str(e)}")
            
    def update_stats(self):
        if not self.duplicate_data:
            return
            
        total_groups = len(self.duplicate_data)
        total_images = sum(len(group['files']) for group in self.duplicate_data)
        exact_groups = sum(1 for group in self.duplicate_data if group['reason'] == '完全相同')
        similar_groups = sum(1 for group in self.duplicate_data if '相似' in group['reason'])
        pure_groups = sum(1 for group in self.duplicate_data if group['reason'] == '纯色图片')
        
        stats_text = f"总组数: {total_groups} | 总图片数: {total_images} | 完全相同: {exact_groups}组 | 相似图片: {similar_groups}组 | 纯色图片: {pure_groups}组"
        self.stats_label.config(text=stats_text)
        
    def update_group_list(self):
        self.group_listbox.delete(0, tk.END)
        
        for i, group in enumerate(self.duplicate_data):
            group_text = f"组{i+1}: {group['reason']} ({len(group['files'])}张)"
            self.group_listbox.insert(tk.END, group_text)
            
    def on_group_select(self, event):
        selection = self.group_listbox.curselection()
        if not selection:
            return
            
        self.current_group_index = selection[0]
        self.display_group_images()
        
    def display_group_images(self):
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
            # 保留最近的30张图片缓存
            cache_items = list(self.image_cache.items())
            self.image_cache = dict(cache_items[-30:])
            
        if not self.duplicate_data or self.current_group_index >= len(self.duplicate_data):
            return
            
        group = self.duplicate_data[self.current_group_index]
        
        # 显示组信息
        info_label = ttk.Label(self.images_frame, text=f"{group['reason']} - {len(group['files'])}张图片", 
                              font=('Arial', 12, 'bold'))
        info_label.pack(pady=(0, 10))
        
        # 显示图片
        for i, file_path in enumerate(group['files']):
            self.create_image_widget(file_path, i)
            
        # 更新滚动区域
        self.images_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def create_image_widget(self, file_path, index):
        # 创建图片容器
        img_frame = ttk.Frame(self.images_frame, relief="solid", borderwidth=1)
        img_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件名标签
        filename = os.path.basename(file_path)
        name_label = ttk.Label(img_frame, text=filename, font=('Arial', 10, 'bold'))
        name_label.pack(pady=(5, 0))
        
        # 图片标签（占位符）
        img_label = ttk.Label(img_frame, text="加载中...", background="lightgray")
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
        copy_btn = ttk.Button(btn_frame, text="复制路径", 
                             command=lambda: self.copy_path(file_path))
        copy_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 打开文件按钮
        open_btn = ttk.Button(btn_frame, text="打开文件", 
                             command=lambda: self.open_file(file_path))
        open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 打开文件夹按钮
        folder_btn = ttk.Button(btn_frame, text="打开文件夹", 
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
            distance_text = f"dHash距离: {distance_info['dhash_distance']} | pHash距离: {distance_info['phash_distance']} | aHash距离: {distance_info['ahash_distance']}"
            distance_label = ttk.Label(distance_frame, text=distance_text, 
                                     font=('Arial', 8), foreground="blue")
            distance_label.pack()
        elif index == 0:
            # 基准文件标识
            base_frame = ttk.Frame(parent_frame)
            base_frame.pack(pady=(0, 5))
            
            base_label = ttk.Label(base_frame, text="基准图片 (距离: 0)", 
                                 font=('Arial', 8), foreground="green")
            base_label.pack()
        
    def process_load_queue(self):
        """处理图片加载队列"""
        while True:
            try:
                # 等待队列中的加载请求
                file_path, img_label = self.load_queue.get(timeout=1)
                
                # 等待直到有可用的加载槽位
                while self.loading_threads >= self.max_concurrent_loads:
                    time.sleep(0.1)
                
                # 启动加载线程
                self.loading_threads += 1
                threading.Thread(target=self.load_image_async, 
                                args=(file_path, img_label), daemon=True).start()
                
                self.load_queue.task_done()
                
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                print(f"队列处理错误: {e}")
                continue
    
    def load_image_async(self, file_path, img_label):
        try:
            if not os.path.exists(file_path):
                self.root.after(0, lambda: self.safe_update_label(img_label, text="文件不存在", foreground="red"))
                return
                
            # 检查缓存
            if file_path in self.image_cache:
                photo = self.image_cache[file_path]
                self.root.after(0, lambda: self.safe_update_image_label(img_label, photo))
                return
                
            # 加载并调整图片大小
            with Image.open(file_path) as img:
                # 计算缩放比例
                max_size = (200, 150)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换为tkinter可用格式
                photo = ImageTk.PhotoImage(img)
                
                # 缓存图片（限制缓存大小）
                if len(self.image_cache) < 50:  # 最多缓存50张图片
                    self.image_cache[file_path] = photo
                
                # 更新UI（必须在主线程中）
                self.root.after(0, lambda: self.safe_update_image_label(img_label, photo))
                
        except Exception as e:
            self.root.after(0, lambda: self.safe_update_label(img_label, text=f"加载失败: {str(e)}", foreground="red"))
        finally:
            # 减少加载线程计数
            self.loading_threads = max(0, self.loading_threads - 1)
            
    def safe_update_image_label(self, img_label, photo):
        try:
            # 检查组件是否仍然存在
            if img_label.winfo_exists():
                img_label.config(image=photo, text="")
                img_label.image = photo  # 保持引用
        except tk.TclError:
            # 组件已被销毁，忽略错误
            pass
            
    def safe_update_label(self, img_label, text="", foreground="black"):
        try:
            # 检查组件是否仍然存在
            if img_label.winfo_exists():
                img_label.config(text=text, foreground=foreground)
        except tk.TclError:
            # 组件已被销毁，忽略错误
            pass
        
    def copy_path(self, file_path):
        self.root.clipboard_clear()
        self.root.clipboard_append(file_path)
        messagebox.showinfo("成功", "路径已复制到剪贴板")
        
    def open_file(self, file_path):
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")
            
    def open_folder(self, file_path):
        try:
            folder_path = os.path.dirname(file_path)
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")

def main():
    root = tk.Tk()
    app = DuplicateImageViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()