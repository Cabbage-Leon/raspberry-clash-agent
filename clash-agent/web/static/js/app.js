/**
 * Clash Agent Web UI - JavaScript
 */

// 全局变量
let socket = null;
let currentPage = 'dashboard';
let logs = [];
let chatHistory = [];

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    initNavigation();
    initDashboard();
    initTools();
    initChat();
    initLogs();
    initMemory();
    
    // 初始加载
    refreshStatus();
    loadSystemInfo();
    loadTools();
});

// ==================== WebSocket ====================

function initSocket() {
    socket = io();
    
    socket.on('connect', () => {
        updateConnectionStatus(true);
        showNotification('已连接到服务器', 'success');
    });
    
    socket.on('disconnect', () => {
        updateConnectionStatus(false);
        showNotification('与服务器断开连接', 'error');
    });
    
    socket.on('log', (data) => {
        addLog(data.level, data.message, data.timestamp);
    });
    
    socket.on('connected', (data) => {
        console.log('WebSocket已连接:', data.message);
    });
    
    socket.on('chat_response', (data) => {
        handleChatResponse(data);
    });
    
    socket.on('tool_result', (data) => {
        showToolResult(data);
    });
}

function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.connection-status span:last-child');
    
    if (connected) {
        statusDot.classList.remove('disconnected');
        statusDot.classList.add('connected');
        statusText.textContent = '已连接';
    } else {
        statusDot.classList.remove('connected');
        statusDot.classList.add('disconnected');
        statusText.textContent = '未连接';
    }
}

// ==================== 导航 ====================

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            switchPage(page);
        });
    });
}

function switchPage(page) {
    // 更新导航项
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });
    
    // 更新页面显示
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    document.getElementById(`page-${page}`).classList.add('active');
    
    currentPage = page;
    
    // 页面特定初始化
    if (page === 'memory') {
        loadMemoryStats();
        loadFaults();
    }
}

// ==================== 仪表盘 ====================

function initDashboard() {
    // 刷新状态
    document.getElementById('btn-refresh-status').addEventListener('click', refreshStatus);
    
    // Clash控制
    document.getElementById('btn-clash-on').addEventListener('click', () => {
        apiCall('/api/clash/on', 'POST')
            .then(data => {
                if (data.success) {
                    showNotification('Clash已开启', 'success');
                    refreshStatus();
                } else {
                    showNotification('开启失败: ' + data.error, 'error');
                }
            });
    });
    
    document.getElementById('btn-clash-off').addEventListener('click', () => {
        apiCall('/api/clash/off', 'POST')
            .then(data => {
                if (data.success) {
                    showNotification('Clash已关闭', 'success');
                    refreshStatus();
                } else {
                    showNotification('关闭失败: ' + data.error, 'error');
                }
            });
    });
    
    document.getElementById('btn-clash-restart').addEventListener('click', () => {
        apiCall('/api/clash/restart', 'POST')
            .then(data => {
                if (data.success) {
                    showNotification('Clash已重启', 'success');
                    setTimeout(refreshStatus, 1000);
                } else {
                    showNotification('重启失败: ' + data.error, 'error');
                }
            });
    });
    
    // 网络测试
    document.getElementById('btn-network-test').addEventListener('click', () => {
        const target = document.getElementById('test-target').value;
        apiCall('/api/network/test', 'POST', { target })
            .then(data => {
                const resultDiv = document.getElementById('network-test-result');
                if (data.success) {
                    resultDiv.className = 'result-display success';
                    resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> 连接成功 (HTTP ${data.http_code})`;
                } else {
                    resultDiv.className = 'result-display error';
                    resultDiv.innerHTML = `<i class="fas fa-times-circle"></i> ${data.error}`;
                }
            });
    });
    
    // DNS检查
    document.getElementById('btn-dns-check').addEventListener('click', () => {
        const domain = document.getElementById('dns-domain').value;
        apiCall('/api/dns/check', 'POST', { domain })
            .then(data => {
                const resultDiv = document.getElementById('dns-check-result');
                if (data.success) {
                    const ips = data.resolved_ips.join('<br>');
                    resultDiv.className = 'result-display success';
                    resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> 解析成功<br>${ips}`;
                } else {
                    resultDiv.className = 'result-display error';
                    resultDiv.innerHTML = `<i class="fas fa-times-circle"></i> ${data.error}`;
                }
            });
    });
    
    // 订阅更新
    document.getElementById('btn-sub-update').addEventListener('click', () => {
        const url = document.getElementById('sub-url').value;
        apiCall('/api/clash/update', 'POST', { url: url || null })
            .then(data => {
                const resultDiv = document.getElementById('sub-update-result');
                if (data.success) {
                    resultDiv.className = 'result-display success';
                    resultDiv.innerHTML = `<i class="fas fa-check-circle"></i> 更新成功`;
                } else {
                    resultDiv.className = 'result-display error';
                    resultDiv.innerHTML = `<i class="fas fa-times-circle"></i> ${data.error}`;
                }
            });
    });
}

