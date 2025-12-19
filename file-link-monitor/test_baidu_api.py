"""
测试百度网盘API - 验证搜索+创建分享链接逻辑
"""
import requests
from urllib.parse import quote
import json

BAIDU_COOKIE = """
BAIDUID=29F8A9F9ED335ED512B1471B22CE89E0:FG=1; BAIDUID_BFESS=29F8A9F9ED335ED512B1471B22CE89E0:FG=1; PANWEB=1; BIDUPSID=29F8A9F9ED335ED512B1471B22CE89E0; PSTM=1764809630; H_PS_PSSID=60271_63145_65314_66118_66216_66191_66196_66165_66280_66268_66393_66515_66529_66558_66584_66578_66590_66601_66605_66641_66647_66663_66676_66686_66689_66720_66745_66754_66784_66793_66803_66802_66599; ZFY=jfLIkUHeox9wwLBVmHHhvN1hAM0:BomG7j0Uug30AXB8:C; newlogin=1; ploganondeg=1; csrfToken=PW8iEzTufit-4GtCTeSUQhtJ; ppfuid=FOCoIC3q5fKa8fgJnwzbE0LGziLN3VHbX8wfShDP6RCsfXQp/69CStRUAcn/QmhIlFDxPrAc/s5tJmCocrihdwitHd04Lvs3Nfz26Zt2holplnIKVacidp8Sue4dMTyfg65BJnOFhn1HthtSiwtygiD7piS4vjG/W9dLb1VAdqPDGlvl3S9CENy8XO0gBHvcO0V6uxgO+hV7+7wZFfXG0MSpuMmh7GsZ4C7fF/kTgmt3jpj+McMorhe+Cj/9lStSBwMLYHXX6sSySAfDc47AfQqYgheSYkz7BDnJkD5v5D41v2iwj13daM+9aWJ5GJCQM+RpBohGNhMcqCHhVhtXpVObaDCHgWJZH3ZrTGYHmi7XJB9z3y2o8Kqxep5XBCsuFKJEamDWP0B99HzIVbHvrePooLbKBIKSSHTndNj5TmhzHi2LCZ2gO1+19qyTSEpAFeLs4wygIv6m069lhsdmzQ+ReezgAmT3lwuMU1qOVEPQFXV1C8qyUqcAnBm7hcJuxcqfdReixTVTfT+miI3ZV5eQE96jz5eP/gEigLYjtZnrOQVr9TB3lK8L3WS99/Zr9ng7DJNA0zsRL0eZGEKF1aDRInbESzVqJcCK3XpGJOV/zZ6wkf5f+PnYbtHcSvBB4lPdCgO/rhHbvTb7w1sYiN/Vk5/GFQKmYmpXiN4dJoe04sIEztQcQ/Sj8aeZwWg0mAteMeU9qyn6SoJvv6345Qt76XFBJWSgbZ6/F0ZRwCDo0NPL3fh6V0Qf84X0lHCGDVE6dnYotaYeW3myaaKjCupBJR/TSirmjBV2s3jnlQqvo9oPyP0nG9iKj3wRQUwzcav1VQU9Nb3SpOs6OnNPHvOBRFTC3dJt11rYxTmLu8GIDQxqMKltDwwpum3Juw8bhBgKsG2JlL29AEHRUoKNa0CrXiJwBTbsQ97ckDDWTffZfhpcog1PhEwkcbrqGW8fYF5mPl3xfYG6Tu9VE0I+fw7vVtkGN3nMKm3rd2mDkhNuquWLv5kuJDMwwerkeHUP9Bq7zt2A9A8E851l8QtBoQFIuWEGY3DMQGzE4fLtBnD2IBA1xgIrbF95h/aKYBNVXdvBhoLwXhcnXaiqXEpcvFQlonIv85FfaVbfEoKujQX2IBA1xgIrbF95h/aKYBNVh6Y0NjEKZ13xldTgKDiG2QRBJFTPsviSSEvgLGRO3YgGOv+/I3nwGp9q5hLF8/07goRUnieOy9WY3CCu1FKQrXv4Kl2tvhm/51VQHSSoTtFbHhSGlEKo+S0ciyUHoRYU; XFI=99cd36e0-dc76-11f0-836f-29e902b45a37; XFCS=E98094733FFB5868BE72F6A9FFFC911E55E9B82D806F45A4F13B36208220DD2E; XFT=ghEH7uQwcUv4NxEodQAAhBTv723Np9gUODUb7MjX8aI=; BDUSS=g0eHg3cE9MS2JPaEF-bm5Fc2Z0dm12YThFSERVYlRJbjktdVVrcDF3eXdNV3hwSVFBQUFBJCQAAAAAAQAAAAEAAABfSCmdvKvL2bj80MLXytS0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCkRGmwpERpd2; BDUSS_BFESS=g0eHg3cE9MS2JPaEF-bm5Fc2Z0dm12YThFSERVYlRJbjktdVVrcDF3eXdNV3hwSVFBQUFBJCQAAAAAAQAAAAEAAABfSCmdvKvL2bj80MLXytS0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCkRGmwpERpd2; STOKEN=80ae0f23fc60d90df511dc0a9c250a0c14f666f3b393a4131cfcabf1df38f005; BDCLND=rhiZ6qFTgMKn5sPss1%2BUBXQZdUn8znJ5cGwDM0C3vMY%3D; ndut_fmt=C30BDF417529EF017643AEC0C290553FD53BDFEC2F00D6EE88A53062D13C0453; ab_sr=1.0.1_YzY0ZTIxZTYxNTJjNjAyYjY4Y2I3MWJiNzYxMWE4NmU5Yjg1M2QzOWE1NmJmMGRkZGU2ZWViNWU2MmMzYWFmMDVlZWQ1M2M4ZWVjNzgzZTE3OWM2OGNkYmE5MDQwN2M4MDJiODVhZDFmM2Y4N2JjMjk5MDEyY2ViMTc0NGUwMWViYjM4ZmFhY2ZkMTE5ZTc0ZGRmM2E1M2E3MzM4MGI2NGI4YmVhOTkzMTIzMzExOWQ1YzQwOTc5YmYyODNjZGU2; PANPSC=10799957046963188896%3Au9Rut0jYI4ocyrHrO%2FcAv1cS2d9ns3O5C61tf8CKQkgw19TaLWf8SQXQ225L75l2wGQB7ARhquAd%2Bd6J43yXeQjn4HR56deP8oEHn5ZIJOmpKicp4leI%2Ft8WDKjdwpGvW1XX9xnmeNltcQe%2BbgwEaXWegKR%2ByMKcWP%2FWBC2ONxfgK8WiEYvObjEIKJQ%2BkRn2uPZxTPIZzXRtoLnfYC42LfDSJFbrrClxWDN81yfxsC8zfNvvSokn3AT5bdufxZCm5tFeRaakq8za51hMEGV028YD9Uwr9LAJ%2FCobuSJW7IR1Gv5h8iKvzz1o2HyqHDuYyCkP%2FabYFNrQJPTuxHgNcTp6OPEZDW9bd5ua1qgFiHY%3D
"""

