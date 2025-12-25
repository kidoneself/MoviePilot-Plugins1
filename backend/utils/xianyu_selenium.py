"""
闲鱼卡密管理自动化服务
使用 Selenium 自动化浏览器操作
全局浏览器实例，保持登录会话
"""
import logging
import time
import platform
from pathlib import Path
from typing import Optional, Callable
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


# 全局浏览器实例管理
_global_driver: Optional[webdriver.Chrome] = None
_global_headless: bool = True


def get_global_driver(headless: bool = True) -> webdriver.Chrome:
    """获取全局浏览器实例（单例模式，保持会话）"""
    global _global_driver, _global_headless
    
    # 如果模式改变，关闭旧实例
    if _global_driver and _global_headless != headless:
        logger.info("浏览器模式改变，关闭旧实例")
        try:
            _global_driver.quit()
        except:
            pass
        _global_driver = None
    
    # 检查浏览器是否仍然活着
    if _global_driver:
        try:
            _ = _global_driver.current_url  # 测试连接
        except:
            logger.warning("全局浏览器实例已失效，重新创建")
            _global_driver = None
    
    if _global_driver is None:
        logger.info(f"创建全局浏览器实例（{'无头' if headless else '有头'}模式）")
        _global_driver = _create_driver(headless)
        _global_headless = headless
    
    return _global_driver


def _create_driver(headless: bool) -> webdriver.Chrome:
    """创建浏览器驱动实例"""
    # 检测操作系统和架构
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if 'darwin' in system:  # macOS
        if 'arm' in machine or 'aarch64' in machine:
            platform_name = 'mac-arm64'
        else:
            platform_name = 'mac-x64'
    elif 'linux' in system:
        platform_name = 'linux64'
    elif 'windows' in system:
        platform_name = 'win64'
    else:
        platform_name = 'linux64'
    
    logger.info(f"检测到操作系统: {system} ({machine}), 使用平台: {platform_name}")
    logger.info(f"使用 {'无头模式' if headless else '有头模式'}")
    
    # ChromeDriver 路径查找（按优先级）
    home_dir = Path.home()
    driver_path = None
    
    # 1. 查找缓存目录下的所有版本（自动找最新的）
    cache_base = home_dir / '.cache' / 'selenium' / 'chromedriver' / platform_name
    if cache_base.exists():
        # 找到所有版本目录
        version_dirs = sorted([d for d in cache_base.iterdir() if d.is_dir()], reverse=True)
        for version_dir in version_dirs:
            potential_path = version_dir / 'chromedriver'
            if 'windows' in system:
                potential_path = potential_path.with_suffix('.exe')
            if potential_path.exists():
                driver_path = potential_path
                logger.info(f"找到 ChromeDriver: {driver_path}")
                break
    
    # 2. 检查系统路径（/usr/local/bin/chromedriver）
    if not driver_path:
        system_paths = [
            Path('/usr/local/bin/chromedriver'),
            Path('/usr/bin/chromedriver'),
        ]
        for path in system_paths:
            if path.exists():
                driver_path = path
                logger.info(f"使用系统 ChromeDriver: {driver_path}")
                break
    
    if not driver_path:
        logger.info("未找到本地 ChromeDriver，尝试使用 Selenium Manager 自动下载")
    
    # 配置 Chrome 选项
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
    
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 反自动化检测
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 禁用日志
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--silent')
    
    # 创建 Service
    service = None
    if driver_path:
        service = Service(executable_path=str(driver_path))
    
    logger.info("创建 ChromeDriver 实例...")
    try:
        if service:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Selenium 4.6+ 会自动使用 Selenium Manager 下载 ChromeDriver
            driver = webdriver.Chrome(options=chrome_options)
        
        # 隐藏 webdriver 属性
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        logger.info("浏览器驱动创建成功")
        return driver
    except Exception as e:
        logger.error(f"创建驱动失败: {e}")
        raise


def close_global_driver():
    """关闭全局浏览器实例"""
    global _global_driver
    if _global_driver:
        logger.info("关闭全局浏览器实例")
        try:
            _global_driver.quit()
        except:
            pass
        _global_driver = None


