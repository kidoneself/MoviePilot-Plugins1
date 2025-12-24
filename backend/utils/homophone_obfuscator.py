# -*- coding: utf-8 -*-
"""
同音字混淆器 - 确定性哈希方案
用MD5哈希确保同一名字永远生成相同的混淆结果
"""
import hashlib
from .homophone_map import HOMOPHONE_MAP


class HomophoneObfuscator:
    """同音字混淆器"""
    
    def __init__(self):
        """初始化混淆器"""
        self.homophone_map = HOMOPHONE_MAP
    
    def obfuscate(self, name: str) -> str:
        """
        混淆文件名 - 使用同音字替换
        只混淆中文，英文、数字、符号保持不变
        
        Args:
            name: 原始名称
            
        Returns:
            混淆后的名称（用.分隔中文）
        """
        import re
        
        # 生成固定哈希值作为种子
        hash_value = int(hashlib.md5(name.encode('utf-8')).hexdigest(), 16)
        
        result = []
        i = 0
        for char in name:
            if char in self.homophone_map:
                # 中文字符：使用同音字替换
                candidates = self.homophone_map[char]
                index = (hash_value + i) % len(candidates)
                result.append(candidates[index])
                i += 1
            elif '\u4e00' <= char <= '\u9fff':
                # 中文字符但不在映射表中，保持原样
                result.append(char)
                i += 1
            else:
                # 非中文（英文、数字、符号、空格等）保持不变
                # 如果前面有内容且是中文，不加点
                if result and not result[-1].isascii():
                    result.append('.')
                result.append(char)
        
        # 清理多余的点
        obfuscated = ''.join(result)
        obfuscated = re.sub(r'\.+', '.', obfuscated)  # 多个点变一个
        obfuscated = re.sub(r'^\.|\.(?=\s)|(?<=\s)\.|\.(?=[^\u4e00-\u9fff])|(?<=[^\u4e00-\u9fff])\.', '', obfuscated)  # 去掉不需要的点
        
        return obfuscated
    
    def obfuscate_with_year(self, name: str) -> str:
        """
        混淆文件名并去掉年份
        
        例如：超感迷宫 (2025) → 钞敢密功
        
        Args:
            name: 原始名称（可能包含年份）
            
        Returns:
            混淆后的名称（不含年份）
        """
        import re
        
        # 去掉年份部分 (YYYY)
        base_name = re.sub(r'\s*\((\d{4})\)\s*$', '', name).strip()
        return self.obfuscate(base_name)


def test_obfuscator():
    """测试混淆器"""
    obf = HomophoneObfuscator()
    
    test_names = [
        '超感迷宫 (2025)',
        '庆余年',
        '繁花',
        '与凤行',
        '狐妖小红娘',
        '三体',
        '墨雨云间',
        '大奉打更人',
    ]
    
    print("=== 同音字混淆测试 ===\n")
    for name in test_names:
        obfuscated = obf.obfuscate_with_year(name)
        print(f"{name:20s} → {obfuscated}")
        
        # 验证确定性（多次执行结果相同）
        obfuscated2 = obf.obfuscate_with_year(name)
        assert obfuscated == obfuscated2, "混淆结果不一致！"
    
    print("\n✅ 确定性测试通过！同一名字永远生成相同结果。")


if __name__ == '__main__':
    test_obfuscator()