function refreshStatus() {
    apiCall('/api/status')
        .then(data => {
            if (data.success) {
                updateClashStatus(data.clash);
            }
        });
}

function updateClashStatus(data) {
    const badge = document.getElementById('clash-status-badge');
    const infoList = document.getElementById('clash-info-list');
    
    if (data.success) {
        badge.className = 'status-badge running';
        badge.textContent = '运行中';
        infoList.innerHTML = `<div class="info-row"><span class="label">状态</span><span class="value">${data.status || '正常'}</span></div>`;
    } else {
        badge.className = 'status-badge stopped';
        badge.textContent = '已停止';
        infoList.innerHTML = `<div class="info-row"><span class="label">错误</span><span class="value">${data.error || '未知'}</span></div>`;
    }
}

function loadSystemInfo() {
    apiCall('/api/system')
        .then(data => {
            if (data.success) {
                // 系统信息
                document.getElementById('sys-hostname').textContent = data.system.info?.hostname || '-';
                document.getElementById('sys-os').textContent = data.system.info?.os || '-';
                document.getElementById('sys-arch').textContent = data.system.info?.arch || '-';
                document.getElementById('sys-kernel').textContent = data.system.info?.kernel || '-';
                
                // 内存
                if (data.memory.success) {
                    document.getElementById('memory-progress').style.width = data.memory.percent + '%';
                    document.getElementById('memory-text').textContent = 
                        `${data.memory.used_mb}MB / ${data.memory.total_mb}MB (${data.memory.percent}%)`;
                }
                
                // 磁盘
                if (data.disk.success) {
                    const percent = parseInt(data.disk.use_percent);
                    document.getElementById('disk-progress').style.width = percent + '%';
                    document.getElementById('disk-text').textContent = 
                        `${data.disk.used} / ${data.disk.size} (${data.disk.use_percent})`;
                }
            }
        });
}

// ==================== 工具管理 ====================

function initTools() {
    document.getElementById('btn-execute-tool').addEventListener('click', executeSelectedTool);
}

function loadTools() {
    apiCall('/api/tools')
        .then(data => {
            if (data.success) {
                renderTools(data.tools);
                document.getElementById('tools-count').textContent = data.count;
                
                // 填充选择器
                const select = document.getElementById('tool-select');
                select.innerHTML = '<option value="">选择工具...</option>';
                data.tools.forEach(tool => {
                    const option = document.createElement('option');
                    option.value = tool.name;
                    option.textContent = tool.name;
                    select.appendChild(option);
                });
            }
        });
}

