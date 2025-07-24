#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复图片查看器服务器启动脚本
用于启动本地HTTP服务器，以便在浏览器中查看重复图片
"""

import os
import sys
import webbrowser
import http.server
import socketserver
from pathlib import Path

def start_server(port=8000):
    """
    启动本地HTTP服务器
    
    Args:
        port (int): 服务器端口，默认8000
    """
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent.absolute()
    
    # 切换到项目根目录
    os.chdir(current_dir)
    
    # 检查HTML文件是否存在
    html_file = current_dir / "image_viewer.html"
    if not html_file.exists():
        print(f"错误: 找不到 {html_file}")
        return
    
    # 检查是否有查重结果文件
    results_dir = current_dir / "results"
    json_files = list(results_dir.glob("*.json")) if results_dir.exists() else []
    
    print("=" * 60)
    print("重复图片查看器服务器")
    print("=" * 60)
    print(f"服务器目录: {current_dir}")
    print(f"服务器端口: {port}")
    
    if json_files:
        print(f"\n发现 {len(json_files)} 个查重结果文件:")
        for json_file in sorted(json_files):
            print(f"  - {json_file.name}")
    else:
        print("\n警告: 未发现查重结果JSON文件")
    
    print(f"\n浏览器访问地址: http://localhost:{port}/image_viewer.html")
    print("\n使用说明:")
    print("1. 在浏览器中打开上述地址")
    print("2. 点击'选择文件'按钮，选择查重结果JSON文件")
    print("3. 查看重复图片并点击'复制完整路径'按钮复制图片路径")
    print("4. 按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        # 创建HTTP服务器
        handler = http.server.SimpleHTTPRequestHandler
        
        # 添加CORS头部，允许跨域访问
        class CORSRequestHandler(handler):
            def end_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                super().end_headers()
        
        with socketserver.TCPServer(("", port), CORSRequestHandler) as httpd:
            print(f"\n服务器已启动，监听端口 {port}...")
            
            # 自动打开浏览器
            try:
                webbrowser.open(f'http://localhost:{port}/image_viewer.html')
                print("已自动打开浏览器")
            except Exception as e:
                print(f"无法自动打开浏览器: {e}")
                print("请手动在浏览器中访问上述地址")
            
            # 启动服务器
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n错误: 端口 {port} 已被占用")
            print(f"请尝试使用其他端口: python start_viewer.py --port 8001")
        else:
            print(f"\n错误: {e}")
    except Exception as e:
        print(f"\n意外错误: {e}")

def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='启动重复图片查看器服务器')
    parser.add_argument('--port', '-p', type=int, default=8000, 
                       help='服务器端口 (默认: 8000)')
    
    args = parser.parse_args()
    
    start_server(args.port)

if __name__ == "__main__":
    main()