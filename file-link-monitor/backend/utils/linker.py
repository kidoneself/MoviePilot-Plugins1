import os
import shutil
from pathlib import Path
from typing import Tuple
import logging
import fnmatch
from .obfuscator import FolderObfuscator

logger = logging.getLogger(__name__)


class FileLinker:
    """文件硬链接工具类"""
    
    def __init__(self, obfuscate_enabled: bool = False):
        """
        初始化硬链接工具
        
        Args:
            obfuscate_enabled: 是否启用文件夹名混淆
        """
        self.obfuscator = FolderObfuscator(enabled=obfuscate_enabled)

    def create_hardlink(self, source: Path, target: Path, source_base: Path = None, target_base: Path = None) -> Tuple[bool, str, str]:
        """
        创建硬链接，失败则降级为复制（支持文件夹名混淆）
        
        Args:
            source: 源文件路径
            target: 目标文件路径
            source_base: 源目录基础路径（用于计算相对路径）
            target_base: 目标目录基础路径（用于混淆）
            
        Returns:
            (是否成功, 使用的方法, 错误信息)
        """
        try:
            # 应用文件夹名混淆
            if self.obfuscator.enabled:
                target = self._apply_folder_obfuscation(source, target, source_base, target_base)
            
            # 确保目标目录存在
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果目标文件已存在，先删除
            if target.exists():
                logger.info(f"目标文件已存在，删除: {target}")
                target.unlink()
            
            # 尝试创建硬链接
            try:
                os.link(str(source), str(target))
                logger.info(f"硬链接成功: {source} -> {target}")
                return True, "硬链接", None
            except OSError as e:
                # 硬链接失败，降级为复制
                logger.warning(f"硬链接失败，尝试复制: {e}")
                shutil.copy2(str(source), str(target))
                logger.info(f"复制成功: {source} -> {target}")
                return True, "复制", None
                
        except Exception as e:
            error_msg = f"操作失败: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def _apply_folder_obfuscation(self, source: Path, target: Path, source_base: Path = None, target_base: Path = None) -> Path:
        """
        应用文件夹名混淆和文件名改名
        
        Args:
            source: 源文件路径
            target: 目标文件路径
            source_base: 源目录基础路径
            target_base: 目标目录基础路径
            
        Returns:
            混淆后的目标路径
        """
        # 如果提供了基础路径，使用它们计算相对路径
        if source_base and target_base:
            try:
                # 计算源文件相对于源目录的相对路径
                relative_path = source.relative_to(source_base)
                relative_parts = list(relative_path.parts[:-1])  # 不含文件名
                file_name = relative_path.parts[-1]
            except ValueError:
                # 回退到旧逻辑
                parts = list(target.parts)
                base_idx = len(target_base.parts)
                relative_parts = parts[base_idx:-1]
                file_name = parts[-1]
        else:
            # 旧逻辑：从target.parts猜测
            parts = list(target.parts)
            base_idx = 0
            for i, part in enumerate(parts):
                if part.startswith('/') or (i > 0 and parts[i-1] == '/'):
                    base_idx = i + 1
            base_parts = parts[:base_idx] if base_idx > 0 else []
            relative_parts = parts[base_idx:-1]
            file_name = parts[-1]
            target_base = Path(*base_parts) if base_parts else Path('/')
            
        # 改名视频文件
        new_file_name = self.obfuscator.rename_video_file(file_name)
        logger.info(f"文件名改名: {file_name} -> {new_file_name}")
        
        if relative_parts:
            # 先检查是否存在旧混淆路径
            legacy_dir, is_legacy = self.obfuscator.check_legacy_path(
                source, target_base, relative_parts
            )
            
            if is_legacy:
                # 使用已存在的旧混淆路径
                result = legacy_dir / new_file_name
                logger.info(f"使用旧混淆路径: {'/'.join(legacy_dir.parts[len(target_base.parts):])}")
                return result
            
            # 没有旧路径，使用混淆逻辑处理
            obfuscated_parts = self.obfuscator.obfuscate_folder_path(relative_parts)
            obfuscated_dir = target_base / Path(*obfuscated_parts)
            result = obfuscated_dir / new_file_name
            logger.info(f"路径混淆: {'/'.join(relative_parts)} -> {'/'.join(obfuscated_parts)}")
            return result
        else:
            # 没有相对路径，只改文件名
            return target_base / new_file_name
    
    @staticmethod
    def get_relative_path(file_path: Path, base_path: Path) -> Path:
        """获取相对路径"""
        try:
            return file_path.relative_to(base_path)
        except ValueError:
            return file_path
    
    def link_template_files(self, target_dir: Path, template_dir: Path) -> int:
        """
        将模板目录的文件硬链接到目标目录
        
        Args:
            target_dir: 目标剧集文件夹路径
            template_dir: 模板文件目录路径
            
        Returns:
            成功链接的文件数量
        """
        if not template_dir or not template_dir.exists():
            return 0
        
        linked_count = 0
        try:
            # 遍历模板目录中的所有文件
            for template_file in template_dir.iterdir():
                if template_file.is_file():
                    target_file = target_dir / template_file.name
                    
                    # 如果目标文件已存在，跳过
                    if target_file.exists():
                        logger.debug(f"模板文件已存在，跳过: {target_file}")
                        continue
                    
                    try:
                        # 创建硬链接
                        os.link(str(template_file), str(target_file))
                        logger.info(f"✓ 模板文件硬链接: {template_file.name} -> {target_dir}")
                        linked_count += 1
                    except OSError as e:
                        # 硬链接失败，尝试复制
                        try:
                            shutil.copy2(str(template_file), str(target_file))
                            logger.info(f"✓ 模板文件复制: {template_file.name} -> {target_dir}")
                            linked_count += 1
                        except Exception as copy_err:
                            logger.error(f"模板文件链接/复制失败: {template_file.name}, 错误: {copy_err}")
        except Exception as e:
            logger.error(f"处理模板文件失败: {e}")
        
        return linked_count
    
    @staticmethod
    def should_exclude(file_path: Path, exclude_patterns: list) -> bool:
        """检查文件是否应该被排除"""
        if not exclude_patterns:
            return False
        
        import fnmatch
        file_name = file_path.name
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                logger.debug(f"文件被排除: {file_name} (匹配模式: {pattern})")
                return True
        
        return False
