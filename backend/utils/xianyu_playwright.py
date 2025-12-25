"""
闲鱼卡密管理自动化服务（Playwright版本）
使用 Playwright 替代 Selenium，解决Docker兼容性问题
全局浏览器实例，保持登录会话
"""
import logging
import time
import os
from pathlib import Path
from typing import Optional, Callable
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
import threading

logger = logging.getLogger(__name__)

# 是否使用无头模式，默认根据环境变量判断
HEADLESS_MODE = os.getenv('XIANYU_HEADLESS', 'true').lower() == 'true'

# 全局浏览器实例管理
_global_playwright = None
_global_browser: Optional[Browser] = None
_global_context: Optional[BrowserContext] = None
_global_headless: bool = True
_browser_lock = threading.Lock()


def get_global_browser(headless: bool = True) -> tuple[Browser, BrowserContext]:
    """获取全局浏览器实例（单例模式，保持会话）"""
    global _global_playwright, _global_browser, _global_context, _global_headless
    
    with _browser_lock:
        # 如果模式改变，关闭旧实例
        if _global_browser and _global_headless != headless:
            logger.info("浏览器模式改变，重启浏览器")
            close_global_browser()
        
        # 如果已存在，直接返回
        if _global_browser and _global_context:
            logger.info("✅ 复用全局Playwright浏览器实例")
            return _global_browser, _global_context
        
        # 创建新的浏览器实例
        mode = "无头" if headless else "有头"
        logger.info(f"🌐 启动全局Playwright浏览器（{mode}模式）...")
        
        _global_playwright = sync_playwright().start()
        _global_browser = _global_playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        _global_context = _global_browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        _global_headless = headless
        logger.info(f"✅ 全局Playwright浏览器启动成功（{mode}模式）")
        
        return _global_browser, _global_context


def close_global_browser():
    """关闭全局浏览器实例"""
    global _global_playwright, _global_browser, _global_context
    
    with _browser_lock:
        if _global_context:
            logger.info("关闭全局浏览器上下文")
            try:
                _global_context.close()
            except:
                pass
            _global_context = None
        
        if _global_browser:
            logger.info("关闭全局浏览器实例")
            try:
                _global_browser.close()
            except:
                pass
            _global_browser = None
        
        if _global_playwright:
            try:
                _global_playwright.stop()
            except:
                pass
            _global_playwright = None


