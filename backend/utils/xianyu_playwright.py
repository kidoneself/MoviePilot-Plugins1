"""
闲鱼卡密管理自动化服务（Playwright版本）
使用 Playwright 替代 Selenium，解决Docker兼容性问题
每个 KamiAutomation 实例完全独立管理自己的浏览器，无全局状态
"""
import logging
import time
import os
import platform
from pathlib import Path
from typing import Optional, Callable
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Playwright

logger = logging.getLogger(__name__)

# 登录状态文件路径（跨实例共享）
STORAGE_STATE_FILE = os.path.expanduser('~/.xianyu_storage_state.json')
        
# 反检测脚本
ANTI_DETECT_SCRIPT = """
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
"""


class KamiAutomation:
    """
    卡密管理自动化（Playwright版本）
    
    每个实例完全独立管理自己的浏览器，无全局状态，无线程问题
    """
    
    def __init__(self, phone: Optional[str] = None, headless: bool = True):
        """
        初始化（不启动浏览器，延迟到需要时再启动）
        
        Args:
            phone: 手机号（用于登录）
            headless: 是否无头模式
        """
        self.phone = phone
        self.headless = headless
        self.step_callback: Optional[Callable] = None
        
        # 每个实例独立管理自己的 Playwright
        self._playwright: Optional[Playwright] = None
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
        """获取浏览器页面实例（延迟启动，每个实例独立）"""
        if self.page is not None:
            return self.page
        
        mode = "无头" if self.headless else "有头"
        logger.info(f"🌐 启动Playwright浏览器（{mode}模式）...")
        
        # 启动 Playwright
        self._playwright = sync_playwright().start()
        
        # 反检测参数
        launch_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
        ]
        
        # macOS ARM 浏览器路径
        executable_path = None
        if platform.system() == 'Darwin' and 'arm' in platform.machine().lower():
            arm_path = os.path.expanduser(
                '~/Library/Caches/ms-playwright/chromium-1200/'
                'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
            )
            if os.path.exists(arm_path):
                executable_path = arm_path
        
        # 启动浏览器（Java 第82-102行的反检测配置）
        self.browser = self._playwright.chromium.launch(
            headless=self.headless,
            executable_path=executable_path,
            args=launch_args,
            chromium_sandbox=False,
            # Java: options.setExperimentalOption("excludeSwitches", new String[]{"enable-automation"})
            ignore_default_args=['--enable-automation']
        )
        
        # 加载已保存的登录状态
        storage_state = None
        if os.path.exists(STORAGE_STATE_FILE):
            try:
                storage_state = STORAGE_STATE_FILE
                logger.info(f"📂 加载登录状态: {STORAGE_STATE_FILE}")
            except:
                pass
        
        # 创建上下文
        self.context = self.browser.new_context(
            storage_state=storage_state,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            permissions=['geolocation', 'notifications'],
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        )
        
        # 注入反检测脚本
        self.context.add_init_script(ANTI_DETECT_SCRIPT)
        
        # 创建页面
        self.page = self.context.new_page()
        logger.info(f"✅ 浏览器启动成功（{mode}模式）")
        
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
                page.wait_for_load_state('networkidle', timeout=15000)
                logger.info("页面加载完成（networkidle）")
            except:
                logger.info("等待networkidle超时，继续...")
            
            # 额外等待，确保 JavaScript 渲染完成
            # 给页面更多时间加载二维码（JS动态生成）
            page.wait_for_timeout(5000)  # 等待5秒让JS渲染
            
            # 再次检查URL（页面可能在等待期间自动跳转）
            current_url = page.url
            if 'login' not in current_url:
                self._send_step("检测到已登录", "success")
                logger.info(f"页面已跳转到: {current_url}")
                return True
            
            # 保存页面HTML和截图，帮助调试
            try:
                # 保存完整HTML
                html_path = '/tmp/xianyu_login_page.html'
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page.content())
                logger.info(f"✅ 已保存页面HTML到: {html_path}")
                
                # 保存截图
                screenshot_path = '/tmp/xianyu_login_page.png'
                page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"✅ 已保存页面截图到: {screenshot_path}")
                
                # 打印页面标题和URL
                logger.info(f"页面标题: {page.title()}")
                logger.info(f"页面URL: {page.url}")
                
                # 查找所有img标签
                imgs = page.locator('img').all()
                logger.info(f"页面中找到 {len(imgs)} 个img标签")
                for idx, img in enumerate(imgs):
                    try:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt')
                        class_name = img.get_attribute('class')
                        id_attr = img.get_attribute('id')
                        logger.info(f"  img[{idx}]: src={src if src else 'None'}")
                        logger.info(f"         alt={alt}, class={class_name}, id={id_attr}")
                    except:
                        pass
                
                # 查找所有可能的登录相关元素
                logger.info("查找登录相关元素...")
                possible_selectors = [
                    "button", "div[class*='login']", "div[class*='qr']", 
                    "div[class*='code']", "div[id*='wechat']", "canvas"
                ]
                for sel in possible_selectors:
                    try:
                        elements = page.locator(sel).all()
                        if len(elements) > 0:
                            logger.info(f"  找到 {len(elements)} 个 {sel} 元素")
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"保存调试信息失败: {e}")
            
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
            
            # 等待二维码元素（等待带alt属性的img）
            # 从日志看，二维码有 alt="Scan me!" 属性
            qr_selectors = [
                "img[alt='Scan me!']",  # 从调试日志发现的
                "//div[contains(@class,'bind-code-scan')]//img",  # Selenium 版本的
                "#wechat-bind-code img",
            ]
            
            logger.info(f"等待二维码元素加载...")
            qr_img = None
            
            for selector in qr_selectors:
                try:
                    logger.info(f"  尝试: {selector}")
                    qr_img = page.wait_for_selector(selector, timeout=10000, state='visible')
                    if qr_img:
                        logger.info(f"  ✅ 找到二维码: {selector}")
                        break
                except Exception as e:
                    logger.info(f"  ❌ 失败: {selector}")
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
                    
                    # 自动关闭"知道了"弹窗
                    try:
                        know_btn = page.locator("text=知道了").first
                        if know_btn.is_visible(timeout=3000):
                            know_btn.click()
                            logger.info("✅ 已关闭'知道了'弹窗")
                            time.sleep(0.5)
                    except:
                        pass
                    
                    # 保存登录状态到文件，下次可以复用
                    try:
                        self.context.storage_state(path=STORAGE_STATE_FILE)
                        logger.info(f"💾 登录状态已保存到: {STORAGE_STATE_FILE}")
                    except Exception as e:
                        logger.warning(f"保存登录状态失败: {e}")
                    
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
        创建卡密类型（完全按照Java版本第122-256行）
        
        Args:
            kind_name: 卡种名称
            category_id: 分类ID（可选）
            
        Returns:
            bool: 是否成功
        """
        try:
            self._send_step(f"开始创建卡种: {kind_name}", "loading")
            page = self._get_page()
            
            # 访问卡密类型添加页面（Java 第128-131行）
            add_url = "https://www.goofish.pro/kam/kind/add"
            page.goto(add_url, timeout=30000)
            self._send_step("访问卡密类型添加页面", "loading")
            logger.info(f"访问卡密类型添加页面: {add_url}")
            
            # 等待页面加载（Java 第134行）
            time.sleep(2)  # Thread.sleep(2000)
            
            # 检查是否需要登录（Java 第137-148行）
            if 'login' in page.url:
                self._send_step("检测到需要登录，等待扫码登录...", "loading")
                logger.info("需要登录，开始自动登录流程")
                if not self._login():
                    self._send_step("登录失败", "error")
                    logger.error("登录失败")
                    return False
                self._send_step("登录成功", "success")
                # 登录后重新访问添加页面
                page.goto(add_url, timeout=30000)
            
            # 等待表单加载（Java 第151行）
            time.sleep(2)
            
            # 1. 选择卡种分类（Java 第153-173行）
            try:
                self._send_step("选择卡种分类", "loading")
                category_select = page.locator("xpath=//label[contains(text(),'卡种分类')]/..//input[@placeholder='请选择']").first
                category_select.click()
                logger.info("点击卡种分类下拉框")
                time.sleep(0.5)
                
                # 选择"影视"分类（Java 第164-169行）
                category_option = page.locator("xpath=//div[contains(@class,'el-select-dropdown')]//li[contains(.,'影视')]").first
                category_option.click(timeout=10000)
                logger.info("选择卡种分类: 影视")
                self._send_step("已选择卡种分类: 影视", "success")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"卡种分类选择失败，使用默认值: {e}")
            
            # 2. 填写卡种名称（Java 第175-182行）
            self._send_step(f"填写卡种名称: {kind_name}", "loading")
            name_input = page.locator("xpath=//label[contains(text(),'卡种名称')]/..//input").first
            name_input.wait_for(state='visible', timeout=10000)
            name_input.clear()
            name_input.fill(kind_name)
            logger.info(f"填写卡种名称: {kind_name}")
            
            # 3. 清空卡号前缀（Java 第184-194行）
            try:
                self._send_step("清空卡号前缀", "loading")
                card_prefix_input = page.locator("xpath=//label[contains(text(),'卡号前缀')]/..//input").first
                card_prefix_input.clear()
                card_prefix_input.fill("  ")
                logger.info("清空卡号前缀")
            except Exception as e:
                logger.warning(f"清空卡号前缀失败: {e}")
            
            # 4. 清空密码前缀（Java 第196-206行）
            try:
                self._send_step("清空密码前缀", "loading")
                pwd_prefix_input = page.locator("xpath=//label[contains(text(),'密码前缀')]/..//input").first
                pwd_prefix_input.clear()
                pwd_prefix_input.fill("  ")
                logger.info("清空密码前缀")
            except Exception as e:
                logger.warning(f"清空密码前缀失败: {e}")
            
            # 5. 填写库存预警（Java 第208-218行）
            try:
                self._send_step("填写库存预警", "loading")
                stock_input = page.locator("xpath=//label[contains(text(),'库存预警')]/..//input").first
                stock_input.clear()
                stock_input.fill("1")
                logger.info("填写库存预警: 1")
            except Exception as e:
                logger.warning(f"填写库存预警失败: {e}")
            
            time.sleep(1)
            
            # 6. 点击创建按钮
            create_button = page.locator("//button[contains(.,'创建')]").first
            create_button.click()
            self._send_step("提交创建请求", "loading")
            
            # 等待页面响应 - 可能跳转到列表页，也可能停留在当前页（有错误提示）
            time.sleep(3)
            
            # 检查是否有错误提示
            try:
                error_msg = page.locator(".el-message--error, .el-message__content").first
                if error_msg.is_visible(timeout=1000):
                    error_text = error_msg.text_content()
                    logger.error(f"创建失败，页面错误提示: {error_text}")
                    self._send_step(f"创建失败: {error_text}", "error")
                    # 保存失败截图
                    try:
                        page.screenshot(path="/tmp/create_kind_failed.png")
                        logger.info("已保存创建失败截图: /tmp/create_kind_failed.png")
                    except:
                        pass
                    return False
            except:
                pass
            
            # 检查是否成功（URL跳转）
            current_url = page.url
            logger.info(f"提交后URL: {current_url}")
            
            if '/list' in current_url or '/add' not in current_url:
                self._send_step(f"卡种创建成功: {kind_name}", "success")
                return True
            else:
                # 再等5秒看是否跳转
                logger.info("URL未立即跳转，再等待5秒...")
                time.sleep(5)
                current_url = page.url
                logger.info(f"5秒后URL: {current_url}")
                
                if '/list' in current_url or '/add' not in current_url:
                    self._send_step(f"卡种创建成功: {kind_name}", "success")
                    return True
                else:
                    self._send_step("卡种创建失败（URL未跳转）", "error")
                    # 保存失败截图
                    try:
                        page.screenshot(path="/tmp/create_kind_no_redirect.png")
                        logger.info("已保存未跳转截图: /tmp/create_kind_no_redirect.png")
                    except:
                        pass
                return False
            
        except Exception as e:
            self._send_step(f"创建异常: {e}", "error")
            logger.error(f"创建卡密类型失败: {e}", exc_info=True)
            return False
    
    def _close_popup(self, page):
        """关闭可能出现的弹窗"""
        try:
            # 关闭"知道了"弹窗
            know_btn = page.locator("text=知道了").first
            if know_btn.is_visible(timeout=2000):
                know_btn.click()
                logger.info("✅ 已关闭'知道了'弹窗")
                time.sleep(0.5)
        except:
            pass
        
        try:
            # 关闭其他可能的弹窗（X 按钮）
            close_btns = page.locator(".el-dialog__headerbtn").all()
            for btn in close_btns:
                if btn.is_visible():
                    btn.click()
                    time.sleep(0.3)
        except:
            pass
    
    def add_kami_cards(self, kind_name: str, kami_data: str, repeat_count: int = 1) -> bool:
        """
        添加卡密到指定卡种（完全按照 Java 版本翻译）
        参考: Java KamiService.java 第343-528行
        
        Args:
            kind_name: 卡种名称
            kami_data: 卡密数据（每行一组，格式: 卡号 密码）
            repeat_count: 重复次数
            
        Returns:
            bool: 是否成功
        """
        try:
            self._send_step(f"开始添加卡密到卡种: {kind_name}", "loading")
            page = self._get_page()
            
            # 1. 访问卡种列表页面（Java 第370-375行）
            self._send_step("访问卡种列表页面", "loading")
            list_url = "https://www.goofish.pro/kam/kind/list"
            logger.info(f"访问卡种列表页面: {list_url}")
            page.goto(list_url, timeout=30000)
            time.sleep(3)  # 增加等待时间确保页面完全加载
            
            # 检查登录（Java 第356-367行）
            if 'login' in page.url:
                self._send_step("检测到需要登录，等待扫码...", "loading")
                logger.info("需要登录，开始自动登录流程")
                if not self._login():
                    self._send_step("登录失败", "error")
                    logger.error("登录失败")
                    return False
                self._send_step("登录成功", "success")
            
            # 2. 使用 JavaScript 查找并点击"添加卡密"按钮（Java 第379-412行）
            self._send_step(f"查找卡种: {kind_name}", "loading")
            logger.info(f"查找卡种: {kind_name}")
            
            # 完全按照 Java 的 JavaScript 代码（Java 第384-400行）
            script = f"""
            (function() {{
                var rows = document.querySelectorAll('tr');
                for (var i = 0; i < rows.length; i++) {{
                    var row = rows[i];
                    var text = row.textContent;
                    if (text.includes('{kind_name}')) {{
                        var divs = row.querySelectorAll('div');
                        for (var j = 0; j < divs.length; j++) {{
                            var div = divs[j];
                            if (div.textContent.trim() === '添加卡密') {{
                                div.click();
                                return true;
                            }}
                        }}
                    }}
                }}
                return false;
            }})()
            """
            
            clicked = page.evaluate(script)
            
            if clicked:
                self._send_step("点击添加卡密按钮", "success")
                logger.info("通过JavaScript成功点击添加卡密按钮")
            else:
                self._send_step("未找到添加卡密按钮", "error")
                logger.error("未找到添加卡密按钮")
                return False
            
            time.sleep(1)
            
            # 4. 输入卡密数据到文本框（Java 第430-441行）
            self._send_step("填写卡密数据", "loading")
            textarea = page.locator("xpath=//textarea").first
            textarea.wait_for(state='visible', timeout=15000)
            textarea.clear()
            textarea.fill(kami_data)
            self._send_step("卡密数据填写完成", "success")
            logger.info("填写卡密数据")
            
            # 等待页面内容完全加载
            time.sleep(2)
            
            # 6. 开启"重复卡密"开关（Java 第443-464行）
            try:
                self._send_step("开启重复卡密开关", "loading")
                repeat_switch = page.locator("xpath=//p[contains(text(),'重复卡密')]/following-sibling::div//div[@role='switch']").first
                
                # 检查开关状态
                switch_class = repeat_switch.get_attribute("class")
                if switch_class and 'is-checked' not in switch_class:
                    repeat_switch.click()
                    self._send_step("重复卡密开关已开启", "success")
                    logger.info("开启重复卡密开关")
                    time.sleep(2)  # 等待开关动画完成和输入框启用
                else:
                    self._send_step("重复卡密开关已开启", "success")
                    logger.info("重复卡密开关已开启")
            except Exception as e:
                self._send_step(f"开关操作失败: {e}", "error")
                logger.error(f"重复卡密开关操作失败: {e}")
                raise e
            
            # 7. 填写重复次数（Java 第466-498行）
            time.sleep(2)  # 等待开关切换后的动画和输入框启用
            
            try:
                self._send_step(f"填写重复次数: {repeat_count}", "loading")
                repeat_input = page.locator("xpath=//p[contains(text(),'重复卡密')]/following-sibling::div//input[@placeholder='请输入数字']").first
                logger.info("找到重复卡密输入框")
                
                time.sleep(1)  # 等待一下确保完全可交互
                
                # 滚动到输入框可见位置
                repeat_input.scroll_into_view_if_needed()
                time.sleep(0.5)
                
                # 使用 sendKeys 填写（Java 第488行）
                repeat_input.fill(str(repeat_count))
                self._send_step(f"重复次数已设置: {repeat_count}", "success")
                logger.info(f"通过fill填写重复次数: {repeat_count}")
                
                time.sleep(1)  # 等待Vue更新
            except Exception as e:
                self._send_step("填写重复次数失败，将添加1组卡密", "error")
                logger.error(f"填写重复次数失败: {e}")
                logger.warning("跳过重复次数填写，将添加1组卡密")
            
            # 8. 点击"添加"按钮（Java 第500-507行）
            self._send_step("提交卡密数据", "loading")
            time.sleep(0.5)
            # 完全按照 Java 的 XPath: //button[contains(.,'添加') and not(contains(.,'添加卡密'))]
            submit_button = page.locator("xpath=//button[contains(.,'添加') and not(contains(.,'添加卡密'))]").first
            submit_button.click()
            logger.info("点击添加按钮提交")
            
            # 9. 等待提交完成（Java 第509-510行）
            time.sleep(3)
            
            # 10. 刷新页面（Java 第512-515行）
            page.reload()
            logger.info("刷新页面")
            time.sleep(1)
            
            self._send_step("卡密添加成功", "success")
            logger.info("卡密添加成功")
            return True
                
        except Exception as e:
            self._send_step(f"添加卡密失败: {e}", "error")
            logger.error(f"添加卡密失败", e)
            return False
    
    def setup_auto_shipping(self, kind_name: str, product_title: str) -> bool:
        """
        设置自动发货（通过搜索商品标题）
        
        Args:
            kind_name: 卡种名称
            product_title: 商品标题（用于搜索）
            
        Returns:
            bool: 是否成功
        """
        try:
            self._send_step(f"开始设置自动发货: {kind_name}", "loading")
            logger.info(f"开始设置自动发货，卡种: {kind_name}, 商品: {product_title}")
            page = self._get_page()
            
            # 1. 访问发货设置页面
            self._send_step("访问发货设置页面", "loading")
            page.goto("https://www.goofish.pro/kam/send/consign-setting/list", timeout=30000)
            logger.info("访问发货设置页面")
            time.sleep(3)
            
            # 检查登录
            if 'login' in page.url:
                self._send_step("检测到需要登录，等待扫码...", "loading")
                if not self._login():
                    self._send_step("登录失败", "error")
                    return False
                page.goto("https://www.goofish.pro/kam/send/consign-setting/list", timeout=30000)
                time.sleep(3)
            
            # 2. 点击"销售中"标签
            self._send_step("切换到销售中标签", "loading")
            try:
                selling_tab = page.locator("text=销售中").first
                selling_tab.click()
                logger.info("点击销售中标签")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"点击销售中标签失败: {e}")
            
            # 3. 在"商品标题"输入框搜索
            self._send_step(f"搜索商品: {product_title}", "loading")
            try:
                # 找到"商品标题"输入框
                title_input = page.locator("input[placeholder='商品标题']").first
                title_input.clear()
                title_input.fill(product_title)
                logger.info(f"输入商品标题: {product_title}")
                time.sleep(0.5)
                
                # 点击"搜索"按钮
                search_button = page.locator("button:has-text('搜索')").first
                search_button.click()
                logger.info("点击搜索按钮")
                self._send_step("搜索商品中...", "loading")
                time.sleep(3)  # 等待搜索结果
                
                # 验证搜索结果是否包含目标商品
                verify_script = f"""
                (function() {{
                    var rows = document.querySelectorAll('tbody tr');
                    var foundCount = 0;
                    for (var i = 0; i < rows.length; i++) {{
                        var text = rows[i].textContent;
                        if (text.includes('{product_title}')) {{
                            foundCount++;
                        }}
                    }}
                    return foundCount;
                }})()
                """
                
                found_count = page.evaluate(verify_script)
                logger.info(f"搜索结果中找到 {found_count} 个匹配的商品")
                
                if found_count == 0:
                    # 商品可能还在审核中，发送需要重试的提示
                    self._send_step(f"搜索'{product_title}'暂无结果（商品可能在审核中），请稍后重试", "need_retry")
                    logger.warning(f"搜索'{product_title}'无结果，可能商品还在审核")
                    page.screenshot(path="/tmp/search_no_result.png", full_page=True)
                    # 保持浏览器打开，等待用户重试
                    return False
                
                self._send_step(f"找到 {found_count} 个匹配商品", "success")
                
            except Exception as e:
                logger.error(f"搜索商品失败: {e}")
                page.screenshot(path="/tmp/search_product_failed.png", full_page=True)
                return False
            
            # 4. 点击全选（用JavaScript强制点击）
            self._send_step("点击全选", "loading")
            time.sleep(2)  # 等待搜索结果加载
            
            # 用JavaScript强制点击全选（不管是否visible）
            select_all_script = """
            (function() {
                var selectAll = document.querySelector('thead input[type="checkbox"]');
                if (selectAll) {
                    selectAll.click();
                    return true;
                }
                return false;
            })()
            """
            
            selected = page.evaluate(select_all_script)
            if selected:
                logger.info("点击全选checkbox")
                self._send_step("已勾选所有商品", "success")
                time.sleep(1)
            else:
                logger.error("未找到全选checkbox")
                page.screenshot(path="/tmp/no_select_all.png", full_page=True)
                return False
            
            # 5. 点击"批量设置付款后发货"
            self._send_step("点击批量设置付款后发货", "loading")
            batch_button = page.locator("xpath=//button[contains(.,'批量设置付款后发货')]").first
            batch_button.click(timeout=15000)
            logger.info("点击批量设置付款后发货")
            time.sleep(2)
            
            # 6. 在弹窗中选择"单卡种"
            try:
                self._send_step("选择单卡种模式", "loading")
                single_kind_radio = page.locator("xpath=//label[contains(.,'单卡种')]").first
                single_kind_radio.click(timeout=10000)
                logger.info("选择单卡种")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"选择单卡种失败: {e}")
            
            # 7. 选择发货卡种（在弹窗内，找"发货卡种"标签旁的下拉框）
            self._send_step(f"选择发货卡种: {kind_name}", "loading")
            time.sleep(1)  # 等待弹窗完全显示
            
            # 用JavaScript在弹窗内查找"发货卡种"下拉框并选择
            select_kind_script = f"""
            (function() {{
                // 在可见的dialog中查找
                var dialog = document.querySelector('.el-dialog__wrapper:not([style*="display: none"])');
                if (!dialog) return false;
                
                // 在dialog内找到"发货卡种"标签
                var labels = dialog.querySelectorAll('span, label, div');
                for (var i = 0; i < labels.length; i++) {{
                    if (labels[i].textContent.trim() === '发货卡种') {{
                        // 找到标签后，找它附近的input
                        var parent = labels[i].parentElement;
                        var input = parent.querySelector('.el-select input');
                        if (input) {{
                            input.click();
                            
                            // 等待下拉框出现，然后选择
                            setTimeout(function() {{
                                var options = document.querySelectorAll('.el-select-dropdown:not([style*="display: none"]) li');
                                for (var j = 0; j < options.length; j++) {{
                                    if (options[j].textContent.includes('{kind_name}')) {{
                                        options[j].click();
                                        return;
                                    }}
                                }}
                            }}, 500);
                            
                            return true;
                        }}
                    }}
                }}
                return false;
            }})()
            """
            
            selected = page.evaluate(select_kind_script)
            if selected:
                logger.info(f"选择发货卡种: {kind_name}")
                self._send_step(f"发货卡种已选择: {kind_name}", "success")
                time.sleep(2)  # 等待选择完成
            else:
                logger.error("未找到发货卡种下拉框")
                page.screenshot(path="/tmp/kind_select_failed.png", full_page=True)
                return False
            
            # 8. 点击"确认"按钮
            self._send_step("保存发货设置", "loading")
            confirm_button = page.locator("xpath=//button[contains(@class,'el-button--primary') and contains(.,'确认')]").first
            confirm_button.click(timeout=10000)
            logger.info("点击确认按钮")
            time.sleep(3)
            
            self._send_step("自动发货设置成功", "success")
            logger.info("自动发货设置成功")
            return True
            
        except Exception as e:
            self._send_step(f"设置失败: {e}", "error")
            logger.error(f"设置自动发货失败: {e}")
            return False
    
    def close(self):
        """关闭浏览器（任务结束后调用）"""
        # 先保存登录状态
        if self.context:
            try:
                self.context.storage_state(path=STORAGE_STATE_FILE)
                logger.info(f"💾 登录状态已保存")
            except:
                pass
        
        # 关闭页面
        if self.page:
            try:
                self.page.close()
            except:
                pass
            self.page = None
        
        # 关闭 context
        if self.context:
            try:
                self.context.close()
            except:
                pass
            self.context = None
        
        # 关闭浏览器
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
            self.browser = None
        
        # 关闭 Playwright
        if self._playwright:
            try:
                self._playwright.stop()
            except:
                pass
            self._playwright = None
        
        logger.info("🔒 浏览器已关闭")


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

