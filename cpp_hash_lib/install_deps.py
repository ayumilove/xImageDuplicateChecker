#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows环境依赖自动安装脚本

帮助用户在Windows环境下自动安装编译C++哈希库所需的依赖
"""

import os
import sys
import subprocess
import platform
import urllib.request
import tempfile
from pathlib import Path


def is_admin():
    """
    检查是否以管理员权限运行
    
    Returns:
        bool: 是否为管理员权限
    """
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """
    以管理员权限重新运行脚本
    """
    try:
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
    except Exception as e:
        print(f"无法以管理员权限运行: {e}")
        return False
    return True


def check_command(cmd):
    """
    检查命令是否可用
    
    Args:
        cmd: 命令名称
        
    Returns:
        bool: 命令是否可用
    """
    try:
        subprocess.run(
            [cmd, '--version'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_chocolatey():
    """
    安装Chocolatey包管理器
    
    Returns:
        bool: 安装是否成功
    """
    print("正在安装Chocolatey包管理器...")
    
    try:
        # 设置执行策略
        subprocess.run([
            'powershell', '-Command',
            'Set-ExecutionPolicy Bypass -Scope Process -Force'
        ], check=True)
        
        # 安装Chocolatey
        install_script = (
            "[System.Net.ServicePointManager]::SecurityProtocol = "
            "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
            "iex ((New-Object System.Net.WebClient).DownloadString("
            "'https://community.chocolatey.org/install.ps1'))"
        )
        
        subprocess.run([
            'powershell', '-Command', install_script
        ], check=True)
        
        print("✓ Chocolatey安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Chocolatey安装失败: {e}")
        return False


def install_with_chocolatey(packages):
    """
    使用Chocolatey安装包
    
    Args:
        packages: 要安装的包列表
        
    Returns:
        bool: 安装是否成功
    """
    if not check_command('choco'):
        print("Chocolatey未安装，正在安装...")
        if not install_chocolatey():
            return False
        
        # 刷新环境变量
        os.environ['PATH'] = os.environ.get('PATH', '') + ';C:\\ProgramData\\chocolatey\\bin'
    
    print(f"正在使用Chocolatey安装: {', '.join(packages)}")
    
    try:
        cmd = ['choco', 'install'] + packages + ['-y']
        subprocess.run(cmd, check=True)
        print("✓ 包安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 包安装失败: {e}")
        return False


def install_with_winget(packages):
    """
    使用winget安装包
    
    Args:
        packages: 要安装的包列表（包含包ID）
        
    Returns:
        bool: 安装是否成功
    """
    if not check_command('winget'):
        print("winget不可用（需要Windows 10 1709+）")
        return False
    
    print(f"正在使用winget安装包...")
    
    success = True
    for package in packages:
        try:
            print(f"安装 {package}...")
            subprocess.run(['winget', 'install', package, '--silent'], check=True)
            print(f"✓ {package} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"✗ {package} 安装失败: {e}")
            success = False
    
    return success


def download_and_install_cmake():
    """
    下载并安装CMake
    
    Returns:
        bool: 安装是否成功
    """
    print("正在下载CMake安装包...")
    
    try:
        # CMake下载URL（可能需要更新版本号）
        cmake_url = "https://github.com/Kitware/CMake/releases/download/v3.27.7/cmake-3.27.7-windows-x86_64.msi"
        
        # 下载到临时目录
        with tempfile.NamedTemporaryFile(suffix='.msi', delete=False) as tmp_file:
            print("下载中...")
            urllib.request.urlretrieve(cmake_url, tmp_file.name)
            
            print("正在安装CMake...")
            # 静默安装CMake
            subprocess.run([
                'msiexec', '/i', tmp_file.name, 
                '/quiet', '/norestart',
                'ADD_CMAKE_TO_PATH=System'
            ], check=True)
            
            # 清理临时文件
            os.unlink(tmp_file.name)
        
        print("✓ CMake安装成功")
        return True
        
    except Exception as e:
        print(f"✗ CMake安装失败: {e}")
        return False


def install_visual_studio_buildtools():
    """
    下载并安装Visual Studio Build Tools
    
    Returns:
        bool: 安装是否成功
    """
    print("正在下载Visual Studio Build Tools...")
    
    try:
        # VS Build Tools下载URL
        vs_url = "https://aka.ms/vs/17/release/vs_buildtools.exe"
        
        # 下载到临时目录
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as tmp_file:
            print("下载中...")
            urllib.request.urlretrieve(vs_url, tmp_file.name)
            
            print("正在安装Visual Studio Build Tools...")
            print("注意：这可能需要几分钟时间")
            
            # 静默安装VS Build Tools
            subprocess.run([
                tmp_file.name,
                '--quiet', '--wait',
                '--add', 'Microsoft.VisualStudio.Workload.VCTools',
                '--add', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
                '--add', 'Microsoft.VisualStudio.Component.Windows10SDK.19041'
            ], check=True)
            
            # 清理临时文件
            os.unlink(tmp_file.name)
        
        print("✓ Visual Studio Build Tools安装成功")
        return True
        
    except Exception as e:
        print(f"✗ Visual Studio Build Tools安装失败: {e}")
        return False


def refresh_environment():
    """
    刷新环境变量
    """
    print("刷新环境变量...")
    
    # 常见的安装路径
    cmake_paths = [
        'C:\\Program Files\\CMake\\bin',
        'C:\\Program Files (x86)\\CMake\\bin'
    ]
    
    vs_paths = [
        'C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\*\\bin\\Hostx64\\x64',
        'C:\\Program Files\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\*\\bin\\Hostx64\\x64'
    ]
    
    current_path = os.environ.get('PATH', '')
    
    # 添加CMake路径
    for path in cmake_paths:
        if os.path.exists(path) and path not in current_path:
            os.environ['PATH'] = current_path + ';' + path
            current_path = os.environ['PATH']
    
    print("环境变量已刷新")


def auto_install_dependencies():
    """
    自动安装依赖
    
    Returns:
        bool: 安装是否成功
    """
    print("开始自动安装依赖...")
    
    success = True
    
    # 检查当前状态
    cmake_available = check_command('cmake')
    compiler_available = any([
        check_command('cl'),
        check_command('gcc'),
        check_command('clang')
    ])
    
    print(f"当前状态:")
    print(f"  CMake: {'✓' if cmake_available else '✗'}")
    print(f"  编译器: {'✓' if compiler_available else '✗'}")
    
    # 尝试不同的安装方法
    if not cmake_available or not compiler_available:
        print("\n尝试方法1: 使用winget安装")
        winget_packages = []
        if not cmake_available:
            winget_packages.append('Kitware.CMake')
        if not compiler_available:
            winget_packages.append('Microsoft.VisualStudio.2022.BuildTools')
        
        if winget_packages and install_with_winget(winget_packages):
            refresh_environment()
            cmake_available = check_command('cmake')
            compiler_available = any([
                check_command('cl'),
                check_command('gcc'),
                check_command('clang')
            ])
    
    if not cmake_available or not compiler_available:
        print("\n尝试方法2: 使用Chocolatey安装")
        choco_packages = []
        if not cmake_available:
            choco_packages.append('cmake')
        if not compiler_available:
            choco_packages.append('visualstudio2022buildtools')
        
        if choco_packages and install_with_chocolatey(choco_packages):
            refresh_environment()
            cmake_available = check_command('cmake')
            compiler_available = any([
                check_command('cl'),
                check_command('gcc'),
                check_command('clang')
            ])
    
    if not cmake_available:
        print("\n尝试方法3: 直接下载安装CMake")
        if download_and_install_cmake():
            refresh_environment()
            cmake_available = check_command('cmake')
    
    if not compiler_available:
        print("\n尝试方法4: 直接下载安装Visual Studio Build Tools")
        if install_visual_studio_buildtools():
            refresh_environment()
            compiler_available = any([
                check_command('cl'),
                check_command('gcc'),
                check_command('clang')
            ])
    
    # 最终检查
    print("\n最终状态:")
    print(f"  CMake: {'✓' if cmake_available else '✗'}")
    print(f"  编译器: {'✓' if compiler_available else '✗'}")
    
    if cmake_available and compiler_available:
        print("\n✓ 所有依赖安装成功！")
        return True
    else:
        print("\n✗ 部分依赖安装失败")
        return False


def main():
    """
    主函数
    """
    print("Windows环境依赖自动安装脚本")
    print("=" * 50)
    
    if platform.system() != "Windows":
        print("此脚本仅适用于Windows系统")
        return
    
    # 检查管理员权限
    if not is_admin():
        print("检测到非管理员权限")
        choice = input("是否以管理员权限重新运行？(y/n): ").lower().strip()
        if choice == 'y':
            if run_as_admin():
                return
            else:
                print("无法获取管理员权限，将尝试用户级安装")
        else:
            print("将尝试用户级安装（可能会失败）")
    
    # 自动安装依赖
    if auto_install_dependencies():
        print("\n" + "=" * 50)
        print("依赖安装完成！")
        print("\n请重启命令行窗口，然后运行:")
        print("  python build.py")
        print("\n如果仍有问题，请查看 install_dependencies.md 获取手动安装指南")
    else:
        print("\n" + "=" * 50)
        print("自动安装失败！")
        print("\n请查看 install_dependencies.md 获取手动安装指南")
        print("或者访问以下链接手动下载安装:")
        print("  CMake: https://cmake.org/download/")
        print("  Visual Studio: https://visualstudio.microsoft.com/downloads/")


if __name__ == "__main__":
    main()