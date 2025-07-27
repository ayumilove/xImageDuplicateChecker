#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建完整的分发包
"""

import os
import shutil
import zipfile
from pathlib import Path
import datetime

def create_distribution():
    """创建完整的分发包"""
    print("创建完整的分发包...")
    
    # 检查exe文件是否存在
    exe_file = Path("dist/xImageDuplicateChecker.exe")
    if not exe_file.exists():
        print("✗ 找不到exe文件，请先运行 build_exe.py")
        return False
    
    # 创建分发目录
    dist_name = f"xImageDuplicateChecker_v1.0_{datetime.datetime.now().strftime('%Y%m%d')}"
    dist_dir = Path(f"release/{dist_name}")
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"创建分发目录: {dist_dir}")
    
    # 复制exe文件
    shutil.copy2(exe_file, dist_dir / "xImageDuplicateChecker.exe")
    print("✓ 复制exe文件")
    
    # 复制DLL文件
    dll_files = [
        "hash_algorithms.dll",
        "opencv_videoio_ffmpeg4120_64.dll", 
        "opencv_world4120.dll"
    ]
    
    for dll_file in dll_files:
        if os.path.exists(dll_file):
            shutil.copy2(dll_file, dist_dir)
            print(f"✓ 复制 {dll_file}")
        else:
            print(f"⚠ 未找到 {dll_file}")
    
    # 复制cpp_hash_lib目录中的DLL
    cpp_lib_dir = Path("cpp_hash_lib")
    if cpp_lib_dir.exists():
        target_cpp_dir = dist_dir / "cpp_hash_lib"
        target_cpp_dir.mkdir(exist_ok=True)
        
        for dll_file in cpp_lib_dir.glob("*.dll"):
            shutil.copy2(dll_file, target_cpp_dir)
            print(f"✓ 复制 {dll_file} 到 cpp_hash_lib")
    
    # 创建详细的使用说明
    create_detailed_readme(dist_dir)
    
    # 复制许可证文件
    if os.path.exists("LICENSE"):
        shutil.copy2("LICENSE", dist_dir)
        print("✓ 复制许可证文件")
    
    # 创建ZIP压缩包
    zip_file = Path(f"release/{dist_name}.zip")
    create_zip_package(dist_dir, zip_file)
    
    print(f"\n✓ 分发包创建完成！")
    print(f"目录版本: {dist_dir}")
    print(f"压缩包版本: {zip_file}")
    print(f"\n可以将 {zip_file} 分享给其他用户")
    
    return True

def create_detailed_readme(dist_dir):
    """创建详细的使用说明"""
    readme_content = f"""
# xImageDuplicateChecker v1.0 - 重复图片检测工具

## 📋 关于
这是一个功能强大的重复图片检测工具，可以帮助您快速找到计算机中的重复图片文件。

## 🚀 主要功能
- **多种检测算法**: 支持dHash、pHash、aHash等多种图片哈希算法
- **旋转检测**: 能够识别旋转后的相同图片
- **缩放检测**: 支持检测不同尺寸的相同图片
- **增强相似度检测**: 使用先进算法检测经过变换的相似图片
- **纯色图片检测**: 自动识别和标记纯色或接近纯色的图片
- **批量处理**: 支持递归扫描整个目录树
- **直观界面**: 友好的图形用户界面，操作简单
- **多语言支持**: 支持中文和英文界面
- **多种格式**: 支持JPG、PNG、BMP、GIF、TIFF等常见图片格式

## 💻 系统要求
- **操作系统**: Windows 7/8/10/11 (64位)
- **内存**: 建议至少 4GB RAM
- **磁盘空间**: 至少 100MB 可用空间
- **处理器**: 支持SSE2指令集的处理器

## 📖 使用方法

### 1. 启动程序
双击 `xImageDuplicateChecker.exe` 启动程序

### 2. 扫描图片
1. 切换到"扫描与检测"标签页
2. 点击"选择目录"按钮，选择要扫描的文件夹
3. 根据需要调整检测参数：
   - **递归扫描**: 是否扫描子文件夹
   - **检测纯色图片**: 是否标记纯色图片
   - **增强相似度检测**: 是否启用高级检测算法
   - **哈希阈值**: 调整相似度敏感度（数值越小越严格）