function renderTools(tools) {
    const toolsGrid = document.getElementById('tools-list');
    toolsGrid.innerHTML = '';
    
    tools.forEach(tool => {
        const card = document.createElement('div');
        card.className = 'tool-card';
        card.dataset.toolName = tool.name;
        card.innerHTML = `
            <h4><i class="fas fa-wrench"></i> ${tool.name}</h4>
            <p>${tool.description}</p>
            <div class="params">参数: ${tool.params.join(', ') || '无'}</div>
        `;
        
        card.addEventListener('click', () => {
            document.querySelectorAll('.tool-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            document.getElementById('tool-select').value = tool.name;
        });
        
        toolsGrid.appendChild(card);
    });
}

function executeSelectedTool() {
    const toolName = document.getElementById('tool-select').value;
    const paramsText = document.getElementById('tool-params').value;
    
    if (!toolName) {
        showNotification('请选择工具', 'error');
        return;
    }
    
    let params = {};
    try {
        params = JSON.parse(paramsText);
    } catch (e) {
        showNotification('参数格式错误，请使用JSON格式', 'error');
        return;
    }
    
    apiCall('/api/tool/execute', 'POST', { tool: toolName, params })
        .then(data => {
            const resultBox = document.getElementById('tool-result');
            if (data.success) {
                resultBox.innerHTML = `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
                resultBox.style.color = '#31d350';
                showNotification('工具执行成功', 'success');
            } else {
                resultBox.innerHTML = `错误: ${data.error}`;
                resultBox.style.color = '#ff4141';
                showNotification('执行失败: ' + data.error, 'error');
            }
        });
}

function showToolResult(data) {
    const resultBox = document.getElementById('tool-result');
    if (data.success) {
        resultBox.innerHTML = `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
        resultBox.style.color = '#31d350';
    } else {
        resultBox.innerHTML = `错误: ${data.error}`;
        resultBox.style.color = '#ff4141';
    }
}

// ==================== 聊天 ====================

function initChat() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('btn-send-chat');
    
    // 发送按钮
    sendBtn.addEventListener('click', sendChatMessage);
    
    // Enter发送
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // 自动调整高度
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
    
    // 清空聊天
    document.getElementById('btn-clear-chat').addEventListener('click', () => {
        document.getElementById('chat-messages').innerHTML = `
            <div class="welcome-message">
                <i class="fas fa-robot"></i>
                <p>欢迎使用Clash Agent智能运维助手！</p>
                <p class="hint">你可以输入问题描述，如"节点超时怎么办"、"面板打不开"等...</p>
            </div>
        `;
        chatHistory = [];
    });
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // 添加用户消息
    addChatMessage('user', message);
    input.value = '';
    
    // 显示加载状态
    const loadingMsg = addChatMessage('agent', '<div class="loading"></div> 正在思考...');
    
    // 通过WebSocket发送
    socket.emit('chat_message', { message });
}

function addChatMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    
    // 清除欢迎消息
    const welcome = messagesDiv.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const time = new Date().toLocaleTimeString();
    
    if (role === 'user') {
        msgDiv.innerHTML = `
            <div>${content}</div>
            <div class="time">${time}</div>
        `;
    } else {
        msgDiv.innerHTML = `
            <div>${content}</div>
            <div class="time">${time}</div>
        `;
    }
    
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return msgDiv;
}

function handleChatResponse(data) {
    // 移除加载消息
    const loadingMsg = document.querySelector('.message.agent:last-child');
    if (loadingMsg && loadingMsg.querySelector('.loading')) {
        loadingMsg.remove();
    }
    
    if (data.success) {
        // 构建详细响应
        let content = `<div>${data.response}</div>`;
        
        if (data.steps && data.steps.length > 0) {
            content += `<div class="reasoning" style="margin-top: 10px;">
                <strong>推理过程 (${data.iterations}步):</strong>
            </div>`;
            
            data.steps.forEach((step, i) => {
                content += `<div class="tool-call">
                    Step ${i + 1}: ${step.action || '分析'}<br>
                    推理: ${step.reasoning?.substring(0, 100)}...
                </div>`;
            });
        }
        
        addChatMessage('agent', content);
    } else {
        addChatMessage('agent', `<div class="error">错误: ${data.error}</div>`);
    }
}

// ==================== 日志 ====================

function initLogs() {
    document.getElementById('btn-clear-logs').addEventListener('click', () => {
        document.getElementById('logs-list').innerHTML = '';
        logs = [];
    });
    
    document.getElementById('log-level-filter').addEventListener('change', filterLogs);
}

function addLog(level, message, timestamp) {
    logs.push({ level, message, timestamp });
    
    const logsList = document.getElementById('logs-list');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.dataset.level = level;
    
    entry.innerHTML = `
        <span class="time">${timestamp}</span>
        <span class="level ${level}">${level}</span>
        <span class="message">${message}</span>
    `;
    
    logsList.appendChild(entry);
    logsList.scrollTop = logsList.scrollHeight;
}

function filterLogs() {
    const filter = document.getElementById('log-level-filter').value;
    const entries = document.querySelectorAll('.log-entry');
    
    entries.forEach(entry => {
        if (filter === 'all' || entry.dataset.level === filter) {
            entry.style.display = 'flex';
        } else {
            entry.style.display = 'none';
        }
    });
}

// ==================== 记忆系统 ====================

function initMemory() {
    // 初始化时加载
}

function loadMemoryStats() {
    apiCall('/api/memory/stats')
        .then(data => {
            if (data.success) {
                const stats = data.stats;
                document.getElementById('stat-total-faults').textContent = stats.total_faults || 0;
                document.getElementById('stat-resolved-faults').textContent = stats.resolved_faults || 0;
                document.getElementById('stat-experiences').textContent = stats.total_experiences || 0;
                document.getElementById('stat-week-faults').textContent = stats.faults_last_7_days || 0;
            }
        });
}

function loadFaults() {
    apiCall('/api/memory/faults?limit=20')
        .then(data => {
            if (data.success) {
                renderFaults(data.faults);
            }
        });
}

function renderFaults(faults) {
    const tbody = document.getElementById('faults-table-body');
    tbody.innerHTML = '';
    
    faults.forEach(fault => {
        const tr = document.createElement('tr');
        
        const statusClass = fault.resolved ? 'resolved' : (fault.status === 'failed' ? 'failed' : 'pending');
        const statusText = fault.resolved ? '已解决' : (fault.status === 'failed' ? '失败' : '待处理');
        
        tr.innerHTML = `
            <td>${fault.timestamp || '-'}</td>
            <td>${fault.symptom || '-'}</td>
            <td>${fault.root_cause || '-'}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
        `;
        
        tbody.appendChild(tr);
    });
}

// ==================== API辅助 ====================

async function apiCall(url, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API调用失败:', error);
        return { success: false, error: error.message };
    }
}

// ==================== 通知 ====================

function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-times-circle';
    
    notification.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// ==================== 定时刷新 ====================

setInterval(() => {
    if (currentPage === 'dashboard') {
        refreshStatus();
        loadSystemInfo();
    }
}, 30000);  // 30秒刷新一次