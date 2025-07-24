# xImageDuplicateChecker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

一个高效的Python图像查重工具，专门用于在百万级别的图片文件中找出重复的图像文件。支持多种重复检测算法，包括完全相同文件检测和视觉相似图片识别。

## 项目环境

本项目使用Python开发，推荐使用项目同级目录下的`.venv`虚拟环境。

### 环境配置

1. 激活虚拟环境：
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 项目功能

本工具能够识别和检测多种类型的重复图像，包括：

### 重复图片定义

1. **分辨率调整**
   - 检测相同图片在不同分辨率下的重复
   - 支持缩放、拉伸等变换后的图片识别

2. **图片部分截取**
   - 识别原图与其裁剪版本的重复关系
   - 检测图片的局部截取或区域提取

3. **完全一样的文件复制**
   - 检测完全相同的图片文件
   - 基于文件哈希值的快速比对

4. **图片水印文字变更**
   - 识别添加或修改水印后的重复图片
   - 检测文字、logo等叠加元素的变化

## 使用方法

### 本地目录查重

```bash
python main.py [图片目录] [选项]
```

#### 参数说明

- `directory`：要扫描的图片目录（必需）
- `-r, --recursive`：递归扫描子目录（可选）
- `-t, --threshold`：感知哈希相似度阈值，默认为8（可选）
- `-o, --output`：结果输出目录，默认为'results'（可选）

#### 使用示例

```bash
# 扫描单个目录
python main.py ./images

# 递归扫描目录及其子目录
python main.py ./images -r

# 调整相似度阈值（值越小要求越严格）
python main.py ./images -r -t 6

# 指定输出目录
python main.py ./images -r -o ./my_results
```



### 输出结果

程序会在指定的输出目录（默认为'results'）生成以下文件：

- `duplicates_[时间戳].csv`：CSV格式的重复图片列表
- `duplicates_[时间戳].json`：JSON格式的重复图片列表
- `summary_[时间戳].txt`：查重统计摘要

## 性能特点

- 支持百万级别图片文件的高效处理
- 多种重复检测算法结合
- 优化的内存使用和处理速度

## 开发状态

### 已实现功能

- [x] 基于MD5哈希的完全重复检测
- [x] 基于感知哈希(dHash/pHash/aHash)的视觉相似检测
- [x] 批量处理和递归目录扫描
- [x] 结果导出(CSV/JSON)和统计摘要

- [x] 大文件批量处理

### 待实现功能

- [ ] 基于SIFT/ORB特征点匹配的部分截取检测
- [ ] 基于深度学习的水印区域排除和内容特征匹配
- [ ] 图形用户界面
- [ ] 增量更新和实时监控

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 支持的图片格式

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)

## 系统要求

- Python 3.8 或更高版本
- 支持 Windows、macOS 和 Linux

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件