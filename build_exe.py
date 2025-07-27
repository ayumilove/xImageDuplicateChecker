#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用PyInstaller打包GUI应用程序为exe文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller已安装，版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("✗ PyInstaller未安装")
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ PyInstaller安装失败: {e}")
        return False

def create_spec_file():
    """创建PyInstaller spec文件"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件和隐藏导入
added_files = [
    ('src', 'src'),
    ('cpp_hash_lib/*.dll', 'cpp_hash_lib'),
    ('*.dll', '.'),
]

hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'ttkbootstrap',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'numpy',
    'threading',
    'queue',
    'json',
    'subprocess',
    'platform',
    'webbrowser',
    'cpp_hash_lib.cpp_duplicate_checker',
    'src.duplicate_checker',
    'src.enhanced_similarity_detector',
    'src.hash_utils',
    'src.result_logger',
    'src.rotation_invariant_hash',
    'i18n',
]

a = Analysis(
    ['integrated_desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='xImageDuplicateChecker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
)
'''
    
    with open('xImageDuplicateChecker.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✓ 已创建PyInstaller spec文件")

def build_exe():
    """构建exe文件"""
    print("开始构建exe文件...")
    try:
        # 使用spec文件构建
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "xImageDuplicateChecker.spec"]
        subprocess.check_call(cmd)
        print("✓ exe文件构建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ exe文件构建失败: {e}")
        return False

def copy_additional_files():
    """复制额外的文件到dist目录"""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("✗ dist目录不存在")
        return False
    
    # 查找exe文件目录
    exe_dir = None
    for item in dist_dir.iterdir():
        if item.is_dir():
            exe_dir = item
            break
    
    if not exe_dir:
        print("✗ 找不到exe目录")
        return False
    
    print(f"复制额外文件到: {exe_dir}")
    
    # 复制DLL文件
    dll_files = [
        "hash_algorithms.dll",
        "opencv_videoio_ffmpeg4120_64.dll", 
        "opencv_world4120.dll"
    ]
    
    for dll_file in dll_files:
        if os.path.exists(dll_file):
            shutil.copy2(dll_file, exe_dir)
            print(f"✓ 复制 {dll_file}")
        else:
            print(f"⚠ 未找到 {dll_file}")
    
    # 复制cpp_hash_lib目录中的DLL
    cpp_lib_dir = Path("cpp_hash_lib")
    if cpp_lib_dir.exists():
        target_cpp_dir = exe_dir / "cpp_hash_lib"
        target_cpp_dir.mkdir(exist_ok=True)
        
        for dll_file in cpp_lib_dir.glob("*.dll"):
            shutil.copy2(dll_file, target_cpp_dir)
            print(f"✓ 复制 {dll_file} 到 cpp_hash_lib")
    
    print("✓ 额外文件复制完成")
    return True

def create_readme():
    """创建使用说明"""
    readme_content = """
# xImageDuplicateChecker 使用说明

## 关于
这是一个重复图片检测工具的独立可执行版本。

## 使用方法
1. 双击 xImageDuplicateChecker.exe 启动程序
2. 在"扫描与检测"标签页中选择要扫描的目录
3. 调整检测参数（可选）
4. 点击"开始扫描"按钮
5. 扫描完成后，在"结果查看"标签页中查看重复图片

## 功能特性
- 支持多种图片格式（JPG, PNG, BMP, GIF等）
- 多种哈希算法检测相似图片
- 支持旋转图片识别
- 增强相似度检测（可检测缩放、旋转的图片）
- 纯色图片检测
- 直观的图形界面
- 多语言支持

## 系统要求
- Windows 7/8/10/11 (64位)
- 至少 2GB 内存
- 足够的磁盘空间用于临时文件

## 注意事项
- 首次运行可能需要较长时间初始化
- 扫描大量图片时请耐心等待
- 建议在扫描前关闭不必要的程序以释放内存

## 技术支持
GitHub: https://github.com/ayumilove/xImageDuplicateChecker

© 2024 xImageDuplicateChecker
MIT License
"""
    
    dist_dir = Path("dist")
    if dist_dir.exists():
        with open(dist_dir / "README.txt", 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("✓ 已创建使用说明文件")

def main():
    """主函数"""
    print("=" * 60)
    print("xImageDuplicateChecker exe打包工具")
    print("=" * 60)
    
    # 检查当前目录
    if not os.path.exists("integrated_desktop_app.py"):
        print("✗ 请在项目根目录运行此脚本")
        return False
    
    # 检查并安装PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            return False
    
    # 创建spec文件
    create_spec_file()
    
    # 构建exe
    if not build_exe():
        return False
    
    # 复制额外文件
    copy_additional_files()
    
    # 创建说明文件
    create_readme()
    
    print("\n" + "=" * 60)
    print("✓ 打包完成！")
    print("\n生成的文件位于 dist 目录中")
    print("可以将整个 dist 目录复制到其他计算机上运行")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按回车键退出...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户取消操作")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        sys.exit(1)
    
    input("\n按回车键退出...")