const API_BASE = '/api';
let currentPage = 1;
let config = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadConfig();
    loadStats();
    loadSourceTree();
    
    // 定时刷新统计信息
    setInterval(loadStats, 30000);
});

// 标签切换
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // 切换到记录页时加载数据
            if (tabName === 'records') {
                loadRecords();
            }
            // 切换到映射管理页时加载数据
            if (tabName === 'mappings') {
                loadMappings();
            }
        });
    });
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const result = await response.json();
        
        if (result.success) {
            config = result.data;
            renderConfig();
            
            // 填充目标目录选择器
            const selector = document.getElementById('targetSelector');
            selector.innerHTML = '<option value="">选择目标目录</option>';
            
            if (config.monitors && config.monitors.length > 0) {
                const targets = config.monitors[0].targets || [];
                targets.forEach((target, index) => {
                    const option = document.createElement('option');
                    // 支持新旧配置格式
                    if (typeof target === 'object' && target !== null) {
                        // 新格式：对象
                        option.value = target.path || '';
                        option.textContent = target.name || `目标${index + 1}`;
                    } else {
                        // 旧格式：字符串
                        option.value = target || '';
                        option.textContent = `目标${index + 1}: ${target}`;
                    }
                    selector.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 根据目标路径获取自定义名称
function getTargetName(targetPath) {
    if (!config || !config.monitors || !config.monitors.length) {
        return null;
    }
    
    const targets = config.monitors[0].targets || [];
    for (let target of targets) {
        if (typeof target === 'object' && target.path) {
            if (targetPath.startsWith(target.path)) {
                return target.name;
            }
        }
    }
    return null;
}

// 渲染配置
function renderConfig() {
    const container = document.getElementById('configContent');
    if (!config || !config.monitors) {
        container.innerHTML = '<p>暂无配置</p>';
        return;
    }
    
    let html = '';
    config.monitors.forEach((monitor, index) => {
        html += `
            <div class="config-item">
                <h4>监控配置 ${index + 1}</h4>
                <p><span class="label">源目录:</span> ${monitor.source}</p>
                <p><span class="label">目标目录:</span></p>
                <ul>
                    ${monitor.targets.map(t => {
                        if (typeof t === 'object' && t.path) {
                            return `<li><strong>${t.name}</strong>: ${t.path}</li>`;
                        }
                        return `<li>${t}</li>`;
                    }).join('')}
                </ul>
                <p><span class="label">状态:</span> ${monitor.enabled ? '✅ 启用' : '❌ 禁用'}</p>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            document.getElementById('todayCount').textContent = data.today_count;
            document.getElementById('totalCount').textContent = data.total_records;
            document.getElementById('successCount').textContent = data.success_count;
            document.getElementById('failedCount').textContent = data.failed_count;
            document.getElementById('totalSize').textContent = formatSize(data.total_size);
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 加载源目录树
async function loadSourceTree() {
    if (!config || !config.monitors || config.monitors.length === 0) {
        setTimeout(loadSourceTree, 1000);
        return;
    }
    
    const sourcePath = config.monitors[0].source;
    await loadTree(sourcePath, 'sourceTree');
}

// 刷新源目录树
function refreshSourceTree() {
    loadSourceTree();
}

// 刷新目标目录树
function refreshTargetTree() {
    const selector = document.getElementById('targetSelector');
    const targetPath = selector.value;
    
    if (!targetPath) {
        document.getElementById('targetTree').innerHTML = '<div class="loading">请选择目标目录</div>';
        return;
    }
    
    loadTree(targetPath, 'targetTree');
}

// 加载目录树
async function loadTree(path, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/tree?path=${encodeURIComponent(path)}&depth=2`);
        const result = await response.json();
        
        if (result.success) {
            container.innerHTML = '';
            renderTreeNode(result.data, container, 0);
        } else {
            container.innerHTML = `<div class="loading">加载失败: ${result.message}</div>`;
        }
    } catch (error) {
        console.error('加载目录树失败:', error);
        container.innerHTML = '<div class="loading">加载失败</div>';
    }
}

// 渲染树节点
function renderTreeNode(node, container, level) {
    if (!node) return;
    
    const item = document.createElement('div');
    item.className = `tree-item ${node.type}`;
    item.style.paddingLeft = `${level * 20}px`;
    
    // 文件夹展开/收起图标（默认折叠）
    let expandIcon = '';
    if (node.type === 'directory' && node.children && node.children.length > 0) {
        expandIcon = '<span class="expand-icon">▶</span>';
        item.classList.add('expandable', 'collapsed');
    }
    
    const icon = node.type === 'directory' ? '📁' : '📄';
    const sizeText = node.type === 'file' 
        ? formatSize(node.size)
        : `${node.file_count || 0} 文件`;
    
    item.innerHTML = `
        ${expandIcon}
        <span class="icon">${icon}</span>
        <span class="name">${node.name}</span>
        <span class="size">${sizeText}</span>
    `;
    
    container.appendChild(item);
    
    // 创建子节点容器（默认隐藏）
    if (node.children && node.children.length > 0) {
        const childContainer = document.createElement('div');
        childContainer.className = 'tree-children hidden';
        
        node.children.forEach(child => {
            renderTreeNode(child, childContainer, level + 1);
        });
        
        container.appendChild(childContainer);
        
        // 添加点击事件切换展开/收起
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            item.classList.toggle('collapsed');
            childContainer.classList.toggle('hidden');
            
            const expandIcon = item.querySelector('.expand-icon');
            if (expandIcon) {
                expandIcon.textContent = item.classList.contains('collapsed') ? '▶' : '▼';
            }
        });
    }
}

// 加载记录
async function loadRecords(page = 1) {
    currentPage = page;
    const status = document.getElementById('statusFilter').value;
    const groupBy = document.getElementById('groupByFilter').value;
    const search = document.getElementById('searchInput').value.trim();
    const container = document.getElementById('recordsList');
    
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        let url = `${API_BASE}/records?page=${page}&page_size=20`;
        if (status) {
            url += `&status=${status}`;
        }
        if (groupBy) {
            url += `&group_by=${groupBy}`;
        }
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            if (result.grouped) {
                renderGroupedRecords(result.data, result.group_type);
            } else {
                renderRecords(result.data);
            }
            renderPagination(result.total, result.page, result.page_size);
            
            // 如果有搜索词，显示批量删除按钮
            const batchDeleteBtn = document.getElementById('batchDeleteBtn');
            if (search) {
                batchDeleteBtn.style.display = 'inline-block';
            } else {
                batchDeleteBtn.style.display = 'none';
            }
        } else {
            container.innerHTML = `<div class="loading">加载失败: ${result.message}</div>`;
        }
    } catch (error) {
        console.error('加载记录失败:', error);
        container.innerHTML = '<div class="loading">加载失败</div>';
    }
}

