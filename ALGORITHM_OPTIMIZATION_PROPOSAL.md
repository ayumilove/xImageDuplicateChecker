# 图片查重算法优化方案

## 问题分析

当前在处理64万张照片时，分组比较阶段性能极差，每50张照片的对比需要按小时计算。

### 性能瓶颈分析

1. **算法复杂度问题**：
   - 当前使用O(n²)嵌套循环比较
   - 64万张图片需要进行 `640,000 × 639,999 / 2 ≈ 2000亿次` 比较
   - 每次比较需要计算3种哈希的汉明距离

2. **具体瓶颈位置**：
   - `cpp_duplicate_checker.py` 第595-650行的嵌套循环
   - 每个文件与所有其他文件逐一比较
   - 缺乏有效的索引和预筛选机制

## 优化方案

### 方案1：哈希索引优化（推荐）

**原理**：将相似的哈希值聚类，只在同一聚类内进行比较

**实现步骤**：
1. 将64位哈希值按前缀分组（如前16位）
2. 只在相同前缀组内进行详细比较
3. 使用多级索引进一步细分

**预期效果**：
- 复杂度从O(n²)降低到O(n×k)，其中k是平均组大小
- 性能提升：**50-100倍**

### 方案2：局部敏感哈希（LSH）

**原理**：使用LSH算法快速找到候选相似图片

**实现步骤**：
1. 对每个图片的哈希值计算LSH签名
2. 使用LSH索引快速找到候选匹配
3. 只对候选匹配进行精确比较

**预期效果**：
- 复杂度降低到O(n×log n)
- 性能提升：**100-500倍**

### 方案3：分层检测策略

**原理**：先用快速算法筛选，再用精确算法验证

**实现步骤**：
1. 第一层：使用单一哈希算法快速筛选
2. 第二层：对候选结果使用多重哈希验证
3. 第三层：对高相似度结果进行增强检测

**预期效果**：
- 大幅减少需要精确比较的图片对数量
- 性能提升：**20-50倍**

### 方案4：并行处理优化

**原理**：充分利用多核CPU进行并行计算

**实现步骤**：
1. 将图片列表分割成多个批次
2. 使用多进程/多线程并行处理
3. 合并结果时去重

**预期效果**：
- 性能提升：**4-16倍**（取决于CPU核心数）

### 方案5：内存优化

**原理**：优化内存使用，减少缓存未命中

**实现步骤**：
1. 使用更紧凑的数据结构存储哈希值
2. 按内存局部性原则重新排列数据
3. 使用内存映射文件处理大数据集

**预期效果**：
- 性能提升：**2-5倍**

## 推荐实施方案

### 阶段1：哈希索引优化（立即实施）

```python
def create_hash_index(file_hashes, prefix_bits=16):
    """创建哈希索引"""
    index = defaultdict(list)
    mask = (1 << prefix_bits) - 1
    
    for file_hash in file_hashes:
        # 使用dhash的前16位作为索引键
        dhash_int = int(file_hash['dhash'], 16)
        prefix = dhash_int & mask
        index[prefix].append(file_hash)
    
    return index

def optimized_perceptual_compare(file_hashes):
    """优化的感知哈希比较"""
    # 创建索引
    hash_index = create_hash_index(file_hashes)
    
    similar_groups = []
    processed = set()
    
    for prefix, group in hash_index.items():
        if len(group) < 2:
            continue
            
        # 只在同一组内进行比较
        for i, file1 in enumerate(group):
            if file1['file_path'] in processed:
                continue
                
            similar_files = []
            for j in range(i + 1, len(group)):
                file2 = group[j]
                if file2['file_path'] in processed:
                    continue
                    
                # 进行精确比较
                if is_similar(file1, file2):
                    similar_files.append(file2)
                    
            if similar_files:
                # 创建相似组
                group_files = [file1] + similar_files
                similar_groups.append(group_files)
                
                # 标记为已处理
                for f in group_files:
                    processed.add(f['path'])
    
    return similar_groups
```

### 阶段2：分层检测（后续实施）

```python
def layered_detection(file_hashes):
    """分层检测策略"""
    # 第一层：快速筛选（只用dhash）
    candidates = fast_dhash_filter(file_hashes)
    
    # 第二层：多重哈希验证
    verified = multi_hash_verify(candidates)
    
    # 第三层：增强检测（可选）
    final_groups = enhanced_detection(verified)
    
    return final_groups
```

### 阶段3：并行处理（性能进一步提升）

```python
from multiprocessing import Pool, cpu_count

def parallel_compare(file_hashes, num_processes=None):
    """并行比较处理"""
    if num_processes is None:
        num_processes = cpu_count()
    
    # 将数据分割成批次
    batch_size = len(file_hashes) // num_processes
    batches = [file_hashes[i:i+batch_size] 
               for i in range(0, len(file_hashes), batch_size)]
    
    # 并行处理
    with Pool(num_processes) as pool:
        results = pool.map(optimized_perceptual_compare, batches)
    
    # 合并结果
    return merge_results(results)
```

## 预期性能提升

| 优化方案 | 性能提升倍数 | 64万图片预计耗时 | 实施难度 |
|----------|-------------|------------------|----------|
| 当前方案 | 1x | 数天-数周 | - |
| 哈希索引 | 50-100x | 数小时 | 低 |
| LSH算法 | 100-500x | 30分钟-2小时 | 中 |
| 分层检测 | 20-50x | 2-6小时 | 低 |
| 并行处理 | 4-16x | 配合其他方案 | 中 |
| 综合优化 | 200-1000x | 10-30分钟 | 高 |

## 实施建议

1. **立即实施**：哈希索引优化（方案1）
2. **短期实施**：分层检测策略（方案3）
3. **中期实施**：并行处理优化（方案4）
4. **长期实施**：LSH算法（方案2）

通过这些优化，可以将64万张图片的查重时间从数天缩短到数小时甚至数十分钟。