4. 点击"开始扫描"按钮开始检测

### 3. 查看结果
1. 扫描完成后，切换到"结果查看"标签页
2. 程序会自动加载最新的扫描结果
3. 使用"上一组"和"下一组"按钮浏览不同的重复图片组
4. 对于每张图片，您可以：
   - 📋 复制文件路径
   - 🖼️ 打开图片文件
   - 📁 打开文件所在文件夹

### 4. 保存和加载结果
- 扫描结果会自动保存为JSON格式
- 可以通过"文件"菜单加载之前的扫描结果
- 支持导出为CSV格式便于进一步分析

## ⚙️ 参数说明

### 哈希阈值
- **dHash阈值**: 默认12，范围0-64，数值越小检测越严格
- **pHash阈值**: 默认4，范围0-64，数值越小检测越严格  
- **aHash阈值**: 默认4，范围0-64，数值越小检测越严格

### 增强相似度检测
- 启用后可以检测旋转、缩放后的图片
- 计算量较大，处理时间会增加
- 建议在普通检测无法满足需求时使用

### 置信度阈值
- 仅在增强相似度检测中使用
- 范围0.0-1.0，建议值0.5-0.8
- 数值越高要求相似度越高

## 🔧 故障排除

### 程序无法启动
- 确保您的系统是64位Windows
- 尝试以管理员身份运行
- 检查是否有杀毒软件误报

### 扫描速度慢
- 关闭增强相似度检测可以显著提升速度
- 适当提高哈希阈值可以减少计算量
- 确保有足够的可用内存

### 检测结果不准确
- 降低哈希阈值可以提高检测精度
- 启用增强相似度检测可以找到更多相似图片
- 调整置信度阈值来过滤误报

### 内存不足
- 分批处理大量图片
- 关闭其他不必要的程序
- 考虑升级系统内存

## 📁 文件说明
- `xImageDuplicateChecker.exe`: 主程序文件
- `*.dll`: 必需的动态链接库文件
- `cpp_hash_lib/`: C++加速库文件夹
- `README.txt`: 本说明文件
- `LICENSE`: 软件许可证

## 🔒 隐私和安全
- 本软件完全在本地运行，不会上传任何数据
- 不会修改或删除您的图片文件
- 仅读取图片文件进行分析，不会泄露隐私

## 📞 技术支持
- **GitHub项目**: https://github.com/ayumilove/xImageDuplicateChecker
- **问题反馈**: 请在GitHub上提交Issue
- **功能建议**: 欢迎在GitHub上提交Feature Request

## 📄 版本信息
- **版本**: v1.0
- **发布日期**: {datetime.datetime.now().strftime('%Y年%m月%d日')}
- **许可证**: MIT License

## 🙏 致谢
感谢所有为这个项目贡献代码和建议的开发者们！

---
© 2024 xImageDuplicateChecker Team
"""
    
    with open(dist_dir / "README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✓ 创建详细使用说明")

def create_zip_package(source_dir, zip_path):
    """创建ZIP压缩包"""
    print(f"创建压缩包: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_dir.rglob('*'):
            if file_path.is_file():
                # 计算相对路径
                arcname = file_path.relative_to(source_dir.parent)
                zipf.write(file_path, arcname)
                print(f"  添加: {arcname}")
    
    # 显示压缩包大小
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"✓ 压缩包创建完成，大小: {size_mb:.1f} MB")

def main():
    """主函数"""
    print("=" * 60)
    print("xImageDuplicateChecker 分发包创建工具")
    print("=" * 60)
    
    if not create_distribution():
        return False
    
    print("\n" + "=" * 60)
    print("✓ 分发包创建完成！")
    print("\n您现在可以：")
    print("1. 将release目录中的ZIP文件分享给其他用户")
    print("2. 用户解压后直接运行xImageDuplicateChecker.exe")
    print("3. 无需安装Python或其他依赖")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按回车键退出...")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
    
    input("\n按回车键退出...")