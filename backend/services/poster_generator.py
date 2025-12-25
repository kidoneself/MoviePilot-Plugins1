"""
海报生成器
使用 Pillow 自动生成闲鱼商品海报
完全按照Java版本的样式
"""
import io
import logging
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional, List, Tuple
from pathlib import Path
import cairosvg

logger = logging.getLogger(__name__)


class PosterGenerator:
    """海报生成器"""
    
    def __init__(self):
        self.canvas_width = 800
        self.canvas_height = 1200
        
        # 字体
        self.font_path = self._find_font()
        
        # Logo缓存
        self.logos = {}
        self._load_logos()
    
    def _find_font(self) -> Optional[str]:
        """查找系统中文字体"""
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
            "C:/Windows/Fonts/msyh.ttc",  # Windows
        ]
        
        for path in font_paths:
            if Path(path).exists():
                logger.info(f"使用字体: {path}")
                return path
        
        logger.warning("未找到中文字体")
        return None
    
    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """加载字体"""
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, size)
        except:
            pass
        return ImageFont.load_default()
    
    def _load_logos(self):
        """加载网盘Logo（SVG转PNG）"""
        svg_dir = Path(__file__).parent.parent.parent / "frontend-vue" / "public" / "svg"
        
        logo_files = {
            'baidu': svg_dir / '百度网盘.svg',
            'quark': svg_dir / '夸克网盘.svg',
            'xunlei': svg_dir / '迅雷.svg'
        }
        
        for name, svg_path in logo_files.items():
            try:
                if svg_path.exists():
                    # SVG转PNG
                    png_data = cairosvg.svg2png(url=str(svg_path), output_width=60, output_height=60)
                    self.logos[name] = Image.open(io.BytesIO(png_data))
                    logger.info(f"Logo加载成功: {name}")
            except Exception as e:
                logger.warning(f"Logo加载失败 {name}: {e}")
    
    def _download_image(self, url: str) -> Optional[Image.Image]:
        """下载图片"""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            # 转换为RGB（去除透明通道）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                return background
            return img.convert('RGB')
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.Draw, xy, radius, fill, outline=None, width=0):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = xy[0][0], xy[0][1], xy[1][0], xy[1][1]
        
        # 创建一个临时图层用于绘制圆角矩形
        mask = Image.new('L', (x2 - x1, y2 - y1), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (x2 - x1, y2 - y1)], radius, fill=255)
        
        # 创建填充图层
        rect_img = Image.new('RGB', (x2 - x1, y2 - y1), fill)
        
        return mask, rect_img, (x1, y1)
    
    def generate_poster_auto(
        self,
        poster_url: str,
        media_name: str,
        episode_count: Optional[str] = None,
        is_completed: bool = False
    ) -> Optional[bytes]:
        """
        自动生成海报（完全按照Java版本）
        
        Args:
            poster_url: TMDB海报URL
            media_name: 媒体名称
            episode_count: 集数
            is_completed: 是否完结
            
        Returns:
            PNG图片字节数据
        """
        try:
            # 下载原始海报
            poster_img = self._download_image(poster_url)
            if not poster_img:
                logger.error("下载海报失败")
                return None
            
            # 创建画布
            canvas = Image.new('RGB', (self.canvas_width, self.canvas_height), (255, 255, 255))
            
            # 缩放并绘制背景图（填充满画布）
            scale = max(self.canvas_width / poster_img.width, self.canvas_height / poster_img.height)
            new_width = int(poster_img.width * scale)
            new_height = int(poster_img.height * scale)
            poster_resized = poster_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            x = (self.canvas_width - new_width) // 2
            y = (self.canvas_height - new_height) // 2
            canvas.paste(poster_resized, (x, y))
            
            # 创建绘图对象
            draw = ImageDraw.Draw(canvas)
            
            # 1. 绘制顶部网盘Logo徽章（黄色背景 + 白色圆形 + Logo）
            self._draw_top_logos_badge(canvas, draw)
            
            # 2. 绘制左侧竖排剧名
            self._draw_left_vertical_text(draw, media_name)
            
            # 3. 绘制中心"4K超清"粉色徽章
            self._draw_center_badge(draw, "4K超清")
            
            # 4. 绘制集数（如果有）
            if episode_count:
                self._draw_episode_count(draw, episode_count)
            
            # 5. 绘制底部三色条
            self._draw_bottom_bar(draw)
            
            # 转换为字节
            output = io.BytesIO()
            canvas.save(output, format='PNG', quality=95, optimize=True)
            output.seek(0)
            
            logger.info("海报生成成功")
            return output.getvalue()
        
        except Exception as e:
            logger.error(f"生成海报失败: {e}", exc_info=True)
            return None
    
    def _draw_top_logos_badge(self, canvas: Image.Image, draw: ImageDraw.Draw):
        """绘制顶部网盘Logo徽章（完全按照Java版本）"""
        logo_size = 60
        spacing = 15
        total_width = logo_size * 3 + spacing * 2
        start_x = (self.canvas_width - total_width) // 2
        logo_y = 25
        
        # 黄色徽章背景
        badge_padding_x = 25
        badge_padding_y = 15
        badge_x = start_x - badge_padding_x
        badge_y = logo_y - badge_padding_y
        badge_width = total_width + badge_padding_x * 2
        badge_height = logo_size + badge_padding_y * 2
        badge_radius = 12
        
        # 绘制黄色圆角矩形（渐变简化为纯色）
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=badge_radius,
            fill='#ffa500',
            outline='white',
            width=3
        )
        
        # 绘制Logo（顺序：百度、夸克、迅雷）
        logo_order = ['baidu', 'quark', 'xunlei']
        for i, logo_name in enumerate(logo_order):
            if logo_name in self.logos:
                logo_x = start_x + i * (logo_size + spacing)
                logo_center_x = logo_x + logo_size // 2
                logo_center_y = logo_y + logo_size // 2
                
                # 绘制白色圆形背景
                circle_radius = logo_size // 2 + 5
                draw.ellipse(
                    [
                        (logo_center_x - circle_radius, logo_center_y - circle_radius),
                        (logo_center_x + circle_radius, logo_center_y + circle_radius)
                    ],
                    fill='white'
                )
                
                # 粘贴Logo
                logo_img = self.logos[logo_name]
                if logo_img.mode == 'RGBA':
                    canvas.paste(logo_img, (logo_x, logo_y), logo_img)
                else:
                    canvas.paste(logo_img, (logo_x, logo_y))
    
    def _draw_left_vertical_text(self, draw: ImageDraw.Draw, text: str):
        """绘制左侧竖排文字"""
        font = self._load_font(22, bold=True)
        
        # 只取前6个字
        chars = list(text[:6])
        y = 100
        
        for char in chars:
            if char not in [' ', '\n']:
                # 白色文字 + 黑色描边
                draw.text((30, y), char, font=font, fill='white', stroke_width=2, stroke_fill='black')
                y += 30
            else:
                y += 15
    
    def _draw_center_badge(self, draw: ImageDraw.Draw, text: str):
        """绘制中心粉色徽章"""
        font = self._load_font(48, bold=True)
        
        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        padding_x = 30
        padding_y = 20
        badge_width = text_width + padding_x * 2
        badge_height = text_height + padding_y * 2
        
        badge_x = (self.canvas_width - badge_width) // 2
        badge_y = self.canvas_height // 2 - 100
        
        # 绘制粉色圆角矩形
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=15,
            fill='#ff1493',
            outline='white',
            width=4
        )
        
        # 绘制文字（居中）
        text_x = self.canvas_width // 2
        text_y = badge_y + badge_height // 2
        draw.text((text_x, text_y), text, font=font, fill='white', anchor='mm')
    
    def _draw_episode_count(self, draw: ImageDraw.Draw, count: str):
        """绘制集数"""
        font = self._load_font(80, bold=True)
        text = f"全{count}集"
        
        # 白色文字 + 黑色描边
        draw.text(
            (self.canvas_width // 2, self.canvas_height - 280),
            text,
            font=font,
            fill='white',
            anchor='mm',
            stroke_width=3,
            stroke_fill='black'
        )
    
    def _draw_bottom_bar(self, draw: ImageDraw.Draw):
        """绘制底部三色条"""
        bottom_height = int(self.canvas_height * 0.2)
        bottom_y = self.canvas_height - bottom_height
        third_width = self.canvas_width // 3
        
        # 蓝色 - 黄色 - 蓝色
        draw.rectangle([(0, bottom_y), (third_width, self.canvas_height)], fill='#1e3a8a')
        draw.rectangle([(third_width, bottom_y), (third_width * 2, self.canvas_height)], fill='#fbbf24')
        draw.rectangle([(third_width * 2, bottom_y), (self.canvas_width, self.canvas_height)], fill='#1e3a8a')
        
        # 文字大小
        font_size = int(self.canvas_height * 0.037)
        font = self._load_font(font_size, bold=True)
        
        # 左侧文字（国语 / 中字）
        draw.text(
            (third_width // 2, bottom_y + int(bottom_height * 0.37)),
            "国语",
            font=font,
            fill='white',
            anchor='mm'
        )
        draw.text(
            (third_width // 2, bottom_y + int(bottom_height * 0.63)),
            "中字",
            font=font,
            fill='white',
            anchor='mm'
        )
        
        # 右侧文字（蓝光 / 画质）
        draw.text(
            (third_width * 2 + third_width // 2, bottom_y + int(bottom_height * 0.37)),
            "蓝光",
            font=font,
            fill='white',
            anchor='mm'
        )
        draw.text(
            (third_width * 2 + third_width // 2, bottom_y + int(bottom_height * 0.63)),
            "画质",
            font=font,
            fill='white',
            anchor='mm'
        )
        
        # 中间4K ULTRA HD
        font_4k = self._load_font(int(self.canvas_height * 0.08), bold=True)
        draw.text(
            (third_width + third_width // 2, bottom_y + int(bottom_height * 0.43)),
            '4K',
            font=font_4k,
            fill='white',
            anchor='mm'
        )
        
        font_ultra = self._load_font(int(self.canvas_height * 0.037), bold=True)
        draw.text(
            (third_width + third_width // 2, bottom_y + int(bottom_height * 0.7)),
            'ULTRA HD',
            font=font_ultra,
            fill='black',
            anchor='mm'
        )