// 渲染记录列表
function renderRecords(records) {
    const container = document.getElementById('recordsList');
    
    if (!records || records.length === 0) {
        container.innerHTML = '<div class="loading">暂无记录</div>';
        return;
    }
    
    let html = '';
    records.forEach(record => {
        const statusClass = record.status === 'success' ? 'success' : 'failed';
        const statusText = record.status === 'success' ? '✅ 成功' : '❌ 失败';
        const retryBtn = record.status === 'failed' 
            ? `<button class="retry-btn" onclick="retryLink(${record.id})">🔄 重试</button>` 
            : '';
        const resyncBtn = `<button class="resync-btn" onclick="resyncLink(${record.id})">🔄 重新同步</button>`;
        
        html += `
            <div class="record-item ${statusClass}">
                <div class="record-header">
                    <span class="record-status ${statusClass}">${statusText}</span>
                    <span>${record.created_at}</span>
                    <div class="record-actions">
                        ${retryBtn}
                        ${resyncBtn}
                    </div>
                </div>
                <div class="record-path">
                    <strong>源:</strong> ${record.source_file}
                </div>
                <div class="record-path">
                    <strong>目标:</strong> ${(() => {
                        const targetName = getTargetName(record.target_file);
                        if (targetName) {
                            return `<span class="target-label">[${targetName}]</span> ${record.target_file}`;
                        }
                        return record.target_file;
                    })()}
                </div>
                <div class="record-meta">
                    <span>方式: ${record.link_method || '-'}</span>
                    <span>大小: ${formatSize(record.file_size)}</span>
                    ${record.error_msg ? `<span style="color: #f5222d;">错误: ${record.error_msg}</span>` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 渲染分组记录
function renderGroupedRecords(groups, groupType) {
    const container = document.getElementById('recordsList');
    
    if (!groups || groups.length === 0) {
        container.innerHTML = '<div class="loading">暂无记录</div>';
        return;
    }
    
    // 按网盘统计的嵌套渲染
    if (groupType === 'target_show') {
        let html = '';
        groups.forEach(target => {
            html += `
                <div class="record-group">
                    <div class="group-header" onclick="toggleGroup(this)">
                        <span class="expand-icon">▼</span>
                        <strong>📁 ${target.dir_name}</strong>
                        <span class="group-count">${target.count} 个文件</span>
                    </div>
                    <div class="group-content">
            `;
            
            target.shows.forEach(show => {
                html += `
                    <div class="show-group">
                        <div class="show-header" onclick="toggleGroup(this)">
                            <span class="expand-icon">▼</span>
                            <strong>🎬 ${show.show_name}</strong>
                            <span class="show-stats">${show.count} 集 · ${formatSize(show.total_size)}</span>
                        </div>
                        <div class="group-content">
                `;
                
                show.records.forEach(record => {
                    const statusClass = record.status === 'success' ? 'success' : 'failed';
                    const statusText = record.status === 'success' ? '✅' : '❌';
                    const fileName = record.source_file.split('/').pop();
                    
                    html += `
                        <div class="group-record-item ${statusClass}" style="padding: 8px 15px; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 16px;">${statusText}</span>
                            <span style="flex: 1;">${fileName}</span>
                            <span style="color: #999; font-size: 13px;">${formatSize(record.file_size)}</span>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        return;
    }
    
    // 普通分组渲染
    let html = '';
    groups.forEach(group => {
        const recordIds = group.records ? group.records.map(r => r.id).join(',') : '';
        
        html += `
            <div class="record-group">
                <div class="group-header" onclick="toggleGroup(this)">
                    <span class="expand-icon">▼</span>
                    <strong>📁 ${group.dir_name}</strong>
                    <span class="group-count">${group.count} 条记录</span>
                </div>
                <div class="group-content">
        `;
        
        if (group.records) {
            group.records.forEach(record => {
                const statusClass = record.status === 'success' ? 'success' : 'failed';
                const statusText = record.status === 'success' ? '✅' : '❌';
                const fileName = record.source_file.split('/').pop();
                const targetPath = record.target_file.split('/').slice(-3, -1).join('/');
                
                html += `
                    <div class="group-record-item ${statusClass}" style="padding: 8px 15px; border-bottom: 1px solid #f0f0f0;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                            <span style="font-size: 14px;">${statusText}</span>
                            <strong style="font-size: 14px; flex: 1;">${fileName}</strong>
                            <span style="font-size: 12px; color: #999;">${formatSize(record.file_size)}</span>
                        </div>
                        <div style="padding-left: 24px; font-size: 12px; color: #999;">
                            → ${targetPath}
                        </div>
                    </div>
                `;
            });
        }
        
        html += `
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 切换分组展开/收起
function toggleGroup(element) {
    // element可能是div或header，需要找到正确的header
    const header = element.classList.contains('group-header') ? element : element.closest('.group-header');
    header.classList.toggle('collapsed');
    const content = header.nextElementSibling;
    content.classList.toggle('hidden');
    
    const expandIcon = header.querySelector('.expand-icon');
    if (expandIcon) {
        expandIcon.textContent = header.classList.contains('collapsed') ? '▶' : '▼';
    }
}

// 渲染分页
function renderPagination(total, page, pageSize) {
    const container = document.getElementById('pagination');
    const totalPages = Math.ceil(total / pageSize);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = `
        <button ${page === 1 ? 'disabled' : ''} onclick="loadRecords(${page - 1})">上一页</button>
        <span>第 ${page} / ${totalPages} 页 (共 ${total} 条)</span>
        <button ${page === totalPages ? 'disabled' : ''} onclick="loadRecords(${page + 1})">下一页</button>
    `;
    
    container.innerHTML = html;
}

// 格式化文件大小
function formatSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// 搜索记录（已废弃，改用后端搜索）
function searchRecords() {
    // 直接调用loadRecords进行后端搜索
    loadRecords(1);
}

// 批量删除记录
async function batchDeleteRecords() {
    const search = document.getElementById('searchInput').value.trim();
    
    if (!search) {
        alert('请先输入搜索条件');
        return;
    }
    
    if (!confirm(`确定要删除所有包含"${search}"的记录吗？\n删除后可以通过全量同步重新创建。`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/records/batch?search=${encodeURIComponent(search)}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.message}\n\n提示：可以点击"全量同步"重新同步这些文件`);
            loadRecords();
            loadStats();
        } else {
            alert(`❌ 删除失败: ${result.message}`);
        }
    } catch (error) {
        console.error('批量删除失败:', error);
        alert('❌ 删除失败，请查看控制台');
    }
}

