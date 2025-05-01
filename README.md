# FMI Validator

一个基于Web的FMU验证工具，用于验证Functional Mock-up Units (FMUs)的完整性和正确性。



## 功能特点

- 验证FMU文件的完整性
- 检查模型描述的XML架构
- 验证变量名的唯一性和有效性
- 检查模型结构的完整性和完整性
- 验证必需的初始值
- 检查因果关系和可变性的组合
- 验证单位定义
- 验证fmu保护的DLL是否包含约定函数
- 支持FMI 1.0、2.0和3.0版本

## 后续计划
- [ ] 增加测试用例集做覆盖测试
- [ ] 提供预仿真功能，支持dll函数调用的测试
- [ ] 优化测试结果的展示效果
- [ ] 支持批量验证特定系统生成fmu，评估系统的可靠性

## 项目结构

```
fmpy_validator/
├── fmpy_validator/          # 主要的包目录
│   ├── __init__.py          # 包初始化文件
│   ├── validator.py         # 核心验证功能
│   └── webapp/              # Web应用程序
│       ├── __init__.py
│       ├── app.py           # Flask应用
│       ├── __main__.py      # 作为模块运行入口
│       └── templates/       # 前端模板
├── templates/               # 全局模板
├── setup.py                 # 安装配置
├── pyproject.toml           # 项目元数据
├── install_dependencies.py  # 依赖安装脚本
└── README.md                # 项目说明文档
```

## 安装要求

- Python 3.10 或更高版本
- FMPy 0.3.23 或更高版本
- Flask
- Werkzeug

## 安装方法

### 方法一：使用依赖安装脚本（推荐）

该方法适用于所有平台（Windows, macOS, Linux）：

```bash
# 进入项目根目录
cd fmi_validator

# 运行依赖安装脚本
python install_dependencies.py
```

### 方法二：手动安装

#### 步骤 1: 安装依赖

```bash
# 安装所需的依赖包
pip install fmpy flask werkzeug pytest
```

#### 步骤 2: 安装 FMI Validator（开发模式）

```bash
# 进入项目根目录
cd fmi_validator

# 安装项目（开发模式）
pip install -e .
```

## 启动应用程序

### 方法一：直接在项目中启动

#### Windows

```bash
# 命令提示符(CMD)
cd fmi_validator
python fmpy_validator\webapp\app.py

# PowerShell
cd fmi_validator
python .\fmpy_validator\webapp\app.py

# Git Bash
cd fmi_validator
python fmpy_validator/webapp/app.py

# 通过__main__.py启动
cd fmi_validator
python fmpy_validator/webapp/__main__.py
```

#### macOS/Linux

```bash
# 进入项目根目录
cd fmi_validator
python fmpy_validator/webapp/app.py

# 通过__main__.py启动
cd fmi_validator
python fmpy_validator/webapp/__main__.py
```

### 方法二：作为Python模块启动

适用于所有平台（Windows, macOS, Linux）：

```bash
# 进入项目根目录
cd fmi_validator

# 方式1: 使用Python -m命令
python -m fmpy_validator.webapp

# 方式2: 使用项目安装后的入口点
python -m flask --app fmpy_validator.webapp.app run --host=0.0.0.0 --port=5000
```

### 方法三：安装为包后启动

如果您已经将FMI Validator安装为包（使用`pip install .`而非开发模式），可以从任何位置启动：

```bash
# 直接启动模块
python -m fmpy_validator.webapp

# 或者使用Flask命令（需要先安装flask）
flask --app fmpy_validator.webapp.app run --host=0.0.0.0 --port=5000
```

### 通过环境变量配置

您可以通过设置环境变量来配置应用的主机地址和端口：

#### Windows (CMD)

```bash
set FMPY_VALIDATOR_HOST=127.0.0.1
set FMPY_VALIDATOR_PORT=8080
python -m fmpy_validator.webapp
```

#### Windows (PowerShell)

```powershell
$env:FMPY_VALIDATOR_HOST = "127.0.0.1"
$env:FMPY_VALIDATOR_PORT = "8080"
python -m fmpy_validator.webapp
```

#### macOS/Linux

```bash
export FMPY_VALIDATOR_HOST=127.0.0.1
export FMPY_VALIDATOR_PORT=8080
python -m fmpy_validator.webapp
```

## 访问Web界面

启动应用后，在浏览器中访问：http://localhost:5000

## 平台特定说明

### Windows

- 如果使用虚拟环境，确保先激活：`venv\Scripts\activate`
- 如果遇到路径问题，请使用反斜杠`\`或使用原始字符串`r"path\to\file"`

### macOS/Linux

- 如果使用虚拟环境，确保先激活：`source venv/bin/activate`
- 确保文件有执行权限：`chmod +x fmpy_validator/webapp/app.py`
- 可使用前导`./`运行脚本：`./fmpy_validator/webapp/app.py`

### 常见问题解决

1. **模块导入错误**：确保您在正确的目录中启动应用，或者已将项目根目录添加到`PYTHONPATH`：
   ```bash
   # Windows (PowerShell)
   $env:PYTHONPATH = $pwd.Path

   # macOS/Linux
   export PYTHONPATH=$PWD
   ```

2. **权限问题**：
   - Windows: 以管理员身份运行命令提示符或PowerShell
   - macOS/Linux: 使用`sudo`或设置适当的文件权限

3. **端口被占用**：更改端口号：
   ```python
   # 在app.py中
   app.run(debug=False, host='0.0.0.0', port=8080)  # 改用8080端口
   ```
   或使用环境变量：
   ```bash
   export FMPY_VALIDATOR_PORT=8080  # Linux/macOS
   set FMPY_VALIDATOR_PORT=8080     # Windows
   ```

## 使用方法

### 命令行验证

```python
from fmpy_validator import validate_fmu, get_fmu_info

# 验证FMU文件
problems = validate_fmu("path/to/model.fmu")
if problems:
    print("验证发现问题：")
    for problem in problems:
        print(f"- {problem}")
else:
    print("验证通过！")

# 获取FMU信息
info = get_fmu_info("path/to/model.fmu")
print(f"模型名称: {info['model_name']}")
print(f"FMI版本: {info['fmi_version']}")
print(f"变量数量: {info['variable_count']}")
```

### Web界面

启动Web服务器：
```bash
python -m fmpy_validator.webapp
```

然后在浏览器中访问：http://localhost:5000

## 验证选项

`validate_fmu` 函数支持以下选项：

- `validate_variable_names`: 是否验证变量名（默认为True）
- `validate_model_structure`: 是否验证模型结构（默认为True）
- `strict_initial_unknowns`: 是否严格验证InitialUnknowns（默认为False）

示例：
```python
# 只进行基本验证
problems = validate_fmu("model.fmu", 
                       validate_variable_names=False,
                       validate_model_structure=False)

# 严格验证，包括InitialUnknowns
problems = validate_fmu("model.fmu", strict_initial_unknowns=True)
```

## 开发

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/fmpy_validator.git
cd fmpy_validator
```

2. 安装开发依赖：
```bash
pip install -e ".[dev]"
```

3. 运行测试：
```bash
pytest
```

## 许可证

BSD License

## 贡献

欢迎提交问题和拉取请求！

## 联系方式

如有问题或建议，请通过GitHub Issues联系我们。 


