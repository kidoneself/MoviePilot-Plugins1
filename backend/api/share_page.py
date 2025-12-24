"""
短链接分享页面API
"""
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend.models import CustomNameMapping, get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/s/{mapping_id}", response_class=HTMLResponse)
async def share_page(mapping_id: int, request: Request, db: Session = Depends(get_db)):
    """
    短链接分享页面
    
    Args:
        mapping_id: 映射ID
    """
    try:
        # 查询映射
        mapping = db.query(CustomNameMapping).filter(
            CustomNameMapping.id == mapping_id
        ).first()
        
        if not mapping:
            return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>剧集不存在</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>😔 剧集不存在</h1>
        <p>链接可能已失效</p>
    </div>
</body>
</html>
"""
        
        # 构建HTML页面
        status_emoji = "✅ 完结" if mapping.is_completed else "📺 更新中"
        
        links_html = ""
        if mapping.quark_link:
            links_html += f"""
            <div class="link-item">
                <div class="link-icon">🟡</div>
                <div class="link-content">
                    <div class="link-title">夸克网盘</div>
                    <div class="link-url">{mapping.quark_link}</div>
                    <button class="copy-btn" onclick="copyLink('{mapping.quark_link}', this)">📋 复制链接</button>
                </div>
            </div>
            """
        
        if mapping.baidu_link:
            links_html += f"""
            <div class="link-item">
                <div class="link-icon">🔵</div>
                <div class="link-content">
                    <div class="link-title">百度网盘</div>
                    <div class="link-url">{mapping.baidu_link}</div>
                    <button class="copy-btn" onclick="copyLink('{mapping.baidu_link}', this)">📋 复制链接</button>
                </div>
            </div>
            """
        
        if mapping.xunlei_link:
            links_html += f"""
            <div class="link-item">
                <div class="link-icon">🔴</div>
                <div class="link-content">
                    <div class="link-title">迅雷网盘</div>
                    <div class="link-url">{mapping.xunlei_link}</div>
                    <button class="copy-btn" onclick="copyLink('{mapping.xunlei_link}', this)">📋 复制链接</button>
                </div>
            </div>
            """
        
        if not links_html:
            links_html = "<div class='no-links'>😔 暂无分享链接</div>"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{mapping.original_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .title {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .status {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 20px;
        }}
        .link-item {{
            display: flex;
            align-items: flex-start;
            padding: 20px;
            margin-bottom: 16px;
            background: #f7f9fc;
            border-radius: 12px;
            transition: all 0.3s;
        }}
        .link-item:hover {{
            background: #eef2f7;
            transform: translateY(-2px);
        }}
        .link-icon {{
            font-size: 32px;
            margin-right: 16px;
        }}
        .link-content {{
            flex: 1;
        }}
        .link-title {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }}
        .link-url {{
            font-size: 13px;
            color: #666;
            word-break: break-all;
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .copy-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
        }}
        .copy-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .copy-btn:active {{
            transform: scale(0.95);
        }}
        .copy-btn.copied {{
            background: #10b981;
        }}
        .no-links {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 16px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">📺 {mapping.original_name}</div>
            <div class="status">{status_emoji}</div>
        </div>
        <div class="content">
            {links_html}
        </div>
        <div class="footer">
            闲鱼影视 · 剧集分享
        </div>
    </div>
    
    <script>
        function copyLink(link, btn) {{
            navigator.clipboard.writeText(link).then(function() {{
                btn.textContent = '✅ 已复制';
                btn.classList.add('copied');
                setTimeout(function() {{
                    btn.textContent = '📋 复制链接';
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(function(err) {{
                alert('复制失败，请手动复制');
            }});
        }}
    </script>
</body>
</html>
"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"生成分享页面失败: {e}")
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>错误</title>
</head>
<body>
    <h1>错误</h1>
    <p>{str(e)}</p>
</body>
</html>
"""