// 全量同步
async function syncAll() {
    const btn = document.querySelector('.sync-all-btn');
    
    if (!confirm('确定要全量同步所有文件吗？这会扫描源目录所有文件并创建硬链接。')) {
        return;
    }
    
    // 禁用按钮
    btn.disabled = true;
    btn.textContent = '🔄 同步中...';
    
    try {
        const response = await fetch(`${API_BASE}/sync-all`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ 全量同步完成！\n\n总文件: ${result.total_files}\n新建: ${result.success_count}\n跳过: ${result.skipped_count || 0}\n失败: ${result.failed_count}`);
            
            // 刷新数据
            loadStats();
            loadRecords();
            refreshSourceTree();
            refreshTargetTree();
        } else {
            alert(`❌ 同步失败: ${result.message}`);
        }
    } catch (error) {
        console.error('全量同步失败:', error);
        alert('❌ 同步失败，请查看控制台');
    } finally {
        // 恢复按钮
        btn.disabled = false;
        btn.textContent = '🔄 全量同步';
    }
}

// 重试硬链接
async function retryLink(recordId) {
    try {
        const response = await fetch(`${API_BASE}/records/${recordId}/retry`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            // 刷新记录和统计
            loadRecords(currentPage);
            loadStats();
        } else {
            alert(`❌ ${result.message}`);
        }
    } catch (error) {
        console.error('重试失败:', error);
        alert('❌ 重试失败，请查看控制台');
    }
}

// 重新同步（删除记录并重新创建）
async function resyncLink(recordId) {
    if (!confirm('确定要重新同步吗？这会删除当前记录并重新创建硬链接。')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/records/${recordId}/resync`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            // 刷新记录和统计
            loadRecords(currentPage);
            loadStats();
        } else {
            alert(`❌ ${result.message}`);
        }
    } catch (error) {
        console.error('重新同步失败:', error);
        alert('❌ 重新同步失败，请查看控制台');
    }
}

