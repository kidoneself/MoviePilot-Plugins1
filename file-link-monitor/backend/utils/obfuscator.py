"""
文件夹名混淆器 - 拆字方案
将汉字拆分为偏旁部首，达到混淆效果但保持一定辨识度
兼容旧插件的混淆方式（中文+拼音混合）
"""
import re
import hashlib
from pathlib import Path


class FolderObfuscator:
    """文件夹名混淆器 - 汉字拆字方案"""
    
    # 常用汉字拆字映射表（固定规则）
    CHAR_SPLIT_MAP = {
        # 常见影视剧用字
        '双': '又又', '轨': '车九', '速': '束', '度': '广彳又', '与': '一', '激': '氵白方',
        '情': '忄青', '权': '木又', '力': '力', '的': '白勺', '游': '氵斿', '戏': '戈戈又',
        '三': '三', '体': '亻本', '流': '氵㐬', '浪': '氵良', '地': '土也', '球': '王求',
        '爱': '爫友', '死': '歹匕', '机': '木几', '器': '口口口犬', '人': '人',
        '独': '犭虫', '行': '彳亍', '月': '月', '侠': '亻夹', '风': '风', '云': '云',
        '雨': '雨', '雷': '雨田', '电': '电', '火': '火', '水': '氵', '木': '木',
        '金': '金', '土': '土', '海': '氵每', '贼': '贝戋', '王': '王',
        '神': '礻申', '鬼': '鬼', '龙': '龙', '凤': '风凡', '虎': '虎',
        '狼': '犭良', '豹': '豸勺', '狮': '犭师', '鹰': '广隹', '熊': '能灬',
        '战': '战', '士': '士', '将': '将', '军': '车云', '国': '囗玉',
        '家': '宀豕', '天': '一大', '下': '一卜', '上': '卜一', '中': '口丨',
        '大': '大', '小': '小', '高': '高', '低': '亻氐', '长': '长',
        '短': '矢豆', '好': '女子', '坏': '土褱', '新': '亲斤', '旧': '旧',
        '东': '东', '西': '西', '南': '南', '北': '北', '前': '前',
        '后': '后', '左': '左', '右': '右', '里': '里', '外': '外',
        '黑': '黑', '白': '白', '红': '纟工', '绿': '纟录', '蓝': '蓝',
        '黄': '黄', '紫': '此糸', '灰': '火', '粉': '米分', '银': '金艮',
        '星': '日生', '辰': '辰', '日': '日', '夜': '夜', '晨': '日辰',
        '光': '光', '明': '日月', '暗': '日音', '亮': '亮', '黯': '黑音',
        '心': '心', '灵': '灵', '魂': '云鬼', '魄': '白鬼', '意': '音心',
        '志': '士心', '念': '今心', '想': '相心', '思': '田心', '忆': '忄乙',
        '恋': '亦心', '爱': '爫友', '情': '忄青', '欲': '谷欠', '望': '亡月王',
        '梦': '林夕', '幻': '幺丿', '想': '相心', '像': '亻象', '影': '彡景',
        '声': '士殳', '音': '音', '乐': '乐', '歌': '哥欠', '舞': '舛', 
        '剑': '剑', '刀': '刀', '枪': '木仓', '炮': '火包', '弓': '弓',
        '箭': '竹前', '盾': '盾', '甲': '甲', '兵': '兵', '将': '将',
        '侠': '亻夹', '客': '宀各', '贼': '贝戋', '匪': '匚非', '盗': '盗',
        '杀': '杀', '伤': '亻伤', '死': '歹匕', '生': '生', '活': '氵舌',
        '命': '命', '运': '辶军', '气': '气', '血': '血', '肉': '月',
        '骨': '骨', '皮': '皮', '毛': '毛', '发': '发', '手': '手',
        '足': '足', '头': '头', '目': '目', '口': '口', '耳': '耳',
        '鼻': '鼻', '身': '身', '心': '心', '脑': '月脑', '肺': '月市',
        '肝': '月干', '肾': '月臤', '胃': '月胃', '肠': '月肠', '血': '血',
        '泪': '氵泪', '汗': '氵干', '尿': '尸水', '屎': '尸米', '屁': '尸比',
        # 补充常用字
        '超': '走召', '感': '咸心', '迷': '辶米', '宫': '宀口',
        '产': '产', '剧': '刂居', '集': '隹木',
        '闻': '门耳', '女': '女',
        '港': '氵巷', '台': '台',
    }
    
    def __init__(self, enabled: bool = False):
        """
        初始化混淆器
        
        Args:
            enabled: 是否启用混淆
        """
        self.enabled = enabled
        # 加载拼音映射表（用于旧混淆算法）
        self.pinyin_map = self._load_pinyin_map()
    
    def obfuscate_name(self, name: str, max_length: int = 20) -> str:
        """
        混淆文件夹名（优先旧混淆，无效果才用拆字）
        
        Args:
            name: 原始文件夹名
            max_length: 最大长度限制
            
        Returns:
            混淆后的名称
        """
        if not self.enabled:
            return name
        
        # 1. 先尝试旧混淆算法
        legacy_result = self.obfuscate_name_legacy(name)
        
        # 2. 如果旧混淆有效果（结果不等于原字符串），直接返回
        if legacy_result != name:
            return legacy_result
        
        # 3. 旧混淆无效果，使用拆字混淆
        result = []
        current_length = 0
        
        for i, char in enumerate(name):
            # 如果已经达到长度限制，后续保持原样
            if current_length >= max_length:
                result.append(char)
                continue
            
            if char in self.CHAR_SPLIT_MAP:
                # 汉字拆分
                split_chars = self.CHAR_SPLIT_MAP[char]
                # 检查拆分后是否超长
                if current_length + len(split_chars) <= max_length:
                    result.append(split_chars)
                    current_length += len(split_chars)
                else:
                    # 超长了，用原字
                    result.append(char)
                    current_length += 1
            elif '\u4e00' <= char <= '\u9fff':
                # 未在映射表的汉字，用单字旧混淆
                legacy_char = self._obfuscate_single_char(char, i)
                result.append(legacy_char)
                current_length += len(legacy_char)
            else:
                # 数字、字母、符号保持不变
                result.append(char)
                current_length += 1
        
        return ''.join(result)
    
    def _obfuscate_single_char(self, char: str, position: int) -> str:
        """
        对单个汉字应用旧混淆逻辑（用于没有拆字映射的字）
        
        Args:
            char: 单个汉字
            position: 字符位置（用于哈希计算）
            
        Returns:
            混淆后的字符（可能是原字或拼音）
        """
        # 使用字符本身的MD5计算choice
        hash_obj = hashlib.md5(char.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # 根据位置和hash决定保留中文还是转拼音
        choice = (hash_int >> (position * 3)) % 2
        
        if choice == 0:
            # 保留中文
            return char
        else:
            # 转拼音
            return self.pinyin_map.get(char, char)
    
    def _get_pinyin_initial(self, char: str) -> str:
        """
        获取汉字拼音首字母（简化版）
        对于映射表之外的字，用哈希值映射到a-z
        """
        # 使用MD5哈希映射到字母
        hash_value = int(hashlib.md5(char.encode()).hexdigest(), 16)
        letter = chr(ord('a') + (hash_value % 26))
        return letter
    
    def _load_pinyin_map(self) -> dict:
        """加载简化的拼音映射表"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "plugins.v2" / "cloudlinkmonitor"))
            from pinyin_map import PINYIN_MAP
            return PINYIN_MAP
        except:
            return {}
    
    def obfuscate_name_legacy(self, name: str) -> str:
        """
        旧插件的混淆算法：中文+拼音混合+特殊字符
        关键：先提取年份，混淆后再加回
        
        Args:
            name: 原始名称
            
        Returns:
            旧算法混淆后的名称
        """
        # 提取年份（如果有）
        year_match = re.search(r'\((\d{4})\)$', name)
        year_suffix = f" ({year_match.group(1)})" if year_match else ""
        
        # 去掉年份后的目录名
        name_without_year = re.sub(r'\s*\(\d{4}\)$', '', name)
        
        special_chars = ['_', '-']
        
        # 使用MD5确保确定性（对去掉年份的名字计算）
        hash_obj = hashlib.md5(name_without_year.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)
        
        result = []
        for i, char in enumerate(name_without_year):
            # 根据hash决定处理方式
            choice = (hash_int >> (i * 3)) % 2
            
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                if choice == 0:
                    # 保留中文
                    result.append(char)
                else:
                    # 转拼音
                    pinyin = self.pinyin_map.get(char, char)
                    result.append(pinyin)
                
                # 添加特殊字符（概率30%）
                if (hash_int >> (i * 5)) % 10 < 3:
                    special_idx = (hash_int >> (i * 7)) % len(special_chars)
                    result.append(special_chars[special_idx])
            else:
                # 非中文字符保持不变
                result.append(char)
        
        # 混淆名 + 年份
        return ''.join(result) + year_suffix
    
    def obfuscate_folder_path(self, relative_parts: list) -> list:
        """
        混淆文件夹路径（完全照抄旧插件逻辑）
        
        Args:
            relative_parts: 相对路径的各部分（不含文件名）
            
        Returns:
            混淆后的路径各部分
        """
        if not self.enabled or not relative_parts:
            return relative_parts
        
        new_parts = []
        
        for i, dir_name in enumerate(relative_parts):
            # 保留Season目录不变
            if re.match(r'^Season\s+\d+$', dir_name, re.IGNORECASE):
                new_parts.append(dir_name)
                continue
            
            # 保留第一层分类目录不变（剧集、电影等）
            if i == 0:
                new_parts.append(dir_name)
                continue
            
            # 其他目录：混淆
            obfuscated = self.obfuscate_name(dir_name)
            new_parts.append(obfuscated)
        
        return new_parts
    
    def check_legacy_path(self, source_path: Path, target_base: Path, relative_parts: list) -> tuple:
        """
        检查是否存在旧混淆的多层路径结构
        
        Args:
            source_path: 源文件路径
            target_base: 目标基础路径
            relative_parts: 相对路径的各部分（不含文件名）
            
        Returns:
            (混淆后的目录路径, 是否使用旧混淆)
        """
        if not self.enabled or not relative_parts:
            return target_base / Path(*relative_parts), False
        
        # 1. 尝试用旧算法混淆所有文件夹层级
        legacy_parts = []
        for part in relative_parts:
            legacy_name = self.obfuscate_name_legacy(part)
            legacy_parts.append(legacy_name)
        
        # 2. 检查旧混淆的完整路径是否存在
        legacy_full_path = target_base / Path(*legacy_parts)
        if legacy_full_path.exists():
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✓ 检测到旧混淆路径: {'/'.join(legacy_parts)}")
            return legacy_full_path, True
        
        # 3. 旧路径不存在，使用新混淆（拆字方案）
        new_parts = []
        for part in relative_parts:
            new_name = self.obfuscate_name(part, max_length=20)
            new_parts.append(new_name)
        
        new_full_path = target_base / Path(*new_parts)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✓ 使用新混淆路径: {'/'.join(new_parts)}")
        return new_full_path, False
    
    def test_obfuscate(self, test_names: list) -> dict:
        """
        测试混淆效果
        
        Args:
            test_names: 测试名称列表
            
        Returns:
            {原名: 混淆名}
        """
        self.enabled = True
        results = {}
        for name in test_names:
            results[name] = self.obfuscate_name(name)
        return results


if __name__ == "__main__":
    # 测试
    obfuscator = FolderObfuscator(enabled=True)
    
    test_cases = [
        "双轨（2025）",
        "速度与激情10",
        "权力的游戏.S01",
        "三体",
        "流浪地球2",
        "独行月球",
        "神秘海域",
        "速度与激情10：狂野时速",
    ]
    
    print("拆字混淆测试（最大20字符）：\n")
    for name in test_cases:
        obfuscated = obfuscator.obfuscate_name(name, max_length=20)
        print(f"{name:25s} → {obfuscated:30s} (长度: {len(obfuscated)})")
