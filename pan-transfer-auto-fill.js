// ==UserScript==
// @name         网盘转存路径自动填充
// @namespace    moviepilot.pan.autofill
// @version      2.0
// @description  监听网盘转存对话框，自动填充映射路径
// @match        https://pan.baidu.com/s/*
// @match        https://pan.quark.cn/s/*
// @match        https://pan.xunlei.com/s/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @grant        unsafeWindow
// @run-at       document-start
// @connect      10.10.10.17
// @connect      drive-h.quark.cn
// @connect      drive-pc.quark.cn
// @connect      api-pan.xunlei.com
// ==/UserScript==

(function() {
    'use strict';
    
    const API_BASE = 'http://10.10.10.17:9889/api';
    let mappingsCache = null; // 缓存映射列表
    let xunleiCaptchaToken = ''; // 缓存迅雷captcha token
    let xunleiClientId = ''; // 缓存迅雷client id
    let xunleiDeviceId = ''; // 缓存迅雷device id
    let xunleiParentId = ''; // 缓存迅雷当前文件夹ID
    let xunleiAuthorization = ''; // 缓存迅雷authorization token
    let xunleiFilesCache = null; // 缓存迅雷文件列表
    let xunleiPassCodeToken = ''; // 缓存迅雷pass_code_token
    
    console.log('🎬 网盘转存路径自动填充脚本已启动');
    
    // 拦截迅雷API请求，获取captcha token
    if (location.hostname.includes('xunlei')) {
        console.log('🔧 启动迅雷API拦截器');
        
        // 注入页面脚本 - 劫持fetch来获取captcha token
        const script = document.createElement('script');
        script.textContent = `
            (function() {
                console.log('[注入脚本] 劫持Fetch获取参数和响应');
                
                const originalFetch = window.fetch;
                window.fetch = function(...args) {
                    const promise = originalFetch.apply(this, args);
                    
                    // 检查URL
                    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
                    if (url && url.includes('api-pan.xunlei.com')) {
                        console.log('[注入脚本] 拦截到迅雷API请求:', url);
                        
                        // 提取headers中的关键参数
                        if (args[1]?.headers) {
                            const headers = args[1].headers;
                            let captchaToken = null;
                            let clientId = null;
                            let deviceId = null;
                            let authorization = null;
                            
                            if (headers instanceof Headers) {
                                captchaToken = headers.get('x-captcha-token');
                                clientId = headers.get('x-client-id');
                                deviceId = headers.get('x-device-id');
                                authorization = headers.get('authorization');
                            } else if (typeof headers === 'object') {
                                captchaToken = headers['x-captcha-token'] || headers['X-Captcha-Token'];
                                clientId = headers['x-client-id'] || headers['X-Client-Id'];
                                deviceId = headers['x-device-id'] || headers['X-Device-Id'];
                                authorization = headers['authorization'] || headers['Authorization'];
                            }
                            
                            if (captchaToken) {
                                window.__xunlei_captcha_token = captchaToken;
                                console.log('[注入脚本] ✅ 捕获到captcha token:', captchaToken.substring(0, 50) + '...');
                            }
                            if (clientId) {
                                window.__xunlei_client_id = clientId;
                                console.log('[注入脚本] ✅ 捕获到client id:', clientId);
                            }
                            if (deviceId) {
                                window.__xunlei_device_id = deviceId;
                                console.log('[注入脚本] ✅ 捕获到device id:', deviceId);
                            }
                            if (authorization) {
                                window.__xunlei_authorization = authorization;
                                console.log('[注入脚本] ✅ 捕获到authorization');
                            }
                        }
                        
                        // 从URL中提取parent_id（如果在子文件夹中）
                        if (url.includes('/share/detail') && url.includes('parent_id=')) {
                            const match = url.match(/parent_id=([^&]+)/);
                            if (match && match[1]) {
                                window.__xunlei_parent_id = decodeURIComponent(match[1]);
                                console.log('[注入脚本] ✅ 捕获到parent id:', match[1]);
                            }
                        }
                        
                        // 拦截响应，缓存文件列表和pass_code_token
                        if (url.includes('/share/detail') || url.includes('/drive/v1/share?')) {
                            promise.then(response => {
                                // 克隆响应以避免消费原始响应体
                                response.clone().json().then(data => {
                                    if (data && data.files) {
                                        window.__xunlei_files_cache = data.files;
                                        console.log('[注入脚本] ✅ 缓存文件列表，数量:', data.files.length);
                                        
                                        if (data.pass_code_token) {
                                            window.__xunlei_pass_code_token = data.pass_code_token;
                                            console.log('[注入脚本] ✅ 缓存pass_code_token');
                                        }
                                    }
                                }).catch(e => {
                                    // 忽略非JSON响应
                                });
                            }).catch(e => {
                                console.error('[注入脚本] 拦截响应失败:', e);
                            });
                        }
                    }
                    
                    return promise;
                };
                
                console.log('[注入脚本] Fetch劫持完成');
            })();
        `;
        (document.head || document.documentElement).appendChild(script);
        script.remove();
        
        // 定期从页面变量获取参数
        setInterval(() => {
            if (unsafeWindow.__xunlei_captcha_token && unsafeWindow.__xunlei_captcha_token !== xunleiCaptchaToken) {
                xunleiCaptchaToken = unsafeWindow.__xunlei_captcha_token;
                console.log('✅ [Userscript] 同步到captcha token');
            }
            if (unsafeWindow.__xunlei_client_id && unsafeWindow.__xunlei_client_id !== xunleiClientId) {
                xunleiClientId = unsafeWindow.__xunlei_client_id;
                console.log('✅ [Userscript] 同步到client id:', xunleiClientId);
            }
            if (unsafeWindow.__xunlei_device_id && unsafeWindow.__xunlei_device_id !== xunleiDeviceId) {
                xunleiDeviceId = unsafeWindow.__xunlei_device_id;
                console.log('✅ [Userscript] 同步到device id:', xunleiDeviceId);
            }
            if (unsafeWindow.__xunlei_parent_id && unsafeWindow.__xunlei_parent_id !== xunleiParentId) {
                xunleiParentId = unsafeWindow.__xunlei_parent_id;
                console.log('✅ [Userscript] 同步到parent id:', xunleiParentId);
            }
            if (unsafeWindow.__xunlei_authorization && unsafeWindow.__xunlei_authorization !== xunleiAuthorization) {
                xunleiAuthorization = unsafeWindow.__xunlei_authorization;
                console.log('✅ [Userscript] 同步到authorization');
            }
            if (unsafeWindow.__xunlei_files_cache) {
                xunleiFilesCache = unsafeWindow.__xunlei_files_cache;
                console.log('✅ [Userscript] 同步到文件列表，数量:', xunleiFilesCache.length);
            }
            if (unsafeWindow.__xunlei_pass_code_token && unsafeWindow.__xunlei_pass_code_token !== xunleiPassCodeToken) {
                xunleiPassCodeToken = unsafeWindow.__xunlei_pass_code_token;
                console.log('✅ [Userscript] 同步到pass_code_token');
            }
        }, 500);
        
        // 拦截fetch
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = args[0];
            if (url && url.includes('api-pan.xunlei.com')) {
                console.log('[Fetch] 拦截到请求:', url);
                if (args[1] && args[1].headers) {
                    const headers = args[1].headers;
                    let token = '';
                    
                    if (headers instanceof Headers) {
                        token = headers.get('x-captcha-token');
                    } else if (typeof headers === 'object') {
                        token = headers['x-captcha-token'] || headers['X-Captcha-Token'];
                    }
                    
                    if (token) {
                        console.log('[Fetch] 请求头中的token:', token.substring(0, 50) + '...');
                        if (token !== xunleiCaptchaToken) {
                            xunleiCaptchaToken = token;
                            console.log('✅ [Fetch] 拦截到captcha token');
                        }
                    }
                }
            }
            return originalFetch.apply(this, args);
        };
        
        // 拦截XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
        
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            this._headers = {};
            if (url && url.includes('api-pan.xunlei.com')) {
                console.log('[XHR] 拦截到请求:', url);
            }
            return originalOpen.call(this, method, url, ...rest);
        };
        
        XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
            if (this._url && this._url.includes('api-pan.xunlei.com')) {
                this._headers[name] = value;
                console.log('[XHR] 请求头:', name, '=', value ? value.substring(0, 50) + '...' : 'null');
                if (name.toLowerCase() === 'x-captcha-token' && value) {
                    if (value !== xunleiCaptchaToken) {
                        xunleiCaptchaToken = value;
                        console.log('✅ [XHR] 拦截到captcha token');
                    }
                }
            }
            return originalSetRequestHeader.call(this, name, value);
        };
    }
    
    // 检测当前网盘类型
    function detectPanType() {
        const hostname = location.hostname;
        if (hostname.includes('baidu')) return 'baidu';
        if (hostname.includes('quark')) return 'quark';
        if (hostname.includes('xunlei')) return 'xunlei';
        return null;
    }
    
    // 获取映射列表（支持分页和搜索）
    function fetchMappings(page = 1, search = '') {
        console.log('📋 [获取映射列表]', {page, search});
        
        const params = new URLSearchParams({
            page: page,
            page_size: 20,
            enabled: true
        });
        
        if (search) {
            params.append('search', search);
        }
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: `${API_BASE}/mappings?${params.toString()}`,
                headers: {
                    'Accept': 'application/json'
                },
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.success) {
                            console.log('✅ 获取映射列表成功，数量:', result.data.length, '总计:', result.total);
                            resolve(result);
                        } else {
                            reject(new Error(result.message || '获取映射列表失败'));
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 获取勾选的文件ID列表
    function getSelectedFileIds() {
        // 查找所有选中的文件元素（百度网盘用 JS-item-active 标识选中）
        const selectedItems = document.querySelectorAll('dd.JS-item-active, .JS-item-active');
        console.log('📝 找到选中元素:', selectedItems.length, '个');
        
        const fileIds = [];
        
        // 从 window.cache.list.data 获取文件列表
        const cache = unsafeWindow.cache || window.cache;
        let fileList = [];
        
        if (cache && cache.list && cache.list.data) {
            // 获取当前路径的文件列表
            const paths = Object.keys(cache.list.data);
            console.log('📂 可用路径:', paths);
            
            if (paths.length > 0) {
                // 找到文件数量最多的路径（避免选到根路径）
                let maxFiles = 0;
                let bestPath = paths[0];
                
                paths.forEach(path => {
                    const pathData = cache.list.data[path];
                    const fileCount = pathData?.list?.length || 0;
                    if (fileCount > maxFiles) {
                        maxFiles = fileCount;
                        bestPath = path;
                    }
                });
                
                const pathData = cache.list.data[bestPath];
                fileList = pathData?.list || [];
                console.log('📋 选择路径:', bestPath);
                console.log('📋 文件数量:', fileList.length);
            }
        }
        
        if (fileList.length === 0) {
            console.error('❌ 无法获取文件列表');
            return [];
        }
        
        selectedItems.forEach(item => {
            // 获取位置索引
            const position = parseInt(item.getAttribute('_position'));
            console.log('  元素位置:', position);
            
            if (!isNaN(position) && fileList[position]) {
                // 从文件列表中获取对应位置的文件ID
                const file = fileList[position];
                const fsid = file.fs_id || file.fsid;
                if (fsid) {
                    fileIds.push(fsid);
                    console.log('  ✅ 找到文件ID:', fsid, '文件名:', file.server_filename);
                }
            }
        });
        
        console.log('🎯 找到勾选文件:', fileIds.length, '个');
        console.log('  文件ID列表:', fileIds);
        return fileIds;
    }
    
    // 百度确保目录存在（通过OpenList API，和夸克、迅雷统一）
    async function ensureBaiduFolderExists(fullPath) {
        console.log('🔍 通过OpenList检查并创建百度目录:', fullPath);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${API_BASE}/openlist/get-folder-id`,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                data: JSON.stringify({
                    pan_type: 'baidu',
                    path: fullPath
                }),
                onload: (response) => {
                    try {
                        console.log('  后端响应状态:', response.status);
                        console.log('  后端响应内容:', response.responseText);
                        const result = JSON.parse(response.responseText);
                        console.log('  解析后结果:', result);
                        
                        if (result.success) {
                            console.log('✅ OpenList路径就绪:', result.path);
                            resolve(result.path);
                        } else {
                            console.error('  后端返回失败:', result);
                            reject(new Error(`获取路径失败: ${JSON.stringify(result)}`));
                        }
                    } catch (e) {
                        console.error('  解析响应失败:', e);
                        console.error('  原始响应:', response.responseText);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 调用百度网盘原生API转存
    async function callBaiduTransferAPI(fileIds, targetPath) {
        console.log('🚀 调用百度网盘API转存');
        console.log('  文件ID:', fileIds);
        console.log('  原始路径:', targetPath);
        
        // 清理路径：去除网盘前缀，确保以/开头
        let cleanPath = targetPath;
        cleanPath = cleanPath.replace(/^(baidu|kuake|xunlei)/, '');  // 去除开头的网盘名
        cleanPath = cleanPath.replace(/^\/(baidu|kuake|xunlei)\//, '/');  // 去除 /baidu/ 格式
        cleanPath = cleanPath.replace(/^\/(baidu|kuake|xunlei)$/, '/');  // 去除 /baidu 格式
        if (!cleanPath.startsWith('/')) {
            cleanPath = '/' + cleanPath;
        }
        
        console.log('  清理后路径:', cleanPath);
        
        // 从页面获取百度网盘的数据
        const yunData = unsafeWindow.yunData || {};
        console.log('  yunData:', yunData);
        
        if (!yunData.shareid || !yunData.share_uk || !yunData.bdstoken) {
            throw new Error('无法获取页面数据，请刷新页面重试');
        }
        
        // 通过OpenList确保目录存在（统一逻辑）
        try {
            await ensureBaiduFolderExists(cleanPath);
        } catch (error) {
            console.error('❌ OpenList创建目录失败:', error);
            throw new Error(`创建目录失败: ${error.message}`);
        }
        
        const fsidlist = JSON.stringify(fileIds);
        const requestData = `fsidlist=${encodeURIComponent(fsidlist)}&path=${encodeURIComponent(cleanPath)}`;
        const sekey = getCookie('BDCLND');  // Cookie的值已经是编码过的，不要再次编码
        
        // 生成logid和dp-logid
        const logid = btoa(`${Date.now()}${Math.random()}`).substring(0, 32);
        const dpLogid = Date.now().toString() + Math.floor(Math.random() * 100000);
        
        const requestUrl = `https://pan.baidu.com/share/transfer?shareid=${yunData.shareid}&from=${yunData.share_uk}&sekey=${sekey}&ondup=newcopy&async=1&channel=chunlei&web=1&app_id=250528&bdstoken=${yunData.bdstoken}&logid=${logid}&clienttype=0&dp-logid=${dpLogid}`;
        
        console.log('  请求URL:', requestUrl);
        console.log('  请求数据:', requestData);
        console.log('  fsidlist原始值:', fsidlist);
        console.log('  完整请求:');
        console.log(`curl '${requestUrl}' \\
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \\
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \\
  --data-raw '${requestData}'`);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: requestUrl,
                headers: {
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Origin': 'https://pan.baidu.com',
                    'Pragma': 'no-cache',
                    'Referer': location.href,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'User-Agent': navigator.userAgent,
                    'X-Requested-With': 'XMLHttpRequest',
                    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"'
                },
                cookie: document.cookie,
                data: requestData,
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        console.log('✅ 百度API响应:', result);
                        
                        if (result.errno === 0) {
                            resolve(result);
                        } else {
                            reject(new Error(result.show_msg || `转存失败: errno=${result.errno}`));
                        }
                    } catch (e) {
                        console.error('❌ 解析响应失败:', e);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    console.error('❌ 请求失败:', error);
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 获取Cookie值
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }
    
    // 调用后端转存API（备用方案）
    function callTransferAPI(panType, shareUrl, passCode, targetPath) {
        // 清理路径中的网盘前缀（支持多种格式）
        let cleanPath = targetPath;
        
        // 去除开头的网盘名称（baidu/kuake/xunlei）
        cleanPath = cleanPath.replace(/^(baidu|kuake|xunlei)/, '');
        // 去除开头的 /baidu/ /kuake/ /xunlei/
        cleanPath = cleanPath.replace(/^\/(baidu|kuake|xunlei)\//, '/');
        // 去除开头的 /baidu /kuake /xunlei
        cleanPath = cleanPath.replace(/^\/(baidu|kuake|xunlei)$/, '/');
        
        // 确保以 / 开头
        if (!cleanPath.startsWith('/')) {
            cleanPath = '/' + cleanPath;
        }
        
        console.log('🧹 路径清理:');
        console.log('  原始路径:', targetPath);
        console.log('  清理后:', cleanPath);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${API_BASE}/transfer`,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                data: JSON.stringify({
                    pan_type: panType,
                    share_url: shareUrl,
                    pass_code: passCode,
                    target_path: cleanPath
                }),
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.success) {
                            resolve(result);
                        } else {
                            reject(new Error(result.message || '转存失败'));
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 显示映射选择对话框
    function showMappingDialog(panType) {
        return new Promise(async (resolve, reject) => {
            try {
                let currentPage = 1;
                let searchKeyword = '';
                let totalPages = 1;
                
                // 创建遮罩层
                const overlay = document.createElement('div');
                overlay.className = 'mp-autofill-overlay';
                
                // 创建对话框
                const dialog = document.createElement('div');
                dialog.className = 'mp-autofill-dialog';
                
                // 标题
                const title = document.createElement('h3');
                title.textContent = `选择转存路径 (${panType.toUpperCase()})`;
                title.style.margin = '0 0 15px 0';
                dialog.appendChild(title);
                
                // 提示
                const hint = document.createElement('div');
                hint.style.cssText = 'padding: 10px; background: #fff3cd; border-radius: 4px; margin-bottom: 15px; font-size: 13px; color: #856404;';
                hint.textContent = '💡 选择映射后会自动填充路径到网盘转存框';
                dialog.appendChild(hint);
                
                // 搜索框
                const searchBox = document.createElement('input');
                searchBox.type = 'text';
                searchBox.placeholder = '搜索映射名称（回车搜索）...';
                searchBox.className = 'mp-autofill-search';
                dialog.appendChild(searchBox);
                
                // 映射列表容器
                const listContainer = document.createElement('div');
                listContainer.className = 'mp-autofill-list';
                
                // 渲染映射列表
                async function renderMappings() {
                    listContainer.innerHTML = '<div style="text-align:center;color:#999;padding:20px;">加载中...</div>';
                    
                    try {
                        const result = await fetchMappings(currentPage, searchKeyword);
                        const mappings = result.data || [];
                        totalPages = result.total_pages || 1;
                        
                        listContainer.innerHTML = '';
                        
                        if (mappings.length === 0) {
                            listContainer.innerHTML = '<div style="text-align:center;color:#999;padding:20px;">没有找到匹配的映射</div>';
                            updatePagination();
                            return;
                        }
                        
                        mappings.forEach(mapping => {
                        const item = document.createElement('div');
                        item.className = 'mp-autofill-item';
                        
                        const pathKey = `${panType}_name`;
                        const targetPath = mapping[pathKey];
                        
                        if (!targetPath) {
                            item.style.opacity = '0.5';
                            item.style.cursor = 'not-allowed';
                        }
                        
                        // 显示分类标签
                        const categoryBadge = mapping.category 
                            ? `<span style="display:inline-block;padding:2px 8px;background:#e3f2fd;color:#1976d2;border-radius:3px;font-size:11px;margin-right:8px;">${mapping.category}</span>`
                            : '';
                        
                        item.innerHTML = `
                            <div style="margin-bottom:6px;">
                                ${categoryBadge}
                                <span style="font-weight:bold;">${mapping.original_name}</span>
                            </div>
                            <div style="font-size:12px;color:#666;">
                                路径: ${targetPath || '未配置'}
                            </div>
                        `;
                        
                        if (targetPath) {
                            item.onclick = () => {
                                console.log('🎯 用户选择映射:', mapping.original_name);
                                console.log('  目标路径:', targetPath);
                                
                                // 构建完整路径：/A-闲鱼影视（自动更新）/category/targetPath
                                let fullPath = targetPath;
                                if (mapping.category) {
                                    fullPath = `/A-闲鱼影视（自动更新）/${mapping.category}/${targetPath}`;
                                } else {
                                    fullPath = `/A-闲鱼影视（自动更新）/${targetPath}`;
                                }
                                
                                console.log('  完整路径:', fullPath);
                                overlay.remove();
                                resolve(fullPath);
                            };
                        }
                        
                            listContainer.appendChild(item);
                        });
                        
                        updatePagination();
                    } catch (error) {
                        listContainer.innerHTML = `<div style="text-align:center;color:#f44336;padding:20px;">加载失败: ${error.message}</div>`;
                    }
                }
                
                // 分页容器
                const pagination = document.createElement('div');
                pagination.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 15px; padding: 10px;';
                
                // 更新分页按钮
                function updatePagination() {
                    pagination.innerHTML = '';
                    
                    // 上一页
                    const prevBtn = document.createElement('button');
                    prevBtn.textContent = '上一页';
                    prevBtn.disabled = currentPage === 1;
                    prevBtn.style.cssText = 'padding: 5px 15px; cursor: pointer;';
                    if (currentPage === 1) prevBtn.style.opacity = '0.5';
                    prevBtn.onclick = () => {
                        if (currentPage > 1) {
                            currentPage--;
                            renderMappings();
                        }
                    };
                    pagination.appendChild(prevBtn);
                    
                    // 页码
                    const pageInfo = document.createElement('span');
                    pageInfo.textContent = `${currentPage} / ${totalPages}`;
                    pageInfo.style.cssText = 'padding: 0 10px;';
                    pagination.appendChild(pageInfo);
                    
                    // 下一页
                    const nextBtn = document.createElement('button');
                    nextBtn.textContent = '下一页';
                    nextBtn.disabled = currentPage === totalPages;
                    nextBtn.style.cssText = 'padding: 5px 15px; cursor: pointer;';
                    if (currentPage === totalPages) nextBtn.style.opacity = '0.5';
                    nextBtn.onclick = () => {
                        if (currentPage < totalPages) {
                            currentPage++;
                            renderMappings();
                        }
                    };
                    pagination.appendChild(nextBtn);
                }
                
                // 搜索事件（回车触发）
                searchBox.onkeypress = (e) => {
                    if (e.key === 'Enter') {
                        searchKeyword = e.target.value.trim();
                        currentPage = 1;
                        renderMappings();
                    }
                };
                
                dialog.appendChild(listContainer);
                dialog.appendChild(pagination);
                renderMappings();
                
                // 按钮组
                const buttonGroup = document.createElement('div');
                buttonGroup.style.cssText = 'display: flex; gap: 10px; margin-top: 15px;';
                
                // 手动输入按钮
                const manualBtn = document.createElement('button');
                manualBtn.textContent = '手动输入';
                manualBtn.className = 'mp-autofill-btn mp-autofill-btn-secondary';
                manualBtn.onclick = () => {
                    const path = prompt('请输入转存路径（例如：/电影/华语）：', '/');
                    if (path) {
                        overlay.remove();
                        resolve(path);
                    }
                };
                buttonGroup.appendChild(manualBtn);
                
                // 取消按钮
                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = '取消';
                cancelBtn.className = 'mp-autofill-btn mp-autofill-btn-cancel';
                cancelBtn.onclick = () => {
                    overlay.remove();
                    reject(new Error('用户取消'));
                };
                buttonGroup.appendChild(cancelBtn);
                
                dialog.appendChild(buttonGroup);
                overlay.appendChild(dialog);
                document.body.appendChild(overlay);
                
                // 点击遮罩层关闭
                overlay.onclick = (e) => {
                    if (e.target === overlay) {
                        overlay.remove();
                        reject(new Error('用户取消'));
                    }
                };
                
                // 聚焦搜索框
                setTimeout(() => searchBox.focus(), 100);
                
            } catch (error) {
                console.error('❌ 显示对话框失败:', error);
                reject(error);
            }
        });
    }
    
    // 百度网盘：填充路径
    function fillBaiduPath(path) {
        console.log('🔧 [百度网盘] 开始填充路径:', path);
        
        // 查找路径输入框
        const pathInput = document.querySelector('input[class*="save-path"]') ||
                         document.querySelector('input[placeholder*="保存到"]') ||
                         document.querySelector('.save-path-inputbox input') ||
                         document.querySelector('.nd-input input');
        
        if (pathInput) {
            // 设置值
            pathInput.value = path;
            
            // 触发各种事件，确保网盘识别到变化
            pathInput.dispatchEvent(new Event('input', { bubbles: true }));
            pathInput.dispatchEvent(new Event('change', { bubbles: true }));
            pathInput.dispatchEvent(new Event('blur', { bubbles: true }));
            
            console.log('✅ 路径已填充:', path);
            
            // 高亮提示
            pathInput.style.background = '#d4edda';
            setTimeout(() => {
                pathInput.style.background = '';
            }, 1000);
            
            return true;
        } else {
            console.error('❌ 未找到路径输入框');
            return false;
        }
    }
    
    // ==================== 夸克网盘功能 ====================
    
    // 获取夸克未勾选的文件ID（用于排除）
    function getQuarkExcludeFileIds() {
        // 获取所有文件行
        const allRows = document.querySelectorAll('tr.ant-table-row[data-row-key]');
        // 获取已勾选的文件行
        const selectedRows = document.querySelectorAll('tr.ant-table-row-selected[data-row-key]');
        
        const selectedCount = selectedRows.length;
        const totalCount = allRows.length;
        
        console.log('📝 全部文件:', totalCount, '个');
        console.log('✅ 已勾选（将保存）:', selectedCount, '个');
        console.log('❌ 未勾选（将排除）:', (totalCount - selectedCount), '个');
        
        // 已勾选的文件ID
        const selectedIds = new Set();
        selectedRows.forEach(row => {
            const fid = row.getAttribute('data-row-key');
            if (fid) selectedIds.add(fid);
        });
        
        // 未勾选的文件ID（排除列表）
        const excludeIds = [];
        allRows.forEach(row => {
            const fid = row.getAttribute('data-row-key');
            if (fid && !selectedIds.has(fid)) {
                excludeIds.push(fid);
            }
        });
        
        console.log('🎯 实际操作: 保存', selectedCount, '个文件，排除', excludeIds.length, '个文件');
        return excludeIds;
    }
    
    // 获取夸克分享页参数
    async function getQuarkShareParams() {
        const url = location.href;
        const match = url.match(/\/s\/([^#/?]+)/);
        if (!match) {
            throw new Error('无法从URL获取pwd_id');
        }
        
        const pwd_id = match[1];
        console.log('📋 分享ID (pwd_id):', pwd_id);
        
        // 从performance API获取stoken（从已发送的网络请求中提取）
        let stoken = null;
        const entries = performance.getEntries();
        for (const entry of entries) {
            if (entry.name && entry.name.includes('quark.cn') && entry.name.includes('stoken=')) {
                const stokenMatch = entry.name.match(/stoken=([^&]+)/);
                if (stokenMatch) {
                    stoken = decodeURIComponent(stokenMatch[1]);
                    console.log('🔑 从performance获取stoken:', stoken);
                    break;
                }
            }
        }
        
        // 如果performance中没有，尝试从URL参数获取
        if (!stoken) {
            const urlParams = new URLSearchParams(location.search);
            stoken = urlParams.get('stoken');
            if (stoken) {
                console.log('🔑 从URL参数获取stoken:', stoken);
            }
        }
        
        if (!stoken) {
            throw new Error('无法获取stoken，请刷新页面后重试');
        }
        
        // 调用API获取分享详情
        const timestamp = Date.now();
        const apiUrl = `https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pr=ucpro&fr=pc&uc_param_str=&ver=2&pwd_id=${pwd_id}&stoken=${encodeURIComponent(stoken)}&pdir_fid=0&force=0&_page=1&_size=50&_fetch_banner=1&_fetch_share=1&fetch_relate_conversation=1&_fetch_total=1&_sort=file_type:asc,file_name:asc&__dt=${Math.floor(Math.random() * 10000)}&__t=${timestamp}`;
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: apiUrl,
                headers: {
                    'accept': 'application/json, text/plain, */*',
                    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
                    'cache-control': 'no-cache',
                    'origin': 'https://pan.quark.cn',
                    'pragma': 'no-cache',
                    'priority': 'u=1, i',
                    'referer': 'https://pan.quark.cn/',
                    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': navigator.userAgent
                },
                cookie: document.cookie,
                onload: (response) => {
                    try {
                        console.log('  API原始响应:', response.responseText.substring(0, 500) + '...');
                        const result = JSON.parse(response.responseText);
                        console.log('  解析后结果:', result);
                        
                        if (result.status === 200 && result.code === 0) {
                            const data = result.data;
                            console.log('  share数据:', data.share);
                            
                            // 从URL hash获取当前文件夹ID（如果在子文件夹中）
                            // URL格式：https://pan.quark.cn/s/xxx#/list/share/当前文件夹ID
                            let pdir_fid = data.share.first_fid;  // 默认用根目录
                            const hashMatch = location.hash.match(/\/list\/share\/([^/?]+)/);
                            if (hashMatch) {
                                pdir_fid = hashMatch[1];
                                console.log('  📁 当前在子文件夹:', pdir_fid);
                            } else {
                                console.log('  📁 当前在根目录:', pdir_fid);
                            }
                            
                            resolve({
                                pwd_id: pwd_id,
                                stoken: stoken,
                                pdir_fid: pdir_fid
                            });
                        } else {
                            console.error('  API返回状态异常:', result);
                            reject(new Error(`获取分享详情失败: status=${result.status}, code=${result.code}`));
                        }
                    } catch (e) {
                        console.error('  解析响应失败:', e);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 获取夸克用户网盘根目录ID
    async function getQuarkRootFolderId() {
        const apiUrl = 'https://drive-pc.quark.cn/1/clouddrive/file/sort?pr=ucpro&fr=pc&pdir_fid=0&_page=1&_size=50';
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: apiUrl,
                headers: {
                    'accept': 'application/json, text/plain, */*',
                },
                cookie: document.cookie,
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.status === 200 && result.data && result.data.list && result.data.list.length > 0) {
                            // 根目录ID通常是"0"
                            resolve('0');
                        } else {
                            resolve('0'); // fallback
                        }
                    } catch (e) {
                        resolve('0'); // fallback
                    }
                },
                onerror: (error) => {
                    resolve('0'); // fallback
                }
            });
        });
    }
    
    // 夸克创建文件夹（两步：创建临时名+重命名）
    async function createQuarkFolder(parentFid, folderName) {
        console.log('📁 创建夸克文件夹:', folderName, '父目录ID:', parentFid);
        
        // 生成临时文件夹名
        const tempName = `新建文件夹-${Date.now()}`;
        
        // 第一步：创建临时文件夹
        const createUrl = 'https://drive-pc.quark.cn/1/clouddrive/file?pr=ucpro&fr=pc';
        const createData = {
            pdir_fid: parentFid,
            file_name: tempName,
            dir_path: '',
            dir_init_lock: false
        };
        
        const fid = await new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: createUrl,
                headers: {
                    'accept': 'application/json, text/plain, */*',
                    'content-type': 'application/json',
                },
                cookie: document.cookie,
                data: JSON.stringify(createData),
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.status === 200 && result.data && result.data.fid) {
                            console.log('  ✅ 创建临时文件夹成功, fid:', result.data.fid);
                            resolve(result.data.fid);
                        } else {
                            reject(new Error(`创建文件夹失败: ${result.message}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('创建文件夹请求失败'));
                }
            });
        });
        
        // 第二步：重命名
        const renameUrl = 'https://drive-pc.quark.cn/1/clouddrive/file/rename?pr=ucpro&fr=pc';
        const renameData = {
            fid: fid,
            file_name: folderName
        };
        
        await new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: renameUrl,
                headers: {
                    'accept': 'application/json, text/plain, */*',
                    'content-type': 'application/json',
                },
                cookie: document.cookie,
                data: JSON.stringify(renameData),
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.status === 200) {
                            console.log('  ✅ 重命名成功:', folderName);
                            resolve();
                        } else {
                            reject(new Error(`重命名失败: ${result.message}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('重命名请求失败'));
                }
            });
        });
        
        return fid;
    }
    
    // 夸克确保目录存在（通过OpenList API）
    async function ensureQuarkFolderExists(fullPath) {
        console.log('🔍 检查并创建夸克目录:', fullPath);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${API_BASE}/openlist/get-folder-id`,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                data: JSON.stringify({
                    pan_type: 'quark',
                    path: fullPath
                }),
                onload: (response) => {
                    try {
                        console.log('  后端响应状态:', response.status);
                        console.log('  后端响应内容:', response.responseText);
                        const result = JSON.parse(response.responseText);
                        console.log('  解析后结果:', result);
                        
                        if (result.success) {
                            console.log('✅ 获取文件夹ID成功:', result.fid);
                            console.log('  OpenList路径:', result.path);
                            resolve(result.fid);
                        } else {
                            console.error('  后端返回失败:', result);
                            reject(new Error(`获取文件夹ID失败: ${JSON.stringify(result)}`));
                        }
                    } catch (e) {
                        console.error('  解析响应失败:', e);
                        console.error('  原始响应:', response.responseText);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 夸克转存文件
    async function callQuarkTransferAPI(fileIds, targetPath) {
        console.log('🚀 调用夸克网盘API转存');
        console.log('  排除文件ID（未勾选的）:', fileIds);
        console.log('  排除文件数量:', fileIds.length);
        console.log('  目标路径:', targetPath);
        
        // 清理路径
        let cleanPath = targetPath;
        cleanPath = cleanPath.replace(/^(baidu|kuake|xunlei)/, '');
        cleanPath = cleanPath.replace(/^\/(baidu|kuake|xunlei)\//, '/');
        if (!cleanPath.startsWith('/')) {
            cleanPath = '/' + cleanPath;
        }
        
        console.log('  清理后路径:', cleanPath);
        
        // 获取分享参数
        const shareParams = await getQuarkShareParams();
        
        // 确保目标文件夹存在，获取最终fid
        const targetFid = await ensureQuarkFolderExists(cleanPath);
        
        // 调用转存API（注意：夸克使用排除逻辑，exclude_fids是未勾选的文件）
        const timestamp = Date.now();
        const saveUrl = `https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save?pr=ucpro&fr=pc&uc_param_str=&__dt=${Math.floor(Math.random() * 10000)}&__t=${timestamp}`;
        const saveData = {
            pwd_id: shareParams.pwd_id,
            stoken: shareParams.stoken,
            pdir_fid: shareParams.pdir_fid,
            to_pdir_fid: targetFid,
            pdir_save_all: true,  // 保存全部
            exclude_fids: fileIds,  // 排除未勾选的
            scene: 'link'
        };
        
        console.log('  转存参数:', saveData);
        console.log('  ⚠️ exclude_fids详情:', saveData.exclude_fids);
        console.log('  ⚠️ exclude_fids数量:', saveData.exclude_fids.length);
        
        const taskId = await new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: saveUrl,
                headers: {
                    'accept': 'application/json, text/plain, */*',
                    'content-type': 'application/json',
                },
                cookie: document.cookie,
                data: JSON.stringify(saveData),
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        console.log('  转存响应:', result);
                        
                        if (result.status === 200 && result.data && result.data.task_id) {
                            console.log('  ✅ 转存任务创建成功, task_id:', result.data.task_id);
                            resolve(result.data.task_id);
                        } else {
                            reject(new Error(`转存失败: ${result.message}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('转存请求失败'));
                }
            });
        });
        
        // 轮询任务状态
        console.log('⏳ 等待转存任务完成...');
        let retryCount = 0;
        const maxRetries = 30;
        
        while (retryCount < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
            
            const taskUrl = `https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&task_id=${taskId}&retry_index=${retryCount}`;
            
            const taskResult = await new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: taskUrl,
                    headers: {
                        'accept': 'application/json, text/plain, */*',
                    },
                    cookie: document.cookie,
                    onload: (response) => {
                        try {
                            const result = JSON.parse(response.responseText);
                            resolve(result);
                        } catch (e) {
                            reject(e);
                        }
                    },
                    onerror: (error) => {
                        reject(error);
                    }
                });
            });
            
            console.log(`  轮询 ${retryCount + 1}/${maxRetries}:`, taskResult);
            
            if (taskResult.status === 200 && taskResult.data) {
                const status = taskResult.data.status;
                if (status === 2) {
                    console.log('✅ 转存成功！');
                    return taskResult;
                } else if (status === 3) {
                    throw new Error('转存失败');
                }
            }
            
            retryCount++;
        }
        
        throw new Error('转存超时');
    }
    
    // ==================== 迅雷网盘功能 ====================
    
    // 获取迅雷勾选的文件名列表
    function getXunleiSelectedFileNames() {
        const selectedCheckboxes = document.querySelectorAll('.FileCheckBox__checkbox--HYwz8.is-checked');
        const fileNames = [];
        
        selectedCheckboxes.forEach(checkbox => {
            const item = checkbox.closest('.SourceListItem__main--c9HnH');
            if (item) {
                const nameElement = item.querySelector('.SourceListItem__name--y6dVw a');
                if (nameElement) {
                    const fileName = nameElement.getAttribute('title') || nameElement.textContent.trim();
                    if (fileName) {
                        fileNames.push(fileName);
                    }
                }
            }
        });
        
        console.log('📝 已勾选文件:', fileNames.length, '个');
        fileNames.forEach(name => console.log('  ✅', name));
        
        return fileNames;
    }
    
    // 获取迅雷分享参数和文件映射
    async function getXunleiShareParams() {
        console.log('📊 获取迅雷分享参数');
        
        // 优先使用拦截到的缓存数据
        if (xunleiFilesCache && xunleiFilesCache.length > 0) {
            console.log('✅ 使用拦截到的文件列表缓存，数量:', xunleiFilesCache.length);
            
            const urlParams = new URLSearchParams(window.location.search);
            const share_id = location.pathname.match(/\/s\/([^\/]+)/)?.[1];
            
            // 构建文件映射
            const fileMap = new Map();
            for (const file of xunleiFilesCache) {
                fileMap.set(file.name, file.id);
                console.log('   📄 文件映射:', file.name, '→', file.id);
            }
            
            return {
                share_id,
                pass_code_token: xunleiPassCodeToken,
                fileMap,
                current_folder_id: xunleiParentId || '',
                deviceId: xunleiDeviceId,
                clientId: xunleiClientId
            };
        }
        
        console.log('⚠️ 未找到缓存，需要调用API获取');
        const url = location.href;
        const match = url.match(/\/s\/([^?]+)/);
        if (!match) {
            throw new Error('无法从URL获取share_id');
        }
        
        const share_id = match[1];
        const urlParams = new URLSearchParams(location.search);
        const pass_code = urlParams.get('pwd');
        const path = urlParams.get('path');  // 可能在子文件夹
        
        console.log('� 分享ID:', share_id);
        console.log('🔑 密码:', pass_code);
        console.log('📁 当前路径:', path || '根目录');
        
        // 从cookie获取必要参数
        const cookieObj = {};
        document.cookie.split(';').forEach(c => {
            const [key, value] = c.trim().split('=');
            cookieObj[key] = value;
        });
        
        // 使用拦截器获取的参数（与 captcha token 一起从请求中拦截）
        const deviceId = xunleiDeviceId;
        const clientId = xunleiClientId;
        
        if (!deviceId || !clientId) {
            throw new Error('未拦截到设备信息，请先刷新页面或浏览文件列表');
        }
        
        console.log('📱 Device ID:', deviceId);
        console.log('🆔 Client ID:', clientId);
        
        // 根据URL判断是在根目录还是子文件夹
        const decodedPath = path ? decodeURIComponent(path) : '';
        console.log('📂 当前路径:', decodedPath || '根目录');
        
        let parent_id = '';
        let pass_code_token = '';
        
        // 如果在子文件夹中，需要先获取文件夹ID
        if (decodedPath) {
            console.log('🔍 在子文件夹中，需要先获取文件夹ID...');
            
            // 1. 先调用根目录API获取文件夹列表
            const rootApiUrl = `https://api-pan.xunlei.com/drive/v1/share?share_id=${share_id}&pass_code=${pass_code}&limit=100&pass_code_token=&page_token=&thumbnail_size=SIZE_SMALL`;
            
            const rootResult = await new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: rootApiUrl,
                    headers: {
                        'accept': '*/*',
                        'content-type': 'application/json',
                        'x-captcha-token': xunleiCaptchaToken,
                        'x-client-id': clientId,
                        'x-device-id': deviceId
                    },
                    cookie: document.cookie,
                    onload: (response) => {
                        try {
                            const result = JSON.parse(response.responseText);
                            resolve(result);
                        } catch (e) {
                            reject(e);
                        }
                    },
                    onerror: () => reject(new Error('获取根目录失败'))
                });
            });
            
            console.log('   根目录API响应:', rootResult);
            pass_code_token = rootResult.pass_code_token;
            
            // 2. 从文件夹列表中找到当前path对应的文件夹ID
            const folderName = decodedPath.replace(/^\//, ''); // 去掉开头的/
            const folder = rootResult.files?.find(f => f.name === folderName && f.kind === 'drive#folder');
            
            if (!folder) {
                throw new Error(`未找到文件夹: ${folderName}`);
            }
            
            parent_id = folder.id;
            console.log('   ✅ 找到文件夹ID:', parent_id);
        }
        
        // 调用分享API获取文件列表
        let apiUrl;
        if (parent_id) {
            // 在子文件夹中，使用detail API
            apiUrl = `https://api-pan.xunlei.com/drive/v1/share/detail?share_id=${share_id}&parent_id=${parent_id}&pass_code_token=${encodeURIComponent(pass_code_token)}&limit=100&page_token=&thumbnail_size=SIZE_SMALL`;
        } else {
            // 根目录，使用share API
            apiUrl = `https://api-pan.xunlei.com/drive/v1/share?share_id=${share_id}&pass_code=${pass_code}&limit=100&pass_code_token=&page_token=&thumbnail_size=SIZE_SMALL`;
        }
        
        // 使用拦截到的captcha token
        console.log('🔐 准备调用分享API');
        console.log('   captcha token状态:', xunleiCaptchaToken ? '已获取' : '未获取');
        console.log('   captcha token完整值:', xunleiCaptchaToken);
        console.log('   Client ID:', clientId);
        console.log('   Device ID:', deviceId);
        console.log('   API URL:', apiUrl);
        
        const headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'x-client-id': clientId,
            'x-device-id': deviceId
        };
        
        // 添加captcha token
        if (xunleiCaptchaToken) {
            headers['x-captcha-token'] = xunleiCaptchaToken;
            console.log('✅ 已添加captcha token到分享API请求');
        } else {
            console.warn('⚠️ 缺少captcha token');
        }
        
        console.log('   完整请求头:', headers);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: apiUrl,
                headers: headers,
                cookie: document.cookie,
                onload: (response) => {
                    try {
                        console.log('📥 分享API响应状态:', response.status);
                        console.log('   原始响应:', response.responseText.substring(0, 500));
                        const result = JSON.parse(response.responseText);
                        console.log('   解析后结果:', result);
                        
                        if (result.files) {
                            const pass_code_token = result.pass_code_token;
                            const files = result.files;
                            
                            console.log('   📂 文件列表:', files);
                            console.log('   文件数量:', files.length);
                            
                            // 构建文件名→ID映射
                            const fileMap = new Map();
                            files.forEach(file => {
                                fileMap.set(file.name, file.id);
                                console.log('   📄 文件映射:', file.name, '→', file.id);
                            });
                            
                            // 获取当前文件夹ID（如果在子文件夹中）
                            let current_folder_id = parent_id;
                            if (result.parent && result.parent.id) {
                                current_folder_id = result.parent.id;
                            }
                            
                            resolve({
                                share_id,
                                pass_code_token,
                                fileMap,
                                current_folder_id,
                                deviceId,
                                clientId
                            });
                        } else {
                            reject(new Error('API返回数据格式异常'));
                        }
                    } catch (e) {
                        console.error('  解析响应失败:', e);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('网络请求失败'));
                }
            });
        });
    }
    
    // 获取迅雷用户网盘根目录ID（或指定文件夹ID）
    async function getXunleiTargetFolderId(path) {
        // 调用我们自己的后端API（后端再调用OpenList服务）
        const BACKEND_BASE = API_BASE.replace('/api', '');  // http://10.10.10.17:9889
        const OPENLIST_TOKEN = 'openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K2oum4';
        
        console.log('📂 获取迅雷目标文件夹ID:', path);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${BACKEND_BASE}/api/openlist/get-folder-id`,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${OPENLIST_TOKEN}`
                },
                data: JSON.stringify({
                    path: path,
                    pan_type: 'xunlei'
                }),
                onload: (response) => {
                    console.log('📥 后端OpenList响应状态:', response.status);
                    console.log('   响应内容:', response.responseText.substring(0, 500));
                    
                    if (response.status !== 200) {
                        console.error('❌ 后端返回非200状态:', response.status);
                        reject(new Error(`后端OpenList API错误: HTTP ${response.status}`));
                        return;
                    }
                    
                    try {
                        const result = JSON.parse(response.responseText);
                        console.log('   解析后结果:', result);
                        
                        if (result.success) {
                            console.log('✅ 获取文件夹ID成功:', result.fid);
                            resolve(result.fid);
                        } else {
                            reject(new Error(`获取文件夹ID失败: ${JSON.stringify(result)}`));
                        }
                    } catch (e) {
                        console.error('❌ 解析JSON失败，可能后端返回了HTML错误页面');
                        console.error('   错误:', e.message);
                        console.error('   响应内容（前200字符）:', response.responseText.substring(0, 200));
                        reject(new Error('后端OpenList服务异常，请检查服务是否正常运行'));
                    }
                },
                onerror: (error) => {
                    reject(new Error('请求后端失败'));
                }
            });
        });
    }
    
    // 调用迅雷转存API
    async function callXunleiTransferAPI(fileNames, targetPath) {
        console.log('🚀 调用迅雷网盘API转存');
        console.log('  目标路径:', targetPath);
        console.log('  勾选文件:', fileNames);
        
        // 1. 获取分享参数和文件映射
        const shareParams = await getXunleiShareParams();
        console.log('✅ 分享参数获取成功');
        console.log('   完整分享参数:', shareParams);
        console.log('   📝 pass_code_token:', shareParams.pass_code_token);
        
        // 2. 将文件名转换为ID
        const fileIds = [];
        for (const fileName of fileNames) {
            const fileId = shareParams.fileMap.get(fileName);
            if (fileId) {
                fileIds.push(fileId);
                console.log('  📄', fileName, '→', fileId);
            } else {
                console.warn('  ⚠️ 未找到文件ID:', fileName);
            }
        };
        
        if (fileIds.length === 0) {
            throw new Error('没有找到有效的文件ID');
        }
        
        console.log('📋 实际转存文件ID:', fileIds);
        
        // 3. 获取目标文件夹ID
        const targetFid = await getXunleiTargetFolderId(targetPath);
        console.log('✅ 目标文件夹ID:', targetFid);
        
        // 4. 调用转存API
        const restoreUrl = 'https://api-pan.xunlei.com/drive/v1/share/restore';
        
        // 从URL提取pass_code
        const urlParams = new URLSearchParams(window.location.search);
        const pass_code = urlParams.get('pwd') || '';
        
        const restoreData = {
            parent_id: targetFid,
            share_id: shareParams.share_id,
            pass_code: pass_code,  // 添加密码
            pass_code_token: shareParams.pass_code_token || '',
            ancestor_ids: [],
            file_ids: fileIds,
            specify_parent_id: true
        };
        
        console.log('📤 准备发送转存请求');
        console.log('   转存URL:', restoreUrl);
        console.log('   转存数据:', JSON.stringify(restoreData, null, 2));
        
        // 使用拦截器获取的authorization token、captcha token、client id、device id
        const authorization = xunleiAuthorization;
        const captchaToken = xunleiCaptchaToken;
        const clientId = xunleiClientId;
        const deviceId = xunleiDeviceId;
        
        if (!authorization || !captchaToken || !clientId || !deviceId) {
            throw new Error('未拦截到必要参数，请先刷新页面或浏览文件列表');
        }
        
        console.log('🔐 准备调用转存API');
        console.log('   captcha token状态:', captchaToken ? '已获取' : '未获取');
        console.log('   captcha token完整值:', captchaToken);
        console.log('   authorization完整值:', authorization);
        console.log('   Client ID:', shareParams.clientId);
        console.log('   Device ID:', shareParams.deviceId);
        
        if (!captchaToken) {
            console.warn('⚠️ 未拦截到captcha token，请先刷新页面或浏览文件列表');
        }
        
        const headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'authorization': authorization,
            'x-client-id': shareParams.clientId,
            'x-device-id': shareParams.deviceId
        };
        
        // 如果有captcha token，添加到headers
        if (captchaToken) {
            headers['x-captcha-token'] = captchaToken;
            console.log('✅ 已添加captcha token到转存请求头');
        } else {
            console.warn('⚠️ 缺少captcha token，请求可能失败');
        }
        
        console.log('   完整请求头:', JSON.stringify(headers, null, 2));
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: restoreUrl,
                headers: headers,
                data: JSON.stringify(restoreData),
                cookie: document.cookie,
                onload: (response) => {
                    try {
                        console.log('📥 转存API响应状态:', response.status);
                        console.log('   完整响应内容:', response.responseText);
                        const result = JSON.parse(response.responseText);
                        
                        if (result.share_status === 'OK' && result.restore_status) {
                            console.log('✅ 转存成功！');
                            console.log('  状态:', result.restore_status);
                            console.log('  任务ID:', result.restore_task_id);
                            resolve(result);
                        } else {
                            console.error('  转存失败:', result);
                            reject(new Error(`转存失败: ${JSON.stringify(result)}`));
                        }
                    } catch (e) {
                        console.error('  解析响应失败:', e);
                        reject(e);
                    }
                },
                onerror: (error) => {
                    reject(new Error('转存请求失败'));
                }
            });
        });
    }
    
    // 劫持"保存到网盘"按钮
    function hijackSaveButton() {
        const panType = detectPanType();
        if (!panType) return;
        
        console.log('🎯 开始劫持保存按钮...');
        
        // 查找并劫持按钮
        const checkButton = () => {
            let saveButton = null;
            
            if (panType === 'baidu') {
                // 百度网盘的"保存到网盘"按钮
                saveButton = document.querySelector('.save_btn') ||
                           document.querySelector('[node-type="bottomShareSave"]') ||
                           document.querySelector('a[title="保存到网盘"]');
            } else if (panType === 'quark') {
                // 夸克网盘的"保存到网盘"按钮
                saveButton = document.querySelector('button.share-save');
            } else if (panType === 'xunlei') {
                // 迅雷网盘的"转存到云盘"按钮
                saveButton = document.querySelector('button.saveToCloud');
            }
            
            if (saveButton && !saveButton.dataset.hijacked) {
                console.log('✅ 找到保存按钮，开始劫持');
                console.log('  按钮类名:', saveButton.className);
                console.log('  按钮文本:', saveButton.innerText);
                saveButton.dataset.hijacked = 'true';
                
                // 保存原始点击事件
                const originalOnClick = saveButton.onclick;
                
                saveButton.addEventListener('click', async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    console.log('🚫 拦截保存按钮点击');
                    
                    try {
                        // 1. 获取文件ID/名称（百度：ID；夸克：排除ID；迅雷：文件名）
                        let fileData;
                        if (panType === 'baidu') {
                            fileData = getSelectedFileIds();
                            if (!fileData || fileData.length === 0) {
                                showToast('⚠️ 请先勾选要转存的文件', 'warning');
                                return;
                            }
                        } else if (panType === 'quark') {
                            fileData = getQuarkExcludeFileIds();
                            // 夸克不需要检查fileData，可以全选（exclude为空）
                        } else if (panType === 'xunlei') {
                            fileData = getXunleiSelectedFileNames();
                            if (!fileData || fileData.length === 0) {
                                showToast('⚠️ 请先勾选要转存的文件', 'warning');
                                return;
                            }
                        }
                        
                        // 2. 弹出映射选择
                        const path = await showMappingDialog(panType);
                        console.log('📍 用户选择路径:', path);
                        
                        // 3. 调用对应网盘API转存
                        showToast('⏳ 正在转存...', 'info');
                        
                        let result;
                        if (panType === 'baidu') {
                            result = await callBaiduTransferAPI(fileData, path);
                            showToast(`✅ 转存成功！已保存 ${fileData.length} 个文件`, 'success');
                        } else if (panType === 'quark') {
                            result = await callQuarkTransferAPI(fileData, path);
                            showToast(`✅ 转存成功！`, 'success');
                        } else if (panType === 'xunlei') {
                            result = await callXunleiTransferAPI(fileData, path);
                            showToast(`✅ 转存成功！已保存 ${fileData.length} 个文件`, 'success');
                        }
                        
                    } catch (error) {
                        if (error.message !== '用户取消') {
                            console.error('❌ 操作失败:', error);
                            showToast(`❌ ${error.message}`, 'error');
                        }
                    }
                }, true);  // 使用捕获阶段，确保最先执行
            }
        };
        
        // 立即检查
        checkButton();
        
        // 定期检查（适配SPA）
        setInterval(checkButton, 1000);
    }
    
    // 监听转存对话框的出现（用于填充路径）
    function watchTransferDialog() {
        const panType = detectPanType();
        if (!panType) return;
        
        console.log('👀 开始监听转存对话框...');
        console.log('  当前网盘类型:', panType);
        
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType !== 1) continue;
                    
                    // 打印所有新增的DOM节点（调试用）
                    if (node.classList?.length > 0) {
                        console.log('🔍 [DOM变化] 新增节点:', node.className);
                    }
                    
                    let isTransferDialog = false;
                    
                    // 百度网盘转存对话框特征
                    if (panType === 'baidu') {
                        const hasModal = node.classList?.contains('nd-modal') || 
                                       node.classList?.contains('share-transfer-dialog') ||
                                       node.classList?.contains('after-trans-dialog');  // 新增
                        const hasPathInput = node.querySelector?.('.save-path-inputbox') || 
                                           node.querySelector?.('input[class*="save-path"]') ||
                                           node.querySelector?.('input[placeholder*="保存到"]');
                        
                        console.log('  检查百度对话框:', { hasModal, hasPathInput, classList: Array.from(node.classList || []) });
                        
                        isTransferDialog = hasModal || hasPathInput;
                    }
                    // 夸克网盘
                    else if (panType === 'quark') {
                        isTransferDialog = node.classList?.contains('ant-modal') &&
                                          node.querySelector?.('input[placeholder*="保存"]');
                    }
                    // 迅雷网盘
                    else if (panType === 'xunlei') {
                        isTransferDialog = node.querySelector?.('input[placeholder*="保存"]');
                    }
                    
                    if (isTransferDialog) {
                        console.log('🎉 检测到转存对话框！');
                        console.log('  对话框节点:', node);
                        
                        // 立即处理，不要延迟
                        (async () => {
                            try {
                                const path = await showMappingDialog(panType);
                                
                                console.log('📝 用户选择路径:', path);
                                
                                // 等待一下，确保输入框已渲染
                                await new Promise(resolve => setTimeout(resolve, 100));
                                
                                // 填充路径
                                let success = false;
                                if (panType === 'baidu') {
                                    success = fillBaiduPath(path);
                                } else if (panType === 'quark') {
                                    success = fillQuarkPath(path);
                                } else if (panType === 'xunlei') {
                                    success = fillXunleiPath(path);
                                }
                                
                                if (success) {
                                    showToast('✅ 路径已自动填充', 'success');
                                } else {
                                    showToast('⚠️ 填充失败，请手动输入', 'warning');
                                }
                            } catch (error) {
                                if (error.message !== '用户取消') {
                                    console.error('❌ 填充路径失败:', error);
                                    showToast('❌ 操作失败', 'error');
                                }
                            }
                        })();
                    }
                }
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('✅ 监听器已启动');
    }
    
    // 显示提示
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `mp-autofill-toast mp-autofill-toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    // 添加样式
    GM_addStyle(`
        .mp-autofill-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            animation: fadeIn 0.2s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .mp-autofill-dialog {
            background: white;
            border-radius: 12px;
            padding: 24px;
            width: 500px;
            max-width: 90vw;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            animation: slideUp 0.3s ease;
        }
        
        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .mp-autofill-search {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 15px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        
        .mp-autofill-search:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .mp-autofill-list {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            max-height: 400px;
        }
        
        .mp-autofill-item {
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .mp-autofill-item:hover {
            background: #f5f5f5;
            border-color: #667eea;
            transform: translateX(4px);
        }
        
        .mp-autofill-btn {
            flex: 1;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .mp-autofill-btn-secondary {
            background: #667eea;
            color: white;
        }
        
        .mp-autofill-btn-secondary:hover {
            background: #5568d3;
        }
        
        .mp-autofill-btn-cancel {
            background: #f0f0f0;
            color: #666;
        }
        
        .mp-autofill-btn-cancel:hover {
            background: #e0e0e0;
        }
        
        .mp-autofill-toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            z-index: 1000000;
            animation: slideDown 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            color: white;
        }
        
        @keyframes slideDown {
            from { transform: translate(-50%, -20px); opacity: 0; }
            to { transform: translate(-50%, 0); opacity: 1; }
        }
        
        .mp-autofill-toast-success {
            background: #4caf50;
        }
        
        .mp-autofill-toast-warning {
            background: #ff9800;
        }
        
        .mp-autofill-toast-error {
            background: #f44336;
        }
        
        .mp-autofill-toast-info {
            background: #2196f3;
        }
    `);
    
    // 启动劫持
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hijackSaveButton);
    } else {
        hijackSaveButton();
    }
    
})();