// 重新同步整个分组
async function resyncGroup(recordIds) {
    if (!confirm(`确定要重新同步整个分组吗？这会删除 ${recordIds.length} 条记录并重新创建硬链接。`)) {
        return;
    }
    
    let successCount = 0;
    let failedCount = 0;
    
    for (const recordId of recordIds) {
        try {
            const response = await fetch(`${API_BASE}/records/${recordId}/resync`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                successCount++;
            } else {
                failedCount++;
            }
        } catch (error) {
            failedCount++;
            console.error(`重新同步记录 ${recordId} 失败:`, error);
        }
    }
    
    alert(`✅ 分组重新同步完成！\n\n成功: ${successCount}\n失败: ${failedCount}`);
    
    // 刷新记录和统计
    loadRecords(currentPage);
    loadStats();
}

// ==================== 映射管理功能 ====================

// 加载映射列表
let currentMappingPage = 1;
let currentMappingSearch = '';

async function loadMappings(page = 1) {
    currentMappingPage = page;
    const searchInput = document.getElementById('mappingSearch');
    currentMappingSearch = searchInput ? searchInput.value : '';
    
    try {
        const params = new URLSearchParams({
            page: page,
            page_size: 20
        });
        
        if (currentMappingSearch) {
            params.append('search', currentMappingSearch);
        }
        
        const response = await fetch(`${API_BASE}/mappings?${params}`);
        const result = await response.json();
        
        if (result.success) {
            renderMappings(result.data, result.total, result.page, result.total_pages);
        } else {
            document.getElementById('mappingsList').innerHTML = `<div class="error">加载失败: ${result.message}</div>`;
        }
    } catch (error) {
        console.error('加载映射失败:', error);
        document.getElementById('mappingsList').innerHTML = '<div class="error">加载失败</div>';
    }
}

