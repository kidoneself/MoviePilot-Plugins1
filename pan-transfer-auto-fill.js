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
// @connect      10.10.10.17
// @connect      drive-h.quark.cn
// @connect      drive-pc.quark.cn
// ==/UserScript==

(function() {
    'use strict';
    
    const API_BASE = 'http://10.10.10.17:9889/api';
    let mappingsCache = null; // 缓存映射列表
    
    console.log('🎬 网盘转存路径自动填充脚本已启动');
    
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
    
    // 创建百度网盘文件夹
    function createBaiduFolder(path) {
        console.log('📁 创建文件夹:', path);
        
        const yunData = unsafeWindow.yunData || {};
        if (!yunData.bdstoken) {
            throw new Error('无法获取bdstoken');
        }
        
        // 生成logid和dp-logid
        const logid = btoa(`${Date.now()}${Math.random()}`).substring(0, 32);
        const dpLogid = Date.now().toString() + Math.floor(Math.random() * 100000);
        
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `https://pan.baidu.com/api/create?a=commit&channel=chunlei&bdstoken=${yunData.bdstoken}&app_id=250528&web=1&logid=${logid}&clienttype=0&dp-logid=${dpLogid}`,
                headers: {
                    'Accept': '*/*',
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
                data: `path=${encodeURIComponent(path)}&isdir=1&size=&block_list=%5B%5D&method=post&dataType=json`,
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        console.log('  创建文件夹响应:', result);
                        
                        // errno=0 成功，errno=-8 已存在也算成功
                        if (result.errno === 0 || result.errno === -8) {
                            console.log('  ✅ 文件夹已就绪:', path);
                            resolve(result);
                        } else {
                            reject(new Error(`创建文件夹失败: errno=${result.errno}`));
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
    }
    
    // 确保目录存在（逐层创建）
    async function ensureFolderExists(fullPath) {
        console.log('🔍 检查并创建目录:', fullPath);
        
        // 分割路径
        const parts = fullPath.split('/').filter(p => p);
        
        // 逐层创建
        let currentPath = '';
        for (const part of parts) {
            currentPath += '/' + part;
            
            try {
                await createBaiduFolder(currentPath);
            } catch (error) {
                console.error(`  ❌ 创建失败: ${currentPath}`, error);
                throw error;
            }
        }
        
        console.log('✅ 目录检查完成:', fullPath);
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
        
        // 先确保目录存在
        try {
            await ensureFolderExists(cleanPath);
        } catch (error) {
            console.error('❌ 创建目录失败:', error);
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
    
    // 获取夸克勾选的文件ID
    function getQuarkSelectedFileIds() {
        const selectedRows = document.querySelectorAll('tr.ant-table-row-selected');
        console.log('📝 找到选中文件:', selectedRows.length, '个');
        
        const fileIds = [];
        selectedRows.forEach(row => {
            const fid = row.getAttribute('data-row-key');
            if (fid) {
                fileIds.push(fid);
                console.log('  ✅ 找到文件ID:', fid);
            }
        });
        
        console.log('🎯 勾选文件ID列表:', fileIds);
        return fileIds;
    }
    
    // 获取夸克分享页参数
    async function getQuarkShareParams() {
        const url = location.href;
        const match = url.match(/\/s\/([^#/?]+)/);
        if (!match) {
            throw new Error('无法从URL获取pwd_id');
        }
        
        const pwd_id = match[1];
        console.log('� 分享ID (pwd_id):', pwd_id);
        
        // 调用API获取分享详情
        const apiUrl = `https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pr=ucpro&fr=pc&pwd_id=${pwd_id}&pdir_fid=0&_page=1&_size=50&_fetch_banner=1&_fetch_share=1&_fetch_total=1`;
        
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
                        if (result.status === 200 && result.data) {
                            // 从URL参数提取stoken（已编码）
                            const urlParams = new URLSearchParams(location.search);
                            const stoken = urlParams.get('stoken') || result.data.stoken;
                            
                            const params = {
                                pwd_id: pwd_id,
                                stoken: stoken,
                                pdir_fid: result.data.share.first_fid
                            };
                            console.log('✅ 获取分享参数成功:', params);
                            resolve(params);
                        } else {
                            reject(new Error('获取分享详情失败'));
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
                        const result = JSON.parse(response.responseText);
                        if (result.success) {
                            console.log('✅ 获取文件夹ID成功:', result.fid);
                            console.log('  OpenList路径:', result.path);
                            resolve(result.fid);
                        } else {
                            reject(new Error('获取文件夹ID失败'));
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
    
    // 夸克转存文件
    async function callQuarkTransferAPI(fileIds, targetPath) {
        console.log('🚀 调用夸克网盘API转存');
        console.log('  文件ID:', fileIds);
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
        
        // 调用转存API
        const saveUrl = 'https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save?pr=ucpro&fr=pc';
        const saveData = {
            pwd_id: shareParams.pwd_id,
            stoken: shareParams.stoken,
            pdir_fid: shareParams.pdir_fid,
            to_pdir_fid: targetFid,
            pdir_save_all: false,
            exclude_fids: fileIds,
            scene: 'link'
        };
        
        console.log('  转存参数:', saveData);
        
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
    
    // 迅雷网盘：填充路径
    function fillXunleiPath(path) {
        console.log('🔧 [迅雷网盘] 开始填充路径:', path);
        
        const pathInput = document.querySelector('input[placeholder*="保存"]');
        
        if (pathInput) {
            pathInput.value = path;
            pathInput.dispatchEvent(new Event('input', { bubbles: true }));
            pathInput.dispatchEvent(new Event('change', { bubbles: true }));
            console.log('✅ 路径已填充');
            return true;
        } else {
            console.error('❌ 未找到路径输入框');
            return false;
        }
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
                        // 1. 获取勾选的文件ID
                        let fileIds;
                        if (panType === 'baidu') {
                            fileIds = getSelectedFileIds();
                        } else if (panType === 'quark') {
                            fileIds = getQuarkSelectedFileIds();
                        }
                        
                        if (!fileIds || fileIds.length === 0) {
                            showToast('⚠️ 请先勾选要转存的文件', 'warning');
                            return;
                        }
                        
                        // 2. 弹出映射选择
                        const path = await showMappingDialog(panType);
                        console.log('📍 用户选择路径:', path);
                        
                        // 3. 调用对应网盘API转存
                        showToast('⏳ 正在转存...', 'info');
                        
                        let result;
                        if (panType === 'baidu') {
                            result = await callBaiduTransferAPI(fileIds, path);
                        } else if (panType === 'quark') {
                            result = await callQuarkTransferAPI(fileIds, path);
                        }
                        
                        showToast(`✅ 转存成功！已保存 ${fileIds.length} 个文件`, 'success');
                        
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
