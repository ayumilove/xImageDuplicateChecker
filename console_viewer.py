#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复图片控制台查看器
纯命令行界面，最稳定的查看方案
"""

import json
import os
import subprocess
import platform
from pathlib import Path

class ConsoleViewer:
    def __init__(self):
        self.duplicate_data = []
        self.current_group = 0
        
    def load_json_file(self, file_path=None):
        """加载JSON文件"""
        if not file_path:
            # 自动查找results目录下的JSON文件
            results_dir = Path("results")
            if results_dir.exists():
                json_files = list(results_dir.glob("*.json"))
                if json_files:
                    print("\n发现以下JSON文件:")
                    for i, file in enumerate(json_files, 1):
                        print(f"{i}. {file.name}")
                    
                    try:
                        choice = int(input("\n请选择文件编号: ")) - 1
                        if 0 <= choice < len(json_files):
                            file_path = json_files[choice]
                        else:
                            print("无效选择")
                            return False
                    except ValueError:
                        print("无效输入")
                        return False
                else:
                    print("results目录下没有找到JSON文件")
                    return False
            else:
                print("未找到results目录")
                return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.duplicate_data = json.load(f)
            print(f"\n成功加载: {file_path}")
            self.show_stats()
            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False
    
    def show_stats(self):
        """显示统计信息"""
        if not self.duplicate_data:
            return
            
        total_groups = len(self.duplicate_data)
        total_images = sum(len(group['files']) for group in self.duplicate_data)
        exact_groups = sum(1 for group in self.duplicate_data if group['reason'] == '完全相同')
        similar_groups = sum(1 for group in self.duplicate_data if '相似' in group['reason'])
        pure_groups = sum(1 for group in self.duplicate_data if group['reason'] == '纯色图片')
        
        print("\n" + "="*60)
        print("统计信息")
        print("="*60)
        print(f"总组数: {total_groups}")
        print(f"总图片数: {total_images}")
        print(f"完全相同: {exact_groups}组")
        print(f"相似图片: {similar_groups}组")
        print(f"纯色图片: {pure_groups}组")
        print("="*60)
    
    def show_group_list(self):
        """显示组列表"""
        if not self.duplicate_data:
            print("没有数据")
            return
            
        print("\n重复组列表:")
        print("-" * 50)
        for i, group in enumerate(self.duplicate_data):
            marker = ">>> " if i == self.current_group else "    "
            print(f"{marker}{i+1:3d}. {group['reason']} ({len(group['files'])}张图片)")
        print("-" * 50)
    
    def show_current_group(self):
        """显示当前组的详细信息"""
        if not self.duplicate_data or self.current_group >= len(self.duplicate_data):
            print("没有数据")
            return
            
        group = self.duplicate_data[self.current_group]
        print(f"\n当前组 {self.current_group + 1}: {group['reason']}")
        print("=" * 60)
        
        for i, file_path in enumerate(group['files'], 1):
            print(f"\n{i}. {os.path.basename(file_path)}")
            print(f"   路径: {file_path}")
            
            # 检查文件是否存在
            if os.path.exists(file_path):
                try:
                    stat = os.stat(file_path)
                    size_mb = stat.st_size / (1024 * 1024)
                    print(f"   大小: {size_mb:.2f} MB")
                except:
                    print("   大小: 无法获取")
            else:
                print("   状态: 文件不存在")
        
        print("\n操作选项:")
        print("o <编号> - 打开指定图片")
        print("f <编号> - 打开图片所在文件夹")
        print("c <编号> - 复制图片路径")
        print("d <编号> - 删除图片文件")
    
    def open_file(self, file_path):
        """打开文件"""
        try:
            if not os.path.exists(file_path):
                print("文件不存在")
                return
                
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            print("文件已打开")
        except Exception as e:
            print(f"打开文件失败: {e}")
    
    def open_folder(self, file_path):
        """打开文件夹"""
        try:
            if not os.path.exists(file_path):
                print("文件不存在")
                return
                
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                folder_path = os.path.dirname(file_path)
                subprocess.run(['xdg-open', folder_path])
            print("文件夹已打开")
        except Exception as e:
            print(f"打开文件夹失败: {e}")
    
    def copy_path(self, file_path):
        """复制路径到剪贴板"""
        try:
            if platform.system() == 'Windows':
                subprocess.run(['clip'], input=file_path.encode(), check=True)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['pbcopy'], input=file_path.encode(), check=True)
            else:  # Linux
                subprocess.run(['xclip', '-selection', 'clipboard'], input=file_path.encode(), check=True)
            print("路径已复制到剪贴板")
        except Exception as e:
            print(f"复制失败: {e}")
    
    def delete_file(self, file_path):
        """删除文件"""
        try:
            if not os.path.exists(file_path):
                print("文件不存在")
                return
                
            confirm = input(f"确定要删除文件吗? {os.path.basename(file_path)} (y/N): ")
            if confirm.lower() == 'y':
                os.remove(file_path)
                print("文件已删除")
            else:
                print("取消删除")
        except Exception as e:
            print(f"删除失败: {e}")
    
    def run(self):
        """主运行循环"""
        print("重复图片控制台查看器")
        print("=" * 30)
        
        # 加载数据
        if not self.load_json_file():
            return
        
        print("\n命令帮助:")
        print("l - 显示组列表")
        print("s - 显示当前组详情")
        print("n - 下一组")
        print("p - 上一组")
        print("g <编号> - 跳转到指定组")
        print("o <编号> - 打开当前组中的指定图片")
        print("f <编号> - 打开当前组中指定图片的文件夹")
        print("c <编号> - 复制当前组中指定图片的路径")
        print("d <编号> - 删除当前组中的指定图片")
        print("q - 退出")
        print("h - 显示帮助")
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if not cmd:
                    continue
                elif cmd == 'q':
                    break
                elif cmd == 'h':
                    print("\n命令帮助:")
                    print("l - 显示组列表")
                    print("s - 显示当前组详情")
                    print("n - 下一组")
                    print("p - 上一组")
                    print("g <编号> - 跳转到指定组")
                    print("o <编号> - 打开当前组中的指定图片")
                    print("f <编号> - 打开当前组中指定图片的文件夹")
                    print("c <编号> - 复制当前组中指定图片的路径")
                    print("d <编号> - 删除当前组中的指定图片")
                    print("q - 退出")
                elif cmd == 'l':
                    self.show_group_list()
                elif cmd == 's':
                    self.show_current_group()
                elif cmd == 'n':
                    if self.current_group < len(self.duplicate_data) - 1:
                        self.current_group += 1
                        self.show_current_group()
                    else:
                        print("已经是最后一组")
                elif cmd == 'p':
                    if self.current_group > 0:
                        self.current_group -= 1
                        self.show_current_group()
                    else:
                        print("已经是第一组")
                elif cmd.startswith('g '):
                    try:
                        group_num = int(cmd.split()[1]) - 1
                        if 0 <= group_num < len(self.duplicate_data):
                            self.current_group = group_num
                            self.show_current_group()
                        else:
                            print("组编号超出范围")
                    except (ValueError, IndexError):
                        print("无效的组编号")
                elif cmd.startswith(('o ', 'f ', 'c ', 'd ')):
                    try:
                        action = cmd[0]
                        file_num = int(cmd.split()[1]) - 1
                        group = self.duplicate_data[self.current_group]
                        
                        if 0 <= file_num < len(group['files']):
                            file_path = group['files'][file_num]
                            
                            if action == 'o':
                                self.open_file(file_path)
                            elif action == 'f':
                                self.open_folder(file_path)
                            elif action == 'c':
                                self.copy_path(file_path)
                            elif action == 'd':
                                self.delete_file(file_path)
                        else:
                            print("文件编号超出范围")
                    except (ValueError, IndexError):
                        print("无效的文件编号")
                else:
                    print("未知命令，输入 h 查看帮助")
                    
            except KeyboardInterrupt:
                print("\n\n再见!")
                break
            except Exception as e:
                print(f"发生错误: {e}")

def main():
    viewer = ConsoleViewer()
    viewer.run()

if __name__ == "__main__":
    main()