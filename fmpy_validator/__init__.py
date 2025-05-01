"""
FMPy Validator
一个基于FMPy的FMU文件验证工具
"""

__version__ = '0.1.0'
__author__ = 'Your Name'
__email__ = 'your.email@example.com'

from .validator import (
    validate_fmu,
    get_fmu_info,
    FMUValidator
)

__all__ = [
    'validate_fmu',
    'get_fmu_info',
    'FMUValidator'
]

def check_dependencies():
    """检查必要的依赖是否已安装"""
    try:
        import fmpy
        import flask
        import werkzeug
    except ImportError as e:
        raise ImportError(f"缺少必要的依赖: {str(e)}")
    
    # 检查FMPy版本
    if not hasattr(fmpy, 'validation'):
        raise ImportError("请安装最新版本的FMPy (>=0.3.0)") 