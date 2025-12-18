"""
夸克网盘自动化实现
"""
import asyncio
import logging
from typing import Optional
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base import CloudPanBase

logger = logging.getLogger(__name__)


class QuarkPan(CloudPanBase):
    """夸克网盘自动化"""
    
    @property
    def name(self) -> str:
        return "quark"
    
    @property
    def login_url(self) -> str:
        return "https://pan.quark.cn/"
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            # 检查搜索框是否存在（登录后才有）
            await self.page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
            return True
        except PlaywrightTimeoutError:
            return False
    
    async def login(self, wait_for_scan: bool = True) -> bool:
        """
        登录夸克网盘（扫码登录）
        
        Args:
            wait_for_scan: 是否等待用户扫码完成
            
        Returns:
            是否登录成功
        """
        try:
            logger.info(f"⏳ 访问{self.name}网盘...")
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # 检查是否已登录
            if await self.is_logged_in():
                logger.info("✅ 已登录夸克网盘")
                await self._save_cookies()
                return True
            
            # 未登录，等待扫码
            logger.info("⏳ 请使用夸克APP扫码登录...")
            
            if wait_for_scan:
                try:
                    await self.page.wait_for_selector('input[placeholder*="搜索"]', timeout=600000)
                    logger.info("✅ 夸克网盘登录成功！")
                    await self._save_cookies()
                    await asyncio.sleep(2)
                    return True
                except PlaywrightTimeoutError:
                    logger.error("❌ 夸克网盘登录超时")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"夸克网盘登录失败: {e}")
            return False
    
    async def navigate_to_folder(self, folder_path: str) -> bool:
        """
        导航到指定文件夹
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            是否成功
        """
        # TODO: 根据夸克网盘的实际操作实现
        logger.warning("夸克网盘导航功能待实现")
        return False
    
    async def create_share_link(self, folder_name: str, expire_days: int = 0) -> Optional[str]:
        """
        创建分享链接
        
        Args:
            folder_name: 文件夹名称
            expire_days: 有效期天数（夸克统一使用永久有效）
            
        Returns:
            分享链接，失败返回None
        """
        try:
            logger.info(f"⏳ 开始为 {folder_name} 创建夸克网盘分享链接...")
            
            # 使用直接搜索URL
            from urllib.parse import quote
            search_url = f"https://pan.quark.cn/list#/list/search?key={quote(folder_name)}"
            logger.info(f"🔍 直接访问搜索页面: {folder_name}")
            
            await self.page.goto(search_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # 2. 检查是否有搜索结果，并检查是否失效
            logger.info("📋 检查搜索结果...")
            file_row = '#ice-container > section > section > main > div > div.section-main > div.file-list > div.ant-table-wrapper.table-fixed-content > div > div > div > div > div > div.ant-table-body > div > table > tbody > tr:first-child'
            
            try:
                await self.page.wait_for_selector(file_row, timeout=5000)
            except PlaywrightTimeoutError:
                logger.error(f"❌ 未找到文件: {folder_name}")
                return None
            
            # 检查文件名是否包含"失效"
            file_name_element = await self.page.query_selector(f'{file_row} td:nth-child(2)')
            if file_name_element:
                file_text = await file_name_element.inner_text()
                if '失效' in file_text:
                    logger.warning(f"⚠️ 文件已失效，跳过: {folder_name}")
                    return None
            
            # 3. 点击复选框选中文件
            logger.info("✓ 选中文件...")
            checkbox = f'{file_row} td.ant-table-selection-column > span > label > span > input'
            await self.page.click(checkbox)
            await asyncio.sleep(1)
            
            # 4. 点击分享按钮
            logger.info("📤 点击分享按钮...")
            share_btn = '#ice-container > section > section > main > div > div.section-main > div.section-header.list-header > div.btn-operate > div.btn-group > div > button:nth-child(2)'
            await self.page.click(share_btn)
            await asyncio.sleep(2)
            
            # 5. 选择永久有效（可能已经默认选中，保险起见点击一下）
            logger.info("⏰ 设置永久有效...")
            try:
                permanent_radio = 'label.ant-radio-button-wrapper:has-text("永久有效")'
                await self.page.click(permanent_radio, timeout=2000)
                await asyncio.sleep(0.5)
            except:
                logger.info("永久有效可能已默认选中")
            
            # 6. 点击创建分享按钮
            logger.info("🔗 创建分享链接...")
            create_btn = 'div.ant-modal-footer button:has-text("创建分享")'
            await self.page.click(create_btn)
            await asyncio.sleep(2)
            
            # 7. 授予剪贴板权限
            await self.page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
            
            # 8. 点击复制链接按钮
            logger.info("📋 复制链接...")
            copy_btn = 'div.result-info button:has-text("复制链接")'
            await self.page.click(copy_btn)
            await asyncio.sleep(1)
            
            # 9. 从剪贴板读取链接
            clipboard_text = await self.page.evaluate('navigator.clipboard.readText()')
            logger.info(f"📋 剪贴板内容: {clipboard_text}")
            
            # 10. 提取链接（可能包含其他文本）
            import re
            link_match = re.search(r'https://pan\.quark\.cn/s/[a-zA-Z0-9]+', clipboard_text)
            if link_match:
                share_link = link_match.group(0)
                logger.info(f"✅ 成功创建分享链接: {share_link}")
                
                # 关闭分享成功的弹窗
                try:
                    close_btn = 'div.ant-modal-wrap button.ant-modal-close'
                    await self.page.click(close_btn, timeout=2000)
                except:
                    pass
                
                return share_link
            else:
                logger.error(f"❌ 无法从剪贴板提取链接: {clipboard_text}")
                return None
                
        except Exception as e:
            logger.error(f"创建夸克网盘分享链接失败: {e}")
            import traceback
            traceback.print_exc()
            return None
