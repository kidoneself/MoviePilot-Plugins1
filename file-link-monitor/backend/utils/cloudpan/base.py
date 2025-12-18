"""
网盘自动化基类
定义通用接口，各个网盘继承实现
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class CloudPanBase(ABC):
    """网盘自动化基类"""
    
    def __init__(self, headless: bool = False, cookies_dir: str = "./data/cookies"):
        """
        初始化
        
        Args:
            headless: 是否无头模式（False可以看到浏览器操作）
            cookies_dir: Cookie保存目录
        """
        self.headless = headless
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    @property
    @abstractmethod
    def name(self) -> str:
        """网盘名称"""
        pass
    
    @property
    @abstractmethod
    def login_url(self) -> str:
        """登录页面URL"""
        pass
    
    @property
    def cookies_file(self) -> Path:
        """Cookie文件路径"""
        return self.cookies_dir / f"{self.name}_cookies.json"
    
    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        
        # 创建上下文，模拟真实浏览器
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 加载已保存的cookies
        if self.cookies_file.exists():
            try:
                import json
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info(f"✅ 已加载{self.name}的Cookies")
            except Exception as e:
                logger.warning(f"加载{self.name} Cookies失败: {e}")
        
        self.page = await context.new_page()
        
        # 隐藏自动化特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def _save_cookies(self):
        """保存Cookies"""
        try:
            import json
            cookies = await self.page.context.cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 已保存{self.name} Cookies")
        except Exception as e:
            logger.error(f"保存{self.name} Cookies失败: {e}")
    
    @abstractmethod
    async def login(self, wait_for_scan: bool = True) -> bool:
        """
        登录网盘
        
        Args:
            wait_for_scan: 是否等待用户扫码完成
            
        Returns:
            是否登录成功
        """
        pass
    
    @abstractmethod
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        pass
    
    @abstractmethod
    async def navigate_to_folder(self, folder_path: str) -> bool:
        """
        导航到指定文件夹
        
        Args:
            folder_path: 文件夹路径（如：/剧集/国产剧集/老舅）
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def create_share_link(self, folder_name: str, expire_days: int = 0) -> Optional[str]:
        """
        创建分享链接
        
        Args:
            folder_name: 文件夹名称
            expire_days: 有效期天数（0为永久）
            
        Returns:
            分享链接，失败返回None
        """
        pass
    
    async def batch_create_share_links(self, folders: List[str], expire_days: int = 0) -> Dict[str, Optional[str]]:
        """
        批量创建分享链接
        
        Args:
            folders: 文件夹路径列表
            expire_days: 有效期天数
            
        Returns:
            {文件夹路径: 分享链接}
        """
        results = {}
        
        for folder in folders:
            try:
                logger.info(f"⏳ 处理: {folder}")
                link = await self.create_share_link(folder, expire_days)
                results[folder] = link
                
                if link:
                    logger.info(f"✅ 成功: {folder} -> {link}")
                else:
                    logger.warning(f"⚠️ 失败: {folder}")
                    
                # 避免频率限制
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ 错误: {folder} - {e}")
                results[folder] = None
                
        return results
