"""
文件夹名混淆器 - 同音字混淆方案
使用同音字替换达到混淆效果，更自然更难以识别
支持路径白名单（如欧美剧集不混淆）
"""
import re
import hashlib
from pathlib import Path
from .homophone_obfuscator import HomophoneObfuscator


class FolderObfuscator:
    """文件夹名混淆器 - 汉字拆字方案"""
    
    # 视频文件扩展名
    VIDEO_EXTENSIONS = {
        '.mkv', '.mp4', '.avi', '.rmvb', '.wmv', '.m2ts', '.iso',
        '.ts', '.mp4', '.flv', '.mpeg', '.mpg', '.mov'
    }
    
    # 字幕文件扩展名
    SUBTITLE_EXTENSIONS = {
        '.srt', '.ass', '.ssa', '.sub', '.idx', '.sup', '.vtt'
    }
    
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
    
    def __init__(self, enabled: bool = False, db_engine=None):
        """
        初始化混淆器
        
        Args:
            enabled: 是否启用混淆
            db_engine: 数据库引擎（用于查询自定义映射）
        """
        self.enabled = enabled
        self.db_engine = db_engine
        # 初始化同音字混淆器
        self.homophone_obfuscator = HomophoneObfuscator()
        # 加载拼音映射表（用于旧混淆算法备用）
        self.pinyin_map = self._load_pinyin_map()
        # 分类文件夹不混淆（一级和二级）
        self.category_folders = [
            # 一级分类
            '剧集', '电影', '动漫', '其他',
            # 二级分类 - 电影
            '港台电影', '国产电影', '日韩电影', '欧美电影', '动画电影',
            # 二级分类 - 剧集
            '港台剧集', '国产剧集', '日韩剧集', '南亚剧集', '欧美剧集',
            # 二级分类 - 动漫
            '国产动漫', '欧美动漫', '日本番剧',
            # 二级分类 - 其他
            '纪录影片', '综艺节目',
        ]
    
    @staticmethod
    def is_video_file(file_path) -> bool:
        """判断是否为视频文件"""
        from pathlib import Path
        return Path(file_path).suffix.lower() in FolderObfuscator.VIDEO_EXTENSIONS
    
    @staticmethod
    def is_subtitle_file(file_path) -> bool:
        """判断是否为字幕文件"""
        from pathlib import Path
        return Path(file_path).suffix.lower() in FolderObfuscator.SUBTITLE_EXTENSIONS
    
    @staticmethod
    def is_media_file(file_path) -> bool:
        """判断是否为媒体文件（视频或字幕）"""
        ext = Path(file_path).suffix.lower()
        return ext in FolderObfuscator.VIDEO_EXTENSIONS or ext in FolderObfuscator.SUBTITLE_EXTENSIONS
    
    @staticmethod
    def extract_show_name(file_path):
        """从文件路径提取剧集名称（包含年份的目录名）"""
        file_path = Path(file_path)
        # 向上查找包含年份格式 (YYYY) 的目录
        for parent in file_path.parents:
            if re.search(r'\(\d{4}\)', parent.name):
                return parent.name
        # 如果没找到年份，返回倒数第2级目录（通常是剧集目录）
        parts = file_path.parts
        if len(parts) >= 3:
            return parts[-3]
        return None
    
    @staticmethod
    def rename_video_file(file_name: str) -> str:
        """
        重命名视频文件为简化格式
        
        Args:
            file_name: 原始文件名
            
        Returns:
            新文件名（S01E01-1080p.mkv 或 1080p.mkv）
        """
        from pathlib import Path
        file_stem = Path(file_name).stem
        file_suffix = Path(file_name).suffix
        
        # 提取季集号（S01E01格式）
        season_episode = re.search(r'[Ss](\d+)[Ee](\d+)', file_stem)
        
        # 提取视频格式信息（1080p, 4K, 2160p等）
        video_format = re.search(r'(\d{3,4}[pP]|[248][kK]|[hH][dD]|[uU][hH][dD])', file_stem)
        
        if season_episode:
            # 电视剧：S01E01-1080p.mkv
            new_stem = f"S{season_episode.group(1)}E{season_episode.group(2)}"
            if video_format:
                new_stem += f"-{video_format.group(1)}"
        elif video_format:
            # 电影：1080p.mkv
            new_stem = video_format.group(1)
        else:
            # 没有识别到格式，使用movie作为前缀
            new_stem = "movie"
        
        return f"{new_stem}{file_suffix}"
    
    def _get_custom_mapping(self, name: str) -> str:
        """
        从数据库查询自定义名称映射
        
        Args:
            name: 原始名称
            
        Returns:
            自定义名称（如果存在），否则返回None
        """
        if not self.db_engine:
            return None
        
        try:
            from backend.models import CustomNameMapping, get_session
            session = get_session(self.db_engine)
            
            try:
                # 查询启用的自定义映射
                mapping = session.query(CustomNameMapping).filter(
                    CustomNameMapping.original_name == name,
                    CustomNameMapping.enabled == True
                ).first()
                
                if mapping:
                    # 优先返回quark_name，如果没有则返回baidu_name，都没有则返回原名
                    return mapping.quark_name or mapping.baidu_name or name
                return None
            finally:
                session.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"查询自定义映射失败: {e}")
            return None
    
    def _auto_create_mapping(self, original_name: str, obfuscated_name: str, category: str = None):
        """
        自动创建映射记录（如果不存在）
        
        Args:
            original_name: 原始名称
            obfuscated_name: 混淆后的名称
            category: 分类信息（如"剧集/国产剧集"）
        """
        if not self.db_engine:
            return
        
        try:
            from backend.models import CustomNameMapping, get_session
            session = get_session(self.db_engine)
            
            try:
                # 检查是否已存在
                existing = session.query(CustomNameMapping).filter(
                    CustomNameMapping.original_name == original_name
                ).first()
                
                if not existing:
                    # 创建新映射（三个网盘都用混淆后的名字）
                    new_mapping = CustomNameMapping(
                        original_name=original_name,
                        category=category,
                        quark_name=obfuscated_name,
                        baidu_name=obfuscated_name,
                        xunlei_name=obfuscated_name,
                        enabled=True,
                        note="自动创建"
                    )
                    session.add(new_mapping)
                    session.commit()
                    
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"✓ 自动创建映射: {original_name} -> {obfuscated_name}")
            finally:
                session.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"自动创建映射失败: {e}")
    
    def obfuscate_name(self, name: str, category: str = None) -> str:
        """
        混淆文件夹名 - 优先使用自定义映射，否则使用同音字替换
        
        Args:
            name: 原始文件夹名
            category: 分类信息（用于自动创建映射时填充）
            
        Returns:
            混淆后的名称
        """
        if not self.enabled:
            return name
        
        # 分类文件夹不混淆
        if name in self.category_folders:
            return name
        
        # Season目录不混淆（如 Season 1, Season 2）
        if re.match(r'^Season\s+\d+$', name, re.IGNORECASE):
            return name
        
        # 常见子目录不混淆（extras, bonus, specials, featurettes等）
        if name.lower() in ['extras', 'bonus', 'specials', 'featurettes', 'behind the scenes', 'deleted scenes']:
            return name
        
        # 1. 优先检查自定义映射
        custom_name = self._get_custom_mapping(name)
        if custom_name:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✓ 使用自定义映射: {name} -> {custom_name}")
            return custom_name
        
        # 2. 使用同音字混淆（去年份+同音字替换）
        obfuscated = self.homophone_obfuscator.obfuscate_with_year(name)
        
        # 3. 自动创建映射记录到数据库（方便在页面上统一管理和修改）
        self._auto_create_mapping(name, obfuscated, category)
        
        return obfuscated
    
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
        """加载拼音映射表（3500个常用字）"""
        from .pinyin_map import PINYIN_MAP
        return PINYIN_MAP
        
    def _load_pinyin_map_old(self) -> dict:
        """旧的内置映射表（备用）"""
        return {
            # 常见分类
            '国': 'guo', '产': 'chan', '剧': 'ju', '集': 'ji', '电': 'dian', '影': 'ying',
            '视': 'shi', '频': 'pin', '综': 'zong', '艺': 'yi', '动': 'dong', '画': 'hua',
            '纪': 'ji', '录': 'lu', '片': 'pian', '短': 'duan', '体': 'ti', '育': 'yu',
            
            # 地区
            '港': 'gang', '台': 'tai', '日': 'ri', '韩': 'han', '美': 'mei', '英': 'ying',
            '法': 'fa', '德': 'de', '欧': 'ou', '亚': 'ya', '洲': 'zhou', '内': 'nei',
            '陆': 'lu', '地': 'di', '区': 'qu', '本': 'ben', '土': 'tu',
            
            # 数字
            '一': 'yi', '二': 'er', '三': 'san', '四': 'si', '五': 'wu',
            '六': 'liu', '七': 'qi', '八': 'ba', '九': 'jiu', '十': 'shi',
            '百': 'bai', '千': 'qian', '万': 'wan',
            
            # 常用字
            '大': 'da', '小': 'xiao', '中': 'zhong', '新': 'xin', '老': 'lao',
            '好': 'hao', '坏': 'huai', '长': 'chang', '短': 'duan', '高': 'gao',
            '低': 'di', '上': 'shang', '下': 'xia', '前': 'qian', '后': 'hou',
            '左': 'zuo', '右': 'you', '东': 'dong', '南': 'nan', '西': 'xi',
            '北': 'bei', '里': 'li', '外': 'wai', '内': 'nei',
            
            # 常见剧名用字
            '生': 'sheng', '死': 'si', '活': 'huo', '命': 'ming', '人': 'ren',
            '女': 'nv', '男': 'nan', '子': 'zi', '儿': 'er', '童': 'tong',
            '王': 'wang', '后': 'hou', '妃': 'fei', '君': 'jun', '臣': 'chen',
            '将': 'jiang', '军': 'jun', '兵': 'bing', '士': 'shi', '侠': 'xia',
            '客': 'ke', '贼': 'zei', '盗': 'dao', '匪': 'fei',
            
            # 情感动作
            '爱': 'ai', '恨': 'hen', '情': 'qing', '欲': 'yu', '望': 'wang',
            '思': 'si', '念': 'nian', '想': 'xiang', '梦': 'meng', '幻': 'huan',
            '喜': 'xi', '怒': 'nu', '哀': 'ai', '乐': 'le', '悲': 'bei',
            '欢': 'huan', '笑': 'xiao', '哭': 'ku', '泪': 'lei',
            
            # 自然景物
            '天': 'tian', '地': 'di', '山': 'shan', '水': 'shui', '火': 'huo',
            '风': 'feng', '雨': 'yu', '雷': 'lei', '云': 'yun', '雪': 'xue',
            '日': 'ri', '月': 'yue', '星': 'xing', '辰': 'chen', '光': 'guang',
            '明': 'ming', '暗': 'an', '夜': 'ye', '晨': 'chen', '昏': 'hun',
            '海': 'hai', '江': 'jiang', '河': 'he', '湖': 'hu', '溪': 'xi',
            '树': 'shu', '林': 'lin', '森': 'sen', '花': 'hua', '草': 'cao',
            
            # 颜色
            '红': 'hong', '黄': 'huang', '蓝': 'lan', '绿': 'lv', '青': 'qing',
            '紫': 'zi', '白': 'bai', '黑': 'hei', '灰': 'hui', '金': 'jin',
            '银': 'yin', '彩': 'cai', '色': 'se',
            
            # 动物
            '龙': 'long', '凤': 'feng', '虎': 'hu', '狼': 'lang', '豹': 'bao',
            '狮': 'shi', '鹰': 'ying', '熊': 'xiong', '鸟': 'niao', '马': 'ma',
            '牛': 'niu', '羊': 'yang', '犬': 'quan', '猫': 'mao', '鼠': 'shu',
            '猪': 'zhu', '鸡': 'ji', '鸭': 'ya', '鱼': 'yu', '虫': 'chong',
            '蛇': 'she', '龟': 'gui', '鹿': 'lu', '象': 'xiang',
            
            # 武器战争
            '剑': 'jian', '刀': 'dao', '枪': 'qiang', '炮': 'pao', '弓': 'gong',
            '箭': 'jian', '盾': 'dun', '甲': 'jia', '战': 'zhan', '争': 'zheng',
            '打': 'da', '杀': 'sha', '斗': 'dou', '伤': 'shang',
            
            # 方位时间
            '春': 'chun', '夏': 'xia', '秋': 'qiu', '冬': 'dong', '年': 'nian',
            '月': 'yue', '日': 'ri', '时': 'shi', '分': 'fen', '秒': 'miao',
            '今': 'jin', '昨': 'zuo', '明': 'ming', '早': 'zao', '晚': 'wan',
            '午': 'wu', '夕': 'xi', '朝': 'zhao', '暮': 'mu',
            
            # 特殊字
            '的': 'de', '了': 'le', '在': 'zai', '是': 'shi', '我': 'wo',
            '你': 'ni', '他': 'ta', '她': 'ta', '它': 'ta', '们': 'men',
            '这': 'zhe', '那': 'na', '什': 'shen', '么': 'me', '吗': 'ma',
            '呢': 'ne', '啊': 'a', '哦': 'o', '嗯': 'en', '吧': 'ba',
            
            # 其他常用
            '家': 'jia', '国': 'guo', '城': 'cheng', '市': 'shi', '村': 'cun',
            '镇': 'zhen', '县': 'xian', '省': 'sheng', '州': 'zhou', '都': 'du',
            '京': 'jing', '沪': 'hu', '港': 'gang', '澳': 'ao', '台': 'tai',
            '学': 'xue', '校': 'xiao', '院': 'yuan', '堂': 'tang', '馆': 'guan',
            '店': 'dian', '厂': 'chang', '场': 'chang', '园': 'yuan', '宫': 'gong',
            '府': 'fu', '室': 'shi', '厅': 'ting', '楼': 'lou', '塔': 'ta',
            '门': 'men', '窗': 'chuang', '墙': 'qiang', '路': 'lu', '街': 'jie',
            '道': 'dao', '桥': 'qiao', '河': 'he', '江': 'jiang',
            '书': 'shu', '文': 'wen', '字': 'zi', '言': 'yan', '语': 'yu',
            '话': 'hua', '说': 'shuo', '讲': 'jiang', '读': 'du', '写': 'xie',
            '手': 'shou', '足': 'zu', '头': 'tou', '目': 'mu', '耳': 'er',
            '口': 'kou', '鼻': 'bi', '身': 'shen', '心': 'xin', '脑': 'nao',
            '血': 'xue', '肉': 'rou', '骨': 'gu', '皮': 'pi', '毛': 'mao',
            
            # 热门剧名
            '双': 'shuang', '轨': 'gui', '意': 'yi', '狙': 'ju', '击': 'ji',
            '蝴': 'hu', '蝶': 'die', '超': 'chao', '感': 'gan', '迷': 'mi',
            '闻': 'wen', '计': 'ji', '潮': 'chao', '与': 'yu', '安': 'an',
            '猎': 'lie', '冰': 'bing', '罪': 'zui', '庆': 'qing', '余': 'yu',
            '琅': 'lang', '琊': 'ya', '榜': 'bang', '延': 'yan', '禧': 'xi',
            '攻': 'gong', '略': 'lve', '传': 'chuan', '奇': 'qi', '志': 'zhi',
            '怪': 'guai', '谈': 'tan', '诡': 'gui', '秘': 'mi', '密': 'mi',
            '案': 'an', '破': 'po', '局': 'ju', '重': 'chong', '启': 'qi',
            '复': 'fu', '仇': 'chou', '者': 'zhe', '联': 'lian', '盟': 'meng',
            '终': 'zhong', '极': 'ji', '无': 'wu', '限': 'xian', '使': 'shi',
        }
    
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
        混淆文件夹路径（只混淆第3层剧名目录）
        
        路径结构：
        - 第1层：剧集/电影/动漫 → 不混淆
        - 第2层：国产剧集/欧美电影 → 不混淆
        - 第3层：剧名 → 混淆
        - 第4层+：Season/extras/中文等 → 不混淆
        
        Args:
            relative_parts: 相对路径的各部分（不含文件名）
            
        Returns:
            混淆后的路径各部分
        """
        if not self.enabled or not relative_parts:
            return relative_parts
        
        new_parts = []
        category = None
        
        # 提取分类信息（第1层/第2层）
        if len(relative_parts) >= 2:
            category = f"{relative_parts[0]}/{relative_parts[1]}"
        
        for i, dir_name in enumerate(relative_parts):
            # 只混淆第3层（索引2）的剧名目录
            if i == 2:
                obfuscated = self.obfuscate_name(dir_name, category=category)
                new_parts.append(obfuscated)
            else:
                # 其他层全部保持原样
                new_parts.append(dir_name)
        
        return new_parts
    
    def check_legacy_path(self, source_path: Path, target_base: Path, relative_parts: list) -> tuple:
        """
        使用新的同音字混淆规则创建目录路径（只混淆第3层剧名）
        
        Args:
            source_path: 源文件路径
            target_base: 目标基础路径
            relative_parts: 相对路径的各部分（不含文件名）
            
        Returns:
            (混淆后的目录路径, 是否使用旧混淆)
        """
        if not self.enabled or not relative_parts:
            return target_base / Path(*relative_parts), False
        
        # 使用obfuscate_folder_path统一处理
        new_parts = self.obfuscate_folder_path(relative_parts)
        
        new_full_path = target_base / Path(*new_parts)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✓ 同音字混淆: {'/'.join(new_parts)}")
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
