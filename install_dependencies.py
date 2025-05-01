"""
依赖项安装脚本
为FMPy验证器项目安装所有必要的依赖项
"""

import sys
import os
import subprocess
import platform

def main():
    """安装所有必要的依赖项"""
    print("正在安装FMPy验证器所需的依赖项...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 10):
        print(f"错误: 需要Python 3.10或更高版本, 当前版本为{python_version.major}.{python_version.minor}")
        sys.exit(1)
    
    # 获取当前脚本目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 安装项目本身(开发模式)
    try:
        print("\n安装项目(开发模式)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."], cwd=current_dir)
        print("✓ 项目安装成功")
    except subprocess.CalledProcessError as e:
        print(f"项目安装失败: {e}")
        sys.exit(1)
    
    # 安装特定依赖项
    dependencies = ["flask", "werkzeug", "fmpy", "pytest"]
    
    for dep in dependencies:
        try:
            print(f"\n安装 {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✓ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"{dep} 安装失败: {e}")
            sys.exit(1)
    
    print("\n所有依赖项安装完成!")
    print("\n运行应用程序: python app.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 