class KamiAutomation:
    """卡密管理自动化"""
    
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
        # 使用全局driver，不要在这里创建
        self.driver = None
    
    def set_step_callback(self, callback: Callable[[str, str], None]):
        """设置步骤回调函数"""
        self.step_callback = callback
    
    def _send_step(self, step: str, status: str = "loading"):
        """发送步骤消息"""
        if self.step_callback:
            self.step_callback(step, status)
        logger.info(f"[{status.upper()}] {step}")
    
    def _get_driver(self):
        """获取浏览器实例（使用全局单例）"""
        if self.driver is None:
            self.driver = get_global_driver(self.headless)
        return self.driver
    
    def _login(self) -> bool:
        """自动登录"""
        try:
            driver = self._get_driver()
            self._send_step("检测是否需要登录...", "loading")
            time.sleep(3)
            
            # 检查是否在登录页面
            if 'login' not in driver.current_url:
                self._send_step("已登录", "success")
                return True
            
            self._send_step("获取登录二维码...", "loading")
            
            wait = WebDriverWait(driver, 10)
            
            # 获取二维码
            try:
                qr_img = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'bind-code-scan')]//img"))
                )
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
                if 'login' not in driver.current_url:
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
        创建卡密类型
        
        Args:
            kind_name: 卡种名称
            category_id: 分类ID（可选）
            
        Returns:
            是否成功
        """
        try:
            driver = self._get_driver()
            self._send_step(f"开始创建卡种: {kind_name}", "loading")
            
            # 访问卡密类型添加页面
            add_url = "https://www.goofish.pro/kam/kind/add"
            driver.get(add_url)
            self._send_step("访问卡密类型添加页面", "loading")
            
            wait = WebDriverWait(driver, 10)
            
            # 检查是否需要登录
            if 'login' in driver.current_url:
                self._send_step("需要登录，等待扫码...", "loading")
                if not self._login():
                    self._send_step("登录失败", "error")
                    return False
                # 重新访问添加页面
                driver.get(add_url)
            
            time.sleep(2)
            
            # 1. 选择卡种分类
            try:
                self._send_step("选择卡种分类", "loading")
                category_select = driver.find_element(
                    By.XPATH, "//label[contains(text(),'卡种分类')]/..//input[@placeholder='请选择']"
                )
                category_select.click()
                time.sleep(0.5)
                
                category_option = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'el-select-dropdown')]//li[contains(.,'影视')]"))
                )
                category_option.click()
                self._send_step("已选择卡种分类: 影视", "success")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"卡种分类选择失败: {e}")
            
            # 2. 填写卡种名称
            self._send_step(f"填写卡种名称: {kind_name}", "loading")
            name_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//label[contains(text(),'卡种名称')]/..//input"))
            )
            name_input.clear()
            name_input.send_keys(kind_name)
            
            # 3. 填写卡号前缀
            try:
                card_prefix = driver.find_element(By.XPATH, "//label[contains(text(),'卡号前缀')]/..//input")
                card_prefix.clear()
                card_prefix.send_keys("  ")
            except:
                pass
            
            # 4. 填写密码前缀
            try:
                pwd_prefix = driver.find_element(By.XPATH, "//label[contains(text(),'密码前缀')]/..//input")
                pwd_prefix.clear()
                pwd_prefix.send_keys("  ")
            except:
                pass
            
            # 5. 填写库存预警
            try:
                stock_input = driver.find_element(By.XPATH, "//label[contains(text(),'库存预警')]/..//input")
                stock_input.clear()
                stock_input.send_keys("1")
            except:
                pass
            
            time.sleep(1)
            
            # 6. 点击创建按钮
            create_button = driver.find_element(By.XPATH, "//button[contains(.,'创建')]")
            create_button.click()
            self._send_step("提交创建请求", "loading")
            
            time.sleep(2)
            
            # 检查是否成功
            current_url = driver.current_url
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
    
    def add_kami_cards(self, kind_name: str, kami_data: str, repeat_count: int = 1) -> bool:
        """
        添加卡密到指定卡种
        
        Args:
            kind_name: 卡种名称
            kami_data: 卡密数据（每行一组，格式: 卡号 密码）
            repeat_count: 重复次数
            
        Returns:
            是否成功
        """
        try:
            driver = self._get_driver()
            self._send_step(f"开始添加卡密到卡种: {kind_name}", "loading")
            
            # 访问卡种列表
            self._send_step("访问卡种列表页面", "loading")
            driver.get("https://www.goofish.pro/kam/kind/list")
            time.sleep(3)
            
            # 检查登录
            if 'login' in driver.current_url:
                if not self._login():
                    return False
                driver.get("https://www.goofish.pro/kam/kind/list")
                time.sleep(3)
            
            wait = WebDriverWait(driver, 15)
            
            # 查找并点击"添加卡密"按钮
            self._send_step(f"查找卡种: {kind_name}", "loading")
            
            script = f"""
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
            """
            
            clicked = driver.execute_script(script)
            
            if not clicked:
                self._send_step("未找到添加卡密按钮", "error")
                return False
            
            self._send_step("点击添加卡密按钮", "success")
            time.sleep(1)
            
            # 切换到空格标签
            try:
                space_tab = driver.find_element(By.XPATH, "//div[contains(text(),'空格')]")
                space_tab.click()
                self._send_step("切换到空格标签", "success")
                time.sleep(0.5)
            except:
                pass
            
            # 输入卡密数据
            self._send_step("填写卡密数据", "loading")
            textarea = wait.until(EC.presence_of_element_located((By.XPATH, "//textarea")))
            textarea.clear()
            textarea.send_keys(kami_data)
            self._send_step("卡密数据填写完成", "success")
            
            time.sleep(2)
            
            # 开启重复卡密开关
            if repeat_count > 1:
                try:
                    self._send_step("开启重复卡密开关", "loading")
                    repeat_switch = driver.find_element(
                        By.XPATH, "//p[contains(text(),'重复卡密')]/following-sibling::div//div[@role='switch']"
                    )
                    switch_class = repeat_switch.get_attribute('class')
                    if 'is-checked' not in (switch_class or ''):
                        repeat_switch.click()
                        self._send_step("重复卡密开关已开启", "success")
                        time.sleep(2)
                    
                    # 填写重复次数
                    self._send_step(f"填写重复次数: {repeat_count}", "loading")
                    time.sleep(1)
                    
                    repeat_input = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//p[contains(text(),'重复卡密')]/following-sibling::div//input[@placeholder='请输入数字']")
                        )
                    )
                    
                    # 滚动到可见
                    driver.execute_script("arguments[0].scrollIntoView(true);", repeat_input)
                    time.sleep(0.5)
                    
                    repeat_input.send_keys(str(repeat_count))
                    self._send_step(f"重复次数已设置: {repeat_count}", "success")
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"设置重复次数失败: {e}")
                    self._send_step("设置重复次数失败，将添加1组", "warning")
            
            # 点击添加按钮
            self._send_step("提交卡密数据", "loading")
            time.sleep(0.5)
            submit_button = driver.find_element(
                By.XPATH, "//button[contains(.,'添加') and not(contains(.,'添加卡密'))]"
            )
            submit_button.click()
            
            time.sleep(3)
            
            # 刷新页面
            driver.refresh()
            time.sleep(1)
            
            self._send_step("卡密添加成功", "success")
            return True
            
        except Exception as e:
            self._send_step(f"添加卡密失败: {e}", "error")
            logger.error(f"添加卡密失败: {e}", exc_info=True)
            return False
    
    def setup_auto_shipping(self, kind_name: str, product_title: str) -> bool:
        """
        设置自动发货
        
        Args:
            kind_name: 卡种名称
            product_title: 商品标题（用于搜索定位商品）
            
        Returns:
            是否成功
        """
        try:
            driver = self._get_driver()
            self._send_step(f"开始为卡种 {kind_name} 设置自动发货", "loading")
            
            wait = WebDriverWait(driver, 15)
            
            # 导航到发货设置页面
            self._send_step("导航到发货设置页面", "loading")
            driver.get("https://www.goofish.pro/kam/send/consign-setting/list")
            time.sleep(3)
            
            # 检查登录
            if 'login' in driver.current_url:
                if not self._login():
                    return False
                driver.get("https://www.goofish.pro/kam/send/consign-setting/list")
                time.sleep(3)
            
            # 点击"去设置"
            self._send_step("点击去设置按钮", "loading")
            go_set_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'去设置')]")))
            go_set_btn.click()
            time.sleep(3)
            
            # 使用商品标题搜索
            self._send_step(f"搜索商品: {product_title}", "loading")
            
            # 等待页面加载完成
            time.sleep(2)
            
            # 定位搜索输入框并输入关键词
            try:
                # 先找到搜索框容器的第二个子元素（div）
                search_box_div = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-box.custom-element > div:nth-child(2)"))
                )
                
                # 然后在这个div里找input元素
                search_box = search_box_div.find_element(By.TAG_NAME, "input")
                
                # 使用JavaScript设置值并触发事件（更可靠）
                driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, search_box, product_title)
                logger.info(f"已通过JS设置搜索框值并触发事件: {product_title}")
                self._send_step(f"已输入搜索关键词: {product_title}", "success")
                time.sleep(1)
                
                # 找到搜索按钮并点击
                search_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.search-box.custom-element button.search-btn"))
                )
                # 用JavaScript点击（更可靠）
                driver.execute_script("arguments[0].click();", search_btn)
                logger.info("已通过JS点击搜索按钮")
                self._send_step("已点击搜索按钮，等待结果...", "loading")
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"搜索功能使用失败: {e}", exc_info=True)
                self._send_step(f"搜索失败: {str(e)}", "error")
                return False
            
            # 等待商品列表加载
            self._send_step("等待商品列表加载完成...", "loading")
            wait.until(EC.presence_of_element_located((By.XPATH, "//tbody//input[@type='checkbox']")))
            time.sleep(2)
            
            # 先检查有多少个商品
            total_count_script = "return document.querySelectorAll('tbody input[type=\"checkbox\"]').length;"
            total_count = driver.execute_script(total_count_script)
            logger.info(f"搜索结果中找到 {total_count} 个商品")
            self._send_step(f"搜索到 {total_count} 个商品", "success")
            
            # 勾选搜索到的商品（最多2个）
            self._send_step("正在勾选商品（最多2个）...", "loading")
            
            check_script = """
            var checkboxes = document.querySelectorAll('tbody input[type="checkbox"]');
            var count = Math.min(2, checkboxes.length);
            for (var i = 0; i < count; i++) {
                checkboxes[i].click();
            }
            return count;
            """
            
            checkbox_count = driver.execute_script(check_script)
            logger.info(f"实际勾选的商品数量: {checkbox_count}")
            
            if checkbox_count < 1:
                self._send_step("未找到可勾选的商品", "error")
                return False
            
            self._send_step(f"✓ 已勾选 {checkbox_count} 个商品（共{total_count}个可选）", "success")
            time.sleep(2)
            
            # 点击"批量设置付款后发货"
            self._send_step("点击批量设置付款后发货", "loading")
            batch_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'批量设置付款后发货')]"))
            )
            batch_btn.click()
            self._send_step("进入发货设置弹窗", "success")
            time.sleep(2)
            
            # 选择"单卡种"
            try:
                self._send_step("选择单卡种模式", "loading")
                single_kind_radio = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//label[contains(.,'单卡种')]"))
                )
                single_kind_radio.click()
                self._send_step("单卡种模式已选择", "success")
                time.sleep(1)
            except:
                pass
            
            # 选择发货卡种
            self._send_step(f"选择发货卡种: {kind_name}", "loading")
            kind_select = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class,'el-select') and contains(@class,'w-340')]//input")
                )
            )
            kind_select.click()
            time.sleep(1)
            
            kind_option = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[contains(@class,'el-select-dropdown')]//li[contains(.,'{kind_name}')]")
                )
            )
            kind_option.click()
            self._send_step(f"发货卡种已选择: {kind_name}", "success")
            time.sleep(1)
            
            # 点击确认
            self._send_step("保存发货设置", "loading")
            confirm_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class,'el-button--primary') and contains(.,'确认')]")
                )
            )
            confirm_btn.click()
            time.sleep(3)
            
            self._send_step("自动发货设置成功", "success")
            return True
            
        except Exception as e:
            self._send_step(f"设置失败: {e}", "error")
            logger.error(f"设置自动发货失败: {e}", exc_info=True)
            return False
    
    def close(self):
        """关闭浏览器（不推荐，会话会丢失）"""
        # 不再关闭全局driver，保持会话
        logger.info("浏览器会话保持，不关闭")
        pass
