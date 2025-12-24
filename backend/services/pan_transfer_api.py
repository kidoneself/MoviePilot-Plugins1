#!/usr/bin/env python3
"""
三网盘统一转存API
支持百度、夸克、迅雷网盘的分享链接转存
"""
import re
import time
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote


class PanTransferAPI:
    """网盘转存统一接口"""
    
    def __init__(self, pan_type: str, credentials: Dict):
        """
        初始化
        
        Args:
            pan_type: 网盘类型 ('baidu', 'quark', 'xunlei')
            credentials: 认证信息
                - baidu: {'cookie': str}
                - quark: {'cookie': str}
                - xunlei: {'authorization': str, 'x_captcha_token': str, 
                          'x_client_id': str, 'x_device_id': str}
        """
        self.pan_type = pan_type.lower()
        self.credentials = credentials
        
        if self.pan_type not in ['baidu', 'quark', 'xunlei']:
            raise ValueError(f"不支持的网盘类型: {pan_type}")
    
    def transfer(self, share_url: str, pass_code: Optional[str], 
                target_path: str) -> Dict:
        """
        统一转存接口
        
        Args:
            share_url: 分享链接
            pass_code: 提取码（可选）
            target_path: 目标路径
                - baidu: 完整路径，如 "/电影/华语/钢铁侠3"
                - quark: 文件夹ID，如 "a0c40531ee21425aa884e134e53ef6a8"
                - xunlei: 文件夹ID，如 "VOgzQy9ZbNnxrTD95FYf29WGA1"，空字符串表示根目录
        
        Returns:
            统一格式的结果：
            {
                'success': bool,
                'pan_type': str,
                'file_count': int,
                'file_ids': List[str],
                'message': str,
                'details': Dict  # 网盘特定的详细信息
            }
        """
        if self.pan_type == 'baidu':
            return self._transfer_baidu(share_url, pass_code, target_path)
        elif self.pan_type == 'quark':
            return self._transfer_quark(share_url, pass_code, target_path)
        elif self.pan_type == 'xunlei':
            return self._transfer_xunlei(share_url, pass_code, target_path)
    
    # ============ 百度网盘 ============
    
    def _transfer_baidu(self, share_url: str, pass_code: Optional[str], 
                       target_path: str) -> Dict:
        """百度网盘转存"""
        try:
            # 1. 解析分享链接
            shorturl = self._parse_baidu_url(share_url)
            
            # 2. 创建Session并获取bdstoken和sekey（都在同一个session中）
            sekey, session, bdstoken = self._verify_baidu_code_with_session(shorturl, pass_code)
            
            # 3. 获取文件列表（使用同一个session）
            share_id, uk, fs_ids = self._get_baidu_file_list(shorturl, bdstoken, session)
            
            # 5. 转存
            task_id = self._baidu_transfer(
                share_id, uk, fs_ids, target_path, sekey, bdstoken
            )
            
            # 6. 如果是异步任务，轮询
            if task_id != 0:
                self._poll_baidu_task(task_id)
            
            return {
                'success': True,
                'pan_type': 'baidu',
                'file_count': len(fs_ids),
                'file_ids': [str(fid) for fid in fs_ids],
                'message': '转存成功',
                'details': {
                    'task_id': task_id,
                    'target_path': target_path
                }
            }
        except Exception as e:
            return {
                'success': False,
                'pan_type': 'baidu',
                'file_count': 0,
                'file_ids': [],
                'message': f'转存失败: {str(e)}',
                'details': {}
            }
    
    def _parse_baidu_url(self, share_url: str) -> str:
        """解析百度分享链接"""
        match = re.search(r'/s/1([a-zA-Z0-9_-]+)', share_url)
        if not match:
            raise Exception("无效的百度分享链接")
        return match.group(1)
    
    def _verify_baidu_code_with_session(self, shorturl: str, pass_code: Optional[str]) -> Tuple[str, requests.Session, str]:
        """创建session，获取bdstoken，验证提取码，返回sekey、session和bdstoken"""
        # 创建Session保持Cookie状态
        session = requests.Session()
        
        # 设置Cookie
        cookies = self._parse_baidu_cookie()
        session.cookies.update(cookies)
        
        # 清除可能存在的旧BDCLND
        if 'BDCLND' in session.cookies:
            del session.cookies['BDCLND']
        
        # 1. 在session中获取bdstoken
        bds_url = "https://pan.baidu.com/disk/main"
        bds_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = session.get(bds_url, headers=bds_headers)
        
        patterns = [
            r'"bdstoken"\s*:\s*"([^"]+)"',
            r'bdstoken\s*:\s*"([^"]+)"',
            r'bdstoken=([a-f0-9]+)'
        ]
        
        bdstoken = None
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                bdstoken = match.group(1)
                break
        
        if not bdstoken:
            raise Exception("无法提取 bdstoken")
        
        # 2. 验证提取码
        verify_url = "https://pan.baidu.com/share/verify"
        verify_params = {
            'surl': shorturl,
            'channel': 'chunlei',
            'web': '1',
            'app_id': '250528',
            'clienttype': '0'
        }
        verify_data = {'pwd': pass_code} if pass_code else {}
        
        verify_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://pan.baidu.com',
            'Referer': f'https://pan.baidu.com/s/1{shorturl}'
        }
        
        verify_response = session.post(verify_url, params=verify_params, data=verify_data, headers=verify_headers)
        verify_result = verify_response.json()
        
        if verify_result.get('errno') != 0:
            raise Exception(f"验证提取码失败: {verify_result.get('show_msg', 'Unknown error')}")
        
        # 从session.cookies中获取BDCLND
        sekey = None
        for cookie in session.cookies:
            if cookie.name == 'BDCLND':
                sekey = unquote(cookie.value)
                break
        
        if not sekey:
            raise Exception("未获取到 sekey (BDCLND Cookie)")
        
        return sekey, session, bdstoken
    
    def _get_baidu_file_list(self, shorturl: str, bdstoken: str, session: requests.Session) -> Tuple[str, str, List[int]]:
        """获取百度文件列表，使用session保持Cookie状态"""
        url = "https://pan.baidu.com/share/list"
        params = {
            'shorturl': shorturl,
            'root': 1,
            'page': 1,
            'num': 1000,
            'web': 1,
            'channel': 'chunlei',
            'clienttype': 0,
            'showempty': 0,
            'bdstoken': bdstoken,
            'order': 'time',
            'app_id': '250528'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': f'https://pan.baidu.com/s/1{shorturl}'
        }
        
        # 使用同一个session，会自动带上验证时的BDCLND Cookie
        response = session.get(url, params=params, headers=headers)
        result = response.json()
        
        # 记录响应到日志文件
        import json
        import os
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'baidu_list_{shorturl}.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  [DEBUG] 百度文件列表响应已保存到: {log_file}")
        
        if result.get('errno') != 0:
            raise Exception(f"获取文件列表失败: {result}")
        
        share_id = result.get('share_id')
        uk = result.get('uk')
        file_list = result.get('list', [])
        
        # 如果只有一个文件夹，获取文件夹内容
        if len(file_list) == 1 and str(file_list[0].get('isdir')) == '1':
            folder_path = file_list[0]['path']
            params['dir'] = folder_path
            params['root'] = 0  # 非根目录
            response = session.get(url, params=params, headers=headers)
            result = response.json()
            
            # 记录文件夹内容响应
            log_file2 = os.path.join(log_dir, f'baidu_folder_{shorturl}.json')
            with open(log_file2, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  [DEBUG] 百度文件夹内容响应已保存到: {log_file2}")
            
            file_list = result.get('list', [])
        
        fs_ids = [int(f['fs_id']) for f in file_list]
        return share_id, uk, fs_ids
    
    def _get_bdstoken(self) -> str:
        """获取百度 bdstoken"""
        url = "https://pan.baidu.com/disk/main"
        cookies = self._parse_baidu_cookie()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, cookies=cookies, headers=headers)
        
        patterns = [
            r'"bdstoken"\s*:\s*"([^"]+)"',
            r'bdstoken\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                return match.group(1)
        
        raise Exception("无法提取 bdstoken")
    
    def _baidu_transfer(self, share_id: str, uk: str, fs_ids: List[int],
                       target_path: str, sekey: str, bdstoken: str) -> int:
        """百度转存"""
        # 去掉OpenList路径前缀 /baidu/
        if target_path.startswith('/baidu/'):
            target_path = target_path[6:]  # 去掉 /baidu
        
        url = "https://pan.baidu.com/share/transfer"
        params = {
            'shareid': share_id,
            'from': uk,
            'sekey': sekey,
            'ondup': 'newcopy',
            'async': 1,
            'channel': 'chunlei',
            'web': 1,
            'app_id': '250528',
            'bdstoken': bdstoken,
            'clienttype': 0
        }
        
        data = {
            'fsidlist': f'[{",".join(map(str, fs_ids))}]',
            'path': target_path
        }
        
        cookies = self._parse_baidu_cookie()
        cookies['BDCLND'] = sekey
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://pan.baidu.com/'
        }
        
        response = requests.post(url, params=params, data=data, 
                               cookies=cookies, headers=headers)
        result = response.json()
        
        # errno=0: 成功
        # errno=4: 文件已存在（duplicated），也视为成功
        if result.get('errno') == 0:
            info = result.get('info', {})
            # 处理info可能是字典或列表的情况
            if isinstance(info, dict):
                return info.get('task_id', 0)
            else:
                # info是列表或其他类型，返回0表示同步完成
                return 0
        elif result.get('errno') == 4:
            # 文件已存在，视为成功，返回task_id=0（同步完成）
            return 0
        else:
            raise Exception(f"转存失败: {result}")
    
    def _poll_baidu_task(self, task_id: int):
        """轮询百度异步任务"""
        url = "https://pan.baidu.com/share/taskquery"
        cookies = self._parse_baidu_cookie()
        bdstoken = self._get_bdstoken()
        
        params = {'taskid': task_id, 'bdstoken': bdstoken}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        for _ in range(60):
            time.sleep(0.5)
            response = requests.get(url, params=params, cookies=cookies, headers=headers)
            result = response.json()
            
            if result.get('errno') != 0:
                raise Exception(f"查询任务失败: {result}")
            
            status = result.get('status')
            if status == 'success':
                return
            elif status == 'failed':
                raise Exception("转存任务失败")
    
    def _parse_baidu_cookie(self) -> Dict:
        """解析百度Cookie字符串为字典"""
        cookie_str = self.credentials.get('cookie', '')
        cookies = {}
        for item in cookie_str.split('; '):
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        return cookies
    
    # ============ 夸克网盘 ============
    
    def _transfer_quark(self, share_url: str, pass_code: Optional[str],
                       target_fid: str) -> Dict:
        """夸克网盘转存"""
        try:
            # 1. 解析分享链接
            pwd_id = self._parse_quark_url(share_url)
            
            # 2. 获取 stoken
            stoken = self._get_quark_stoken(pwd_id, pass_code)
            
            # 3. 获取文件列表
            pdir_fid, file_count = self._get_quark_file_list(pwd_id, stoken)
            
            # 4. 转存
            task_id = self._quark_transfer(pwd_id, stoken, pdir_fid, target_fid)
            
            # 5. 轮询任务
            result = self._poll_quark_task(task_id)
            
            return {
                'success': True,
                'pan_type': 'quark',
                'file_count': file_count,
                'file_ids': result.get('save_as', {}).get('save_as_top_fids', []),
                'message': '转存成功',
                'details': {
                    'task_id': task_id,
                    'target_fid': target_fid,
                    'save_as': result.get('save_as', {})
                }
            }
        except Exception as e:
            return {
                'success': False,
                'pan_type': 'quark',
                'file_count': 0,
                'file_ids': [],
                'message': f'转存失败: {str(e)}',
                'details': {}
            }
    
    def _parse_quark_url(self, share_url: str) -> str:
        """解析夸克分享链接"""
        match = re.search(r'/s/([a-zA-Z0-9]+)', share_url)
        if not match:
            raise Exception("无效的夸克分享链接")
        return match.group(1)
    
    def _get_quark_headers(self) -> Dict:
        """获取夸克请求头"""
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'cookie': self.credentials.get('cookie', ''),
            'origin': 'https://pan.quark.cn',
            'referer': 'https://pan.quark.cn/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def _get_quark_stoken(self, pwd_id: str, pass_code: Optional[str]) -> str:
        """获取夸克 stoken"""
        url = "https://drive-h.quark.cn/1/clouddrive/share/sharepage/token"
        data = {"pwd_id": pwd_id}
        if pass_code:
            data["passcode"] = pass_code
        
        response = requests.post(url, json=data, headers=self._get_quark_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"获取 stoken 失败: {result}")
        
        return result['data']['stoken']
    
    def _get_quark_file_list(self, pwd_id: str, stoken: str) -> Tuple[str, int]:
        """获取夸克文件列表"""
        url = "https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail"
        params = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1
        }
        
        response = requests.get(url, params=params, headers=self._get_quark_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"获取文件列表失败: {result}")
        
        metadata = result.get('metadata', {})
        pdir_fid = metadata.get('fid', metadata.get('_pdir_fid', '0'))
        file_count = metadata.get('_total', len(result.get('data', {}).get('list', [])))
        
        return pdir_fid, file_count
    
    def _quark_transfer(self, pwd_id: str, stoken: str, pdir_fid: str,
                       to_pdir_fid: str) -> str:
        """夸克转存"""
        url = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save"
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': ''}
        
        data = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": pdir_fid,
            "to_pdir_fid": to_pdir_fid,
            "pdir_save_all": True,
            "scene": "link"
        }
        
        response = requests.post(url, params=params, json=data, 
                               headers=self._get_quark_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"转存失败: {result}")
        
        return result['data']['task_id']
    
    def _poll_quark_task(self, task_id: str) -> Dict:
        """轮询夸克任务"""
        url = "https://drive-pc.quark.cn/1/clouddrive/task"
        
        for retry in range(120):
            time.sleep(0.5)
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': '',
                'task_id': task_id,
                'retry_index': retry
            }
            
            response = requests.get(url, params=params, headers=self._get_quark_headers())
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"查询任务失败: {result}")
            
            task_data = result.get('data', {})
            status = task_data.get('status')
            
            if status == 2:  # 成功
                return task_data
            elif status == 1:  # 失败
                raise Exception("转存任务失败")
        
        raise Exception("任务超时")
    
    # ============ 迅雷网盘 ============
    
    def _transfer_xunlei(self, share_url: str, pass_code: Optional[str],
                        target_folder_id: str) -> Dict:
        """迅雷网盘转存"""
        try:
            # 1. 解析分享链接
            share_id = self._parse_xunlei_url(share_url)
            
            # 2. 验证提取码，获取文件列表
            pass_code_token, file_ids, file_count = self._verify_xunlei_code(
                share_id, pass_code
            )
            
            # 3. 转存
            task_id = self._xunlei_transfer(
                share_id, pass_code_token, file_ids, target_folder_id
            )
            
            # 4. 轮询任务
            self._poll_xunlei_task(task_id)
            
            return {
                'success': True,
                'pan_type': 'xunlei',
                'file_count': file_count,
                'file_ids': file_ids,
                'message': '转存成功',
                'details': {
                    'task_id': task_id,
                    'target_folder_id': target_folder_id
                }
            }
        except Exception as e:
            return {
                'success': False,
                'pan_type': 'xunlei',
                'file_count': 0,
                'file_ids': [],
                'message': f'转存失败: {str(e)}',
                'details': {}
            }
    
    def _parse_xunlei_url(self, share_url: str) -> str:
        """解析迅雷分享链接"""
        # 清理URL末尾的#符号
        share_url = share_url.rstrip('#')
        match = re.search(r'/s/([^?#]+)', share_url)
        if not match:
            raise Exception("无效的迅雷分享链接")
        return match.group(1)
    
    def _get_xunlei_headers(self) -> Dict:
        """获取迅雷请求头"""
        return {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
            'authorization': self.credentials.get('authorization', ''),
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://pan.xunlei.com',
            'referer': 'https://pan.xunlei.com/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'x-captcha-token': self.credentials.get('x_captcha_token', ''),
            'x-client-id': self.credentials.get('x_client_id', ''),
            'x-device-id': self.credentials.get('x_device_id', '')
        }
    
    def _verify_xunlei_code(self, share_id: str, pass_code: Optional[str]) -> Tuple[str, List[str], int]:
        """验证迅雷提取码并获取文件列表"""
        url = "https://api-pan.xunlei.com/drive/v1/share"
        params = {
            "share_id": share_id,
            "pass_code": pass_code or "",
            "limit": 100,
            "thumbnail_size": "SIZE_SMALL"
        }
        
        response = requests.get(url, params=params, headers=self._get_xunlei_headers())
        result = response.json()
        
        if result.get('share_status') != 'OK':
            raise Exception(f"验证提取码失败: {result}")
        
        pass_code_token = result['pass_code_token']
        file_list = result.get('files', [])
        
        # 如果是文件夹，获取内部文件列表
        if len(file_list) == 1 and file_list[0].get('kind') == 'drive#folder':
            folder_id = file_list[0]['id']
            detail_url = "https://api-pan.xunlei.com/drive/v1/share/detail"
            detail_params = {
                "share_id": share_id,
                "parent_id": folder_id,
                "pass_code_token": pass_code_token,
                "limit": 100,
                "thumbnail_size": "SIZE_SMALL"
            }
            
            detail_resp = requests.get(detail_url, params=detail_params, 
                                      headers=self._get_xunlei_headers())
            detail_result = detail_resp.json()
            
            if detail_result.get('share_status') != 'OK':
                raise Exception(f"获取文件夹内容失败: {detail_result}")
            
            file_list = detail_result.get('files', [])
        
        file_ids = [f['id'] for f in file_list]
        return pass_code_token, file_ids, len(file_ids)
    
    def _xunlei_transfer(self, share_id: str, pass_code_token: str,
                        file_ids: List[str], target_folder_id: str) -> str:
        """迅雷转存"""
        url = "https://api-pan.xunlei.com/drive/v1/share/restore"
        data = {
            "parent_id": target_folder_id,
            "share_id": share_id,
            "pass_code_token": pass_code_token,
            "ancestor_ids": [],
            "file_ids": file_ids,
            "specify_parent_id": True
        }
        
        response = requests.post(url, json=data, headers=self._get_xunlei_headers())
        result = response.json()
        
        if result.get('share_status') != 'OK':
            raise Exception(f"转存失败: {result}")
        
        return result.get('restore_task_id', '')
    
    def _poll_xunlei_task(self, task_id: str):
        """轮询迅雷任务"""
        url = f"https://api-pan.xunlei.com/drive/v1/tasks/{task_id}"
        
        for _ in range(60):
            time.sleep(1)
            
            response = requests.get(url, headers=self._get_xunlei_headers())
            result = response.json()
            
            phase = result.get('phase')
            
            if phase == 'PHASE_TYPE_COMPLETE':
                return
            elif phase == 'PHASE_TYPE_ERROR':
                raise Exception(f"转存失败: {result.get('message', 'Unknown error')}")
        
        raise Exception("任务超时")