def parse_cookie(cookie_string):
    """解析Cookie字符串为字典"""
    cookies = {}
    for item in cookie_string.strip().replace('\n', '').split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            cookies[key] = value
    return cookies

def search_file(filename, cookies):
    """搜索文件获取fs_id"""
    url = "https://pan.baidu.com/api/search"
    params = {
        'clienttype': 0,
        'app_id': 250528,
        'web': 1,
        'order': 'name',
        'desc': 0,
        'num': 100,
        'page': 1,
        'recursion': 1,
        'key': filename
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://pan.baidu.com/disk/main',
        'Accept': 'application/json, text/plain, */*',
    }
    
    print(f"🔍 搜索文件: {filename}")
    response = requests.get(url, params=params, cookies=cookies, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    data = response.json()
    print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    if data['errno'] != 0:
        raise Exception(f"搜索失败: errno={data['errno']}")
    
    # 精确匹配文件夹
    for item in data.get('list', []):
        if item['server_filename'] == filename and item['isdir'] == 1:
            print(f"✅ 找到文件夹: {item['server_filename']}")
            print(f"   fs_id: {item['fs_id']}")
            print(f"   path: {item['path']}")
            return item['fs_id']
    
    raise Exception(f"未找到文件夹: {filename}")

def get_bdstoken(cookies):
    """从Cookie中提取bdstoken"""
    # 方案1: 直接从Cookie中获取
    if 'csrfToken' in cookies:
        return cookies['csrfToken']
    if 'bdstoken' in cookies:
        return cookies['bdstoken']
    
    # 方案2: 从网盘首页提取（如果Cookie中没有）
    print("⚠️  Cookie中未找到bdstoken，尝试从页面提取...")
    url = "https://pan.baidu.com/disk/main"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    response = requests.get(url, cookies=cookies, headers=headers)
    
    # 从页面HTML中查找 window.yunData.bdstoken
    import re
    match = re.search(r'bdstoken["\']?\s*:\s*["\']([^"\']+)', response.text)
    if match:
        bdstoken = match.group(1)
        print(f"   从页面提取到bdstoken: {bdstoken}")
        return bdstoken
    
    raise Exception("无法获取bdstoken")

def create_share_link(fs_id, cookies, bdstoken, pwd='yyds', period=0):
    """创建分享链接"""
    url = "https://pan.baidu.com/share/pset"
    params = {
        'channel': 'chunlei',
        'bdstoken': bdstoken,
        'clienttype': 0,
        'app_id': 250528,
        'web': 1,
    }
    
    data = {
        'is_knowledge': 0,
        'public': 0,
        'period': period,  # 0=永久
        'pwd': pwd,
        'eflag_disable': 'true',
        'linkOrQrcode': 'link',
        'channel_list': '[]',
        'schannel': 4,
        'fid_list': f'[{fs_id}]'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://pan.baidu.com/disk/main',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json, text/plain, */*',
    }
    
    print(f"📤 创建分享链接...")
    print(f"   fs_id: {fs_id}")
    print(f"   提取码: {pwd}")
    
    response = requests.post(url, params=params, data=data, cookies=cookies, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    result = response.json()
    print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result['errno'] != 0:
        raise Exception(f"创建分享链接失败: errno={result['errno']}")
    
    link = result['link']
    print(f"✅ 分享链接创建成功!")
    print(f"   链接: {link}")
    print(f"   提取码: {pwd}")
    
    return f"{link}?pwd={pwd} 提取码: {pwd}"

def main():
    """主测试流程"""
    print("=" * 60)
    print("百度网盘API测试")
    print("=" * 60)
    
    # 测试文件名（从接口文档中的例子）
    test_filename = "731： 胜华气市路"
    
    try:
        # 1. 解析Cookie
        cookies = parse_cookie(BAIDU_COOKIE)
        print(f"\n📝 Cookie解析完成，包含 {len(cookies)} 个字段")
        
        # 2. 搜索文件获取fs_id
        print("\n" + "=" * 60)
        fs_id = search_file(test_filename, cookies)
        
        # 3. 获取bdstoken
        print("\n" + "=" * 60)
        print("🔑 获取bdstoken...")
        bdstoken = get_bdstoken(cookies)
        print(f"   bdstoken: {bdstoken}")
        
        # 4. 创建分享链接
        print("\n" + "=" * 60)
        share_link = create_share_link(fs_id, cookies, bdstoken)
        
        # 5. 输出结果
        print("\n" + "=" * 60)
        print("🎉 测试成功!")
        print(f"完整分享链接: {share_link}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
