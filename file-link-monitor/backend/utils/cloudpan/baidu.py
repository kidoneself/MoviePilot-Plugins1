"""
百度网盘自动化实现
"""
import asyncio
import logging
from typing import Optional
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base import CloudPanBase

logger = logging.getLogger(__name__)


class BaiduPan(CloudPanBase):
    """百度网盘自动化"""
    
    @property
    def name(self) -> str:
        return "baidu"
    
    @property
    def login_url(self) -> str:
        return "https://pan.baidu.com/disk/main#/index?category=all"
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            await self.page.wait_for_selector('.nd-main-layout', timeout=5000)
            return True
        except PlaywrightTimeoutError:
            return False
    
    async def login(self, wait_for_scan: bool = True) -> bool:
        """
        登录百度网盘（扫码登录）
        
        Args:
            wait_for_scan: 是否等待用户扫码完成
            
        Returns:
            是否登录成功
        """
        try:
            # 访问百度网盘
            logger.info(f"⏳ 访问{self.name}网盘...")
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # 检查是否已登录
            if await self.is_logged_in():
                logger.info("✅ 已登录百度网盘")
                await self._save_cookies()
                return True
            
            # 未登录，等待扫码
            logger.info("⏳ 请使用百度APP扫码登录...")
            
            if wait_for_scan:
                # 等待登录完成（最多5分钟）
                try:
                    await self.page.wait_for_selector('.nd-main-layout', timeout=300000)
                    logger.info("✅ 百度网盘登录成功！")
                    await self._save_cookies()
                    await asyncio.sleep(2)
                    return True
                except PlaywrightTimeoutError:
                    logger.error("❌ 百度网盘登录超时")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"百度网盘登录失败: {e}")
            return False
    
    async def navigate_to_folder(self, folder_path: str) -> bool:
        """
        导航到指定文件夹
        
        Args:
            folder_path: 文件夹路径（如：/剧集/国产剧集/老舅）
            
        Returns:
            是否成功
        """
        try:
            # 百度网盘的文件夹路径处理
            # 方式1: 通过搜索找到文件夹
            # 方式2: 通过URL直接访问
            
            # 这里使用搜索方式
            parts = [p for p in folder_path.split('/') if p]
            if not parts:
                return False
            
            # 使用最后一个部分（文件夹名）进行搜索
            folder_name = parts[-1]
            
            # 点击搜索框
            await self.page.click('.wp-s-header__search input', timeout=5000)
            await asyncio.sleep(0.5)
            
            # 输入文件夹名
            await self.page.fill('.wp-s-header__search input', folder_name)
            await asyncio.sleep(0.5)
            
            # 回车搜索
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"导航到文件夹失败 {folder_path}: {e}")
            return False
    
    async def create_share_link(self, folder_name: str, expire_days: int = 0) -> Optional[str]:
        """
        创建分享链接
        
        Args:
            folder_name: 文件夹名称
            expire_days: 有效期天数（0为永久，7为7天）
            
        Returns:
            分享链接，失败返回None
        """
        try:
            # 1. 搜索文件夹
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # 点击搜索框
            await self.page.click('.wp-s-header__search input')
            await asyncio.sleep(0.5)
            
            # 输入文件夹名并搜索
            await self.page.fill('.wp-s-header__search input', folder_name)
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            # 2. 找到文件夹并右键点击
            # 这里需要找到搜索结果中的文件夹
            try:
                # 等待搜索结果
                await self.page.wait_for_selector('.list-view__body', timeout=10000)
                
                # 找到第一个文件夹结果（假设是我们要的）
                folder_item = await self.page.query_selector('.list-view__body .list-view__item')
                if not folder_item:
                    logger.warning(f"未找到文件夹: {folder_name}")
                    return None
                
                # 勾选该文件夹
                checkbox = await folder_item.query_selector('input[type="checkbox"]')
                if checkbox:
                    await checkbox.click()
                    await asyncio.sleep(0.5)
                
                # 点击顶部的"分享"按钮
                await self.page.click('text=分享', timeout=5000)
                await asyncio.sleep(2)
                
                # 3. 设置分享选项
                # 选择有效期
                if expire_days == 0:
                    # 选择永久有效
                    try:
                        await self.page.click('text=永久有效', timeout=3000)
                    except:
                        pass
                elif expire_days == 7:
                    try:
                        await self.page.click('text=7天', timeout=3000)
                    except:
                        pass
                
                await asyncio.sleep(1)
                
                # 4. 创建链接
                await self.page.click('button:has-text("创建链接")', timeout=5000)
                await asyncio.sleep(2)
                
                # 5. 获取分享链接
                # 等待链接生成
                link_input = await self.page.wait_for_selector('input[readonly][value^="https://pan.baidu.com/s/"]', timeout=10000)
                share_link = await link_input.get_attribute('value')
                
                # 关闭分享弹窗
                try:
                    await self.page.click('.dialog-footer button:has-text("知道了")', timeout=2000)
                except:
                    try:
                        await self.page.keyboard.press('Escape')
                    except:
                        pass
                
                await asyncio.sleep(1)
                
                return share_link
                
            except Exception as e:
                logger.error(f"创建分享链接过程出错: {e}")
                return None
                
        except Exception as e:
            logger.error(f"创建{folder_name}的分享链接失败: {e}")
            return None
