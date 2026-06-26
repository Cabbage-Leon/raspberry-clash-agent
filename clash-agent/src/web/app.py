"""
Web服务 - Flask后端API
"""

import json
import threading
import time
import queue
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import logging

from config.settings import CLASH_CONFIG, LLM_CONFIG
from src.core.llm_adapter import LLMManager
from src.core.tool_registry import ToolRegistry, global_tool_registry
from src.core.memory import Memory
from src.core.react_engine import ReActEngine
from src.tools.clash_tools import clash_tools
from src.tools.network_tools import network_tools
from src.tools.system_tools import system_tools
from src.utils.logger import get_logger

logger = get_logger()

# 创建Flask应用
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent

app = Flask(__name__, 
            template_folder=str(PROJECT_ROOT / 'web' / 'templates'),
            static_folder=str(PROJECT_ROOT / 'web' / 'static'))
app.config['SECRET_KEY'] = 'clash-agent-secret-key'

# 创建SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局Agent实例
agent = None

# 日志消息队列
log_queue = queue.Queue(maxsize=1000)


def init_agent():
    """初始化Agent"""
    global agent
    if agent is None:
        from main import register_all_tools
        register_all_tools()
        llm_manager = LLMManager()
        memory = Memory()
        agent = ReActEngine(
            llm_manager=llm_manager,
            tool_registry=global_tool_registry,
            memory=memory
        )
    return agent


