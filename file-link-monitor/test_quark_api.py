"""
夸克网盘API测试脚本
测试完整流程：搜索文件 → 创建分享 → 轮询任务 → 获取链接
"""
import requests
import json
import time
from urllib.parse import quote

# 夸克Cookie
QUARK_COOKIE = """
b-user-id=8656abfd-ab9d-6d6a-e38f-c1b761d1c8e5; __sdid=AATOnqv5W6hIVXme8f/9wDsDrZLUWIfJgO02GFCf1/tpXs3cQY2aX2LjYS/zRNuADlQ=; _UP_A4A_11_=wb9d01614d704b3cafca764183c46eba; __kps=AASN593sgdaQrTW/48UVrnOD; __ktd=r4AuCjAEcKjUxTlg5xJB1A==; __uid=AASN593sgdaQrTW/48UVrnOD; __pus=ac2712c15667902d0f3f6ce5a122cb14AARwAVc/Dvm9mk6cev7rxG7ra/IomTxYNEiRIKNWp7CWT7AxJ0RgZnAac+LCYKgTIgbCWhFmTqDL+rOL5DC2KaC3; __kp=1c058f40-d4de-11f0-86b1-c71b3f60f0b8; cs_xcustomer_switch_user_key=775393f9-c8e4-4769-b6fd-d21bd96303d8; kkpcwpea=qs_clear_res=1&a=a&uc_param_str=einibicppfmivefrlantcunwsssvjbktchnnsnddds&instance=kkpcwp&pf=145&self_service=true&plain_utdid=ZjnVno1H6aEDADkt9wvrZ9YM&system_ver=Darwin_26.0.1&channel_no=pckk%40other_ch&ve=3.23.2&sv=release; CwsSessionId=53010a9a-d797-4459-97e3-ebf42a05c8b8; xlly_s=1; __puus=6a62929f174e0614973df330331ff0f7AAT1PrfXNhk3Gxfuk1rMWgk8QKeT9mKduhwtcQkUJSVfjTvdxG7CbaoYHm8/WwIkCPjE1WbOVPHde0R6NojuBb10pYJLXZZRJOhp0Jsl+TiNnPGw+UGjAKftzSkkPgkJNTEAbHIn8PbJ/vCSC9UOdhHlxo49W4gpsp+0foQaJ+OUjGKs9wN0VhUGGPOXisx9TG+uaPhc40TsOub1wh1+5CQc; tfstk=gga-uF1rOsdR699ywJjcKjTB48fcBi0zayyW-e0nEiwxhW1rxWikR2FLUDaut4MQHJcZNufEdETK6JhQrT359wFQ1YTu-goBJxwpAp1yRKgbIXrhaTkClmwZPDroKYDKJWyOiObGS7Pr84XGINf1Ni-E7eGINpmXlf3KNFJ1r_Nr826DiesGW7yu5cYsV21xlXhid2tWVsnjOf3BPDTWcKMqO2gIFYNXlfGnd3iSAsFj3XgIdJgCMqMqO2MQd2GQRaMvOv8Lq7dk-yS55y4gkbn-CSIwJe1nNdDTNxLBRDh-2hNSHeTQlkMJ0EHOkKM0O5rIDyQDu2P0XJEQh6TIpoGTBf2llU3Qc-UtfSW9zYEbUy3obwdKMlFbezVAtneLh5rZPz6erYrQGyM0P6YKClVZkjzh3UMLckao42J5ejU86yEd4VzgW7NXIAhHVsCvYHoSg-05MImoenExMAf-FH-E0flxIsI9YHoSgjHGwTteYmlN.; isg=BAkJy27khPw5Tnh84JuC9T9QGDNjVv2INGQhX6t_hPAv8igE8qekWfdqMFbEkJXA
"""

def get_headers(cookie):
    """构造请求头"""
    return {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'cookie': cookie.strip(),
        'origin': 'https://pan.quark.cn',
        'referer': 'https://pan.quark.cn/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
    }


