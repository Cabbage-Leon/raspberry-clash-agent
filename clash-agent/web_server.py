#!/usr/bin/env python3
"""
Web UI启动脚本
"""

import argparse
import sys
import os

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)) or '/workspace/clash-agent')

from src.web.app import run_web_server


def main():
    parser = argparse.ArgumentParser(description='Clash Agent Web UI')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════╗
║          Clash Agent Web UI                      ║
║                                                  ║
║  地址: http://{args.host}:{args.port}              ║
║  状态: 启动中...                                  ║
╚══════════════════════════════════════════════════╝
""")
    
    try:
        run_web_server(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()