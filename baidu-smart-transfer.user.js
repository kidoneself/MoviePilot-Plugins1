// ==UserScript==
// @name         百度网盘智能转存（广告过滤版）
// @namespace    baidu.smart.transfer
// @version      1.0
// @description  百度网盘智能转存，自动过滤广告，智能选择策略
// @match        https://pan.baidu.com/s/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-idle
// @connect      10.10.10.17
// @connect      pan.baidu.com
// ==/UserScript==

(function() {
    'use strict';
    
    const API_BASE = 'http://10.10.10.17:9889/api';
    
    console.log('🎬 百度网盘智能转存脚本已启动');
    
    // ==================== 工具函数 ====================
    
    // 获取Cookie值
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
        return null;
    }
    
    // 获取bdstoken
    function getBdstoken() {
        // 优先从yunData获取
        if (typeof yunData !== 'undefined' && yunData.bdstoken) {
            return yunData.bdstoken;
        }
        // 从Cookie获取
        const csrfToken = getCookie('csrfToken');
        if (csrfToken) return csrfToken;
        
        // 从页面查找
        const match = document.body.innerHTML.match(/bdstoken["\s:=]+([a-zA-Z0-9]+)/);
        return match ? match[1] : null;
    }
    
    // 获取sekey (BDCLND Cookie)
    function getSekey() {
        return getCookie('BDCLND') || '';
    }
    
    // 从URL获取shorturl和提取码
    function parseShareUrl() {
        const url = location.href;
        const match = url.match(/\/s\/1([a-zA-Z0-9_-]+)/);
        if (!match) {
            throw new Error('无法从URL获取shorturl');
        }
        
        const shorturl = match[1];
        const urlParams = new URLSearchParams(location.search);
        const pwd = urlParams.get('pwd') || '';
        
        console.log('📋 分享参数:', { shorturl, pwd });
        return { shorturl, pwd };
    }
    
    // ==================== 广告过滤 ====================
    
    // 判断是否为广告文件
    function isAdFile(fileName, fileSize) {
        const AD_KEYWORDS = [
            '群', '更新', '关注', '订阅', '微信', 'QQ', '频道', 
            '电报', 'Telegram', '推荐', '福利', '免费', 
            '网址', '网站', '发布', '必看', '说明', '广告', 
            '二维码', '热门影视', '资源', '入群', '扫码',
            '夸克资源', '阿里资源', '百度资源', '更多资源'
        ];
        
        const AD_EXTENSIONS = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
            '.txt', '.nfo', '.url'
        ];
        
        const name = fileName.toLowerCase();
        const ext = name.substring(name.lastIndexOf('.'));
        
        // 规则1: 小图片/文本 + 关键词
        if (AD_EXTENSIONS.includes(ext) && fileSize < 5*1024*1024) {
            for (const keyword of AD_KEYWORDS) {
                if (name.includes(keyword.toLowerCase())) {
                    return true;
                }
            }
        }
        
        // 规则2: 很小的文本文件
        if (['.txt', '.nfo', '.url'].includes(ext) && fileSize < 500*1024) {
            return true;
        }
        
        return false;
    }
    
    // ==================== API调用 ====================
    
    // 验证提取码
    async function verifyPassword(shorturl, pwd) {
        if (!pwd) {
            console.log('⚠️ 无提取码，跳过验证');
            return true;
        }
        
        try {
            const bdstoken = getBdstoken();
            const url = `/share/verify?surl=${shorturl}&t=${Date.now()}` +
                       `&bdstoken=${bdstoken || ''}&channel=chunlei&web=1&app_id=250528&clienttype=0`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `pwd=${encodeURIComponent(pwd)}`,
                credentials: 'include'
            });
            
            const data = await response.json();
            console.log('🔑 验证提取码:', data);
            
            if (data.errno === 0) {
                console.log('✅ 提取码验证成功');
                return true;
            } else {
                console.error('❌ 提取码验证失败:', data.errno);
                return false;
            }
        } catch (error) {
            console.error('❌ 验证提取码出错:', error);
            return false;
        }
    }
    
    // 获取分享文件列表
    async function getFileList(shorturl, dir = '/') {
        try {
            const bdstoken = getBdstoken();
            const sekey = getSekey();
            
            // 从全局变量获取 shareid 和 uk
            let shareid = '';
            let uk = '';
            if (typeof yunData !== 'undefined') {
                shareid = yunData.shareid || yunData.share_id || '';
                uk = yunData.share_uk || yunData.uk || '';
            }
            
            const isRoot = (dir === '/');
            let url = `/share/list?`;
            
            // 添加参数
            const params = new URLSearchParams({
                shorturl: shorturl,
                dir: dir,
                root: isRoot ? '1' : '0',
                page: '1',
                num: '1000',
                order: 'name',
                desc: '0',
                showempty: '0',
                web: '1',
                channel: 'chunlei',
                app_id: '250528',
                clienttype: '0'
            });
            
            if (bdstoken) params.append('bdstoken', bdstoken);
            if (sekey) params.append('sekey', sekey);
            if (shareid) params.append('shareid', shareid);
            if (uk) params.append('uk', uk);
            
            url += params.toString();
            
            console.log('🌐 请求URL参数:', { shorturl, dir, sekey: sekey ? '有' : '无', shareid, uk });
            
            const response = await fetch(url, {
                credentials: 'include'
            });
            
            const data = await response.json();
            console.log('📂 文件列表响应:', data);
            
            if (data.errno === 0) {
                return {
                    list: data.list || [],
                    shareid: data.share_id || shareid,
                    uk: data.uk || uk
                };
            } else {
                throw new Error(`获取文件列表失败: errno=${data.errno}, ${data.show_msg || ''}`);
            }
        } catch (error) {
            console.error('❌ 获取文件列表出错:', error);
            throw error;
        }
    }
    
    // 通过OpenList创建百度文件夹（百度使用路径，不是fid）
    async function ensureBaiduFolderExists(fullPath) {
        console.log('🔍 通过OpenList创建百度文件夹:', fullPath);
        
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
                        const result = JSON.parse(response.responseText);
                        
                        if (result.success) {
                            let returnPath = result.path || fullPath;
                            // 去掉OpenList的挂载点前缀 /baidu/
                            if (returnPath.startsWith('/baidu/')) {
                                returnPath = returnPath.substring(6); // 去掉 /baidu
                            }
                            console.log('✅ 百度文件夹已就绪:', returnPath);
                            resolve(returnPath);
                        } else {
                            // 即使创建失败也返回路径（可能已存在）
                            console.warn('⚠️ OpenList响应:', result);
                            resolve(fullPath);
                        }
                    } catch (e) {
                        // 解析失败也返回路径
                        console.warn('⚠️ OpenList解析失败，使用原路径');
                        resolve(fullPath);
                    }
                },
                onerror: (error) => {
                    // 网络失败也返回路径
                    console.warn('⚠️ OpenList网络失败，使用原路径');
                    resolve(fullPath);
                }
            });
        });
    }
    
    // 获取映射列表
    function fetchMappings(page = 1, search = '') {
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
    
    // 执行转存
    async function transferFiles(shareid, uk, fsidList, targetPath = '/') {
        try {
            const bdstoken = getBdstoken();
            const sekey = getSekey();
            
            if (!sekey) {
                throw new Error('无法获取sekey，请先验证提取码');
            }
            
            const url = `/share/transfer?` +
                       `shareid=${shareid}` +
                       `&from=${uk}` +
                       `&sekey=${encodeURIComponent(sekey)}` +
                       `&ondup=newcopy` +
                       `&async=1` +
                       `&bdstoken=${bdstoken || ''}` +
                       `&channel=chunlei&web=1&app_id=250528&clienttype=0`;
            
            const formData = new URLSearchParams();
            formData.append('fsidlist', `[${fsidList.join(',')}]`);
            formData.append('path', targetPath);
            
            console.log('🚀 转存参数:', {
                shareid, uk, sekey: sekey.substring(0, 20) + '...', 
                fsidList, targetPath, bdstoken
            });
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData.toString(),
                credentials: 'include'
            });
            
            const data = await response.json();
            console.log('📦 转存结果:', data);
            
            return data;
        } catch (error) {
            console.error('❌ 转存出错:', error);
            throw error;
        }
    }
    
    // ==================== 主流程 ====================
    
    // 智能转存（包含广告过滤）
    async function smartTransfer(targetPath) {
        try {
            console.log('🚀 开始智能转存');
            console.log('  目标路径:', targetPath);
            
            // 1. 解析URL
            showToast('📋 正在获取文件列表...', 'info');
            const { shorturl, pwd } = parseShareUrl();
            
            // 2. 验证提取码
            if (pwd) {
                const verified = await verifyPassword(shorturl, pwd);
                if (!verified) {
                    showToast('❌ 提取码验证失败', 'error');
                    return;
                }
                // 等待Cookie生效
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // 3. 获取文件列表（从hash获取当前目录）
            let currentDir = '/';
            const hashMatch = location.hash.match(/path=([^&]+)/);
            if (hashMatch) {
                currentDir = decodeURIComponent(hashMatch[1]);
                console.log('  📁 当前目录:', currentDir);
            }
            
            const { list, shareid, uk } = await getFileList(shorturl, currentDir);
            if (!list || list.length === 0) {
                showToast('⚠️ 没有找到文件', 'warning');
                return;
            }
            
            console.log('📊 文件统计:');
            console.log('  总文件数:', list.length);
            
            // 4. 过滤广告文件
            const adFiles = list.filter(f => isAdFile(f.server_filename, f.size));
            const cleanFiles = list.filter(f => !isAdFile(f.server_filename, f.size));
            
            console.log('  广告文件:', adFiles.length, '个');
            adFiles.forEach(f => console.log('    🚫', f.server_filename));
            console.log('  干净文件:', cleanFiles.length, '个');
            
            if (adFiles.length > 0) {
                showToast(`🚫 已过滤 ${adFiles.length} 个广告文件`, 'warning');
            }
            
            if (cleanFiles.length === 0) {
                showToast('⚠️ 过滤后没有可转存的文件', 'warning');
                return;
            }
            
            // 5. 获取用户勾选的文件（从DOM）
            let selectedFids = new Set();
            let userSelectedCount = 0;
            
            // 从DOM获取选中的文件（通过 JS-item-active 类名）
            try {
                const checkedItems = document.querySelectorAll('dd.g-clearfix.JS-item-active[_position]');
                console.log('  📋 DOM选中元素数量:', checkedItems.length);
                
                checkedItems.forEach(item => {
                    const position = parseInt(item.getAttribute('_position'));
                    if (!isNaN(position) && list[position]) {
                        const file = list[position];
                        selectedFids.add(file.fs_id);
                        console.log(`    - 位置${position}: ${file.server_filename} (fs_id: ${file.fs_id})`);
                    }
                });
                
                userSelectedCount = checkedItems.length;
                console.log('  ✅ 识别到选中文件:', selectedFids.size, '个');
            } catch (e) {
                console.warn('  ⚠️ 无法从DOM获取选中文件:', e);
            }
            
            // 如果没有检测到选中，默认全选所有非广告文件
            if (selectedFids.size === 0) {
                console.log('  ✅ 未检测到勾选，默认转存所有非广告文件');
                cleanFiles.forEach(f => selectedFids.add(f.fs_id));
                userSelectedCount = list.length;
            }
            
            // 6. 计算实际要转存的文件（干净 + 已勾选）
            const toTransferFiles = cleanFiles.filter(f => 
                selectedFids.has(f.fs_id)
            );
            
            if (toTransferFiles.length === 0) {
                showToast('⚠️ 没有可转存的文件', 'warning');
                return;
            }
            
            console.log('  用户勾选:', userSelectedCount, '个（含广告）');
            console.log('  实际转存:', toTransferFiles.length, '个（已过滤广告）');
            
            // 7. 确保目标文件夹存在
            showToast('📁 正在创建目标目录...', 'info');
            const actualPath = await ensureBaiduFolderExists(targetPath);
            
            // 8. 提取fs_id列表
            const fsidList = toTransferFiles.map(f => f.fs_id);
            
            // 9. 执行转存
            showToast(`⏳ 正在转存 ${toTransferFiles.length} 个文件...`, 'info');
            const result = await transferFiles(shareid, uk, fsidList, actualPath);
            
            if (result.errno === 0) {
                console.log('✅ 转存完成！');
                console.log('📊 最终统计:');
                console.log('  当前文件夹文件数:', list.length);
                console.log('  过滤广告:', adFiles.length, '个');
                console.log('  实际转存:', toTransferFiles.length, '个');
                
                showToast(
                    `✅ 转存成功！\n` +
                    `总文件: ${list.length}\n` +
                    `过滤广告: ${adFiles.length}\n` +
                    `实际转存: ${toTransferFiles.length}`,
                    'success'
                );
                
                return {
                    success: true,
                    total: list.length,
                    filtered: adFiles.length,
                    transferred: toTransferFiles.length
                };
            } else if (result.errno === 12) {
                showToast('⚠️ 文件已存在', 'warning');
            } else if (result.errno === -9) {
                showToast('❌ 需要登录百度网盘', 'error');
            } else {
                showToast(`❌ 转存失败: ${result.show_msg || result.errno}`, 'error');
            }
            
        } catch (error) {
            console.error('❌ 智能转存失败:', error);
            showToast(`❌ 转存失败: ${error.message}`, 'error');
            throw error;
        }
    }
    
    // 显示映射选择对话框
    function showMappingDialog() {
        return new Promise(async (resolve, reject) => {
            try {
                let currentPage = 1;
                let searchKeyword = '';
                let totalPages = 1;
                
                // 创建遮罩层
                const overlay = document.createElement('div');
                overlay.className = 'baidu-overlay';
                
                // 创建对话框
                const dialog = document.createElement('div');
                dialog.className = 'baidu-dialog';
                
                // 标题
                const title = document.createElement('h3');
                title.textContent = '选择转存路径';
                title.style.margin = '0 0 15px 0';
                dialog.appendChild(title);
                
                // 提示
                const hint = document.createElement('div');
                hint.style.cssText = 'padding: 10px; background: #fff3cd; border-radius: 4px; margin-bottom: 15px; font-size: 13px; color: #856404;';
                hint.textContent = '💡 选择映射后会自动过滤广告并转存';
                dialog.appendChild(hint);
                
                // 搜索框
                const searchBox = document.createElement('input');
                searchBox.type = 'text';
                searchBox.placeholder = '搜索映射名称（回车搜索）...';
                searchBox.className = 'baidu-search';
                dialog.appendChild(searchBox);
                
                // 映射列表容器
                const listContainer = document.createElement('div');
                listContainer.className = 'baidu-list';
                
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
                            item.className = 'baidu-item';
                            
                            const targetPath = mapping.baidu_name;
                            
                            if (!targetPath) {
                                item.style.opacity = '0.5';
                                item.style.cursor = 'not-allowed';
                            }
                            
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
                                    let fullPath = targetPath;
                                    if (mapping.category) {
                                        fullPath = `/A-闲鱼影视（自动更新）/${mapping.category}/${targetPath}`;
                                    } else {
                                        fullPath = `/A-闲鱼影视（自动更新）/${targetPath}`;
                                    }
                                    
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
                    
                    const pageInfo = document.createElement('span');
                    pageInfo.textContent = `${currentPage} / ${totalPages}`;
                    pageInfo.style.cssText = 'padding: 0 10px;';
                    pagination.appendChild(pageInfo);
                    
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
                
                // 搜索事件
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
                manualBtn.className = 'baidu-btn baidu-btn-secondary';
                manualBtn.onclick = () => {
                    const path = prompt('请输入转存路径（例如：/A-闲鱼影视（自动更新）/电影/华语）：', '/A-闲鱼影视（自动更新）/');
                    if (path) {
                        overlay.remove();
                        resolve(path);
                    }
                };
                buttonGroup.appendChild(manualBtn);
                
                // 取消按钮
                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = '取消';
                cancelBtn.className = 'baidu-btn baidu-btn-cancel';
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
    
    // 显示提示（支持堆叠）
    function showToast(message, type = 'info') {
        // 创建容器（如果不存在）
        let container = document.getElementById('baidu-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'baidu-toast-container';
            container.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000000; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `baidu-toast baidu-toast-${type}`;
        toast.textContent = message;
        toast.style.whiteSpace = 'pre-line';
        toast.style.pointerEvents = 'auto';
        
        // 错误和警告显示更久
        const duration = type === 'error' ? 5000 : type === 'warning' ? 4000 : 3000;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                toast.remove();
                // 如果容器空了，删除容器
                if (container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }, duration);
    }
    
    // ==================== UI ====================
    
    function addSmartTransferButton() {
        console.log('🎯 开始添加智能转存按钮...');
        
        const checkButton = () => {
            // 查找保存按钮容器
            const saveButton = document.querySelector('a[title="保存到网盘"]') ||
                              document.querySelector('.g-button-blue-large') ||
                              document.querySelector('[class*="save"]');
            
            if (saveButton && !document.getElementById('baidu-smart-save-btn')) {
                console.log('✅ 找到保存按钮，准备添加智能转存按钮');
                
                // 创建新的智能转存按钮
                const smartButton = document.createElement('button');
                smartButton.id = 'baidu-smart-save-btn';
                smartButton.style.cssText = `
                    margin-left: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                    border: none;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
                    height: 36px;
                    line-height: 20px;
                `;
                smartButton.textContent = '🎯 智能转存';
                
                // 添加悬停效果
                smartButton.addEventListener('mouseenter', () => {
                    smartButton.style.transform = 'translateY(-2px)';
                    smartButton.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
                });
                smartButton.addEventListener('mouseleave', () => {
                    smartButton.style.transform = 'translateY(0)';
                    smartButton.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
                });
                
                // 点击事件
                smartButton.addEventListener('click', async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('🎯 智能转存按钮被点击');
                    
                    try {
                        // 1. 弹出映射选择
                        const path = await showMappingDialog();
                        console.log('📍 用户选择路径:', path);
                        
                        // 2. 智能转存
                        const result = await smartTransfer(path);
                        
                        if (result && result.success) {
                            // 成功消息已在 smartTransfer 中显示
                            console.log('✅ 转存流程完成');
                        }
                        
                    } catch (error) {
                        if (error.message !== '用户取消') {
                            console.error('❌ 操作失败:', error);
                            console.error('❌ 错误堆栈:', error.stack);
                        }
                    }
                }, true);
                
                // 插入到原按钮后面
                saveButton.parentNode.insertBefore(smartButton, saveButton.nextSibling);
                console.log('✅ 智能转存按钮已添加');
            }
        };
        
        // 立即检查
        checkButton();
        
        // 定期检查（适配SPA）
        setInterval(checkButton, 1000);
    }
    
    // ==================== 样式 ====================
    
    GM_addStyle(`
        .baidu-overlay {
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
        
        .baidu-dialog {
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
        
        .baidu-search {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 15px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        
        .baidu-search:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .baidu-list {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            max-height: 400px;
        }
        
        .baidu-item {
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .baidu-item:hover {
            background: #f5f5f5;
            border-color: #667eea;
            transform: translateX(4px);
        }
        
        .baidu-btn {
            flex: 1;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .baidu-btn-secondary {
            background: #667eea;
            color: white;
        }
        
        .baidu-btn-secondary:hover {
            background: #5568d3;
        }
        
        .baidu-btn-cancel {
            background: #f0f0f0;
            color: #666;
        }
        
        .baidu-btn-cancel:hover {
            background: #e0e0e0;
        }
        
        .baidu-toast {
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            color: white;
            max-width: 400px;
            animation: slideIn 0.3s ease;
            transition: opacity 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .baidu-toast-success {
            background: #4caf50;
        }
        
        .baidu-toast-warning {
            background: #ff9800;
        }
        
        .baidu-toast-error {
            background: #f44336;
        }
        
        .baidu-toast-info {
            background: #2196f3;
        }
    `);
    
    // ==================== 启动 ====================
    
    // 页面加载完成后添加按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addSmartTransferButton);
    } else {
        addSmartTransferButton();
    }
    
    console.log('✅ 百度网盘智能转存脚本初始化完成');
    
})();