// 渲染映射列表
function renderMappings(mappings, total, page, totalPages) {
    const container = document.getElementById('mappingsList');
    
    if (mappings.length === 0) {
        container.innerHTML = '<div class="empty">暂无映射规则，点击"添加映射"创建第一条</div>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr><th>原名称</th><th>自定义名称</th><th>状态</th><th>备注</th><th>操作</th></tr></thead><tbody>';
    
    mappings.forEach(m => {
        const statusBadge = m.enabled ? '<span class="badge success">✓ 启用</span>' : '<span class="badge">× 禁用</span>';
        html += `
            <tr>
                <td>${escapeHtml(m.original_name)}</td>
                <td><strong>${escapeHtml(m.custom_name)}</strong></td>
                <td>${statusBadge}</td>
                <td>${escapeHtml(m.note || '-')}</td>
                <td>
                    <button class="btn-small" onclick="editMapping(${m.id})">编辑</button>
                    <button class="btn-small btn-danger" onclick="deleteMapping(${m.id}, '${escapeHtml(m.original_name)}')">删除</button>
                    <button class="btn-small" onclick="clearShowRecords('${escapeHtml(m.original_name)}')">清除记录</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    
    // 添加分页
    html += '<div class="pagination">';
    html += `<span class="page-info">共 ${total} 条记录，第 ${page}/${totalPages} 页</span>`;
    
    if (totalPages > 1) {
        if (page > 1) {
            html += `<button class="page-btn" onclick="loadMappings(${page - 1})">上一页</button>`;
        }
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === page) {
                html += `<button class="page-btn active">${i}</button>`;
            } else if (i === 1 || i === totalPages || Math.abs(i - page) <= 2) {
                html += `<button class="page-btn" onclick="loadMappings(${i})">${i}</button>`;
            } else if (i === page - 3 || i === page + 3) {
                html += '<span class="page-ellipsis">...</span>';
            }
        }
        
        if (page < totalPages) {
            html += `<button class="page-btn" onclick="loadMappings(${page + 1})">下一页</button>`;
        }
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// 显示添加映射对话框
function showAddMappingDialog() {
    const originalName = prompt('请输入原名称（例如：老舅 (2023)）：');
    if (!originalName) return;
    
    const customName = prompt('请输入自定义名称：');
    if (!customName) return;
    
    const note = prompt('备注（可选）：') || '';
    
    addMapping(originalName, customName, note);
}

// 添加映射
async function addMapping(originalName, customName, note) {
    try {
        const response = await fetch(`${API_BASE}/mappings`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({original_name: originalName, custom_name: customName, note: note})
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ 映射添加成功！');
            loadMappings();
        } else {
            alert('❌ 添加失败: ' + result.message);
        }
    } catch (error) {
        console.error('添加映射失败:', error);
        alert('❌ 添加失败');
    }
}

// 编辑映射
async function editMapping(id) {
    const customName = prompt('请输入新的自定义名称：');
    if (!customName) return;
    
    try {
        const response = await fetch(`${API_BASE}/mappings/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({custom_name: customName})
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ 映射更新成功！');
            loadMappings();
        } else {
            alert('❌ 更新失败: ' + result.message);
        }
    } catch (error) {
        console.error('更新映射失败:', error);
        alert('❌ 更新失败');
    }
}

// 删除映射
async function deleteMapping(id, name) {
    if (!confirm(`确定要删除映射"${name}"吗？`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/mappings/${id}`, {method: 'DELETE'});
        const result = await response.json();
        
        if (result.success) {
            alert('✅ 映射删除成功！');
            loadMappings();
        } else {
            alert('❌ 删除失败: ' + result.message);
        }
    } catch (error) {
        console.error('删除映射失败:', error);
        alert('❌ 删除失败');
    }
}

// 清除指定剧集的记录
async function clearShowRecords(showName) {
    if (!confirm(`确定要清除"${showName}"的所有硬链接记录吗？\n\n清除后可以重新同步以使用新的映射名称。`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/records/by-show?show_name=${encodeURIComponent(showName)}`, {method: 'DELETE'});
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ 成功清除 ${result.deleted_count} 条记录！\n\n现在可以重新同步以使用新名称。`);
        } else {
            alert('❌ 清除失败: ' + result.message);
        }
    } catch (error) {
        console.error('清除记录失败:', error);
        alert('❌ 清除失败');
    }
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 导出链接记录
function exportRecords() {
    const statusFilter = document.getElementById('statusFilter').value;
    const searchInput = document.getElementById('searchInput').value;
    
    const params = new URLSearchParams();
    if (statusFilter) params.append('status', statusFilter);
    if (searchInput) params.append('search', searchInput);
    
    const url = `${API_BASE}/export/records?${params.toString()}`;
    
    // 直接在新窗口打开下载链接
    window.open(url, '_blank');
}