class KamiAutomation:
    """卡密管理自动化（Playwright版本）"""
    
    def __init__(self, phone: Optional[str] = None, headless: bool = True):
        """
        初始化
        
        Args:
            phone: 手机号（用于登录）
            headless: 是否无头模式
        """
        self.phone = phone
        self.headless = headless
        self.step_callback: Optional[Callable] = None
        
        # 使用全局browser和context，不要在这里创建
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def set_step_callback(self, callback: Callable[[str, str], None]):
        """设置步骤回调函数"""
        self.step_callback = callback
    
    def _send_step(self, step: str, status: str = "loading"):
        """发送步骤消息"""
        if self.step_callback:
            self.step_callback(step, status)
        logger.info(f"[{status.upper()}] {step}")
    
    def _get_page(self) -> Page:
        """获取浏览器页面实例（使用全局单例）"""
        if self.page is None:
            self.browser, self.context = get_global_browser(self.headless)
            self.page = self.context.new_page()
        return self.page
    
    def _login(self) -> bool:
        """自动登录（和 Selenium 版本逻辑一致）"""
        try:
            page = self._get_page()
            self._send_step("检测是否需要登录...", "loading")
            time.sleep(3)
            
            # 检查是否在登录页面
            if 'login' not in page.url:
                self._send_step("已登录", "success")
                return True
            
            self._send_step("获取登录二维码...", "loading")
            
            # 获取二维码
            try:
                qr_img = page.wait_for_selector("//div[contains(@class,'bind-code-scan')]//img", timeout=10000)
                qr_base64 = qr_img.get_attribute('src')
                
                if self.step_callback:
                    self.step_callback(f"QRCODE:{qr_base64}", "qrcode")
                
                logger.info("二维码已获取，等待扫码...")
                self._send_step("请扫码登录（120秒）", "loading")
                
            except Exception as e:
                logger.error(f"获取二维码失败: {e}")
                self._send_step(f"获取二维码失败: {e}", "error")
                return False
            
            # 等待登录成功
            for i in range(120):
                time.sleep(1)
                if 'login' not in page.url:
                    self._send_step("✓ 登录成功！", "success")
                    logger.info("登录成功")
                    return True
                
                if i > 0 and i % 15 == 0:
                    self._send_step(f"等待扫码中... 已等待{i}秒", "loading")
            
            self._send_step("登录超时（120秒）", "error")
            return False
            
        except Exception as e:
            self._send_step(f"登录过程出错: {e}", "error")
            logger.error(f"登录过程出错: {e}")
            return False
    
    def create_kami_kind(self, kind_name: str, category_id: Optional[int] = None) -> bool:
        """
        创建卡密类型（和 Selenium 版本逻辑完全一致）
        
        Args:
            kind_name: 卡种名称
            category_id: 分类ID（可选）
            
        Returns:
            bool: 是否成功
        """
        try:
            page = self._get_page()
            self._send_step(f"开始创建卡种: {kind_name}", "loading")
            
            # 访问卡密类型添加页面（和 Selenium 版本一样）
            add_url = "https://www.goofish.pro/kam/kind/add"
            page.goto(add_url, timeout=30000)
            self._send_step("访问卡密类型添加页面", "loading")
            
            time.sleep(2)
            
            # 检查是否需要登录
            if 'login' in page.url:
                self._send_step("需要登录，等待扫码...", "loading")
                if not self._login():
                    self._send_step("登录失败", "error")
                    return False
                # 重新访问添加页面
                page.goto(add_url, timeout=30000)
            
            time.sleep(2)
            
            # 1. 选择卡种分类
            try:
                self._send_step("选择卡种分类", "loading")
                category_select = page.locator("//label[contains(text(),'卡种分类')]/..//input[@placeholder='请选择']").first
                category_select.click()
                time.sleep(0.5)
                
                category_option = page.locator("//div[contains(@class,'el-select-dropdown')]//li[contains(.,'影视')]").first
                category_option.click()
                self._send_step("已选择卡种分类: 影视", "success")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"卡种分类选择失败: {e}")
            
            # 2. 填写卡种名称
            self._send_step(f"填写卡种名称: {kind_name}", "loading")
            name_input = page.locator("//label[contains(text(),'卡种名称')]/..//input").first
            name_input.fill("")  # 先清空
            name_input.fill(kind_name)
            
            # 3. 填写卡号前缀
            try:
                card_prefix = page.locator("//label[contains(text(),'卡号前缀')]/..//input").first
                card_prefix.fill("  ")
            except:
                pass
            
            # 4. 填写密码前缀
            try:
                pwd_prefix = page.locator("//label[contains(text(),'密码前缀')]/..//input").first
                pwd_prefix.fill("  ")
            except:
                pass
            
            # 5. 填写库存预警
            try:
                stock_input = page.locator("//label[contains(text(),'库存预警')]/..//input").first
                stock_input.fill("1")
            except:
                pass
            
            time.sleep(1)
            
            # 6. 点击创建按钮
            create_button = page.locator("//button[contains(.,'创建')]").first
            create_button.click()
            self._send_step("提交创建请求", "loading")
            
            time.sleep(2)
            
            # 检查是否成功
            current_url = page.url
            if '/list' in current_url or '/add' not in current_url:
                self._send_step(f"卡种创建成功: {kind_name}", "success")
                return True
            else:
                self._send_step("卡种创建失败", "error")
                return False
            
        except Exception as e:
            self._send_step(f"创建异常: {e}", "error")
            logger.error(f"创建卡密类型失败: {e}", exc_info=True)
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.page:
            try:
                self.page.close()
            except:
                pass
            self.page = None
        # 不关闭browser和context，保留给全局复用


# 便捷函数
def create_kami_kind_simple(kind_name: str, category_id: Optional[int] = None, 
                            headless: bool = True) -> bool:
    """
    简单的卡种创建函数
    
    Args:
        kind_name: 卡种名称
        category_id: 分类ID（可选）
        headless: 是否无头模式
        
    Returns:
        bool: 是否成功
    """
    automation = KamiAutomation(headless=headless)
    try:
        return automation.create_kami_kind(kind_name, category_id)
    finally:
        automation.close()


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    result = create_kami_kind_simple("测试卡种", headless=False)
    print(f"创建结果: {'成功' if result else '失败'}")
    close_global_browser()

