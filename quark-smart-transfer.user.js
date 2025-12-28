// ==UserScript==
// @name         夸克网盘智能转存（广告过滤版）
// @namespace    quark.smart.transfer
// @version      1.0
// @description  夸克网盘智能转存，自动过滤广告，智能选择策略
// @match        https://pan.quark.cn/s/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @run-at       document-start
// @connect      10.10.10.17
// @connect      drive-h.quark.cn
// @connect      drive-pc.quark.cn
// ==/UserScript==

(function() {
    'use strict';
    
    const API_BASE = 'http://10.10.10.17:9889/api';
    
    console.log('🎬 夸克网盘智能转存脚本已启动');
    
    // ==================== 核心功能 ====================
    
    // 获取夸克分享参数
    async function getQuarkShareParams() {
        const url = location.href;
        const match = url.match(/\/s\/([^#/?]+)/);
        if (!match) {
            throw new Error('无法从URL获取pwd_id');
        }
        
        const pwd_id = match[1];
        console.log('📋 分享ID (pwd_id):', pwd_id);
        
        // 从performance API获取stoken
        let stoken = null;
        const entries = performance.getEntries();
        for (const entry of entries) {
            if (entry.name && entry.name.includes('quark.cn') && entry.name.includes('stoken=')) {
                const stokenMatch = entry.name.match(/stoken=([^&]+)/);
                if (stokenMatch) {
                    stoken = decodeURIComponent(stokenMatch[1]);
                    console.log('🔑 从performance获取stoken');
                    break;
                }
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
                },
                cookie: document.cookie,
                onload: (response) => {
                    try {
                        const result = JSON.parse(response.responseText);
                        
                        if (result.status === 200 && result.code === 0) {
                            const data = result.data;
                            
                            // 从URL hash获取当前文件夹ID
                            let pdir_fid = data.share.first_fid;
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
                            reject(new Error(`获取分享详情失败: status=${result.status}, code=${result.code}`));
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
    
    // 获取夸克完整文件列表（包含share_fid_token）
    async function getQuarkCompleteFileList() {
        console.log('📋 获取夸克完整文件列表');
        
        const shareParams = await getQuarkShareParams();
        
        const timestamp = Date.now();
        const apiUrl = `https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pr=ucpro&fr=pc&uc_param_str=&ver=2&pwd_id=${shareParams.pwd_id}&stoken=${encodeURIComponent(shareParams.stoken)}&pdir_fid=${shareParams.pdir_fid}&force=0&_page=1&_size=100&_fetch_banner=0&_fetch_share=0&fetch_relate_conversation=0&_fetch_total=1&_sort=file_type:asc,file_name:asc&__dt=${Math.floor(Math.random() * 10000)}&__t=${timestamp}`;
        
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
                        if (result.status === 200 && result.data && result.data.list) {
                            console.log('✅ 获取文件列表成功，数量:', result.data.list.length);
                            resolve({
                                files: result.data.list,
                                share_params: shareParams
                            });
                        } else {
                            reject(new Error('获取文件列表失败'));
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
                if (name.includes(keyword)) {
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
    
    // 通过OpenList确保目录存在并获取ID
    async function ensureQuarkFolderExists(fullPath) {
        console.log('🔍 通过OpenList获取文件夹ID:', fullPath);
        
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
                            resolve(result.fid);
                        } else {
                            reject(new Error(`获取文件夹ID失败: ${JSON.stringify(result)}`));
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
    
    // 智能转存（包含广告过滤 + 智能选择策略）
    async function smartTransfer(targetPath) {
        console.log('🚀 开始智能转存');
        console.log('  目标路径:', targetPath);
        
        // 1. 获取完整文件列表
        showToast('📋 正在获取文件列表...', 'info');
        const { files, share_params } = await getQuarkCompleteFileList();
        
        console.log('📊 文件统计:');
        console.log('  总文件数:', files.length);
        
        // 2. 过滤广告文件
        const adFiles = files.filter(f => isAdFile(f.file_name, f.size));
        const cleanFiles = files.filter(f => !isAdFile(f.file_name, f.size));
        
        console.log('  广告文件:', adFiles.length, '个');
        adFiles.forEach(f => console.log('    🚫', f.file_name));
        console.log('  干净文件:', cleanFiles.length, '个');
        
        if (adFiles.length > 0) {
            showToast(`🚫 已过滤 ${adFiles.length} 个广告文件`, 'warning');
        }
        
        // 3. 获取用户勾选状态（从夸克内部状态读取，避免虚拟滚动问题）
        let selectedFids = new Set();
        let userSelectedCount = 0;
        let readMethod = 'unknown';
        
        // 方法1: 尝试从 React 组件状态读取（夸克使用 React）
        try {
            const tableElement = document.querySelector('.ant-table-tbody');
            if (tableElement) {
                console.log('  🔍 开始查找 React 状态...');
                
                // 查找 React Fiber 节点
                const fiberKey = Object.keys(tableElement).find(key => 
                    key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')
                );
                console.log('  🔍 Fiber Key:', fiberKey);
                
                if (fiberKey) {
                    let fiber = tableElement[fiberKey];
                    let depth = 0;
                    const maxDepth = 50; // 限制遍历深度
                    
                    // 向上遍历找到包含 selectedRowKeys 的组件
                    while (fiber && depth < maxDepth) {
                        // 检查多个可能的位置（优先级从高到低）
                        let selectedKeys = null;
                        let source = '';
                        
                        // 优先级1: memoizedProps.rowSelection.selectedRowKeys
                        if (fiber.memoizedProps?.rowSelection?.selectedRowKeys) {
                            selectedKeys = fiber.memoizedProps.rowSelection.selectedRowKeys;
                            source = 'memoizedProps.rowSelection';
                        }
                        // 优先级2: memoizedProps.selectedRowKeys
                        else if (fiber.memoizedProps?.selectedRowKeys) {
                            selectedKeys = fiber.memoizedProps.selectedRowKeys;
                            source = 'memoizedProps';
                        }
                        // 优先级3: memoizedState.selectedRowKeys
                        else if (fiber.memoizedState?.selectedRowKeys) {
                            selectedKeys = fiber.memoizedState.selectedRowKeys;
                            source = 'memoizedState';
                        }
                        // 优先级4: stateNode.state.selectedRowKeys
                        else if (fiber.stateNode?.state?.selectedRowKeys) {
                            selectedKeys = fiber.stateNode.state.selectedRowKeys;
                            source = 'stateNode.state';
                        }
                        
                        if (selectedKeys && Array.isArray(selectedKeys) && selectedKeys.length > 0) {
                            console.log(`  ✅ 从 React Fiber 读取到选中项: ${selectedKeys.length} 个 (深度: ${depth}, 来源: ${source})`);
                            selectedKeys.forEach(key => selectedFids.add(String(key)));
                            userSelectedCount = selectedKeys.length;
                            readMethod = 'react-fiber';
                            break;
                        }
                        
                        fiber = fiber.return;
                        depth++;
                    }
                    
                    if (depth >= maxDepth && selectedFids.size === 0) {
                        console.warn('  ⚠️ React Fiber 遍历达到最大深度，未找到 selectedRowKeys');
                    }
                }
            }
        } catch (e) {
            console.warn('  ⚠️ 从 React 状态读取异常:', e.message, e.stack);
        }
        
        // 方法2: 尝试从 window 对象查找（可能有全局状态）
        if (selectedFids.size === 0 && window.__INITIAL_STATE__) {
            try {
                console.log('  🔍 尝试从 window.__INITIAL_STATE__ 读取...');
                // 这里可能需要根据实际结构调整
                const state = window.__INITIAL_STATE__;
                // 打印结构供调试
                console.log('  🔍 __INITIAL_STATE__ keys:', Object.keys(state || {}));
            } catch (e) {
                console.warn('  ⚠️ 从 window 状态读取失败:', e.message);
            }
        }
        
        // 方法3: 检查是否全选
        if (selectedFids.size === 0) {
            const selectAllCheckbox = document.querySelector('thead .ant-checkbox-input');
            const isAllSelected = selectAllCheckbox?.checked;
            
            if (isAllSelected) {
                console.log('  ✅ 检测到全选状态，将转存所有非广告文件');
                cleanFiles.forEach(f => selectedFids.add(f.fid));
                userSelectedCount = files.length; // 包括广告
                readMethod = 'select-all';
            } else {
                // 兜底：从 DOM 读取（可能不准确）
                const selectedRows = document.querySelectorAll('tr.ant-table-row-selected[data-row-key]');
                console.warn('  ⚠️ 无法从内部状态读取，从DOM读取（可能因虚拟滚动不准确）:', selectedRows.length, '个');
                console.warn('  ⚠️ 建议：使用全选功能，或将所有要选的文件滚动到可见区域');
                selectedRows.forEach(row => {
                    selectedFids.add(row.getAttribute('data-row-key'));
                });
                userSelectedCount = selectedRows.length;
                readMethod = 'dom-fallback';
            }
        }
        
        // 4. 计算实际要转存的文件（干净 + 已勾选）
        const toTransferFiles = cleanFiles.filter(f => selectedFids.has(f.fid));
        
        if (toTransferFiles.length === 0) {
            throw new Error('没有可转存的文件（请勾选文件或检查是否全是广告）');
        }
        
        console.log('  用户勾选:', userSelectedCount, '个（含广告）');
        console.log('  实际转存:', toTransferFiles.length, '个（已过滤广告）');
        
        // 5. 智能选择策略
        const ratio = toTransferFiles.length / cleanFiles.length;
        console.log('  选择比例:', (ratio * 100).toFixed(1) + '%');
        
        // 6. 确保目标文件夹存在
        showToast('📁 正在创建目标目录...', 'info');
        const targetFid = await ensureQuarkFolderExists(targetPath);
        
        let saveData;
        let modeDesc;
        
        if (ratio === 1) {
            // 全选模式
            modeDesc = '全选模式';
            saveData = {
                pwd_id: share_params.pwd_id,
                stoken: share_params.stoken,
                pdir_fid: share_params.pdir_fid,
                to_pdir_fid: targetFid,
                pdir_save_all: true,
                scene: 'link'
            };
            
            // 如果有广告需要排除
            if (adFiles.length > 0) {
                saveData.exclude_fids = adFiles.map(f => f.fid);
                modeDesc += ' + 排除广告';
            }
        } else if (ratio < 0.5) {
            // 包含模式（选择较少）
            modeDesc = '包含模式（选择较少，使用fid_list）';
            saveData = {
                pwd_id: share_params.pwd_id,
                stoken: share_params.stoken,
                pdir_fid: share_params.pdir_fid,
                to_pdir_fid: targetFid,
                fid_list: toTransferFiles.map(f => f.fid),
                fid_token_list: toTransferFiles.map(f => f.share_fid_token),
                scene: 'link'
            };
        } else {
            // 排除模式（选择较多）
            modeDesc = '排除模式（选择较多，使用exclude_fids）';
            const excludeFiles = cleanFiles.filter(f => !toTransferFiles.find(tf => tf.fid === f.fid));
            saveData = {
                pwd_id: share_params.pwd_id,
                stoken: share_params.stoken,
                pdir_fid: share_params.pdir_fid,
                to_pdir_fid: targetFid,
                pdir_save_all: true,
                exclude_fids: excludeFiles.map(f => f.fid),
                scene: 'link'
            };
        }
        
        console.log('  📝 使用策略:', modeDesc);
        console.log('  📤 转存参数:', saveData);
        
        // 7. 调用转存API
        showToast(`⏳ 正在转存 ${toTransferFiles.length} 个文件...`, 'info');
        
        const timestamp = Date.now();
        const saveUrl = `https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save?pr=ucpro&fr=pc&uc_param_str=&__dt=${Math.floor(Math.random() * 10000)}&__t=${timestamp}`;
        
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
                        
                        if (result.status === 200 && result.data && result.data.task_id) {
                            console.log('  ✅ 转存任务创建成功, task_id:', result.data.task_id);
                            resolve(result.data.task_id);
                        } else {
                            reject(new Error(`转存失败: ${result.message || JSON.stringify(result)}`));
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
        
        // 8. 轮询任务状态
        console.log('⏳ 等待转存任务完成...');
        let retryCount = 0;
        const maxRetries = 30;
        
        while (retryCount < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
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
            
            if (taskResult.status === 200 && taskResult.data) {
                const status = taskResult.data.status;
                if (status === 2) {
                    console.log('✅ 转存完成！');
                    console.log('📊 最终统计:');
                    console.log('  当前文件夹文件数:', files.length);
                    console.log('  过滤广告:', adFiles.length, '个');
                    console.log('  实际转存:', toTransferFiles.length, '个');
                    
                    return {
                        success: true,
                        total: files.length,
                        filtered: adFiles.length,
                        transferred: toTransferFiles.length,
                        mode: modeDesc
                    };
                } else if (status === 3) {
                    throw new Error('转存失败');
                }
            }
            
            retryCount++;
        }
        
        throw new Error('转存超时');
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
                overlay.className = 'quark-overlay';
                
                // 创建对话框
                const dialog = document.createElement('div');
                dialog.className = 'quark-dialog';
                
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
                searchBox.className = 'quark-search';
                dialog.appendChild(searchBox);
                
                // 映射列表容器
                const listContainer = document.createElement('div');
                listContainer.className = 'quark-list';
                
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
                            item.className = 'quark-item';
                            
                            const targetPath = mapping.quark_name;
                            
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
                manualBtn.className = 'quark-btn quark-btn-secondary';
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
                cancelBtn.className = 'quark-btn quark-btn-cancel';
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
    
    // 添加智能转存按钮（不劫持原按钮）
    function addSmartSaveButton() {
        console.log('🎯 开始添加智能转存按钮...');
        
        const checkButton = () => {
            const saveButton = document.querySelector('button.share-save');
            
            if (saveButton && !document.getElementById('quark-smart-save-btn')) {
                console.log('✅ 找到保存按钮，准备添加智能转存按钮');
                
                // 创建新的智能转存按钮
                const smartButton = document.createElement('button');
                smartButton.id = 'quark-smart-save-btn';
                smartButton.className = 'share-save'; // 复用样式
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
                        
                        // 3. 显示结果
                        showToast(
                            `✅ 转存成功！\n` +
                            `总文件: ${result.total}\n` +
                            `过滤广告: ${result.filtered}\n` +
                            `实际转存: ${result.transferred}\n` +
                            `策略: ${result.mode}`,
                            'success'
                        );
                        
                    } catch (error) {
                        if (error.message !== '用户取消') {
                            console.error('❌ 操作失败:', error);
                            console.error('❌ 错误堆栈:', error.stack);
                            showToast(`❌ 操作失败：\n${error.message}\n\n详情请查看控制台（F12）`, 'error');
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
    
    // 显示提示（支持堆叠）
    function showToast(message, type = 'info') {
        // 创建容器（如果不存在）
        let container = document.getElementById('quark-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'quark-toast-container';
            container.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000000; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `quark-toast quark-toast-${type}`;
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
    
    // 添加样式
    GM_addStyle(`
        .quark-overlay {
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
        
        .quark-dialog {
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
        
        .quark-search {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 15px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        
        .quark-search:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .quark-list {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            max-height: 400px;
        }
        
        .quark-item {
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .quark-item:hover {
            background: #f5f5f5;
            border-color: #667eea;
            transform: translateX(4px);
        }
        
        .quark-btn {
            flex: 1;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .quark-btn-secondary {
            background: #667eea;
            color: white;
        }
        
        .quark-btn-secondary:hover {
            background: #5568d3;
        }
        
        .quark-btn-cancel {
            background: #f0f0f0;
            color: #666;
        }
        
        .quark-btn-cancel:hover {
            background: #e0e0e0;
        }
        
        .quark-toast {
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
        
        .quark-toast-success {
            background: #4caf50;
        }
        
        .quark-toast-warning {
            background: #ff9800;
        }
        
        .quark-toast-error {
            background: #f44336;
        }
        
        .quark-toast-info {
            background: #2196f3;
        }
    `);
    
    // 启动智能转存按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addSmartSaveButton);
    } else {
        addSmartSaveButton();
    }
    
})();