class LogEmitter:
    """日志发射器 - 将日志推送到WebSocket"""
    
    def __init__(self):
        self.enabled = True
    
    def emit(self, level, message):
        """发射日志消息"""
        if self.enabled:
            try:
                socketio.emit('log', {
                    'level': level,
                    'message': message,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception:
                pass


log_emitter = LogEmitter()


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """仪表板页面"""
    return render_template('dashboard.html')


@app.route('/tools')
def tools_page():
    """工具页面"""
    return render_template('tools.html')


@app.route('/logs')
def logs_page():
    """日志页面"""
    return render_template('logs.html')


@app.route('/memory')
def memory_page():
    """记忆页面"""
    return render_template('memory.html')


# ==================== API路由 ====================

@app.route('/api/status')
def api_status():
    """获取状态"""
    try:
        result = clash_tools.status()
        return jsonify({
            'success': True,
            'clash': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/system')
def api_system():
    """获取系统状态"""
    try:
        system_info = system_tools.system_info()
        memory_usage = system_tools.memory_usage()
        disk_usage = system_tools.disk_usage()
        
        return jsonify({
            'success': True,
            'system': system_info,
            'memory': memory_usage,
            'disk': disk_usage
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/tools')
def api_tools():
    """获取可用工具列表"""
    tools = global_tool_registry.list_tools()
    return jsonify({
        'success': True,
        'tools': tools,
        'count': len(tools)
    })


@app.route('/api/tool/execute', methods=['POST'])
def api_tool_execute():
    """执行工具"""
    data = request.json
    tool_name = data.get('tool')
    params = data.get('params', {})
    
    if not tool_name:
        return jsonify({'success': False, 'error': '缺少工具名称'})
    
    # 发送日志
    log_emitter.emit('INFO', f'执行工具: {tool_name}, 参数: {params}')
    
    try:
        result = global_tool_registry.execute(tool_name, **params)
        log_emitter.emit('INFO', f'工具执行完成: {tool_name}')
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        log_emitter.emit('ERROR', f'工具执行失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话接口"""
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'success': False, 'error': '缺少消息内容'})
    
    log_emitter.emit('INFO', f'收到用户消息: {message}')
    
    try:
        engine = init_agent()
        result = engine.run(message)
        
        log_emitter.emit('INFO', f'Agent响应: {result.response[:100]}...')
        
        return jsonify({
            'success': True,
            'response': result.response,
            'iterations': result.iterations,
            'steps': [s.to_dict() for s in result.steps],
            'final_state': result.final_state
        })
    except Exception as e:
        log_emitter.emit('ERROR', f'对话处理失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/memory/stats')
def api_memory_stats():
    """获取记忆统计"""
    try:
        engine = init_agent()
        stats = engine.memory.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/memory/faults')
def api_memory_faults():
    """获取故障记录"""
    limit = request.args.get('limit', 20, type=int)
    try:
        engine = init_agent()
        faults = engine.memory.get_recent_faults(limit)
        return jsonify({
            'success': True,
            'faults': faults
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/clash/on', methods=['POST'])
def api_clash_on():
    """开启Clash"""
    log_emitter.emit('INFO', '正在开启Clash代理...')
    try:
        result = clash_tools.on()
        log_emitter.emit('INFO', 'Clash代理已开启')
        return jsonify(result)
    except Exception as e:
        log_emitter.emit('ERROR', f'开启失败: {e}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/clash/off', methods=['POST'])
def api_clash_off():
    """关闭Clash"""
    log_emitter.emit('INFO', '正在关闭Clash代理...')
    try:
        result = clash_tools.off()
        log_emitter.emit('INFO', 'Clash代理已关闭')
        return jsonify(result)
    except Exception as e:
        log_emitter.emit('ERROR', f'关闭失败: {e}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/clash/restart', methods=['POST'])
def api_clash_restart():
    """重启Clash"""
    log_emitter.emit('INFO', '正在重启Clash服务...')
    try:
        result = clash_tools.restart()
        log_emitter.emit('INFO', 'Clash服务已重启')
        return jsonify(result)
    except Exception as e:
        log_emitter.emit('ERROR', f'重启失败: {e}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/clash/update', methods=['POST'])
def api_clash_update():
    """更新订阅"""
    data = request.json
    url = data.get('url')
    log_emitter.emit('INFO', f'正在更新订阅: {url or "默认订阅"}')
    try:
        result = clash_tools.update_subscription(url)
        log_emitter.emit('INFO', '订阅更新完成')
        return jsonify(result)
    except Exception as e:
        log_emitter.emit('ERROR', f'更新失败: {e}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/network/test', methods=['POST'])
def api_network_test():
    """网络测试"""
    data = request.json
    target = data.get('target', 'https://www.google.com')
    log_emitter.emit('INFO', f'正在测试网络连接: {target}')
    try:
        result = network_tools.connectivity_test(target)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/dns/check', methods=['POST'])
def api_dns_check():
    """DNS检查"""
    data = request.json
    domain = data.get('domain', 'google.com')
    log_emitter.emit('INFO', f'正在检查DNS: {domain}')
    try:
        result = network_tools.dns_check(domain)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== WebSocket事件 ====================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '已连接到Clash Agent'})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info('客户端已断开')


@socketio.on('chat_message')
def handle_chat_message(data):
    """处理对话消息"""
    message = data.get('message', '')
    log_emitter.emit('INFO', f'收到消息: {message}')
    
    try:
        engine = init_agent()
        result = engine.run(message)
        
        emit('chat_response', {
            'success': True,
            'response': result.response,
            'iterations': result.iterations,
            'steps': [s.to_dict() for s in result.steps]
        })
        
        log_emitter.emit('INFO', f'响应完成，共{result.iterations}轮')
    except Exception as e:
        emit('chat_response', {
            'success': False,
            'error': str(e)
        })
        log_emitter.emit('ERROR', f'处理失败: {e}')


@socketio.on('execute_tool')
def handle_execute_tool(data):
    """处理工具执行"""
    tool_name = data.get('tool')
    params = data.get('params', {})
    
    log_emitter.emit('INFO', f'WebSocket执行工具: {tool_name}')
    
    try:
        result = global_tool_registry.execute(tool_name, **params)
        emit('tool_result', {
            'success': True,
            'tool': tool_name,
            'result': result
        })
        log_emitter.emit('INFO', f'工具执行完成')
    except Exception as e:
        emit('tool_result', {
            'success': False,
            'tool': tool_name,
            'error': str(e)
        })
        log_emitter.emit('ERROR', f'工具执行失败: {e}')


def run_web_server(host='0.0.0.0', port=5000, debug=False):
    """运行Web服务器"""
    logger.info(f'启动Web服务器: http://{host}:{port}')
    
    # 初始化Agent
    init_agent()
    
    # 运行SocketIO
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_web_server(debug=True)