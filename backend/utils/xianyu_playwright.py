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
        
        # 反检测参数配置
        launch_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',  # 关键：隐藏自动化特征
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
        ]
        
        _global_browser = _global_playwright.chromium.launch(
            headless=headless,
            args=launch_args,
            chromium_sandbox=False
        )
        
        # 创建上下文，模拟真实浏览器
        _global_context = _global_browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            # 模拟真实浏览器的权限
            permissions=['geolocation', 'notifications'],
            # 设置额外的HTTP头
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        )
        
        # 注入反检测脚本到每个新页面
        _global_context.add_init_script("""
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 覆盖 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 覆盖 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 覆盖 chrome 对象
            window.chrome = {
                runtime: {}
            };
            
            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
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
            current_url = page.url
            logger.info(f"当前页面 URL: {current_url}")
            
            if 'login' not in current_url:
                self._send_step("已登录", "success")
                return True
            
            # 打印页面标题和内容，帮助调试
            logger.info(f"页面标题: {page.title()}")
            
            # 等待页面完全加载
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
                logger.info("页面加载完成（networkidle）")
            except:
                logger.info("等待networkidle超时，继续...")
            
            # 打印页面部分HTML，帮助调试
            try:
                body_html = page.content()
                # 只打印前2000字符
                logger.info(f"页面HTML片段: {body_html[:2000]}")
                # 查找所有img标签
                imgs = page.locator('img').all()
                logger.info(f"页面中找到 {len(imgs)} 个img标签")
                for idx, img in enumerate(imgs[:5]):  # 只看前5个
                    try:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt')
                        class_name = img.get_attribute('class')
                        logger.info(f"  img[{idx}]: src={src[:50] if src else 'None'}, alt={alt}, class={class_name}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"打印HTML失败: {e}")
            
            # 查找并点击可能触发二维码显示的按钮
            logger.info("尝试触发二维码显示...")
            try:
                # 尝试多种可能的触发按钮
                trigger_selectors = [
                    "text=微信登录",
                    "text=扫码登录",
                    "text=二维码登录",
                    ".wechat-login",
                    "#wechat-login-btn",
                    "button:has-text('微信')",
                    "div:has-text('微信登录')"
                ]
                
                clicked = False
                for selector in trigger_selectors:
                    try:
                        logger.info(f"尝试点击触发按钮: {selector}")
                        btn = page.locator(selector).first
                        if btn.count() > 0:
                            btn.click()
                            logger.info(f"✅ 点击了触发按钮: {selector}")
                            time.sleep(3)  # 等待二维码加载
                            clicked = True
                            break
                    except Exception as e:
                        logger.info(f"触发按钮不存在: {selector}")
                        continue
                
                if not clicked:
                    logger.info("未找到触发按钮，二维码可能已在页面上")
                else:
                    # 点击后重新检查img标签
                    imgs = page.locator('img').all()
                    logger.info(f"点击后页面中找到 {len(imgs)} 个img标签")
                    for idx, img in enumerate(imgs[:10]):
                        try:
                            src = img.get_attribute('src')
                            alt = img.get_attribute('alt')
                            id_attr = img.get_attribute('id')
                            logger.info(f"  img[{idx}]: src={src[:80] if src else 'None'}, alt={alt}, id={id_attr}")
                        except:
                            pass
                    
            except Exception as e:
                logger.info(f"触发二维码显示失败: {e}")
            
            self._send_step("获取登录二维码...", "loading")
            
            # 尝试多种二维码选择器
            qr_selectors = [
                "#wechat-bind-code > img",  # 最新的正确选择器
                "#wechat-bind-code img",    # 不带 > 的版本
                "//div[contains(@class,'bind-code-scan')]//img",
                "//div[contains(@class,'qrcode')]//img",
                "//div[@id='wechat-bind-code']//img",  # xpath版本
                "img[alt*='二维码']",
                "img[alt*='扫码']",
                ".qrcode-img",
                "#J_QRCodeImg"
            ]
            
            qr_img = None
            for selector in qr_selectors:
                try:
                    logger.info(f"尝试选择器: {selector}")
                    # 第一个选择器多等待一会儿
                    timeout = 10000 if selector == "#wechat-bind-code > img" else 3000
                    qr_img = page.wait_for_selector(selector, timeout=timeout)
                    if qr_img:
                        logger.info(f"✅ 找到二维码，使用选择器: {selector}")
                        break
                except Exception as e:
                    logger.info(f"选择器失败: {selector}")
                    continue
            
            if not qr_img:
                # 截图保存，方便调试
                try:
                    screenshot_path = '/tmp/login_page_screenshot.png'
                    page.screenshot(path=screenshot_path)
                    logger.error(f"未找到二维码元素，已保存截图到: {screenshot_path}")
                except:
                    pass
                
                logger.error("所有二维码选择器都失败了")
                self._send_step("未找到二维码，请检查页面", "error")
                return False
            
            try:
                qr_base64 = qr_img.get_attribute('src')
                
                if self.step_callback:
                    self.step_callback(f"QRCODE:{qr_base64}", "qrcode")
                
                logger.info("二维码已获取，等待扫码...")
                self._send_step("请扫码登录（120秒）", "loading")
                
            except Exception as e:
                logger.error(f"获取二维码src失败: {e}")
                self._send_step(f"获取二维码失败: {e}", "error")
                return False
            
            # 等待登录成功
            for i in range(120):
                time.sleep(1)
                current_url = page.url
                
                # 多种方式判断登录成功
                login_success = False
                
                # 方式1: URL跳转（离开登录页或到达首页）
                if 'login' not in current_url:
                    login_success = True
                    logger.info(f"检测到URL跳转: {current_url}")
                
                # 检查是否跳转到了首页
                if '/sale/statistics' in current_url or '/home' in current_url:
                    login_success = True
                    logger.info(f"检测到跳转到首页: {current_url}")
                
                # 方式2: 检查是否出现"我的工作台"等元素
                if not login_success:
                    try:
                        # 检查是否有登录后的元素
                        logged_in_elements = [
                            "text=我的工作台",
                            "text=退出登录",
                            "text=个人中心",
                            ".user-info",
                            "#user-menu"
                        ]
                        for selector in logged_in_elements:
                            if page.locator(selector).count() > 0:
                                login_success = True
                                logger.info(f"检测到登录元素: {selector}")
                                break
                    except:
                        pass
                
                # 方式3: 检查cookie是否有登录凭证
                if not login_success and i > 5:  # 5秒后开始检查cookie
                    try:
                        cookies = self.context.cookies()
                        for cookie in cookies:
                            if cookie.get('name') in ['token', 'sid', 'session', 'auth', '_tb_token_']:
                                if cookie.get('value'):
                                    login_success = True
                                    logger.info(f"检测到登录Cookie: {cookie.get('name')}")
                                    break
                    except:
                        pass
                
                if login_success:
                    self._send_step("✓ 登录成功！", "success")
                    logger.info(f"登录成功，当前URL: {current_url}")
                    time.sleep(2)  # 等待页面稳定
                    return True
                
                if i > 0 and i % 15 == 0:
                    self._send_step(f"等待扫码中... 已等待{i}秒", "loading")
                    logger.info(f"等待扫码中... URL: {current_url}")
            
            self._send_step("登录超时（120秒）", "error")
            return False
            
        except Exception as e:
            self._send_step(f"登录过程出错: {e}", "error")
            logger.error(f"登录过程出错: {e}", exc_info=True)
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
            
            # 先访问登录页检查登录状态
            login_url = "https://www.goofish.pro/login"
            page.goto(login_url, timeout=30000)
            time.sleep(2)
            
            # 检查是否需要登录
            if 'login' in page.url:
                self._send_step("需要登录，等待扫码...", "loading")
                if not self._login():
                    self._send_step("登录失败", "error")
                    return False
            else:
                self._send_step("已登录", "success")
            
            # 访问卡密类型添加页面
            add_url = "https://www.goofish.pro/kam/kind/add"
            page.goto(add_url, timeout=30000)
            self._send_step("访问卡密类型添加页面", "loading")
            
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
            name_input.clear()
            name_input.fill(kind_name)
            
            # 3. 填写卡号前缀
            try:
                card_prefix = page.locator("//label[contains(text(),'卡号前缀')]/..//input").first
                card_prefix.clear()
                card_prefix.fill("  ")
            except:
                pass
            
            # 4. 填写密码前缀
            try:
                pwd_prefix = page.locator("//label[contains(text(),'密码前缀')]/..//input").first
                pwd_prefix.clear()
                pwd_prefix.fill("  ")
            except:
                pass
            
            # 5. 填写库存预警
            try:
                stock_input = page.locator("//label[contains(text(),'库存预警')]/..//input").first
                stock_input.clear()
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

