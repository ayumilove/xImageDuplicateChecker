#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复图片查看器启动脚本
用户可以选择使用控制台版本或桌面版本
"""

import sys
import os

def show_menu():
    print("="*50)
    print("重复图片查看器")
    print("="*50)
    print("请选择查看器类型:")
    print("1. 控制台版 (最稳定 - 推荐)")
    print("2. 桌面版 (GUI界面)")
    print("3. 退出")
    print("="*50)
    
def main():
    while True:
        show_menu()
        
        try:
            choice = input("请输入选择 (1-3): ").strip()
            
            if choice == '1':
                print("\n启动控制台版查看器...")
                try:
                    import console_viewer
                    console_viewer.main()
                except Exception as e:
                    print(f"启动控制台版失败: {e}")
                break
                
            elif choice == '2':
                print("\n启动桌面版查看器...")
                try:
                    import desktop_viewer
                    desktop_viewer.main()
                except ImportError as e:
                    print(f"错误: 缺少依赖库 - {e}")
                    print("请运行: pip install -r requirements.txt")
                except Exception as e:
                    print(f"启动桌面版失败: {e}")
                break
                
            elif choice == '3':
                print("\n再见!")
                break
                
            else:
                print("\n无效选择，请重新输入!")
                input("按回车键继续...")
                
        except KeyboardInterrupt:
            print("\n\n用户取消操作")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            input("按回车键继续...")

if __name__ == "__main__":
    main()