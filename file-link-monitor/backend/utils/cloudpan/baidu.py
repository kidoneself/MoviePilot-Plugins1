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
    
    async def _close_popups(self):
        """关闭百度网盘的各种弹窗"""
        try:
            # 使用实际的弹窗关闭按钮选择器
            close_selectors = [
                # 主弹窗关闭按钮（下载客户端弹窗）
                '.pc-client-modal-close',
                # 用户提示气泡
                '.u-tooltip-inner i',
                # 侧边栏气泡提示
                '.wp-s-aside-nav-bubble-close',
                # 其他通用关闭按钮
                '[class*="close"]',
                'button:has-text("关闭")',
            ]
            
            for selector in close_selectors:
                try:
                    await self.page.click(selector, timeout=1000)
                    await asyncio.sleep(0.3)
                    logger.debug(f"已关闭弹窗: {selector}")
                except:
                    pass
            
            # 按ESC键关闭其他可能的弹窗
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.3)
            except:
                pass
                
            logger.info("✅ 已尝试关闭所有弹窗")
            
        except Exception as e:
            logger.warning(f"关闭弹窗时出错（可忽略）: {e}")
    
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
                
                # 关闭可能出现的弹窗
                await self._close_popups()
                
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
            # 使用直接搜索URL
            from urllib.parse import quote
            search_url = f"https://pan.baidu.com/disk/main?from=homeFlow#/index?category=all&search={quote(folder_name)}"
            logger.info(f"🔍 直接访问搜索页面: {folder_name}")
            
            await self.page.goto(search_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # 关闭可能出现的弹窗
            await self._close_popups()
            
            # 2. 找到文件夹并勾选
            try:
                # 等待文件列表加载
                await self.page.wait_for_selector('.wp-s-pan-table__body tbody tr', timeout=10000)
                
                # 找到第一个文件行
                first_row = await self.page.query_selector('.wp-s-pan-table__body tbody tr')
                if not first_row:
                    logger.warning(f"未找到文件夹: {folder_name}")
                    return None
                
                # 先hover到文件行，让复选框显示出来
                await first_row.hover()
                await asyncio.sleep(0.5)
                
                # 勾选该文件夹（点击checkbox所在的td）
                checkbox_td = await first_row.query_selector('td.wp-s-pan-table__body-row--checkbox-block')
                if checkbox_td:
                    await checkbox_td.click()
                    await asyncio.sleep(1)
                    logger.info(f"✅ 已选中文件: {folder_name}")
                else:
                    logger.error("未找到复选框")
                    return None
                
                # 点击顶部的"分享"按钮
                share_btn = '.wp-s-agile-tool-bar__h-group button'
                await self.page.click(share_btn, timeout=5000)
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
                
                # 4. 创建链接并复制
                # 点击"复制链接"按钮（会自动创建链接并复制到剪贴板）
                copy_link_btn = '.wp-share-file__link-create-btn button'
                await self.page.click(copy_link_btn, timeout=5000)
                await asyncio.sleep(2)
                
                # 5. 从剪贴板获取分享链接
                # 先授予剪贴板权限
                try:
                    context = self.page.context
                    await context.grant_permissions(['clipboard-read'])
                except Exception as e:
                    logger.warning(f"授予剪贴板权限时出错: {e}")
                
                # 使用Playwright的evaluate方法读取剪贴板
                try:
                    clipboard_text = await self.page.evaluate('navigator.clipboard.readText()')
                    logger.info(f"📋 从剪贴板获取到文本: {clipboard_text[:100]}...")
                    
                    # 从剪贴板文本中提取链接和提取码
                    import re
                    
                    # 提取链接（不带pwd参数的基础链接）
                    link_match = re.search(r'https://pan\.baidu\.com/s/[\w\-]+', clipboard_text)
                    # 提取提取码
                    pwd_match = re.search(r'(?:提取码[：:]\s*|pwd=)([\w]+)', clipboard_text)
                    
                    if link_match:
                        base_link = link_match.group(0)
                        
                        if pwd_match:
                            pwd = pwd_match.group(1)
                            # 格式化成: https://pan.baidu.com/s/xxxxx?pwd=xxxx 提取码: xxxx
                            share_link = f"{base_link}?pwd={pwd} 提取码: {pwd}"
                            logger.info(f"✅ 成功提取分享链接和提取码: {share_link}")
                        else:
                            share_link = base_link
                            logger.info(f"✅ 成功提取分享链接（无提取码）: {share_link}")
                    else:
                        logger.error(f"未能从剪贴板文本中提取到链接")
                        return None
                        
                except Exception as e:
                    logger.error(f"读取剪贴板失败: {e}")
                    return None
                
                # 关闭分享弹窗
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
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