def search_file(filename, cookie):
    """
    步骤1: 搜索文件获取fid
    """
    print(f"\n{'='*60}")
    print(f"步骤1: 搜索文件 '{filename}'")
    print(f"{'='*60}")
    
    url = f"https://drive-pc.quark.cn/1/clouddrive/file/search"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
        'q': filename,
        '_page': 1,
        '_size': 50,
        '_fetch_total': 1,
        '_sort': 'file_type:desc,updated_at:desc',
        '_is_hl': 1
    }
    
    headers = get_headers(cookie)
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"请求URL: {response.url}")
        print(f"响应状态码: {response.status_code}")
        
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 检查响应
        if data.get('code') != 0:
            print(f"❌ 搜索失败: {data.get('message')}")
            return None
        
        # 获取文件列表
        files = data.get('data', {}).get('list', [])
        if not files:
            print(f"❌ 未找到文件")
            return None
        
        # 精确匹配文件名（文件夹）
        for file in files:
            if file.get('file_name') == filename and file.get('dir', False):
                fid = file.get('fid')
                print(f"✅ 找到文件夹: {filename}")
                print(f"   fid: {fid}")
                return fid
        
        print(f"❌ 未找到完全匹配的文件夹")
        return None
        
    except Exception as e:
        print(f"❌ 搜索异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_share(fid, title, cookie):
    """
    步骤2: 创建分享（异步）
    """
    print(f"\n{'='*60}")
    print(f"步骤2: 创建分享任务")
    print(f"{'='*60}")
    
    url = "https://drive-pc.quark.cn/1/clouddrive/share"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    
    payload = {
        'fid_list': [fid],
        'title': title,
        'url_type': 1,
        'expired_type': 1
    }
    
    headers = get_headers(cookie)
    
    try:
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
        print(f"请求URL: {response.url}")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}")
        print(f"响应状态码: {response.status_code}")
        
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 检查响应
        if data.get('code') != 0:
            print(f"❌ 创建分享失败: {data.get('message')}")
            return None
        
        # 获取task_id
        task_id = data.get('data', {}).get('task_id')
        if not task_id:
            print(f"❌ 响应中没有task_id")
            return None
        
        print(f"✅ 分享任务已创建")
        print(f"   task_id: {task_id}")
        return task_id
        
    except Exception as e:
        print(f"❌ 创建分享异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def poll_task(task_id, cookie, max_retry=20, interval=0.5):
    """
    步骤3: 轮询任务状态获取share_id
    """
    print(f"\n{'='*60}")
    print(f"步骤3: 轮询任务状态 (最多{max_retry}次，间隔{interval}秒)")
    print(f"{'='*60}")
    
    url = "https://drive-pc.quark.cn/1/clouddrive/task"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': '',
        'task_id': task_id,
        'retry_index': 0
    }
    
    headers = get_headers(cookie)
    
    for i in range(max_retry):
        try:
            print(f"\n第 {i+1}/{max_retry} 次查询...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"❌ 查询失败: {data.get('message')}")
                return None
            
            task_data = data.get('data', {})
            status = task_data.get('status')
            
            print(f"   状态: {status} (2=已完成)")
            
            # 状态2表示完成
            if status == 2:
                share_id = task_data.get('share_id')
                if share_id:
                    print(f"✅ 任务完成！")
                    print(f"   share_id: {share_id}")
                    print(f"   完整响应: {json.dumps(task_data, ensure_ascii=False, indent=2)}")
                    return share_id
                else:
                    print(f"❌ 任务完成但没有share_id")
                    return None
            
            # 等待后继续
            time.sleep(interval)
            
        except Exception as e:
            print(f"❌ 轮询异常: {e}")
            time.sleep(interval)
            continue
    
    print(f"❌ 超过最大重试次数，任务仍未完成")
    return None


def get_share_link(share_id, cookie):
    """
    步骤4: 获取分享链接
    """
    print(f"\n{'='*60}")
    print(f"步骤4: 获取分享链接")
    print(f"{'='*60}")
    
    url = "https://drive-pc.quark.cn/1/clouddrive/share/password"
    params = {
        'pr': 'ucpro',
        'fr': 'pc',
        'uc_param_str': ''
    }
    
    payload = {
        'share_id': share_id
    }
    
    headers = get_headers(cookie)
    
    try:
        response = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
        print(f"请求URL: {response.url}")
        print(f"请求体: {json.dumps(payload, ensure_ascii=False)}")
        print(f"响应状态码: {response.status_code}")
        
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 检查响应
        if data.get('code') != 0:
            print(f"❌ 获取链接失败: {data.get('message')}")
            return None
        
        # 提取链接信息
        share_data = data.get('data', {})
        share_url = share_data.get('share_url')
        passcode = share_data.get('passcode')
        
        if share_url:
            if passcode:
                full_link = f"{share_url} 提取码: {passcode}"
            else:
                full_link = share_url
            
            print(f"✅ 分享链接获取成功！")
            print(f"   链接: {share_url}")
            if passcode:
                print(f"   提取码: {passcode}")
            print(f"   完整: {full_link}")
            return full_link
        else:
            print(f"❌ 响应中没有链接")
            return None
        
    except Exception as e:
        print(f"❌ 获取链接异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_quark_api():
    """测试完整流程"""
    print("\n" + "="*60)
    print("夸克网盘API测试 - 完整流程")
    print("="*60)
    
    # 测试参数
    test_filename = "姥姥姥姥"
    cookie = QUARK_COOKIE.strip()
    
    print(f"\n测试文件: {test_filename}")
    print(f"Cookie长度: {len(cookie)}")
    
    # 步骤1: 搜索文件
    fid = search_file(test_filename, cookie)
    if not fid:
        print(f"\n❌ 测试失败：无法找到文件")
        return
    
    # 步骤2: 创建分享任务
    task_id = create_share(fid, test_filename, cookie)
    if not task_id:
        print(f"\n❌ 测试失败：无法创建分享任务")
        return
    
    # 步骤3: 轮询任务状态
    share_id = poll_task(task_id, cookie)
    if not share_id:
        print(f"\n❌ 测试失败：无法获取share_id")
        return
    
    # 步骤4: 获取分享链接
    share_link = get_share_link(share_id, cookie)
    if not share_link:
        print(f"\n❌ 测试失败：无法获取分享链接")
        return
    
    # 成功
    print(f"\n" + "="*60)
    print(f"✅ 测试成功！完整流程执行完毕")
    print(f"="*60)
    print(f"最终链接: {share_link}")


if __name__ == '__main__':
    test_quark_api()
