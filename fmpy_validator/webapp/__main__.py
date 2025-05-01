"""
FMPy Validator Web Application Entry Point
"""

import os
import sys

# 添加项目根目录到sys.path以支持绝对导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

try:
    # 尝试作为包导入
    from fmpy_validator.webapp.app import app
except ImportError:
    try:
        # 如果作为包导入失败，尝试相对路径导入
        from .app import app
    except ImportError:
        # 如果相对导入失败，尝试直接导入（当前目录）
        from app import app

if __name__ == '__main__':
    # 从环境变量获取主机和端口配置，或使用默认值
    host = os.environ.get('FMPY_VALIDATOR_HOST', '0.0.0.0')
    port = int(os.environ.get('FMPY_VALIDATOR_PORT', 5000))
    
    print(f"启动FMPy Validator Web应用...")
    print(f"监听地址: {host}:{port}")
    print(f"请在浏览器中访问: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    
    app.run(host=host, port=port, debug=True) 