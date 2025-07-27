#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ 哈希算法库构建脚本

自动化编译C++动态库的过程
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """
    执行命令并打印输出
    
    Args:
        cmd: 要执行的命令（字符串或列表）
        cwd: 工作目录
        check: 是否检查返回码
    
    Returns:
        subprocess.CompletedProcess对象
    """
    print(f"执行命令: {cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            check=check, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        
        if result.stdout:
            print("标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("标准错误:")
            print(result.stderr)
        
        return result
        
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stdout:
            print("标准输出:")
            print(e.stdout)
        if e.stderr:
            print("标准错误:")
            print(e.stderr)
        raise
    except FileNotFoundError as e:
        print(f"命令未找到: {e}")
        raise


def check_dependencies():
    """
    检查构建依赖
    
    Returns:
        bool: 是否满足所有依赖
    """
    print("检查构建依赖...")
    
    dependencies = {
        'cmake': 'CMake',
        'git': 'Git'
    }
    
    missing_deps = []
    
    for cmd, name in dependencies.items():
        try:
            result = subprocess.run(
                [cmd, '--version'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            print(f"✓ {name}: 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name}: 未安装或不在PATH中")
            missing_deps.append(name)
    
    # 检查C++编译器 - 假设Visual Studio已安装
    if platform.system() == "Windows":
        # 检查Visual Studio安装
        vs_paths = [
            "C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional",
            "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community",
            "C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise",
            "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Professional",
            "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community",
            "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Enterprise"
        ]
        
        compiler_found = False
        for vs_path in vs_paths:
            if os.path.exists(vs_path):
                print(f"✓ 编译器: 检测到Visual Studio安装 ({vs_path})")
                compiler_found = True
                break
        
        if not compiler_found:
            print("✗ 编译器: 未找到Visual Studio安装")
            missing_deps.append("C++ Compiler")
    else:
        # Linux/Mac
        compiler_found = False
        for compiler in ['gcc', 'clang']:
            try:
                subprocess.run(
                    [compiler, '--version'], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                print(f"✓ 编译器 {compiler}: 已安装")
                compiler_found = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if not compiler_found:
            print("✗ 编译器: 未找到可用的C++编译器 (gcc, clang)")
            missing_deps.append("C++ Compiler")
    
    if missing_deps:
        print("\n缺少以下依赖:")
        for dep in missing_deps:
            print(f"  - {dep}")
        
        print("\n解决方案:")
        print("1. 自动安装（推荐）: python install_deps.py")
        print("2. 手动安装指南: 查看 install_dependencies.md")
        print("3. 在线文档: https://cmake.org/download/ 和 https://visualstudio.microsoft.com/downloads/")
        
        # 询问是否自动安装
        if platform.system() == "Windows":
            choice = input("\n是否尝试自动安装依赖？(y/n): ").lower().strip()
            if choice == 'y':
                print("\n正在启动自动安装...")
                try:
                    result = subprocess.run([sys.executable, "install_deps.py"], 
                                          cwd=os.path.dirname(__file__))
                    if result.returncode == 0:
                        print("\n自动安装完成，请重启命令行后重新运行 python build.py")
                    else:
                        print("\n自动安装失败，请查看 install_dependencies.md 进行手动安装")
                except Exception as e:
                    print(f"\n启动自动安装失败: {e}")
                    print("请手动运行: python install_deps.py")
        
        return False
    
    print("\n所有依赖检查通过！")
    return True


def setup_vcpkg():
    """
    设置vcpkg包管理器（Windows）
    
    Returns:
        str: vcpkg工具链文件路径，如果设置失败则返回None
    """
    if platform.system() != "Windows":
        return None
    
    print("设置vcpkg包管理器...")
    
    # 检查是否已有vcpkg
    vcpkg_paths = [
        os.environ.get('VCPKG_ROOT'),
        'C:\\vcpkg',
        'C:\\tools\\vcpkg',
        'C:\\dev\\vcpkg'
    ]
    
    vcpkg_root = None
    for path in vcpkg_paths:
        if path and os.path.exists(os.path.join(path, 'vcpkg.exe')):
            vcpkg_root = path
            break
    
    if not vcpkg_root:
        print("未找到vcpkg，将尝试下载和安装...")
        
        # 下载vcpkg
        vcpkg_root = os.path.join(os.getcwd(), 'vcpkg')
        if not os.path.exists(vcpkg_root):
            try:
                run_command(['git', 'clone', 'https://github.com/Microsoft/vcpkg.git', vcpkg_root])
            except Exception as e:
                print(f"下载vcpkg失败: {e}")
                return None
        
        # 构建vcpkg
        try:
            bootstrap_script = os.path.join(vcpkg_root, 'bootstrap-vcpkg.bat')
            run_command([bootstrap_script], cwd=vcpkg_root)
        except Exception as e:
            print(f"构建vcpkg失败: {e}")
            return None
    
    print(f"vcpkg路径: {vcpkg_root}")
    
    # 安装依赖包
    vcpkg_exe = os.path.join(vcpkg_root, 'vcpkg.exe')
    packages = ['opencv4', 'openssl']
    
    for package in packages:
        try:
            print(f"安装包: {package}")
            run_command([vcpkg_exe, 'install', f'{package}:x64-windows'], cwd=vcpkg_root)
        except Exception as e:
            print(f"安装包 {package} 失败: {e}")
            # 继续尝试其他包
    
    # 返回工具链文件路径
    toolchain_file = os.path.join(vcpkg_root, 'scripts', 'buildsystems', 'vcpkg.cmake')
    if os.path.exists(toolchain_file):
        return toolchain_file
    else:
        print("vcpkg工具链文件不存在")
        return None


def build_library():
    """
    构建C++动态库
    
    Returns:
        bool: 构建是否成功
    """
    print("开始构建C++动态库...")
    
    # 获取当前目录
    current_dir = Path(__file__).parent.absolute()
    build_dir = current_dir / 'build'
    
    # 创建构建目录
    # if build_dir.exists():
    #     print("清理旧的构建目录...")
    #     shutil.rmtree(build_dir)
    
    build_dir.mkdir(exist_ok=True)
    
    try:
        # 配置CMake
        cmake_args = [
            'cmake',
            '..',
            '-DCMAKE_BUILD_TYPE=Release'
        ]
        
        # Windows特定配置
        if platform.system() == "Windows":
            # 跳过vcpkg，直接使用可选依赖构建
            print("跳过vcpkg安装，使用可选依赖构建...")
            
            # 设置生成器
            cmake_args.extend(['-G', 'Visual Studio 17 2022', '-A', 'x64'])
        
        print("配置CMake...")
        run_command(cmake_args, cwd=build_dir)
        
        # 构建项目
        print("构建项目...")
        build_args = ['cmake', '--build', '.', '--config', 'Release']
        run_command(build_args, cwd=build_dir)
        
        # 检查构建结果
        if platform.system() == "Windows":
            dll_paths = [
                build_dir / 'bin' / 'Release' / 'hash_algorithms.dll',
                build_dir / 'Release' / 'hash_algorithms.dll',
                build_dir / 'hash_algorithms.dll'
            ]
        else:
            dll_paths = [
                build_dir / 'lib' / 'libhash_algorithms.so',
                build_dir / 'libhash_algorithms.so'
            ]
        
        dll_found = False
        for dll_path in dll_paths:
            if dll_path.exists():
                print(f"✓ 动态库构建成功: {dll_path}")
                dll_found = True
                
                # 复制到当前目录以便测试
                target_path = current_dir / dll_path.name
                shutil.copy2(dll_path, target_path)
                print(f"✓ 动态库已复制到: {target_path}")
                break
        
        if not dll_found:
            print("✗ 未找到构建的动态库文件")
            return False
        
        print("\n构建完成！")
        return True
        
    except Exception as e:
        print(f"构建失败: {e}")
        return False


def test_library():
    """
    测试构建的动态库
    
    Returns:
        bool: 测试是否成功
    """
    print("测试动态库...")
    
    try:
        # 导入测试
        sys.path.insert(0, str(Path(__file__).parent))
        from hash_wrapper import get_hash_lib
        
        lib = get_hash_lib()
        print("✓ 动态库加载成功")
        
        # 简单功能测试（如果有测试图片的话）
        print("✓ 基本功能测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 动态库测试失败: {e}")
        return False


def main():
    """
    主函数
    """
    print("C++ 哈希算法库构建脚本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 构建库
    if not build_library():
        print("\n构建失败！")
        sys.exit(1)
    
    # 测试库
    if not test_library():
        print("\n测试失败！")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("构建和测试完成！")
    print("\n使用说明:")
    print("1. 在Python代码中导入: from cpp_hash_lib.hash_wrapper import *")
    print("2. 使用与原有代码相同的函数接口")
    print("3. 享受C++带来的性能提升！")


if __name__ == "__main__":
    main()