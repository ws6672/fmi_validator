from setuptools import setup, find_packages
import os

# 使用UTF-8编码读取README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

setup(
    name="fmpy_validator",
    version="0.1.0",
    packages=find_packages(),
    package_dir={"": "."},
    install_requires=[
        "fmpy",
        "flask",
        "werkzeug"
    ],
    python_requires=">=3.10",
    author="et",
    description="A web-based FMU validator based on FMPy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/et/fmpy-validator",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
)