# -*- coding: utf-8 -*-
"""
基于C++哈希库的图片查重器

使用C++实现的哈希算法来提高性能
"""

import os
import time
from collections import defaultdict, OrderedDict
from typing import List, Dict, Any, Tuple, Set, Optional

from .hash_wrapper import (
    calculate_file_hash, 
    calculate_dhash, 
    calculate_phash, 
    calculate_ahash,
    hamming_distance,
    is_pure_color_image
)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.result_logger import ResultLogger
from src.scan_progress import ScanProgress

# 导入LSH索引模块
try:
    from lsh_index import LSHOptimizedDuplicateChecker
    LSH_AVAILABLE = True
except ImportError:
    LSH_AVAILABLE = False


class CppDuplicateChecker:
    """
    基于C++哈希库的图片查重器
    """
    
    def __init__(self, 
                 phash_threshold: int = 2,
                 dhash_threshold: int = 8,
                 ahash_threshold: int = 2,
                 output_dir: str = "results",
                 detect_pure_color: bool = True,
                 detect_rotation: bool = False,
                 enhanced_similarity: bool = False,
                 confidence_threshold: float = 0.6,
                 enable_resume: bool = True,
                 enable_optimization: bool = True,
                 optimization_threshold: int = 10000,
                 enable_ultra_fast: bool = True,
                 ultra_fast_threshold: int = 100000,
                 enable_lsh: bool = False,
                 lsh_threshold: int = 500000,
                 lsh_num_tables: int = 10,
                 lsh_num_functions: int = 4,
                 enable_exact_match: bool = True,
                 enable_perceptual_hash: bool = True):
        """
        初始化图片查重器
        
        Args:
            phash_threshold: pHash感知哈希相似度阈值，默认为2
            dhash_threshold: dHash感知哈希相似度阈值，默认为8
            ahash_threshold: aHash感知哈希相似度阈值，默认为2
            output_dir: 结果输出目录，默认为"results"
            detect_pure_color: 是否检测并标记纯色图片，默认为True
            detect_rotation: 是否启用旋转识别功能，默认为False
            enhanced_similarity: 是否启用增强相似度检测（支持旋转+分辨率变化），默认为False
            confidence_threshold: 增强检测的置信度阈值，默认为0.6
            enable_resume: 是否启用断点续传，默认为True
            enable_optimization: 是否启用优化算法，默认为True
            optimization_threshold: 优化算法启用阈值，默认为10000
            enable_ultra_fast: 是否启用超高速算法，默认为True
            ultra_fast_threshold: 超高速算法启用阈值，默认为100000
            enable_exact_match: 是否启用完全一致检测，默认为True
            enable_perceptual_hash: 是否启用感知哈希检测，默认为True
        """
        self.phash_threshold = phash_threshold
        self.dhash_threshold = dhash_threshold
        self.ahash_threshold = ahash_threshold
        self.detect_pure_color = detect_pure_color
        self.detect_rotation = detect_rotation
        self.enhanced_similarity = enhanced_similarity
        self.confidence_threshold = confidence_threshold
        self.enable_resume = enable_resume
        self.enable_optimization = enable_optimization
        self.optimization_threshold = optimization_threshold
        self.enable_ultra_fast = enable_ultra_fast
        self.ultra_fast_threshold = ultra_fast_threshold
        
        # 检测方式控制
        self.enable_exact_match = enable_exact_match
        self.enable_perceptual_hash = enable_perceptual_hash
        
        # 输出检测方式设置（调试信息）
        print(f"[DEBUG] CppDuplicateChecker初始化: enable_exact_match={enable_exact_match}, enable_perceptual_hash={enable_perceptual_hash}")
        
        # LSH索引相关参数
        self.enable_lsh = enable_lsh and LSH_AVAILABLE
        self.lsh_threshold = lsh_threshold
        self.lsh_num_tables = lsh_num_tables
        self.lsh_num_functions = lsh_num_functions
        self.lsh_checker = None
        
        if self.enable_lsh and not LSH_AVAILABLE:
            self.log("警告: LSH模块不可用，已禁用LSH索引功能")
            self.enable_lsh = False
        
        self.logger = ResultLogger(output_dir)
        self.progress_manager = ScanProgress()
        
        # 日志回调函数
        self.log_callback = None
        
        # 进度回调函数
        self.progress_callback = None
        
        # 停止标志
        self.should_stop = False
        
        # 断点续传相关
        self.current_scan_directory = None
        self.scan_config = None
        self.processed_files = set()
        self.completed_stages = []
        self.current_stage = ""
        
        # 线程安全锁
        import threading
        self._stats_lock = threading.Lock()
        self._processed_files_lock = threading.Lock()
        self._thread_pools_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        
        # 使用LRU缓存限制内存使用
        from functools import lru_cache
        from collections import OrderedDict
        import psutil
        
        # 应用内存优化配置
        try:
            from memory_optimization_config import get_memory_optimized_config
            memory_config = get_memory_optimized_config()
            self.max_cache_size = memory_config['max_cache_size']
            self.memory_threshold = memory_config['memory_threshold']
            self.memory_critical_threshold = memory_config['memory_critical_threshold']
            self.memory_check_interval = memory_config['memory_check_interval']
            self.gc_interval = memory_config['gc_interval']
            print(f"[DEBUG] 应用内存优化配置: 缓存大小={self.max_cache_size}, 内存阈值={self.memory_threshold}%")
        except ImportError:
            # 回退到默认配置
            self.max_cache_size = 2000
            self.memory_threshold = 70
            self.memory_critical_threshold = 80
            self.memory_check_interval = 50
            self.gc_interval = 1000
            print("[DEBUG] 使用默认内存配置")
        
        self.last_memory_check = 0  # 上次内存检查时间
        self.file_hash_cache = OrderedDict()  # 缓存已计算的文件哈希
        self.phash_cache = OrderedDict()      # 缓存已计算的感知哈希
        
        # 内存优化：启用自动垃圾回收
        self.enable_auto_gc = True
        
        # 存储结果
        self.file_hash_groups = defaultdict(list)  # 文件哈希 -> 文件列表
        self.phash_groups = []  # 感知哈希相似组
        self.pure_color_images = []  # 纯色图片列表
        
        # 统计信息
        self.stats = {
            'total_images': 0,
            'processed_images': 0,
            'duplicate_groups': 0,
            'duplicate_images': 0,
            'pure_color_images': 0,
            'reasons': defaultdict(int),
            'file_status': defaultdict(int)  # 文件状态统计
        }
        
        # 线程池状态跟踪
        self.thread_pools = {
            'hash_pool': None,
            'compare_pool': None,
            'pure_color_pool': None
        }
        self.thread_stats = {
            'hash_threads': 0,
            'compare_threads': 0,
            'pure_color_threads': 0,
            'active_tasks': 0,
            'completed_tasks': 0,
            'current_stage': 'idle'
        }
    
    def _manage_cache_size(self, cache_dict, key: str, value):
        """管理缓存大小，实现LRU策略"""
        # 如果键已存在，先删除旧的
        if key in cache_dict:
            del cache_dict[key]
        
        # 添加新的键值对
        cache_dict[key] = value
        
        # 如果超过最大缓存大小，删除最旧的条目
        while len(cache_dict) > self.max_cache_size:
            oldest_key = next(iter(cache_dict))
            del cache_dict[oldest_key]
            
    def _get_from_cache(self, cache_dict: OrderedDict, key: str):
        """从缓存获取值，并更新LRU顺序"""
        if key in cache_dict:
            # 移动到末尾（最近使用）
            value = cache_dict.pop(key)
            cache_dict[key] = value
            return value
        return None
        
    def _check_memory_usage(self):
        """检查内存使用情况"""
        try:
            memory_percent = psutil.virtual_memory().percent
            return memory_percent
        except Exception:
            return 0
            
    def _auto_manage_memory(self, force_check=False):
        """自动管理内存，在内存使用率过高时清理缓存"""
        current_time = time.time()
        
        # 优化内存检查频率，避免频繁检查影响性能
        if not force_check and (current_time - self.last_memory_check) < 3.0:
            return
            
        self.last_memory_check = current_time
        memory_percent = self._check_memory_usage()
        
        # 分级内存管理策略
        if memory_percent > self.memory_critical_threshold:
            # 临界状态：激进清理
            self._aggressive_cache_cleanup(memory_percent)
        elif memory_percent > self.memory_threshold:
            # 警告状态：温和清理
            self._moderate_cache_cleanup(memory_percent)
            
    def _auto_garbage_collect(self, processed_count):
        """自动垃圾回收"""
        if self.enable_auto_gc and processed_count % self.gc_interval == 0:
            import gc
            collected = gc.collect()
            memory_percent = self._check_memory_usage()
            self.log(f"自动垃圾回收：释放了 {collected} 个对象，当前内存使用率: {memory_percent:.1f}%")
            
    def _moderate_cache_cleanup(self, memory_percent):
        """温和的缓存清理策略"""
        cache_size_before = len(self.file_hash_cache) + len(self.phash_cache)
        
        # 清理1/3的缓存，保留最近使用的
        if len(self.file_hash_cache) > 1000:
            items_to_keep = list(self.file_hash_cache.items())[-len(self.file_hash_cache)*2//3:]
            self.file_hash_cache.clear()
            self.file_hash_cache.update(items_to_keep)
            
        if len(self.phash_cache) > 1000:
            items_to_keep = list(self.phash_cache.items())[-len(self.phash_cache)*2//3:]
            self.phash_cache.clear()
            self.phash_cache.update(items_to_keep)
            
        cache_size_after = len(self.file_hash_cache) + len(self.phash_cache)
        self.log(f"内存使用率 {memory_percent:.1f}% 过高，温和清理缓存：{cache_size_before} -> {cache_size_after}")
        
    def _aggressive_cache_cleanup(self, memory_percent):
        """激进的缓存清理策略"""
        cache_size_before = len(self.file_hash_cache) + len(self.phash_cache)
        
        # 清理2/3的缓存
        if len(self.file_hash_cache) > 500:
            items_to_keep = list(self.file_hash_cache.items())[-len(self.file_hash_cache)//3:]
            self.file_hash_cache.clear()
            self.file_hash_cache.update(items_to_keep)
            
        if len(self.phash_cache) > 500:
            items_to_keep = list(self.phash_cache.items())[-len(self.phash_cache)//3:]
            self.phash_cache.clear()
            self.phash_cache.update(items_to_keep)
            
        cache_size_after = len(self.file_hash_cache) + len(self.phash_cache)
        self.log(f"内存使用率 {memory_percent:.1f}% 临界，激进清理缓存：{cache_size_before} -> {cache_size_after}")
        
        # 如果内存仍然过高，强制垃圾回收
        import gc
        gc.collect()
        self.log("已执行强制垃圾回收")
        
    def _force_shutdown_thread_pool(self, pool, pool_name, timeout=10.0):
        """强制关闭线程池，包含超时和强制终止机制"""
        if pool is None:
            return
            
        try:
            self.log(f"正在关闭线程池 {pool_name}...")
            
            # 第一步：尝试优雅关闭
            pool.shutdown(wait=False)
            
            # 第二步：等待线程完成，带超时
            start_time = time.time()
            if hasattr(pool, '_threads'):
                for thread in pool._threads:
                    if thread.is_alive():
                        remaining_time = timeout - (time.time() - start_time)
                        if remaining_time > 0:
                            thread.join(timeout=min(remaining_time, 5.0))
                        else:
                            break
            
            # 第三步：检查是否还有活跃线程
            active_threads = []
            if hasattr(pool, '_threads'):
                active_threads = [t for t in pool._threads if t.is_alive()]
            
            if active_threads:
                self.log(f"[警告] 线程池 {pool_name} 中仍有 {len(active_threads)} 个线程未能正常关闭")
                
                # 第四步：强制终止（如果支持）
                try:
                    import threading
                    for thread in active_threads:
                        if hasattr(thread, '_stop'):
                            thread._stop()
                        elif hasattr(thread, 'terminate'):
                            thread.terminate()
                    self.log(f"已强制终止线程池 {pool_name} 中的活跃线程")
                except Exception as e:
                    self.log(f"[警告] 强制终止线程时出现异常: {str(e)}")
            else:
                self.log(f"线程池 {pool_name} 已成功关闭")
                
        except Exception as e:
            self.log(f"[错误] 关闭线程池 {pool_name} 时出现异常: {str(e)}")
        
        # 第五步：清理引用
        try:
            del pool
        except:
            pass
            
    def clear_caches(self):
        """清理所有缓存以释放内存"""
        self.file_hash_cache.clear()
        self.phash_cache.clear()
        self.log("已清理所有缓存以释放内存")
        
        # 注意：不再重置统计信息，因为这会导致check_duplicates返回错误的stats
        # 统计信息应该在扫描完成后保持不变
        
        # 重置线程池状态
        for pool_name in self.thread_pools:
            self.thread_pools[pool_name] = None
        
        self.thread_stats = {
            'hash_threads': 0,
            'compare_threads': 0,
            'pure_color_threads': 0,
            'active_tasks': 0,
            'completed_tasks': 0,
            'current_stage': 'idle'
        }
    
    def set_log_callback(self, callback):
        """
        设置日志回调函数
        
        Args:
            callback: 日志回调函数，接收一个字符串参数
        """
        self.log_callback = callback
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收消息和进度百分比两个参数
        """
        self.progress_callback = callback
    
    def get_thread_status(self):
        """
        获取当前线程池的真实状态
        
        Returns:
            dict: 包含线程池状态的字典
        """
        try:
            # 重置线程计数
            hash_threads = 0
            compare_threads = 0
            pure_color_threads = 0
            active_tasks = 0
            
            # 调试：记录线程池状态（仅在需要时启用以避免日志刷屏）
            debug_messages = []
            
            # 检查当前阶段，提供更友好的信息
            current_stage = getattr(self, 'current_stage', 'idle')
            
            # 只在非file_hash阶段输出详细调试信息
            if current_stage not in ['idle', 'scan', 'file_hash']:
                debug_messages.append(f"[调试] 当前阶段: {current_stage} - 检查线程池状态")
                debug_messages.append(f"[调试] 线程池名称: {list(self.thread_pools.keys())}")
                for pool_name, pool in self.thread_pools.items():
                    debug_messages.append(f"[调试] {pool_name} 存在: {pool is not None}, 类型: {type(pool).__name__ if pool else 'None'}")
            
            # 更新线程池状态（仅在需要线程池的阶段）
            if current_stage not in ['idle', 'scan', 'file_hash']:
                for pool_name, pool in self.thread_pools.items():
                    if pool is not None:
                        if hasattr(pool, '_threads'):
                            # ThreadPoolExecutor的线程数
                            all_threads = list(pool._threads) if hasattr(pool, '_threads') else []
                            alive_threads = [t for t in all_threads if t.is_alive()]
                            thread_count = len(alive_threads)
                            max_workers = getattr(pool, '_max_workers', 'N/A')
                            
                            debug_messages.append(f"[调试] {pool_name} - 总线程: {len(all_threads)}, 活跃: {thread_count}, 最大工作线程: {max_workers}")
                            
                            # 当线程刚创建或统计获取过早可能为0，回退到最大工作线程数估计
                            if thread_count == 0 and hasattr(pool, '_max_workers') and pool._max_workers > 0:
                                thread_count = pool._max_workers
                                debug_messages.append(f"[调试] {pool_name} 使用回退值: {thread_count}")
                            
                            if pool_name == 'hash_pool':
                                hash_threads = thread_count
                            elif pool_name == 'compare_pool':
                                compare_threads = thread_count
                            elif pool_name == 'pure_color_pool':
                                pure_color_threads = thread_count
                        else:
                            debug_messages.append(f"[调试] {pool_name} 没有 _threads 属性")
                        
                        # 获取任务队列状态
                        if hasattr(pool, '_work_queue'):
                            try:
                                queue_size = pool._work_queue.qsize()
                                debug_messages.append(f"[调试] {pool_name} 队列大小: {queue_size}")
                                # 对于主要的处理线程池，累计任务数
                                if pool_name in ['hash_pool', 'compare_pool', 'pure_color_pool']:
                                    active_tasks += queue_size
                            except Exception as q_e:
                                debug_messages.append(f"[调试] {pool_name} 队列状态获取失败: {str(q_e)}")
                    else:
                        debug_messages.append(f"[调试] {pool_name} 为 None")
            
            # 更新线程统计信息
            self.thread_stats['hash_threads'] = hash_threads
            self.thread_stats['compare_threads'] = compare_threads
            self.thread_stats['pure_color_threads'] = pure_color_threads
            self.thread_stats['active_tasks'] = active_tasks
            
            # 输出所有调试信息（仅在需要线程池的阶段）
            if current_stage not in ['idle', 'scan', 'file_hash']:
                debug_messages.append(f"[调试] 最终线程统计 - hash:{hash_threads}, compare:{compare_threads}, pure_color:{pure_color_threads}, active_tasks:{active_tasks}")
                
                if hasattr(self, 'log_callback') and self.log_callback:
                    for msg in debug_messages:
                        self.log(msg)
            
            return self.thread_stats.copy()
        except Exception as e:
            # 如果获取失败，返回当前状态而不是零值
            error_msg = f"[调试] get_thread_status 异常: {str(e)}"
            if hasattr(self, 'log_callback') and self.log_callback:
                self.log(error_msg)
            return {
                'hash_threads': self.thread_stats.get('hash_threads', 0),
                'compare_threads': self.thread_stats.get('compare_threads', 0),
                'pure_color_threads': self.thread_stats.get('pure_color_threads', 0),
                'active_tasks': self.thread_stats.get('active_tasks', 0),
                'completed_tasks': self.thread_stats.get('completed_tasks', 0),
                'current_stage': self.thread_stats.get('current_stage', 'idle')
            }
    
    def stop(self):
        """
        停止扫描
        """
        self.should_stop = True
        self.log("收到停止信号，正在停止扫描...")
        
        # 保存当前进度
        if self.enable_resume and self.current_scan_directory:
            self._save_current_progress()
            
        # 只清理缓存，不重置统计信息
        self.file_hash_cache.clear()
        self.phash_cache.clear()
        self.log("已清理缓存以释放内存")
    
    def _save_current_progress(self):
        """
        保存当前扫描进度
        """
        try:
            if not self.current_scan_directory:
                return
            
            # 添加分组比较进度信息
            group_comparison_progress = getattr(self, 'group_comparison_progress', {})
            
            # 收集所有已发现的重复组
            all_duplicate_groups = []
            
            # 添加完全相同的重复组
            if hasattr(self, 'file_hash_groups') and self.file_hash_groups:
                for hash_value, files in self.file_hash_groups.items():
                    if len(files) > 1:
                        group = {
                            'files': files,
                            'similarity_type': 'exact',
                            'reason': '完全相同',
                            'hash': hash_value,
                            'group_size': len(files)
                        }
                        all_duplicate_groups.append(group)
            
            # 添加纯色图片重复组
            if hasattr(self, 'pure_color_images') and len(self.pure_color_images) > 1:
                pure_color_group = {
                    'files': list(self.pure_color_images),
                    'similarity_type': 'pure_color',
                    'reason': '纯色图片',
                    'group_size': len(self.pure_color_images)
                }
                all_duplicate_groups.append(pure_color_group)
            
            # 添加感知哈希相似组
            if hasattr(self, 'phash_groups') and self.phash_groups:
                all_duplicate_groups.extend(self.phash_groups)
            
            # 转换stats中的defaultdict为普通dict以支持JSON序列化
            serializable_stats = dict(self.stats) if self.stats else {}
            if 'reasons' in serializable_stats and hasattr(serializable_stats['reasons'], 'default_factory'):
                serializable_stats['reasons'] = dict(serializable_stats['reasons'])
            if 'file_status' in serializable_stats and hasattr(serializable_stats['file_status'], 'default_factory'):
                serializable_stats['file_status'] = dict(serializable_stats['file_status'])
            
            progress_file = self.progress_manager.save_progress(
                scan_directory=self.current_scan_directory,
                scan_config=self.scan_config,
                current_stage=self.current_stage,
                processed_files=self.processed_files,
                completed_stages=self.completed_stages,
                file_hash_results=self.file_hash_cache,
                phash_results=self.phash_cache,
                duplicate_groups=all_duplicate_groups,
                pure_color_images=self.pure_color_images,
                stats=serializable_stats,
                group_comparison_progress=group_comparison_progress
            )
            self.log(f"扫描进度已保存到: {progress_file}")
        except Exception as e:
            self.log(f"保存进度失败: {str(e)}")
    
    def _load_previous_progress(self, scan_directory: str) -> bool:
        """
        加载之前的扫描进度
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            是否成功加载进度
        """
        try:
            progress_data = self.progress_manager.load_progress(scan_directory)
            if not progress_data:
                return False
            
            # 恢复扫描状态
            self.current_scan_directory = progress_data['scan_directory']
            self.scan_config = progress_data['scan_config']
            self.current_stage = progress_data['current_stage']
            self.processed_files = set(progress_data['processed_files'])
            self.completed_stages = progress_data['completed_stages']
            self.file_hash_cache = progress_data.get('file_hash_results', {})
            self.phash_cache = progress_data.get('phash_results', {})
            self.phash_groups = progress_data.get('duplicate_groups', [])
            self.pure_color_images = progress_data.get('pure_color_images', [])
            self.stats = progress_data.get('stats', {
                'total_images': 0,
                'processed_images': 0,
                'duplicate_groups': 0,
                'duplicate_images': 0,
                'pure_color_images': 0,
                'reasons': defaultdict(int),
                'file_status': defaultdict(int)  # 文件状态统计
            })
            
            # 确保新字段存在（兼容旧版本进度文件）
            if 'file_status' not in self.stats:
                self.stats['file_status'] = defaultdict(int)
            if 'processed_images' not in self.stats:
                self.stats['processed_images'] = 0
            # 确保reasons字段是defaultdict
            if not isinstance(self.stats['reasons'], defaultdict):
                reasons_data = self.stats['reasons'] if isinstance(self.stats['reasons'], dict) else {}
                self.stats['reasons'] = defaultdict(int)
                self.stats['reasons'].update(reasons_data)
            # 确保file_status字段是defaultdict
            if not isinstance(self.stats['file_status'], defaultdict):
                file_status_data = self.stats['file_status'] if isinstance(self.stats['file_status'], dict) else {}
                self.stats['file_status'] = defaultdict(int)
                self.stats['file_status'].update(file_status_data)
            
            # 重建file_hash_groups
            self.file_hash_groups = defaultdict(list)
            for file_path, file_hash in self.file_hash_cache.items():
                self.file_hash_groups[file_hash].append(file_path)
            
            # 更新processed_images为实际处理的文件数
            if 'file_hash' in self.completed_stages:
                # 使用processed_files集合而不是file_hash_cache，因为缓存可能被清理
                self.stats['processed_images'] = len(self.processed_files)
            
            # 恢复分组比较进度
            self.group_comparison_progress = progress_data.get('group_comparison_progress', {})
            
            self.log(f"成功加载之前的扫描进度，已完成阶段: {', '.join(self.completed_stages)}")
            self.log(f"当前阶段: {self.current_stage}，已处理文件: {len(self.processed_files)}")
            if self.group_comparison_progress:
                self.log(f"分组比较进度: 已处理 {len(self.group_comparison_progress)} 个分组")
            
            return True
        except Exception as e:
            self.log(f"加载进度失败: {str(e)}")
            return False
    
    def check_incomplete_scan(self, scan_directory: str) -> Optional[Dict[str, Any]]:
        """
        检查是否有未完成的扫描
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            如果有未完成的扫描，返回进度信息；否则返回None
        """
        if not self.enable_resume:
            return None
        
        if self.progress_manager.has_incomplete_scan(scan_directory):
            return self.progress_manager.get_progress_info(scan_directory)
        
        return None
    
    def clear_scan_progress(self, scan_directory: str) -> bool:
        """
        清除指定目录的扫描进度
        
        Args:
            scan_directory: 扫描目录
            
        Returns:
            是否成功清除
        """
        return self.progress_manager.clear_progress(scan_directory)
    
    def log(self, message):
        """
        输出日志信息
        
        Args:
            message: 日志消息
        """
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """
        扫描目录获取所有图片文件
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录，默认为True
            
        Returns:
            图片文件路径列表
        """
        # 设置当前阶段
        self.current_stage = "scan"
        
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
        image_files = []
        scanned_dirs = 0
        total_files_checked = 0
        
        if recursive:
            # 首先统计总目录数以便显示进度
            total_dirs = sum(1 for _, _, _ in os.walk(directory))
            self.log(f"开始递归扫描，预计需要检查 {total_dirs} 个目录")
            
            for root, _, files in os.walk(directory):
                scanned_dirs += 1
                dir_image_count = 0
                
                for file in files:
                    total_files_checked += 1
                    if os.path.splitext(file)[1].lower() in image_extensions:
                        # 标准化路径分隔符，确保C++库能正确处理
                        file_path = os.path.join(root, file)
                        # 在Windows上统一使用反斜杠，避免混合分隔符问题
                        normalized_path = os.path.normpath(file_path)
                        image_files.append(normalized_path)
                        dir_image_count += 1
                
                # 每扫描100个目录或每10%进度报告一次
                if scanned_dirs % 100 == 0 or scanned_dirs % max(1, total_dirs // 10) == 0:
                    progress = (scanned_dirs / total_dirs) * 100
                    self.log(f"扫描进度: {scanned_dirs}/{total_dirs} ({progress:.1f}%) | 已找到 {len(image_files)} 个图片文件 | 当前目录: {os.path.basename(root)}")
        else:
            files = os.listdir(directory)
            self.log(f"开始扫描单个目录，共 {len(files)} 个文件")
            
            for file in files:
                total_files_checked += 1
                if os.path.isfile(os.path.join(directory, file)) and \
                   os.path.splitext(file)[1].lower() in image_extensions:
                    # 标准化路径分隔符，确保C++库能正确处理
                    file_path = os.path.join(directory, file)
                    normalized_path = os.path.normpath(file_path)
                    image_files.append(normalized_path)
        
        self.log(f"扫描完成！检查了 {total_files_checked} 个文件，找到 {len(image_files)} 个图片文件")
        return image_files
    
    def _check_file_status(self, file_path: str) -> str:
        """检查文件状态，返回状态描述
        
        Returns:
            "valid": 文件正常
            "empty": 空文件（0字节）
            "not_found": 文件不存在
            "permission_denied": 权限不足
            "too_large": 文件过大（超过500MB）
            "invalid_format": 不是有效的图片格式
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return "文件不存在"
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, IOError):
                return "无法访问文件（权限不足或文件被占用）"
            
            # 检查空文件
            if file_size == 0:
                return "空文件（0字节）"
            
            # 检查文件是否过大（超过500MB）
            if file_size > 500 * 1024 * 1024:
                return f"文件过大（{file_size / (1024*1024):.1f}MB，超过500MB限制）"
            
            # 检查文件扩展名
            _, ext = os.path.splitext(file_path.lower())
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}
            if ext not in valid_extensions:
                return f"不支持的文件格式（{ext}）"
            
            # 简单的文件头检查（可选）
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(16)
                    if len(header) < 4:
                        return "文件头不完整"
                    
                    # 检查常见图片格式的文件头
                    if header.startswith(b'\xff\xd8\xff'):  # JPEG
                        pass
                    elif header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                        pass
                    elif header.startswith(b'GIF8'):  # GIF
                        pass
                    elif header.startswith(b'BM'):  # BMP
                        pass
                    elif header.startswith(b'RIFF') and b'WEBP' in header[:16]:  # WebP
                        pass
                    elif header.startswith(b'II*\x00') or header.startswith(b'MM\x00*'):  # TIFF
                        pass
                    else:
                        # 如果文件头不匹配但扩展名正确，仍然尝试处理
                        pass
                        
            except (OSError, IOError):
                return "无法读取文件内容"
            
            return "valid"
            
        except Exception as e:
            return f"检查文件时发生异常: {type(e).__name__}: {str(e)}"
    
    def check_exact_duplicates(self, image_files: List[str]) -> Dict[str, List[str]]:
        """
        检查完全相同的重复图片（基于文件哈希）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            哈希值 -> 文件列表的字典
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        self.current_stage = "file_hash"
        
        # 如果已经完成了文件哈希阶段，直接返回缓存结果
        if "file_hash" in self.completed_stages:
            self.log("文件哈希阶段已完成，使用缓存结果")
            duplicate_groups = {h: files for h, files in self.file_hash_groups.items() if len(files) > 1}
            return duplicate_groups
        
        file_hash_map = defaultdict(list)
        error_count = 0
        max_errors = max(50, len(image_files) // 20)  # 最多允许5%的错误，但至少50个
        
        # 从缓存中恢复已计算的哈希
        for file_path, file_hash in self.file_hash_cache.items():
            if file_path in image_files:
                file_hash_map[file_hash].append(file_path)
                self.processed_files.add(file_path)
        
        # 计算剩余文件的哈希
        remaining_files = [f for f in image_files if f not in self.processed_files]
        
        if remaining_files:
            self.log(f"正在使用多线程计算 {len(remaining_files)} 个剩余文件的哈希值...")
            self.log(f"已从缓存恢复 {len(self.processed_files)} 个文件的哈希值")
            
            # 使用多线程处理文件哈希计算
            def calculate_hash_batch(file_batch):
                """批量计算文件哈希 - 优化版本，支持批次级别超时控制"""
                import time
                batch_start_time = time.time()
                batch_results = []
                processed_in_batch = 0
                
                # 批次级别超时控制：根据批次大小动态调整超时时间
                batch_timeout = min(60.0, max(30.0, len(file_batch) * 2.0))  # 每个文件最多2秒，总超时30-60秒
                
                for file_path in file_batch:
                    if self.should_stop:
                        break
                    
                    # 检查批次是否已超时
                    current_time = time.time()
                    if current_time - batch_start_time > batch_timeout:
                        batch_size = len(file_batch) if isinstance(file_batch, list) else 0
                        self.log(f"[批次超时] 批次处理超时 ({batch_timeout:.1f}秒)，已处理 {processed_in_batch}/{batch_size} 个文件")
                        break
                    
                    # 增强的文件状态检查
                    file_status = self._check_file_status(file_path)
                    if file_status != "valid":
                        with self._stats_lock:
                            self.stats['file_status'][file_status] += 1
                        continue
                    
                    try:
                        # 记录单个文件处理开始时间
                        file_start_time = time.time()
                        
                        # 动态调整单个文件超时：根据剩余批次时间
                        remaining_batch_time = batch_timeout - (file_start_time - batch_start_time)
                        batch_size = len(file_batch) if isinstance(file_batch, list) else 1
                        file_timeout = min(5.0, max(1.0, remaining_batch_time / max(1, batch_size - processed_in_batch)))
                        
                        file_hash = calculate_file_hash(file_path, timeout=file_timeout)
                        file_end_time = time.time()
                        
                        # 检查哈希值的有效性
                        if file_hash and isinstance(file_hash, str) and not file_hash.startswith("ERROR:"):
                            batch_results.append((file_path, file_hash))
                            processed_in_batch += 1
                            
                            # 如果单个文件处理时间过长，记录警告
                            file_time = file_end_time - file_start_time
                            if file_time > 2.0:  # 超过2秒
                                self.log(f"[性能警告] 文件处理耗时: {os.path.basename(file_path)} ({file_time:.2f}秒)")
                        else:
                            error_msg = str(file_hash) if file_hash else 'Unknown error'
                            self.log(f"文件哈希计算失败: {os.path.basename(file_path)}, 原因: {error_msg}")
                            continue
                    except TimeoutError as e:
                        # C++库超时，快速回退到Python实现
                        self.log(f"[超时回退] C++库超时，使用Python计算: {os.path.basename(file_path)}")
                        try:
                            import hashlib
                            with open(file_path, 'rb') as f:
                                file_hash = hashlib.md5(f.read()).hexdigest()
                            batch_results.append((file_path, file_hash))
                            processed_in_batch += 1
                        except Exception as fallback_e:
                            self.log(f"Python回退也失败: {os.path.basename(file_path)}, 错误: {str(fallback_e)}")
                        continue
                    except ValueError as e:
                        # C++库返回的错误信息
                        self.log(f"C++库处理文件失败: {os.path.basename(file_path)}, 错误: {str(e)}")
                        continue
                    except Exception as e:
                        # 其他异常
                        self.log(f"处理文件时发生异常: {os.path.basename(file_path)}, 异常类型: {type(e).__name__}, 详情: {str(e)}")
                        continue
                
                batch_end_time = time.time()
                batch_time = batch_end_time - batch_start_time
                batch_size = len(file_batch) if isinstance(file_batch, list) else 0
                efficiency = (processed_in_batch / batch_size) * 100 if batch_size > 0 else 0
                # 移除重复的批次完成日志，统一在主循环中输出
                # self.log(f"批次完成: 处理 {processed_in_batch}/{batch_size} 个文件 ({efficiency:.1f}%), 耗时 {batch_time:.2f}秒")
                
                # 确保始终返回列表，即使为空
                if not isinstance(batch_results, list):
                    self.log(f"[警告] batch_results类型异常: {type(batch_results)}, 返回空列表")
                    return []
                return batch_results
            
            # 分批并行处理 - 优化多线程配置和动态批次大小
            # 使用适中的线程数以避免UI卡死
            max_workers = min(8, max(4, len(remaining_files) // 1000))  # 最多8个线程，避免UI卡死
            
            # 动态批次大小：根据文件数量和性能要求调整
            if len(remaining_files) < 100:
                batch_size = max(1, len(remaining_files) // max_workers)  # 小数据集：平均分配
            elif len(remaining_files) < 1000:
                batch_size = min(50, max(10, len(remaining_files) // (max_workers * 2)))  # 中等数据集：较小批次
            else:
                batch_size = min(100, max(20, len(remaining_files) // (max_workers * 4)))  # 大数据集：更小批次，更好的负载均衡
            
            batches = [remaining_files[i:i+batch_size] for i in range(0, len(remaining_files), batch_size)]
            
            self.log(f"多线程配置: {max_workers} 个线程, {len(batches)} 个批次, 每批次 {batch_size} 个文件")
            
            # 创建线程池
            hash_pool = ThreadPoolExecutor(max_workers=max_workers)
            with self._thread_pools_lock:
                self.thread_pools['file_hash_pool'] = hash_pool
            
            # 更新线程统计
            self.thread_stats.update({
                'file_hash_pool': {
                    'max_workers': hash_pool._max_workers,
                    'active_threads': 0,
                    'pending_tasks': len(batches)
                },
                'total_tasks': len(batches),
                'completed_tasks': 0,
                'current_stage': 'file_hash_calculation'
            })
            
            try:
                # 性能监控和自适应批次处理
                batch_performance_history = []  # 记录批次性能历史
                adaptive_batch_size = batch_size  # 自适应批次大小
                
                # 分阶段提交任务，而不是一次性提交所有批次
                initial_batch_count = min(max_workers * 2, len(batches))  # 初始提交的批次数
                remaining_batches = batches[initial_batch_count:]
                current_batches = batches[:initial_batch_count]
                
                future_to_batch = {hash_pool.submit(calculate_hash_batch, batch): i for i, batch in enumerate(current_batches)}
                batch_start_times = {}
                
                # 记录每个批次的开始时间
                for future, batch_idx in future_to_batch.items():
                    batch_start_times[future] = time.time()
                
                processed_count = 0
                completed_batches = 0
                submitted_batch_count = initial_batch_count
                
                # 使用while循环替代as_completed，以便能够处理动态添加的futures
                while future_to_batch or remaining_batches:
                    if self.should_stop:
                        break
                    
                    # 等待任何一个future完成
                    if future_to_batch:
                        completed_futures = []
                        for future in list(future_to_batch.keys()):
                            if future.done():
                                completed_futures.append(future)
                        
                        if not completed_futures:
                            time.sleep(0.1)  # 短暂等待
                            continue
                        
                        # 处理第一个完成的future
                        future = completed_futures[0]
                        
                        # 从future_to_batch中移除已完成的future
                        del future_to_batch[future]
                    else:
                        # 没有活跃的futures，但还有剩余批次需要提交
                        if remaining_batches:
                            # 提交新批次
                            batches_to_submit = min(max_workers, len(remaining_batches))
                            for _ in range(batches_to_submit):
                                if remaining_batches:
                                    next_batch = remaining_batches.pop(0)
                                    new_future = hash_pool.submit(calculate_hash_batch, next_batch)
                                    future_to_batch[new_future] = submitted_batch_count
                                    batch_start_times[new_future] = time.time()
                                    submitted_batch_count += 1
                                    current_batches.append(next_batch)
                            continue
                        else:
                            # 没有活跃futures也没有剩余批次，退出循环
                            break
                    
                    try:
                        batch_results = future.result()
                        completed_batches += 1
                        batch_files_processed = 0
                        
                        # 检查batch_results的类型和有效性
                        if batch_results and isinstance(batch_results, list):
                            for item in batch_results:
                                # 确保每个item都是(file_path, file_hash)的元组
                                if isinstance(item, (tuple, list)) and len(item) == 2:
                                    file_path, file_hash = item
                                    file_hash_map[file_hash].append(file_path)
                                    with self._cache_lock:
                                        self._manage_cache_size(self.file_hash_cache, file_hash, file_hash)  # 缓存结果
                                    with self._processed_files_lock:
                                        self.processed_files.add(file_path)
                                    processed_count += 1
                                    batch_files_processed += 1
                                else:
                                    self.log(f"[调试] 批次结果格式错误: {type(item)}, 内容: {item}")
                        elif batch_results is not None:
                            self.log(f"[调试] 批次结果类型错误: {type(batch_results)}, 内容: {batch_results}")
                        
                        # 更新统计
                        self.thread_stats['completed_tasks'] += 1
                        
                        # 更频繁的进度更新
                        batch_progress = (completed_batches / len(batches)) * 100
                        file_progress = (processed_count / len(remaining_files)) * 100
                        
                        # 增强的调试日志
                        remaining_batches_count_debug = len(batches) - completed_batches
                        active_futures = len([f for f in future_to_batch if not f.done()])
                        
                        # 计算批次处理时间和性能指标
                        batch_end_time = time.time()
                        batch_duration = batch_end_time - batch_start_times.get(future, batch_end_time)
                        # 安全获取批次大小
                        batch_idx = future_to_batch.get(future, -1)
                        current_batch_size = 0
                        if batch_idx >= 0 and batch_idx < len(current_batches) and isinstance(current_batches[batch_idx], list):
                            current_batch_size = len(current_batches[batch_idx])
                        elif batch_files_processed > 0:
                            # 如果无法获取原始批次大小，使用实际处理的文件数作为估计
                            current_batch_size = batch_files_processed
                        
                        batch_efficiency = (batch_files_processed / current_batch_size) if current_batch_size > 0 else 0
                        files_per_second = batch_files_processed / max(0.1, batch_duration)
                        
                        # 记录批次性能历史
                        batch_performance_history.append({
                            'duration': batch_duration,
                            'efficiency': batch_efficiency,
                            'files_per_second': files_per_second,
                            'batch_size': current_batch_size
                        })
                        
                        # 自适应批次大小调整（每完成5个批次评估一次）
                        if len(batch_performance_history) >= 5 and remaining_batches:
                            recent_performance = batch_performance_history[-5:]
                            avg_duration = sum(p['duration'] for p in recent_performance) / len(recent_performance)
                            avg_efficiency = sum(p['efficiency'] for p in recent_performance) / len(recent_performance)
                            
                            # 如果平均处理时间过长或效率下降，减小批次大小
                            if avg_duration > 30.0 or avg_efficiency < 0.8:
                                adaptive_batch_size = max(5, int(adaptive_batch_size * 0.7))
                                self.log(f"[自适应优化] 检测到性能下降，调整批次大小: {adaptive_batch_size}")
                            # 如果处理很快且效率高，可以适当增加批次大小
                            elif avg_duration < 10.0 and avg_efficiency > 0.95:
                                adaptive_batch_size = min(200, int(adaptive_batch_size * 1.2))
                                self.log(f"[自适应优化] 性能良好，增加批次大小: {adaptive_batch_size}")
                        
                        self.log(f"批次完成: 处理 {batch_files_processed}/{current_batch_size} 个文件, 耗时 {batch_duration:.2f}秒, 效率 {batch_efficiency:.1%}")
                        self.log(f"总体进度: {completed_batches}/{len(batches)} 批次 ({batch_progress:.1f}%) | {processed_count}/{len(remaining_files)} 文件 ({file_progress:.1f}%)")
                        
                        # 动态提交新批次（如果还有剩余批次）
                        # 放宽提交条件，确保所有批次都能被处理
                        active_futures_count = len([f for f in future_to_batch if not f.done()])
                        if remaining_batches and active_futures_count < max_workers * 3:  # 放宽并发限制
                            # 只在批次大小变化很大时才重新分组，避免频繁重组导致批次丢失
                            if adaptive_batch_size != batch_size and abs(adaptive_batch_size - batch_size) > batch_size * 0.3:
                                # 重新分组剩余文件
                                remaining_files_flat = [f for batch in remaining_batches for f in batch]
                                if remaining_files_flat:  # 确保有文件需要处理
                                    remaining_batches = [remaining_files_flat[i:i+adaptive_batch_size] 
                                                       for i in range(0, len(remaining_files_flat), adaptive_batch_size)]
                                    self.log(f"[自适应优化] 重新分组剩余文件，新批次数: {len(remaining_batches)}")
                                else:
                                    remaining_batches = []  # 确保是空列表而不是其他类型
                            
                            # 提交多个批次以加快处理速度
                            batches_to_submit = min(max_workers - active_futures_count, len(remaining_batches))
                            for _ in range(batches_to_submit):
                                if remaining_batches:
                                    next_batch = remaining_batches.pop(0)
                                    new_future = hash_pool.submit(calculate_hash_batch, next_batch)
                                    future_to_batch[new_future] = submitted_batch_count
                                    batch_start_times[new_future] = time.time()
                                    submitted_batch_count += 1
                                    current_batches.append(next_batch)
                                    self.log(f"[动态提交] 提交新批次 {submitted_batch_count}, 剩余批次: {len(remaining_batches)}")
                        
                        # 确保 remaining_batches 始终是列表类型
                        if not isinstance(remaining_batches, list):
                            remaining_batches = []
                        remaining_batches_count = len(remaining_batches)
                        active_futures = len([f for f in future_to_batch if not f.done()])
                        self.log(f"剩余任务: {remaining_batches_count} 个批次, {active_futures} 个活跃线程")
                        
                        if self.progress_callback:
                            self.progress_callback(f"计算哈希值: {processed_count}/{len(remaining_files)} ({file_progress:.1f}%)", file_progress)
                        
                        # 定期保存进度和管理内存
                        if processed_count % 500 == 0:
                            self._save_current_progress()
                            self._auto_manage_memory()
                            
                    except Exception as e:
                        error_count += 1
                        import traceback
                        self.log(f"批次处理失败: {str(e)}")
                        self.log(f"[调试] 异常类型: {type(e).__name__}")
                        self.log(f"[调试] 完整堆栈跟踪:")
                        self.log(traceback.format_exc())
                        
                        # 如果错误太多，停止处理
                        if error_count > max_errors:
                            self._save_current_progress()
                            break
                            
            finally:
                # 使用改进的线程池强制关闭方法
                self._force_shutdown_thread_pool(hash_pool, 'file_hash_pool')
                
                # 清理线程池引用
                with self._thread_pools_lock:
                    self.thread_pools['file_hash_pool'] = None
                    if 'file_hash_pool' in self.thread_pools:
                        del self.thread_pools['file_hash_pool']
                        
                # 重置线程统计
                self.thread_stats['current_stage'] = 'idle'
                self.thread_stats['completed_tasks'] = 0
                self.thread_stats['total_tasks'] = 0
                    
        else:
            self.log("所有文件哈希已从缓存恢复")
        
        # 处理单线程剩余逻辑（如果有的话）
        if error_count > max_errors:
            self.log(f"错误过多({error_count})，停止处理")
            self.log(f"C++库连续出错过多({error_count}次)，返回空结果")
            return {}
        
        # 分析重复文件
        self.log("\n步骤2: 分析重复文件...")
        self.log(f"开始分析 {len(file_hash_map)} 个唯一哈希值")
        
        # 只保留有重复的组
        duplicate_groups = {h: files for h, files in file_hash_map.items() if len(files) > 1}
        
        # 详细的重复文件统计
        total_duplicate_files = sum(len(files) for files in duplicate_groups.values())
        unique_files = len(file_hash_map) - len(duplicate_groups)
        
        self.log(f"重复文件分析完成:")
        self.log(f"  - 唯一文件: {unique_files} 个")
        self.log(f"  - 重复组数: {len(duplicate_groups)} 组")
        self.log(f"  - 重复文件: {total_duplicate_files} 个")
        self.log(f"  - 可删除文件: {total_duplicate_files - len(duplicate_groups)} 个")
        
        # 更新统计信息
        self.file_hash_groups = file_hash_map
        # 记录实际处理的文件数（排除错误文件），但不覆盖total_images
        actual_processed_files = len(file_hash_map)
        with self._stats_lock:
            self.stats['processed_images'] = actual_processed_files
            
            if duplicate_groups:
                self.stats['reasons']['完全相同'] = len(duplicate_groups)
                self.stats['duplicate_groups'] += len(duplicate_groups)
                self.stats['duplicate_images'] += sum(len(files) - 1 for files in duplicate_groups.values())
        
        # 标记阶段完成
        if not self.should_stop and "file_hash" not in self.completed_stages:
            self.completed_stages.append("file_hash")
            self._save_current_progress()
        
        return duplicate_groups
    
    def check_pure_color_images(self, image_files: List[str]) -> List[str]:
        """
        检测纯色图片（支持多线程并行处理）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            纯色图片列表
        """
        if not self.detect_pure_color:
            return []
        
        self.current_stage = "pure_color"
        
        # 如果已经完成了纯色检测阶段，直接返回缓存结果
        if "pure_color" in self.completed_stages:
            self.log("纯色检测阶段已完成，使用缓存结果")
            return self.pure_color_images
            
        self.log("正在使用C++库并行检测纯色图片...")
        pure_color_images = list(self.pure_color_images)  # 从之前的结果开始
        
        # 找出还未检测的文件
        processed_for_pure_color = set()
        for file_path in image_files:
            if file_path in self.pure_color_images:
                processed_for_pure_color.add(file_path)
        
        remaining_files = [f for f in image_files if f not in processed_for_pure_color]
        
        if remaining_files:
            self.log(f"并行检测 {len(remaining_files)} 个剩余文件的纯色状态...")
            if processed_for_pure_color:
                self.log(f"已从缓存恢复 {len(processed_for_pure_color)} 个文件的检测结果")
        else:
            self.log("所有文件的纯色检测已完成")
            return pure_color_images
        
        # 使用多线程并行处理
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        # 分批处理文件
        batch_size = max(1, len(remaining_files) // 50)  # 每批处理的文件数
        batches = [remaining_files[i:i+batch_size] for i in range(0, len(remaining_files), batch_size)]
        
        def check_pure_color_batch(file_batch):
            """批量检测纯色图片"""
            batch_pure_color = []
            batch_errors = 0
            
            for file_path in file_batch:
                if self.should_stop:
                    break
                try:
                    if is_pure_color_image(file_path):
                        batch_pure_color.append(file_path)
                except Exception as e:
                    batch_errors += 1
                    self.log(f"检测纯色图片时出错: {file_path}, 错误: {str(e)}")
            
            return batch_pure_color, batch_errors
        
        # 并行处理各批次
        max_workers = min(4, len(batches))  # 纯色检测使用较少线程数
        total_errors = 0
        
        # 创建并跟踪线程池
        pure_color_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.thread_pools['pure_color_pool'] = pure_color_pool
        self.thread_stats['current_stage'] = 'pure_color'
        self.thread_stats['active_tasks'] = len(batches)
        self.thread_stats['pure_color_threads'] = max_workers
        
        try:
            self.log(f"使用 {max_workers} 个线程并行处理 {len(batches)} 个批次")
            
            future_to_batch = {pure_color_pool.submit(check_pure_color_batch, batch): i 
                             for i, batch in enumerate(batches)}
            
            completed_batches = 0
            for future in as_completed(future_to_batch):
                if self.should_stop:
                    self.log("扫描已停止")
                    self._save_current_progress()
                    break
                
                batch_pure_color, batch_errors = future.result()
                pure_color_images.extend(batch_pure_color)
                total_errors += batch_errors
                
                # 更新统计信息
                with self._stats_lock:
                    self.stats['pure_color_images'] += len(batch_pure_color)
                self.thread_stats['completed_tasks'] += 1
                self.thread_stats['active_tasks'] = len(batches) - completed_batches - 1
                
                completed_batches += 1
                if completed_batches % 10 == 0 or completed_batches == len(batches):
                    progress = completed_batches / len(batches) * 100
                    self.log(f"纯色检测进度: {completed_batches}/{len(batches)} 批次 ({progress:.1f}%)")
                    # 定期保存进度
                    if completed_batches % 20 == 0:
                        self._save_current_progress()
        finally:
            # 使用改进的线程池强制关闭方法
            self._force_shutdown_thread_pool(pure_color_pool, 'pure_color_pool')
            
            # 清理线程池引用
            with self._thread_pools_lock:
                self.thread_pools['pure_color_pool'] = None
                if 'pure_color_pool' in self.thread_pools:
                    del self.thread_pools['pure_color_pool']
                    
            # 重置线程统计
            self.thread_stats['pure_color_threads'] = 0
            self.thread_stats['current_stage'] = 'idle'

        return pure_color_images
    
    def check_perceptual_duplicates(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        检查感知上相似的图片（基于感知哈希）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            相似图片组列表
        """
        self.current_stage = "perceptual_hash"
        
        # 如果已经完成了感知哈希阶段，直接返回缓存结果
        if "perceptual_hash" in self.completed_stages:
            self.log("感知哈希检测阶段已完成，使用缓存结果")
            return self.phash_groups
        
        # 根据文件数量选择算法
        if self.enable_lsh and len(image_files) >= self.lsh_threshold:
            self.log(f"文件数量 ({len(image_files)}) 超过LSH阈值 ({self.lsh_threshold})，启用LSH索引算法")
            return self._check_perceptual_duplicates_lsh(image_files)
        elif self.enable_ultra_fast and len(image_files) >= self.ultra_fast_threshold:
            self.log(f"文件数量 ({len(image_files)}) 超过超高速阈值 ({self.ultra_fast_threshold})，启用超高速算法")
            return self._check_perceptual_duplicates_ultra_fast(image_files)
        elif self.enable_optimization and len(image_files) >= self.optimization_threshold:
            self.log(f"文件数量 ({len(image_files)}) 超过优化阈值 ({self.optimization_threshold})，启用优化算法")
            return self._check_perceptual_duplicates_optimized(image_files)
        else:
            self.log(f"使用标准算法处理 {len(image_files)} 个文件")
            return self._check_perceptual_duplicates_standard(image_files)
    
    def _check_perceptual_duplicates_standard(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        标准的感知哈希查重算法（原有实现）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            相似图片组列表
        """
        
        # 计算所有图片的感知哈希
        self.log(f"正在使用C++库计算 {len(image_files)} 个文件的感知哈希...")
        
        # 存储每个文件的dhash和phash
        file_hashes = []
        error_count = 0
        max_errors = max(50, len(image_files) // 20)  # 最多允许5%的错误，但至少50个
        
        # 从缓存中恢复已计算的哈希
        processed_for_phash = set()
        for file_path in image_files:
            cached_hashes = self._get_from_cache(self.phash_cache, file_path)
            if cached_hashes:
                dhash, phash, ahash = cached_hashes
                file_hashes.append({
                    'file_path': file_path,  # 改为 file_path 避免旧格式警告
                    'dhash': dhash,
                    'phash': phash,
                    'ahash': ahash
                })
                processed_for_phash.add(file_path)
        
        # 计算剩余文件的哈希
        remaining_files = [f for f in image_files if f not in processed_for_phash]
        
        if remaining_files:
            self.log(f"使用多线程计算 {len(remaining_files)} 个剩余文件的感知哈希...")
            if processed_for_phash:
                self.log(f"已从缓存恢复 {len(processed_for_phash)} 个文件的哈希值")
            
            # 多线程批量计算感知哈希
            def calculate_hash_batch(file_batch):
                """批量计算感知哈希"""
                batch_results = []
                batch_errors = 0
                for file_path in file_batch:
                    if self.should_stop:
                        break
                    try:
                        dhash = calculate_dhash(file_path)
                        phash = calculate_phash(file_path)
                        ahash = calculate_ahash(file_path)
                        
                        # 验证哈希值有效性
                        if dhash and phash and ahash:
                            batch_results.append({
                                'file_path': file_path,
                                'dhash': dhash,
                                'phash': phash,
                                'ahash': ahash
                            })
                        else:
                            batch_errors += 1
                    except Exception as e:
                        batch_errors += 1
                        continue
                return batch_results, batch_errors
            
            # 分批处理文件
            from concurrent.futures import ThreadPoolExecutor, as_completed
            batch_size = max(20, len(remaining_files) // 32)  # 32个批次，每批次至少20个文件
            batches = [remaining_files[i:i+batch_size] for i in range(0, len(remaining_files), batch_size)]
            
            self.log(f"将 {len(remaining_files)} 个文件分为 {len(batches)} 个批次，每批次约 {batch_size} 个文件")
            
            # 创建线程池进行并行计算
            max_workers = min(12, len(batches))  # 使用更多线程
            hash_pool = ThreadPoolExecutor(max_workers=max_workers)
            self.thread_pools['hash_pool'] = hash_pool
            self.thread_stats['current_stage'] = 'perceptual_hash_calculation'
            self.thread_stats['hash_threads'] = max_workers
            self.thread_stats['active_tasks'] = len(batches)
            
            try:
                # 添加线程锁保护共享变量
                import threading
                results_lock = threading.Lock()
                
                future_to_batch = {hash_pool.submit(calculate_hash_batch, batch): i for i, batch in enumerate(batches)}
                
                processed_count = 0
                completed_batches = 0
                total_errors = 0
                
                for future in as_completed(future_to_batch):
                    if self.should_stop:
                        self.log("扫描已停止")
                        self._save_current_progress()
                        break
                    
                    try:
                        batch_results, batch_errors = future.result()
                        
                        # 使用线程锁保护共享变量的修改
                        with results_lock:
                            file_hashes.extend(batch_results)
                            
                            # 缓存结果
                            for result in batch_results:
                                self._manage_cache_size(self.phash_cache, result['file_path'], (result['dhash'], result['phash'], result['ahash']))
                            
                            processed_count += len(batch_results)
                            total_errors += batch_errors
                            completed_batches += 1
                        
                        # 更新进度
                        progress_percent = (processed_count / len(remaining_files)) * 100
                        self.log(f"感知哈希计算进度: {processed_count}/{len(remaining_files)} 个文件 ({progress_percent:.1f}%), 完成批次: {completed_batches}/{len(batches)}")
                        
                        # 定期保存进度和管理内存
                        if completed_batches % 5 == 0:
                            self._save_current_progress()
                            self._auto_manage_memory()
                        
                        # 检查错误率
                        if total_errors > max_errors:
                            self._save_current_progress()
                            raise Exception(f"感知哈希计算错误过多({total_errors}次)，可能存在问题")
                            
                    except Exception as e:
                        self.log(f"批次处理失败: {str(e)}")
                        with results_lock:
                            total_errors += 1
                        
            finally:
                # 使用改进的线程池强制关闭方法
                self._force_shutdown_thread_pool(hash_pool, 'hash_pool')
                
                # 清理线程池引用
                with self._thread_pools_lock:
                    self.thread_pools['hash_pool'] = None
                    if 'hash_pool' in self.thread_pools:
                        del self.thread_pools['hash_pool']
                        
                # 重置线程统计
                self.thread_stats['hash_threads'] = 0
                self.thread_stats['current_stage'] = 'idle'
                
        else:
            self.log("所有文件的感知哈希已从缓存恢复")
        
        # 查找相似图片组
        similar_groups = []
        processed = set()  # 已处理的文件
        
        # 如果启用增强相似度检测，使用增强检测器
        if self.enhanced_similarity:
            self.log("正在使用增强相似度检测（支持旋转+分辨率变化）...")
            try:
                from src.enhanced_similarity_detector import batch_compare_with_enhanced_similarity
                
                # 使用增强相似度检测进行批量比较
                image_paths = [item['file_path'] for item in file_hashes]
                enhanced_groups = batch_compare_with_enhanced_similarity(
                    image_paths,
                    dhash_threshold=self.dhash_threshold + 4,  # 放宽阈值以适应分辨率变化
                    phash_threshold=self.phash_threshold + 2,
                    ahash_threshold=self.ahash_threshold + 2,
                    confidence_threshold=self.confidence_threshold,
                    log_callback=self.log
                )
                
                # 转换格式以保持兼容性
                for group in enhanced_groups:
                    similar_group = {
                        'reason': group['reason'],
                        'files': group['files'],
                        'files_with_distances': [],
                        'detection_info': group.get('detection_info', []),
                        'avg_confidence': group.get('avg_confidence', 0.0)
                    }
                    similar_groups.append(similar_group)
                    
                    # 标记为已处理
                    for file_path in group['files']:
                        processed.add(file_path)
                        
            except ImportError as e:
                self.log(f"增强相似度检测模块导入失败，回退到旋转检测: {str(e)}")
                # 回退到旋转检测
                self.enhanced_similarity = False
            except Exception as e:
                self.log(f"增强相似度检测出错，回退到旋转检测: {str(e)}")
                # 回退到旋转检测
                self.enhanced_similarity = False
        
        # 如果启用旋转检测但未启用增强检测，使用旋转不变哈希
        if self.detect_rotation and not self.enhanced_similarity:
            self.log("正在使用旋转不变哈希查找相似图片组...")
            try:
                from src.rotation_invariant_hash import batch_compare_with_rotation
                
                # 使用旋转不变哈希进行批量比较
                image_paths = [item['file_path'] for item in file_hashes]
                rotation_groups = batch_compare_with_rotation(
                    image_paths,
                    dhash_threshold=self.dhash_threshold,
                    phash_threshold=self.phash_threshold,
                    ahash_threshold=self.ahash_threshold,
                    log_callback=self.log
                )
                
                # 转换格式以保持兼容性
                for group in rotation_groups:
                    similar_group = {
                        'reason': group['reason'] + '(旋转检测)',
                        'files': group['files'],
                        'files_with_distances': group.get('files_with_distances', [])
                    }
                    similar_groups.append(similar_group)
                    
                    # 标记为已处理
                    for file_path in group['files']:
                        processed.add(file_path)
                        
            except ImportError as e:
                self.log(f"旋转检测模块导入失败，回退到标准检测: {str(e)}")
                # 回退到标准检测
                self.detect_rotation = False
            except Exception as e:
                self.log(f"旋转检测出错，回退到标准检测: {str(e)}")
                # 回退到标准检测
                self.detect_rotation = False
        
        # 如果没有启用旋转检测或旋转检测失败，使用多线程标准方法
        if not self.detect_rotation:
            self.log("正在使用多线程查找相似图片组...")
            
            # 多线程比较函数
            def compare_file_batch(batch_indices):
                """批量比较文件哈希 - 超级优化版本，大幅减少比较次数"""
                batch_groups = []
                batch_processed = set()
                comparisons_in_batch = 0
                skipped_comparisons = 0
                batch_start_time = time.time()
                
                for idx, i in enumerate(batch_indices):
                    if self.should_stop or i >= len(file_hashes):
                        break
                        
                    file1 = file_hashes[i]
                    if file1['file_path'] in processed or file1['file_path'] in batch_processed:
                         continue
                    
                    similar_files = []
                    reason = ""
                    
                    # 大幅减少比较范围：只与接下来的少量文件比较
                    max_compare_range = min(500, len(file_hashes) - i - 1)  # 最多只比较500个后续文件
                    
                    for offset in range(1, max_compare_range + 1):
                        j = i + offset
                        if self.should_stop or j >= len(file_hashes):
                            break
                            
                        file2 = file_hashes[j]
                        if file2['file_path'] in processed or file2['file_path'] in batch_processed:
                             continue
                        
                        # 超级早期终止：文件大小预筛选
                        try:
                            import os
                            size1 = os.path.getsize(file1['file_path'])
                            size2 = os.path.getsize(file2['file_path'])
                            # 如果文件大小差异超过50%，直接跳过
                            if abs(size1 - size2) / max(size1, size2, 1) > 0.5:
                                skipped_comparisons += 1
                                continue
                        except:
                            pass
                        
                        comparisons_in_batch += 1
                        
                        # 每2000次比较报告一次进度
                        if comparisons_in_batch % 2000 == 0:
                            elapsed = time.time() - batch_start_time
                            efficiency = skipped_comparisons / (comparisons_in_batch + skipped_comparisons) * 100 if (comparisons_in_batch + skipped_comparisons) > 0 else 0
                            self.log(f"[批次内进度] 已完成 {comparisons_in_batch} 次比较，跳过 {skipped_comparisons} 次，效率 {efficiency:.1f}%，耗时 {elapsed:.1f}秒")
                        
                        # 分层早期终止：先检查dhash
                        dhash_distance = hamming_distance(file1['dhash'], file2['dhash'])
                        if dhash_distance > self.dhash_threshold + 3:  # 更严格的阈值
                            skipped_comparisons += 1
                            continue
                        
                        # 只有dhash通过才计算其他哈希
                        phash_distance = hamming_distance(file1['phash'], file2['phash'])
                        
                        # 如果dhash和phash都不相似，直接跳过ahash
                        if dhash_distance >= self.dhash_threshold and phash_distance >= self.phash_threshold:
                            skipped_comparisons += 1
                            continue
                        
                        ahash_distance = hamming_distance(file1['ahash'], file2['ahash'])
                        
                        # 判断是否相似 - 使用多重验证机制，至少两种算法都判断为相似
                        dhash_similar = dhash_distance < self.dhash_threshold
                        phash_similar = phash_distance < self.phash_threshold
                        ahash_similar = ahash_distance < self.ahash_threshold
                        
                        # 计算相似的算法数量
                        similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                        
                        # 至少需要两种算法都判断为相似才认为是重复
                        if similar_count >= 2:
                            similar_files.append({
                                 'file_path': file2['file_path'],
                                 'dhash_distance': dhash_distance,
                                 'phash_distance': phash_distance,
                                 'ahash_distance': ahash_distance
                             })
                            # 确定主要原因
                            reasons = []
                            if dhash_similar:
                                reasons.append("dHash")
                            if phash_similar:
                                reasons.append("pHash")
                            if ahash_similar:
                                reasons.append("aHash")
                            reason = "+".join(reasons) + "相似(C++)"  # 标记为C++实现
                    
                    if similar_files:
                        # 构建文件列表，包含哈希距离信息
                        files_with_distances = [{
                            'file_path': file1['file_path'],
                            'dhash_distance': 0,  # 基准文件距离为0
                            'phash_distance': 0,
                            'ahash_distance': 0
                        }]
                        files_with_distances.extend(similar_files)
                        
                        similar_group = {
                            'reason': reason,
                            'files': [item['file_path'] for item in files_with_distances],  # 保持向后兼容
                            'files_with_distances': files_with_distances  # 新增：包含距离信息的文件列表
                        }
                        batch_groups.append(similar_group)
                        
                        # 标记为已处理
                        batch_processed.add(file1['file_path'])
                        for sf in similar_files:
                            batch_processed.add(sf['file_path'])
                
                return batch_groups, batch_processed
            
            # 分批处理文件索引 - 优化批次大小以减少计算复杂度
            unprocessed_files = [i for i, fh in enumerate(file_hashes) if fh['file_path'] not in processed]
            
            # 动态计算批次大小：确保每个批次的比较次数不超过合理范围
            # 每个批次内部比较次数 = batch_size * (batch_size - 1) / 2
            # 目标：每批次比较次数不超过10万次，即batch_size不超过450
            if len(unprocessed_files) <= 1000:
                batch_size = min(200, max(50, len(unprocessed_files) // 8))  # 小数据集：8个批次
            elif len(unprocessed_files) <= 10000:
                batch_size = min(300, max(100, len(unprocessed_files) // 32))  # 中等数据集：32个批次
            else:
                batch_size = min(400, max(200, len(unprocessed_files) // 64))  # 大数据集：64个批次
            
            batches = [unprocessed_files[i:i+batch_size] for i in range(0, len(unprocessed_files), batch_size)]
            
            self.log(f"将 {len(unprocessed_files)} 个未处理文件分为 {len(batches)} 个批次进行多线程比较")
            
            # 创建线程池进行并行比较
            max_workers = min(8, len(batches))  # 使用适中的线程数
            compare_pool = ThreadPoolExecutor(max_workers=max_workers)
            self.thread_pools['compare_pool'] = compare_pool
            self.thread_stats['current_stage'] = 'perceptual_hash_comparison'
            self.thread_stats['compare_threads'] = max_workers
            self.thread_stats['active_tasks'] = len(batches)
            
            try:
                # 添加线程锁保护共享变量
                import threading
                comparison_lock = threading.Lock()
                
                future_to_batch = {compare_pool.submit(compare_file_batch, batch): i for i, batch in enumerate(batches)}
                
                completed_batches = 0
                total_processed = 0
                
                for future in as_completed(future_to_batch):
                    if self.should_stop:
                        self.log("扫描已停止")
                        self._save_current_progress()
                        break
                    
                    try:
                        batch_groups, batch_processed = future.result()
                        
                        # 使用线程锁保护共享变量的修改
                        with comparison_lock:
                            similar_groups.extend(batch_groups)
                            processed.update(batch_processed)
                            completed_batches += 1
                            total_processed += len(batch_processed)
                        
                        # 更新进度
                        progress_percent = (completed_batches / len(batches)) * 100
                        self.log(f"感知哈希比较进度: 完成批次 {completed_batches}/{len(batches)} ({progress_percent:.1f}%), 已处理 {total_processed} 个文件")
                        
                        # 定期保存进度和管理内存
                        if completed_batches % 4 == 0:
                            self._save_current_progress()
                            self._auto_manage_memory()
                            
                    except Exception as e:
                        self.log(f"批次比较失败: {str(e)}")
                        
            finally:
                # 使用改进的线程池强制关闭方法
                self._force_shutdown_thread_pool(compare_pool, 'compare_pool')
                
                # 清理线程池引用
                with self._thread_pools_lock:
                    self.thread_pools['compare_pool'] = None
                    if 'compare_pool' in self.thread_pools:
                        del self.thread_pools['compare_pool']
                        
                # 重置线程统计
                self.thread_stats['compare_threads'] = 0
                self.thread_stats['current_stage'] = 'idle'
        
        # 更新统计信息
        self.phash_groups = similar_groups
        if similar_groups:
            with self._stats_lock:
                for group in similar_groups:
                    reason = group['reason']
                    self.stats['reasons'][reason] = self.stats['reasons'].get(reason, 0) + 1
                
                self.stats['duplicate_groups'] += len(similar_groups)
                self.stats['duplicate_images'] += sum(len(group['files']) - 1 for group in similar_groups)
        
        # 标记阶段完成
        if not self.should_stop and "perceptual_hash" not in self.completed_stages:
            self.completed_stages.append("perceptual_hash")
            self._save_current_progress()
        
        return similar_groups
    
    def check_duplicates(self, directory: str, recursive: bool = True, resume: bool = None) -> Dict[str, Any]:
        """
        执行完整的图片查重流程
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录，默认为True
            resume: 是否恢复之前的扫描，如果为None则自动检测
            
        Returns:
            查重结果统计信息
        """
        start_time = time.time()
        
        self.current_scan_directory = directory
        self.scan_config = {
            'directory': directory,
            'recursive': recursive,
            'dhash_threshold': self.dhash_threshold,
            'phash_threshold': self.phash_threshold,
            'ahash_threshold': self.ahash_threshold,
            'detect_pure_color': self.detect_pure_color,
            'detect_rotation': self.detect_rotation,
            'enhanced_similarity': self.enhanced_similarity
        }
        
        # 检查是否有未完成的扫描
        if self.enable_resume and resume is None:
            incomplete_scan = self.check_incomplete_scan(directory)
            if incomplete_scan:
                self.log(f"发现未完成的扫描")
                self.log(f"扫描时间: {incomplete_scan.get('timestamp', 'Unknown')}")
                self.log(f"已完成阶段: {incomplete_scan.get('completed_stages', [])}")
                resume = True
        
        # 如果启用恢复，尝试加载之前的进度
        if self.enable_resume and resume:
            if self._load_previous_progress(directory):
                self.log("已恢复之前的扫描进度")
            else:
                self.log("无法恢复之前的进度，开始新的扫描")
                resume = False
        
        if not resume:
            self.log(f"开始新的扫描: {directory}")
        
        # 扫描目录获取所有图片文件
        self.log(f"正在扫描目录: {directory}")
        image_files = self.scan_directory(directory, recursive)
        self.log(f"找到 {len(image_files)} 个图片文件")
        
        # 初始化或恢复统计信息
        if not resume or not hasattr(self, 'stats') or not self.stats:
            self.stats = {
                'total_images': len(image_files),
                'processed_images': 0,
                'duplicate_groups': 0,
                'duplicate_images': 0,
                'pure_color_images': 0,
                'reasons': defaultdict(int),
                'file_status': defaultdict(int)  # 文件状态统计
            }
        
        self.stats['total_images'] = len(image_files)
        self.log(f"[调试] 设置total_images = {len(image_files)}")
        
        # 保存初始进度
        if self.enable_resume:
            self._save_current_progress()
        
        # 步骤1: 检查完全相同的重复图片（如果启用）
        if self.enable_exact_match and "file_hash" not in self.completed_stages:
            self.log("\n步骤1: 使用C++库检查完全相同的重复图片")
            exact_duplicates = self.check_exact_duplicates(image_files)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        elif self.enable_exact_match and "file_hash" in self.completed_stages:
            self.log("\n步骤1: 完全相同重复图片检查已完成，使用缓存结果")
            exact_duplicates = {h: files for h, files in self.file_hash_groups.items() if len(files) > 1}
        elif not self.enable_exact_match:
            self.log("\n步骤1: 跳过完全一致检测（已禁用）")
            exact_duplicates = {}
        
        # 步骤2: 检查纯色图片（如果启用）
        if self.detect_pure_color and "pure_color" not in self.completed_stages:
            self.log("\n步骤2: 检查纯色图片")
            pure_color_images = self.check_pure_color_images(image_files)
            
            # 将纯色图片转换为重复组格式
            pure_color_groups = []
            if len(pure_color_images) > 1:
                pure_color_groups.append({
                    'files': pure_color_images,
                    'similarity_type': 'pure_color',
                    'reason': '纯色图片',
                    'group_size': len(pure_color_images)
                })
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        elif not self.detect_pure_color:
            self.log("\n步骤2: 跳过纯色检测（已禁用）")
            pure_color_groups = []
        
        # 步骤3: 检查感知相似的重复图片（如果启用）
        if self.enable_perceptual_hash and "perceptual_hash" not in self.completed_stages:
            self.log("\n步骤3: 检查感知相似的重复图片")
            
            # 根据文件数量选择算法
            if self.enable_lsh and len(image_files) >= self.lsh_threshold:
                self.log(f"文件数量 {len(image_files)} >= LSH阈值 {self.lsh_threshold}，使用LSH索引算法")
                similar_groups = self._check_perceptual_duplicates_lsh(image_files)
            elif self.enable_ultra_fast and len(image_files) >= self.ultra_fast_threshold:
                self.log(f"文件数量 {len(image_files)} >= 超高速阈值 {self.ultra_fast_threshold}，使用超高速算法")
                similar_groups = self._check_perceptual_duplicates_ultra_fast(image_files)
            elif self.enable_optimization and len(image_files) >= self.optimization_threshold:
                self.log(f"文件数量 {len(image_files)} >= 优化阈值 {self.optimization_threshold}，使用优化算法")
                similar_groups = self._check_perceptual_duplicates_optimized(image_files)
            else:
                self.log(f"文件数量 {len(image_files)} < 优化阈值 {self.optimization_threshold}，使用标准算法")
                similar_groups = self._check_perceptual_duplicates_standard(image_files)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        elif not self.enable_perceptual_hash:
            self.log("\n步骤3: 跳过感知哈希检测（已禁用）")
            similar_groups = []
        
        # 合并所有重复组
        all_duplicate_groups = []
        
        # 添加完全相同的重复组
        if exact_duplicates:
            for hash_value, files in exact_duplicates.items():
                if len(files) > 1:
                    group = {
                        'files': files,  # 直接使用文件路径字符串数组
                        'similarity_type': 'exact',
                        'reason': '完全相同',  # 添加reason字段
                        'hash': hash_value,
                        'group_size': len(files)
                    }
                    all_duplicate_groups.append(group)
        
        # 添加纯色图片重复组
        all_duplicate_groups.extend(pure_color_groups)
        
        # 添加感知相似的重复组
        all_duplicate_groups.extend(similar_groups)
        
        # 保存结果
        if all_duplicate_groups:
            csv_path = self.logger.save_to_csv(all_duplicate_groups)
            json_path = self.logger.save_to_json(all_duplicate_groups)
            summary_path = self.logger.save_summary(self.stats)
            
            self.log(f"\n查重结果已保存到:")
            self.log(f"- CSV: {csv_path}")
            self.log(f"- JSON: {json_path}")
            self.log(f"- 摘要: {summary_path}")
        else:
            self.log("\n未发现重复图片")
        
        # 清除扫描进度（扫描完成）
        if self.enable_resume:
            self.clear_scan_progress(directory)
        
        # 计算总耗时
        total_time = time.time() - start_time
        self.log(f"\n查重完成！总耗时: {total_time:.2f} 秒")
        self.log(f"扫描到 {self.stats['total_images']} 个图片文件，实际处理了 {self.stats['processed_images']} 个文件")
        self.log(f"发现 {self.stats['duplicate_groups']} 个重复组，包含 {self.stats['duplicate_images']} 个重复图片")
        
        # 清理缓存以释放内存
        self.clear_caches()
        
        return self.stats
    
    def _check_perceptual_duplicates_lsh(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        使用LSH索引进行感知哈希查重（适用于超大规模数据集）
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            相似图片组列表
        """
        self.log(f"开始LSH索引感知哈希查重，文件数量: {len(image_files)}")
        start_time = time.time()
        
        # 初始化LSH检查器
        if self.lsh_checker is None:
            self.lsh_checker = LSHOptimizedDuplicateChecker(
                lsh_num_tables=self.lsh_num_tables,
                lsh_num_functions=self.lsh_num_functions,
                similarity_threshold=0.85,  # 基于汉明距离阈值计算的相似度
                log_callback=self.log_callback  # 传递日志回调函数
            )
        
        # 步骤1：计算所有文件的哈希值
        self.log("计算文件哈希值...")
        file_hashes = []
        
        # 使用多线程计算哈希
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        # 创建线程池
        max_workers = min(8, len(image_files) // 100 + 1)  # 降低线程数避免UI卡死
        hash_pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="LSH_Hash")
        
        # 更新线程状态
        self.thread_pools['lsh_hash_pool'] = hash_pool
        self.thread_stats['lsh_hash_threads'] = max_workers
        self.thread_stats['current_stage'] = 'lsh_hash_calculation'
        
        try:
            # 提交哈希计算任务
            future_to_file = {}
            for file_path in image_files:
                if self.should_stop:
                    break
                    
                future = hash_pool.submit(self._calculate_all_hashes_for_lsh, file_path)
                future_to_file[future] = file_path
            
            # 收集结果
            completed_files = 0
            for future in as_completed(future_to_file):
                if self.should_stop:
                    break
                    
                file_path = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        file_hashes.append(file_hash)
                    
                    completed_files += 1
                    
                    # 进度更新
                    if completed_files % 1000 == 0:
                        progress = completed_files / len(image_files) * 100
                        self.log(f"哈希计算进度: {progress:.1f}% ({completed_files}/{len(image_files)})")
                        
                except Exception as e:
                    self.log(f"计算文件 {file_path} 哈希失败: {e}")
                    
        finally:
            # 使用改进的线程池强制关闭方法
            self._force_shutdown_thread_pool(hash_pool, 'lsh_hash_pool')
            
            # 清理线程池引用
            with self._thread_pools_lock:
                self.thread_pools['lsh_hash_pool'] = None
                if 'lsh_hash_pool' in self.thread_pools:
                    del self.thread_pools['lsh_hash_pool']
                    
            # 重置线程统计
            self.thread_stats['lsh_hash_threads'] = 0
            self.thread_stats['current_stage'] = 'idle'
        
        if not file_hashes:
            self.log("没有成功计算的哈希值")
            return []
        
        self.log(f"成功计算 {len(file_hashes)} 个文件的哈希值")
        
        # 步骤2：使用LSH索引查找相似文件
        self.log("使用LSH索引查找相似文件...")
        
        try:
            similar_groups = self.lsh_checker.find_duplicates_with_lsh(file_hashes)
            
            # 转换为标准格式
            result_groups = []
            for group in similar_groups:
                if len(group) >= 2:
                    group_info = {
                        'files': [{
                            'file_path': file_info['file_path'],
                            'dhash': file_info['dhash'],
                            'phash': file_info['phash'],
                            'ahash': file_info['ahash']
                        } for file_info in group],
                        'similarity_type': 'lsh_perceptual',
                        'group_size': len(group),
                        'reason': 'LSH感知哈希相似'  # 添加reason字段
                    }
                    result_groups.append(group_info)
            
            # 更新统计信息
            total_time = time.time() - start_time
            lsh_stats = self.lsh_checker.lsh_index.get_stats()
            
            self.log(f"\nLSH感知哈希查重完成:")
            self.log(f"  - 总耗时: {total_time:.2f} 秒")
            self.log(f"  - 处理文件: {len(file_hashes)} 个")
            self.log(f"  - 索引构建时间: {lsh_stats.get('index_time', 0):.2f} 秒")
            self.log(f"  - 候选减少比例: {lsh_stats.get('candidate_reduction_ratio', 1):.1f}x")
            self.log(f"  - 找到相似组: {len(result_groups)} 个")
            
            # 保存结果到缓存
            self.phash_groups = result_groups
            self.completed_stages.append("perceptual_hash")
            self._save_current_progress()
            
            return result_groups
            
        except Exception as e:
            self.log(f"LSH查重过程中发生错误: {e}")
            # 回退到超高速算法
            self.log("回退到超高速算法...")
            return self._check_perceptual_duplicates_ultra_fast(image_files)
    
    def _calculate_all_hashes_for_lsh(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        为LSH索引计算文件的所有哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含所有哈希值的字典，失败时返回None
        """
        try:
            # 检查缓存
            cache_key = f"lsh_{file_path}"
            cached_result = self._get_from_cache(self.file_hash_cache, cache_key)
            if cached_result:
                return cached_result
            
            # 计算三种哈希
            dhash = calculate_dhash(file_path)
            phash = calculate_phash(file_path)
            ahash = calculate_ahash(file_path)
            
            if dhash and phash and ahash:
                result = {
                    'file_path': file_path,
                    'dhash': dhash,
                    'phash': phash,
                    'ahash': ahash
                }
                
                # 缓存结果
                self._manage_cache_size(self.file_hash_cache, cache_key, result)
                
                return result
            else:
                return None
                
        except Exception as e:
            self.log(f"计算文件 {file_path} 的LSH哈希失败: {e}")
            return None
        else:
            self.log("\n步骤1: 完全相同重复图片检查已完成，跳过")
            exact_duplicates = {h: files for h, files in self.file_hash_groups.items() if len(files) > 1}
        
        # 从图片列表中移除完全相同的重复图片（只保留每组的第一个）
        unique_images = []
        processed_files = set()
        
        for files in exact_duplicates.values():
            unique_images.append(files[0])
            for file_path in files:
                processed_files.add(file_path)
        
        for file_path in image_files:
            if file_path not in processed_files:
                unique_images.append(file_path)
        
        # 步骤2: 检测纯色图片
        if "pure_color" not in self.completed_stages:
            self.log(f"\n步骤2: 使用C++库检测纯色图片 (共 {len(unique_images)} 个唯一文件)")
            pure_color_images = self.check_pure_color_images(unique_images)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        else:
            self.log("\n步骤2: 纯色图片检测已完成，跳过")
            pure_color_images = self.pure_color_images
        
        # 从图片列表中移除纯色图片
        if pure_color_images:
            unique_images = [img for img in unique_images if img not in set(pure_color_images)]
        
        # 步骤3: 检查感知上相似的图片（如果启用）
        if self.enable_perceptual_hash and "perceptual_hash" not in self.completed_stages:
            self.log(f"\n步骤3: 使用C++库检查感知上相似的图片 (共 {len(unique_images)} 个唯一文件)")
            similar_groups = self.check_perceptual_duplicates(unique_images)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        elif self.enable_perceptual_hash:
            self.log("\n步骤3: 感知相似图片检查已完成，跳过")
            similar_groups = self.phash_groups
        else:
            self.log("\n步骤3: 跳过感知哈希检测（已禁用）")
            similar_groups = []
        
        # 生成结果
        all_duplicate_groups = []
        
        # 添加完全相同的重复组
        for file_hash, files in exact_duplicates.items():
            all_duplicate_groups.append({
                'reason': '完全相同(C++)',
                'files': files
            })
        
        # 添加纯色图片组（如果有）
        if self.pure_color_images:
            all_duplicate_groups.append({
                'reason': '纯色图片(C++)',
                'files': self.pure_color_images
            })
            self.stats['reasons']['纯色图片(C++)'] = 1
            if not self.stats['duplicate_groups']:
                self.stats['duplicate_groups'] = 1
        
        # 添加感知相似的重复组
        all_duplicate_groups.extend(similar_groups)
        
        # 保存结果
        if all_duplicate_groups:
            csv_path = self.logger.save_to_csv(all_duplicate_groups)
            json_path = self.logger.save_to_json(all_duplicate_groups)
            summary_path = self.logger.save_summary(self.stats)
            
            self.log(f"\n查重结果已保存到:")
            self.log(f"- CSV: {csv_path}")
            self.log(f"- JSON: {json_path}")
            self.log(f"- 摘要: {summary_path}")
        else:
            self.log("\n未发现重复图片")
        
        # 清除扫描进度（扫描完成）
        if self.enable_resume:
            self.clear_scan_progress(directory)
        
        # 清理缓存以释放内存
        self.clear_caches()
        
        # 计算总耗时
        total_time = time.time() - start_time
        self.log(f"\n查重完成！总耗时: {total_time:.2f} 秒")
        self.log(f"扫描到 {self.stats['total_images']} 个图片文件，实际处理了 {self.stats['processed_images']} 个文件")
        self.log(f"发现 {self.stats['duplicate_groups']} 个重复组，包含 {self.stats['duplicate_images']} 个重复图片")
        
        # 显示文件状态统计
        if self.stats['file_status']:
            self.log("\n文件状态统计:")
            for status, count in self.stats['file_status'].items():
                self.log(f"  {status}: {count} 个文件")
            total_skipped = sum(self.stats['file_status'].values())
            self.log(f"  总计跳过: {total_skipped} 个文件")
        
        # 确保stats不为None且包含必要字段
        if self.stats is None:
            self.log("[错误] self.stats为None，创建默认stats")
            self.stats = {
                'total_images': 0,
                'processed_images': 0,
                'duplicate_groups': 0,
                'duplicate_images': 0,
                'pure_color_images': 0,
                'reasons': defaultdict(int),
                'file_status': defaultdict(int)
            }
        
        # 确保必要字段存在
        required_fields = ['total_images', 'processed_images', 'duplicate_groups', 'duplicate_images']
        for field in required_fields:
            if field not in self.stats:
                self.log(f"[警告] stats缺少字段 {field}，设置为0")
                self.stats[field] = 0
        
        self.log(f"[调试] 返回stats，total_images = {self.stats.get('total_images', 'None')}")
        self.log(f"[调试] stats类型: {type(self.stats)}, 内容: {dict(self.stats) if self.stats else 'None'}")
        return self.stats
    
    def _check_perceptual_duplicates_optimized(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        优化的感知哈希查重算法
        使用哈希索引和并行处理大幅提升性能
        
        Args:
            image_files: 图片文件路径列表
            
        Returns:
            相似图片组列表
        """
        from collections import defaultdict
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        start_time = time.time()
        self.log(f"启用优化算法处理 {len(image_files)} 个文件")
        
        # 步骤1：并行计算哈希值
        file_hashes = []
        error_count = 0
        
        # 从缓存中恢复已计算的哈希
        processed_for_phash = set()
        for file_path in image_files:
            cached_hashes = self._get_from_cache(self.phash_cache, file_path)
            if cached_hashes:
                dhash, phash, ahash = cached_hashes
                file_hashes.append({
                    'file_path': file_path,  # 改为 file_path 避免旧格式警告
                    'dhash': dhash,
                    'phash': phash,
                    'ahash': ahash,
                    'dhash_int': int(dhash, 16) if dhash else 0
                })
                processed_for_phash.add(file_path)
        
        # 计算剩余文件的哈希
        remaining_files = [f for f in image_files if f not in processed_for_phash]
        
        if remaining_files:
            self.log(f"并行计算剩余 {len(remaining_files)} 个文件的哈希值...")
            
            # 更新线程状态
            self.thread_stats['current_stage'] = 'hash_calculation'
            
            def calculate_hash_batch(file_batch):
                """批量计算哈希值"""
                batch_results = []
                for file_path in file_batch:
                    if self.should_stop:
                        break
                    try:
                        dhash = calculate_dhash(file_path)
                        phash = calculate_phash(file_path)
                        ahash = calculate_ahash(file_path)
                        
                        if dhash and phash and ahash:
                            result = {
                                'file_path': file_path,
                                'dhash': dhash,
                                'phash': phash,
                                'ahash': ahash,
                                'dhash_int': int(dhash, 16)
                            }
                            batch_results.append(result)
                            # 缓存结果
                            self._manage_cache_size(self.phash_cache, file_path, (dhash, phash, ahash))
                            # 更新已完成任务数
                            self.thread_stats['completed_tasks'] += 1
                    except Exception as e:
                        self.log(f"计算哈希失败: {os.path.basename(file_path)} - {str(e)}")
                        continue
                return batch_results
            
            # 分批并行处理
            batch_size = max(1, len(remaining_files) // 32)  # 32个批次
            batches = [remaining_files[i:i+batch_size] for i in range(0, len(remaining_files), batch_size)]
            
            # 使用跟踪的线程池
            hash_pool = ThreadPoolExecutor(max_workers=min(8, len(batches)))  # 降低线程数避免UI卡死
            self.thread_pools['hash_pool'] = hash_pool
            self.thread_stats['active_tasks'] = len(batches)
            self.thread_stats['completed_tasks'] = 0
            self.thread_stats['hash_threads'] = getattr(hash_pool, '_max_workers', 0)
            
            try:
                future_to_batch = {hash_pool.submit(calculate_hash_batch, batch): i for i, batch in enumerate(batches)}
                
                completed_batches = 0
                for future in as_completed(future_to_batch):
                    if self.should_stop:
                        break
                    
                    batch_results = future.result()
                    file_hashes.extend(batch_results)
                    
                    completed_batches += 1
                    self.thread_stats['completed_tasks'] = completed_batches
                    self.thread_stats['active_tasks'] = max(0, len(batches) - completed_batches)
                    progress = completed_batches / len(batches) * 100
                    self.log(f"哈希计算进度: {completed_batches}/{len(batches)} ({progress:.1f}%)")
            finally:
                # 使用改进的线程池强制关闭方法
                self._force_shutdown_thread_pool(hash_pool, 'hash_pool')
                
                # 清理线程池引用
                with self._thread_pools_lock:
                    self.thread_pools['hash_pool'] = None
                    if 'hash_pool' in self.thread_pools:
                        del self.thread_pools['hash_pool']
                        
                # 重置线程统计
                self.thread_stats['hash_threads'] = 0
                self.thread_stats['current_stage'] = 'idle'
        
        if not file_hashes:
            self.log("没有成功计算的哈希值")
            return []
        
        self.log(f"成功计算 {len(file_hashes)} 个文件的哈希值")
        
        # 步骤2：创建哈希索引（按dhash前16位分组）
        self.log("创建哈希索引...")
        hash_index = defaultdict(list)
        prefix_bits = 16
        mask = (1 << prefix_bits) - 1
        
        for file_hash in file_hashes:
            prefix = file_hash['dhash_int'] & mask
            hash_index[prefix].append(file_hash)
        
        # 统计优化效果
        group_sizes = [len(group) for group in hash_index.values()]
        total_files = len(file_hashes)
        naive_comparisons = total_files * (total_files - 1) // 2
        optimized_comparisons = sum(size * (size - 1) // 2 for size in group_sizes)
        optimization_ratio = naive_comparisons / optimized_comparisons if optimized_comparisons > 0 else 1
        
        self.log(f"索引优化效果: 比较次数从 {naive_comparisons:,} 减少到 {optimized_comparisons:,} ({optimization_ratio:.1f}x 提升)")
        
        # 步骤3：分组并行比较
        self.log("开始分组比较...")
        all_similar_groups = []
        total_comparisons = 0
        
        def compare_group(group):
            """优化的组内比较，支持向量化和早期终止"""
            if len(group) < 2:
                return [], 0
            
            # 预处理：转换哈希值为整数形式以加速计算
            for file_hash in group:
                if 'dhash_int' not in file_hash:
                    file_hash['dhash_int'] = int(file_hash['dhash'], 16)
                    file_hash['phash_int'] = int(file_hash['phash'], 16)
                    file_hash['ahash_int'] = int(file_hash['ahash'], 16)
            
            # 大组使用向量化比较
            if len(group) > 50:
                return self._vectorized_group_compare_optimized(group)
            else:
                # 小组使用标准优化比较
                return self._standard_group_compare(group)
        
        # 智能分组策略：处理超大组
        large_groups = [group for group in hash_index.values() if len(group) >= 2]
        
        # 检测和处理超大组
        optimized_groups = self._optimize_large_groups(large_groups)
        
        if optimized_groups:
            # 初始化分组比较进度
            if not hasattr(self, 'group_comparison_progress'):
                self.group_comparison_progress = {}
            
            # 检查并恢复已处理的分组
            remaining_groups = []
            for i, group in enumerate(optimized_groups):
                # 使用分组的哈希前缀和大小作为唯一标识
                group_key = f"group_{i}_{len(group)}_{hash(tuple(sorted([f['file_path'] for f in group[:5]])))}"
                if group_key not in self.group_comparison_progress:
                    remaining_groups.append((i, group, group_key))
                else:
                    # 恢复已处理分组的结果
                    saved_results = self.group_comparison_progress[group_key]
                    all_similar_groups.extend(saved_results.get('similar_groups', []))
                    total_comparisons += saved_results.get('comparisons', 0)
            
            if remaining_groups:
                self.log(f"开始处理 {len(remaining_groups)} 个分组（跳过已处理的 {len(optimized_groups) - len(remaining_groups)} 个分组）")
            else:
                self.log("所有分组已处理完成")
                return all_similar_groups
            
            # 更新线程状态
            self.thread_stats['current_stage'] = 'group_comparison'
            self.thread_stats['active_tasks'] = len(remaining_groups)
            self.thread_stats['completed_tasks'] = len(optimized_groups) - len(remaining_groups)
            
            # 使用适中的线程进行并行处理
            max_workers = min(8, max(4, len(remaining_groups)))  # 降低线程数避免UI卡死
            compare_pool = ThreadPoolExecutor(max_workers=max_workers)
            self.thread_pools['compare_pool'] = compare_pool
            self.thread_stats['compare_threads'] = max_workers
            
            try:
                # 创建任务映射，包含分组索引和分组键
                future_to_group = {}
                for group_index, group, group_key in remaining_groups:
                    future = compare_pool.submit(compare_group, group)
                    future_to_group[future] = (group_index, group_key)
                
                completed_groups = len(optimized_groups) - len(remaining_groups)  # 已完成的分组数
                for future in as_completed(future_to_group):
                    if self.should_stop:
                        self.log("扫描已停止")
                        self._save_current_progress()
                        break
                    
                    group_index, group_key = future_to_group[future]
                    group_results, group_comparisons = future.result()
                    
                    # 保存当前分组的进度
                    self.group_comparison_progress[group_key] = {
                        'similar_groups': group_results,
                        'comparisons': group_comparisons,
                        'completed_at': time.time()
                    }
                    
                    all_similar_groups.extend(group_results)
                    total_comparisons += group_comparisons
                    
                    completed_groups += 1
                    self.thread_stats['completed_tasks'] = completed_groups
                    self.thread_stats['active_tasks'] = max(0, len(optimized_groups) - completed_groups)
                    
                    # 减少日志输出频率以降低UI卡顿
                    if completed_groups % 50 == 0 or completed_groups == len(optimized_groups):
                        progress = completed_groups / len(optimized_groups) * 100
                        self.log(f"分组比较进度: {completed_groups}/{len(optimized_groups)} ({progress:.1f}%)")
                        
                    # 定期保存进度和管理内存
                    if completed_groups % 100 == 0:
                        self._save_current_progress()
                        self._auto_manage_memory()
            finally:
                # 使用改进的线程池强制关闭方法
                self._force_shutdown_thread_pool(compare_pool, 'compare_pool')
                
                # 清理线程池引用
                with self._thread_pools_lock:
                    self.thread_pools['compare_pool'] = None
                    if 'compare_pool' in self.thread_pools:
                        del self.thread_pools['compare_pool']
                        
                # 重置线程统计
                self.thread_stats['compare_threads'] = 0
                self.thread_stats['current_stage'] = 'idle'
        
        # 更新统计信息
        self.phash_groups = all_similar_groups
        if all_similar_groups:
            for group in all_similar_groups:
                reason = group['reason']
                self.stats['reasons'][reason] = self.stats['reasons'].get(reason, 0) + 1
            
            self.stats['duplicate_groups'] += len(all_similar_groups)
            self.stats['duplicate_images'] += sum(len(group['files']) - 1 for group in all_similar_groups)
        
        # 标记阶段完成
        if not self.should_stop and "perceptual_hash" not in self.completed_stages:
            self.completed_stages.append("perceptual_hash")
            self._save_current_progress()
        
        total_time = time.time() - start_time
        self.log(f"优化算法完成:")
        self.log(f"  - 总耗时: {total_time:.2f} 秒")
        self.log(f"  - 实际比较次数: {total_comparisons:,}")
        self.log(f"  - 优化倍数: {optimization_ratio:.1f}x")
        self.log(f"  - 找到相似组: {len(all_similar_groups)} 个")
        
        return all_similar_groups
    
    def _vectorized_group_compare_optimized(self, group):
        """向量化组内比较（适用于大组，基于超高速算法优化）"""
        try:
            import numpy as np
        except ImportError:
            self.log("NumPy未安装，回退到标准比较")
            return self._standard_group_compare(group)
        
        group_similar = []
        group_processed = set()
        comparisons = 0
        
        def hex_to_binary_array_fast(hex_hash):
            """高效的十六进制哈希转换为二进制数组"""
            # 直接使用整数位运算，避免字符串转换
            hash_int = int(hex_hash, 16)
            # 使用numpy的unpackbits更高效
            hash_bytes = np.array([hash_int], dtype=np.uint64)
            return np.unpackbits(hash_bytes.view(np.uint8))[:64]
        
        def hamming_distance_vectorized_fast(hash1_array, hash2_array):
            """优化的向量化汉明距离计算"""
            # 使用XOR + popcount，比逐位比较更快
            if hash1_array.ndim == 1:
                hash1_array = hash1_array.reshape(1, -1)
            xor_result = hash1_array ^ hash2_array
            return np.sum(xor_result, axis=1, dtype=np.uint8)
        
        def early_termination_filter_vectorized(dhash_ints, target_dhash_int, max_threshold):
            """向量化早期终止过滤"""
            # 使用位运算快速估算距离
            xor_results = dhash_ints ^ target_dhash_int
            rough_distances = np.array([bin(x).count('1') for x in xor_results])
            return rough_distances <= max_threshold * 2
        
        # 预处理：确保所有哈希都有整数形式
        for file_hash in group:
            if 'dhash_int' not in file_hash:
                try:
                    file_hash['dhash_int'] = int(file_hash['dhash'], 16)
                    file_hash['phash_int'] = int(file_hash['phash'], 16)
                    file_hash['ahash_int'] = int(file_hash['ahash'], 16)
                except (ValueError, KeyError) as e:
                    self.log(f"向量化哈希转换错误: {file_hash.get('file_path', 'unknown')} - {str(e)}")
                    # 设置默认值以避免后续错误
                    file_hash['dhash_int'] = 0
                    file_hash['phash_int'] = 0
                    file_hash['ahash_int'] = 0
        
        # 转换为NumPy数组以加速计算
        dhash_arrays = []
        phash_arrays = []
        ahash_arrays = []
        dhash_ints = np.array([file_hash['dhash_int'] for file_hash in group], dtype=np.uint64)
        phash_ints = np.array([file_hash['phash_int'] for file_hash in group], dtype=np.uint64)
        ahash_ints = np.array([file_hash['ahash_int'] for file_hash in group], dtype=np.uint64)
        
        # 只在需要时才转换为二进制数组（延迟计算）
        dhash_matrix = None
        phash_matrix = None
        ahash_matrix = None
        
        # 批量比较（优化版）
        max_threshold = max(self.dhash_threshold, self.phash_threshold, self.ahash_threshold)
        
        for i, file1 in enumerate(group):
            if file1['file_path'] in group_processed or self.should_stop:
                continue
            
            # 计算与后续所有元素的距离
            remaining_indices = list(range(i + 1, len(group)))
            if not remaining_indices:
                continue
            
            # 早期终止过滤：使用整数XOR快速预筛选
            remaining_dhash_ints = dhash_ints[remaining_indices]
            target_dhash_int = dhash_ints[i]
            
            # 向量化早期过滤
            filter_mask = early_termination_filter_vectorized(
                remaining_dhash_ints, target_dhash_int, max_threshold
            )
            
            # 只对通过预筛选的文件进行精确计算
            filtered_indices = [remaining_indices[j] for j, passed in enumerate(filter_mask) if passed]
            
            if not filtered_indices:
                continue
            
            # 延迟初始化二进制矩阵（只在需要时）
            if dhash_matrix is None:
                dhash_arrays = [hex_to_binary_array_fast(file_hash['dhash']) for file_hash in group]
                phash_arrays = [hex_to_binary_array_fast(file_hash['phash']) for file_hash in group]
                ahash_arrays = [hex_to_binary_array_fast(file_hash['ahash']) for file_hash in group]
                
                dhash_matrix = np.array(dhash_arrays)
                phash_matrix = np.array(phash_arrays)
                ahash_matrix = np.array(ahash_arrays)
            
            # 向量化距离计算（只对过滤后的文件）
            dhash_distances = hamming_distance_vectorized_fast(
                dhash_matrix[filtered_indices], dhash_matrix[i:i+1]
            )
            phash_distances = hamming_distance_vectorized_fast(
                phash_matrix[filtered_indices], phash_matrix[i:i+1]
            )
            ahash_distances = hamming_distance_vectorized_fast(
                ahash_matrix[filtered_indices], ahash_matrix[i:i+1]
            )
            
            comparisons += len(filtered_indices)
            
            similar_files = []
            
            for idx, j in enumerate(filtered_indices):
                file2 = group[j]
                if file2['file_path'] in group_processed:
                    continue
                
                dhash_distance = dhash_distances[idx]
                phash_distance = phash_distances[idx]
                ahash_distance = ahash_distances[idx]
                
                # 判断相似性
                dhash_similar = dhash_distance <= self.dhash_threshold
                phash_similar = phash_distance <= self.phash_threshold
                ahash_similar = ahash_distance <= self.ahash_threshold
                
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                
                if similar_count >= 2:
                    reasons = []
                    if dhash_similar:
                        reasons.append("dHash")
                    if phash_similar:
                        reasons.append("pHash")
                    if ahash_similar:
                        reasons.append("aHash")
                    
                    similar_files.append({
                        'file_path': file2['file_path'],
                        'dhash_distance': int(dhash_distance),
                        'phash_distance': int(phash_distance),
                        'ahash_distance': int(ahash_distance),
                        'reason': '+'.join(reasons) + '相似(向量化)'
                    })
            
            if similar_files:
                # 创建相似组
                files_with_distances = [{
                    'file_path': file1['file_path'],
                    'dhash_distance': 0,
                    'phash_distance': 0,
                    'ahash_distance': 0
                }] + similar_files
                
                group_info = {
                    'reason': similar_files[0]['reason'],
                    'files': [item['file_path'] for item in files_with_distances],
                    'files_with_distances': files_with_distances
                }
                group_similar.append(group_info)
                
                # 标记为已处理
                group_processed.add(file1['file_path'])
                for f in similar_files:
                    group_processed.add(f['file_path'])
        
        return group_similar, comparisons
    
    def _optimize_large_groups(self, groups):
        """智能分组优化：处理超大组，避免性能瓶颈"""
        optimized_groups = []
        large_group_threshold = 1000  # 超大组阈值
        
        for group in groups:
            if len(group) <= large_group_threshold:
                # 正常大小的组直接添加
                optimized_groups.append(group)
            else:
                # 超大组需要进一步细分
                self.log(f"检测到超大组 ({len(group)} 个文件)，进行智能细分...")
                sub_groups = self._subdivide_large_group(group)
                optimized_groups.extend(sub_groups)
                self.log(f"超大组已细分为 {len(sub_groups)} 个子组")
        
        return optimized_groups
    
    def _subdivide_large_group(self, large_group):
        """细分超大组为更小的子组"""
        try:
            import numpy as np
        except ImportError:
            # 如果没有NumPy，使用简单的分割策略
            chunk_size = 500
            return [large_group[i:i+chunk_size] for i in range(0, len(large_group), chunk_size)]
        
        # 使用多级哈希进行智能细分
        sub_groups = {}
        
        for file_hash in large_group:
            # 使用phash的前8位作为二级分组键
            phash_prefix = file_hash['phash'][:8]
            
            if phash_prefix not in sub_groups:
                sub_groups[phash_prefix] = []
            sub_groups[phash_prefix].append(file_hash)
        
        # 进一步细分仍然过大的子组
        final_groups = []
        for prefix, sub_group in sub_groups.items():
            if len(sub_group) > 500:  # 子组仍然过大
                # 使用ahash进行三级分组
                tertiary_groups = {}
                for file_hash in sub_group:
                    ahash_prefix = file_hash['ahash'][:4]
                    key = f"{prefix}_{ahash_prefix}"
                    
                    if key not in tertiary_groups:
                        tertiary_groups[key] = []
                    tertiary_groups[key].append(file_hash)
                
                # 添加三级分组结果
                for tertiary_group in tertiary_groups.values():
                    if len(tertiary_group) >= 2:  # 只保留有意义的组
                        final_groups.append(tertiary_group)
            else:
                if len(sub_group) >= 2:  # 只保留有意义的组
                    final_groups.append(sub_group)
        
        return final_groups
    
    def _standard_group_compare(self, group):
        """标准组内比较（小组使用）"""
        group_similar = []
        group_processed = set()
        comparisons = 0
        
        # 确保所有文件都有整数形式的哈希值
        for file_hash in group:
            if 'dhash_int' not in file_hash:
                try:
                    file_hash['dhash_int'] = int(file_hash['dhash'], 16)
                    file_hash['phash_int'] = int(file_hash['phash'], 16)
                    file_hash['ahash_int'] = int(file_hash['ahash'], 16)
                except (ValueError, KeyError) as e:
                    self.log(f"哈希转换错误: {file_hash.get('file_path', 'unknown')} - {str(e)}")
                    # 设置默认值以避免后续错误
                    file_hash['dhash_int'] = 0
                    file_hash['phash_int'] = 0
                    file_hash['ahash_int'] = 0
        
        for i, file1 in enumerate(group):
            if file1['file_path'] in group_processed or self.should_stop:
                continue
            
            similar_files = []
            
            for j in range(i + 1, len(group)):
                file2 = group[j]
                if file2['file_path'] in group_processed:
                    continue
                
                # 优化的早期终止过滤
                # 使用更快的位运算估算距离
                xor_result = file1['dhash_int'] ^ file2['dhash_int']
                # 快速估算：检查是否有太多不同的位
                if xor_result.bit_count() > max(self.dhash_threshold, self.phash_threshold, self.ahash_threshold) * 2:
                    continue
                
                # 进一步过滤：检查phash的粗略距离
                phash_xor = file1['phash_int'] ^ file2['phash_int']
                if phash_xor.bit_count() > self.phash_threshold * 3:
                    continue
                
                # 精确计算哈希距离
                dhash_distance = bin(file1['dhash_int'] ^ file2['dhash_int']).count('1')
                phash_distance = bin(file1['phash_int'] ^ file2['phash_int']).count('1')
                ahash_distance = bin(file1['ahash_int'] ^ file2['ahash_int']).count('1')
                
                comparisons += 1
                
                # 判断相似性
                dhash_similar = dhash_distance <= self.dhash_threshold
                phash_similar = phash_distance <= self.phash_threshold
                ahash_similar = ahash_distance <= self.ahash_threshold
                
                similar_count = sum([dhash_similar, phash_similar, ahash_similar])
                
                if similar_count >= 2:
                    reasons = []
                    if dhash_similar:
                        reasons.append("dHash")
                    if phash_similar:
                        reasons.append("pHash")
                    if ahash_similar:
                        reasons.append("aHash")
                    
                    similar_files.append({
                        'file_path': file2['file_path'],
                        'dhash_distance': dhash_distance,
                        'phash_distance': phash_distance,
                        'ahash_distance': ahash_distance,
                        'reason': '+'.join(reasons) + '相似(标准+)'
                    })
            
            if similar_files:
                # 创建相似组
                files_with_distances = [{
                    'file_path': file1['file_path'],
                    'dhash_distance': 0,
                    'phash_distance': 0,
                    'ahash_distance': 0
                }] + similar_files
                
                group_info = {
                    'reason': similar_files[0]['reason'],
                    'files': [item['file_path'] for item in files_with_distances],
                    'files_with_distances': files_with_distances
                }
                group_similar.append(group_info)
                
                # 标记为已处理
                group_processed.add(file1['file_path'])
                for f in similar_files:
                    group_processed.add(f['file_path'])
        
        return group_similar, comparisons
    
    def _check_perceptual_duplicates_ultra_fast(self, image_files: List[str]) -> List[Dict[str, Any]]:
        """
        超高速感知哈希查重算法
        针对超大规模数据集（>10万张图片）的极致优化
        """
        try:
            # 导入超高速查重器
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from ultra_fast_duplicate_checker import UltraFastDuplicateChecker
            
            # 创建超高速查重器实例
            ultra_checker = UltraFastDuplicateChecker(
                dhash_threshold=self.dhash_threshold,
                phash_threshold=self.phash_threshold,
                ahash_threshold=self.ahash_threshold,
                index_levels=3,  # 使用3级索引
                max_workers=min(8, (os.cpu_count() or 1) * 2),  # 降低线程数避免UI卡死
                batch_size=1000,
                enable_vectorization=True
            )
            
            # 设置日志回调
            ultra_checker.set_log_callback(self.log)
            
            # 执行超高速查重
            similar_groups = ultra_checker.check_duplicates_ultra_fast(image_files)
            
            # 更新统计信息
            self.phash_groups = similar_groups
            if similar_groups:
                for group in similar_groups:
                    reason = group['reason']
                    self.stats['reasons'][reason] = self.stats['reasons'].get(reason, 0) + 1
                
                self.stats['duplicate_groups'] += len(similar_groups)
                self.stats['duplicate_images'] += sum(len(group['files']) - 1 for group in similar_groups)
            
            # 标记阶段完成
            if not self.should_stop and "perceptual_hash" not in self.completed_stages:
                self.completed_stages.append("perceptual_hash")
                self._save_current_progress()
            
            return similar_groups
            
        except ImportError as e:
            self.log(f"超高速算法导入失败，回退到优化算法: {str(e)}")
            return self._check_perceptual_duplicates_optimized(image_files)
        except Exception as e:
            self.log(f"超高速算法执行失败，回退到优化算法: {str(e)}")
            return self._check_perceptual_duplicates_optimized(image_files)
        else:
            self.log("\n步骤1: 完全相同重复图片检查已完成，跳过")
            exact_duplicates = {h: files for h, files in self.file_hash_groups.items() if len(files) > 1}
        
        # 从图片列表中移除完全相同的重复图片（只保留每组的第一个）
        unique_images = []
        processed_files = set()
        
        for files in exact_duplicates.values():
            unique_images.append(files[0])
            for file_path in files:
                processed_files.add(file_path)
        
        for file_path in image_files:
            if file_path not in processed_files:
                unique_images.append(file_path)
        
        # 步骤2: 检测纯色图片
        if "pure_color" not in self.completed_stages:
            self.log(f"\n步骤2: 使用C++库检测纯色图片 (共 {len(unique_images)} 个唯一文件)")
            pure_color_images = self.check_pure_color_images(unique_images)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        else:
            self.log("\n步骤2: 纯色图片检测已完成，跳过")
            pure_color_images = self.pure_color_images
        
        # 从图片列表中移除纯色图片
        if pure_color_images:
            unique_images = [img for img in unique_images if img not in set(pure_color_images)]
        
        # 步骤3: 检查感知上相似的图片
        if "perceptual_hash" not in self.completed_stages:
            self.log(f"\n步骤3: 使用C++库检查感知上相似的图片 (共 {len(unique_images)} 个唯一文件)")
            similar_groups = self.check_perceptual_duplicates(unique_images)
            
            if self.should_stop:
                self.log("扫描被用户停止")
                if self.enable_resume:
                    self._save_current_progress()
                return self.stats
        else:
            self.log("\n步骤3: 感知相似图片检查已完成，跳过")
            similar_groups = self.phash_groups
        
        # 生成结果
        all_duplicate_groups = []
        
        # 添加完全相同的重复组
        for file_hash, files in exact_duplicates.items():
            all_duplicate_groups.append({
                'reason': '完全相同(C++)',
                'files': files
            })
        
        # 添加纯色图片组（如果有）
        if self.pure_color_images:
            all_duplicate_groups.append({
                'reason': '纯色图片(C++)',
                'files': self.pure_color_images
            })
            self.stats['reasons']['纯色图片(C++)'] = 1
            if not self.stats['duplicate_groups']:
                self.stats['duplicate_groups'] = 1
        
        # 添加感知相似的重复组
        all_duplicate_groups.extend(similar_groups)
        
        # 保存结果
        if all_duplicate_groups:
            csv_path = self.logger.save_to_csv(all_duplicate_groups)
            json_path = self.logger.save_to_json(all_duplicate_groups)
            summary_path = self.logger.save_summary(self.stats)
            
            self.log(f"\n查重结果已保存到:")
            self.log(f"- CSV: {csv_path}")
            self.log(f"- JSON: {json_path}")
            self.log(f"- 摘要: {summary_path}")
        else:
            self.log("\n未发现重复图片")
        
        # 清除扫描进度（扫描完成）
        if self.enable_resume:
            self.clear_scan_progress(directory)
        
        # 计算总耗时
        total_time = time.time() - start_time
        self.log(f"\n查重完成！总耗时: {total_time:.2f} 秒")
        self.log(f"扫描到 {self.stats['total_images']} 个图片文件，实际处理了 {self.stats['processed_images']} 个文件")
        self.log(f"发现 {self.stats['duplicate_groups']} 个重复组，包含 {self.stats['duplicate_images']} 个重复图片")
        
        return self.stats