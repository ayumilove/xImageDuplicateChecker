# -*- coding: utf-8 -*-
"""
哈希计算工具模块

提供文件哈希和感知哈希算法实现，用于图片查重
"""

import hashlib
import os
import random
from typing import Tuple, Dict, List, Optional
import numpy as np
from PIL import Image


def calculate_file_hash(file_path: str) -> str:
    """
    计算文件的MD5哈希值
    
    Args:
        file_path: 图片文件路径
        
    Returns:
        文件的MD5哈希值
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
        
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def calculate_dhash(image_path: str, hash_size: int = 8) -> str:
    """
    计算图片的差值哈希(dHash)
    
    Args:
        image_path: 图片文件路径
        hash_size: 哈希大小，默认为8
        
    Returns:
        图片的dHash值（十六进制字符串）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"文件不存在: {image_path}")
    
    # 打开图片并转换为灰度图
    try:
        image = Image.open(image_path).convert('L')
    except Exception as e:
        raise ValueError(f"无法打开或处理图片: {image_path}, 错误: {str(e)}")
    
    # 调整图片大小为hash_size+1 x hash_size
    image = image.resize((hash_size + 1, hash_size), Image.LANCZOS)
    
    # 计算差值
    pixels = np.array(image)
    diff = pixels[:, 1:] > pixels[:, :-1]
    
    # 将布尔值转换为二进制字符串
    binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
    
    # 将二进制字符串转换为十六进制
    hex_hash = ''
    for i in range(0, len(binary_hash), 4):
        hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
    
    return hex_hash


def calculate_phash(image_path: str, hash_size: int = 8) -> str:
    """
    计算图片的感知哈希(pHash)
    
    Args:
        image_path: 图片文件路径
        hash_size: 哈希大小，默认为8
        
    Returns:
        图片的pHash值（十六进制字符串）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"文件不存在: {image_path}")
    
    try:
        # 打开图片并转换为灰度图
        image = Image.open(image_path).convert('L')
        
        # 调整图片大小
        image = image.resize((hash_size * 4, hash_size * 4), Image.LANCZOS)
        
        # 转换为numpy数组
        pixels = np.array(image)
        
        # 计算DCT（离散余弦变换的简化版本）
        dct = np.zeros((hash_size, hash_size))
        for i in range(hash_size):
            for j in range(hash_size):
                dct[i, j] = np.sum(pixels * np.cos(np.pi * i * np.arange(hash_size * 4) / (hash_size * 4)) 
                                   * np.cos(np.pi * j * np.arange(hash_size * 4).reshape(-1, 1) / (hash_size * 4)))
        
        # 计算DCT的均值（不包括第一个直流分量）
        dct_flat = dct.flatten()[1:]
        median = np.median(dct_flat)
        
        # 生成哈希值
        diff = dct_flat > median
        
        # 将布尔值转换为二进制字符串
        binary_hash = ''.join('1' if d else '0' for d in diff)
        
        # 将二进制字符串转换为十六进制
        hex_hash = ''
        for i in range(0, len(binary_hash), 4):
            if i + 4 <= len(binary_hash):
                hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
        
        return hex_hash
    except Exception as e:
        raise ValueError(f"无法计算pHash: {image_path}, 错误: {str(e)}")


def calculate_ahash(image_path: str, hash_size: int = 8) -> str:
    """
    计算图片的平均哈希(aHash)
    
    Args:
        image_path: 图片文件路径
        hash_size: 哈希大小，默认为8
        
    Returns:
        图片的aHash值（十六进制字符串）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"文件不存在: {image_path}")
    
    try:
        # 打开图片并转换为灰度图
        image = Image.open(image_path).convert('L')
        
        # 调整图片大小
        image = image.resize((hash_size, hash_size), Image.LANCZOS)
        
        # 计算像素均值
        pixels = np.array(image)
        avg = np.mean(pixels)
        
        # 检测是否为纯色图片
        std_dev = np.std(pixels)
        if std_dev < 3.0:  # 阈值可调整，越小越严格
            return "pure_color_image"
        
        # 生成哈希值
        diff = pixels > avg
        
        # 将布尔值转换为二进制字符串
        binary_hash = ''.join('1' if d else '0' for d in diff.flatten())
        
        # 将二进制字符串转换为十六进制
        hex_hash = ''
        for i in range(0, len(binary_hash), 4):
            if i + 4 <= len(binary_hash):
                hex_hash += hex(int(binary_hash[i:i+4], 2))[2:]
        
        return hex_hash
    except Exception as e:
        raise ValueError(f"无法计算aHash: {image_path}, 错误: {str(e)}")


def is_pure_color_image(image_path: str, threshold: float = 3.0) -> bool:
    """
    检测图片是否为纯色图片
    
    Args:
        image_path: 图片文件路径
        threshold: 标准差阈值，低于此值被视为纯色图片，默认为3.0
        
    Returns:
        如果是纯色图片返回True，否则返回False
    """
    try:
        # 打开图片并转换为RGB模式
        image = Image.open(image_path).convert('RGB')
        
        # 获取图片尺寸
        width, height = image.size
        
        # 如果图片太小，可能不是有效图片
        if width < 10 or height < 10:
            return True
            
        # 采样图片像素（对于大图片，不需要检查所有像素）
        sample_size = min(100, width * height)
        pixels = []
        
        for _ in range(sample_size):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            pixels.append(image.getpixel((x, y)))
        
        # 计算RGB通道的标准差
        r_values = [p[0] for p in pixels]
        g_values = [p[1] for p in pixels]
        b_values = [p[2] for p in pixels]
        
        r_std = np.std(r_values)
        g_std = np.std(g_values)
        b_std = np.std(b_values)
        
        # 如果所有通道的标准差都小于阈值，认为是纯色图片
        return r_std < threshold and g_std < threshold and b_std < threshold
    except Exception as e:
        print(f"检测纯色图片时出错: {image_path}, 错误: {str(e)}")
        return False

def hamming_distance(hash1: str, hash2: str) -> int:
    """
    计算两个哈希值之间的汉明距离
    
    Args:
        hash1: 第一个哈希值（十六进制字符串）
        hash2: 第二个哈希值（十六进制字符串）
        
    Returns:
        两个哈希值之间的汉明距离
    """
    # 处理纯色图片的特殊标记
    if hash1 == "pure_color_image" or hash2 == "pure_color_image":
        return 64  # 返回最大距离，表示与纯色图片不相似
    
    # 确保两个哈希值长度相同
    if len(hash1) != len(hash2):
        raise ValueError(f"哈希值长度不匹配: {len(hash1)} vs {len(hash2)}")
    
    # 计算汉明距离
    distance = 0
    for i in range(len(hash1)):
        # 将十六进制字符转换为二进制，并计算不同位的数量
        bin1 = bin(int(hash1[i], 16))[2:].zfill(4)
        bin2 = bin(int(hash2[i], 16))[2:].zfill(4)
        
        for j in range(len(bin1)):
            if bin1[j] != bin2[j]:
                distance += 1
    
    return distance