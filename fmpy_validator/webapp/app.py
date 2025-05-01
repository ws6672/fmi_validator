"""
FMI Validator Web Application
"""

import os
import sys
import logging
import warnings
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

# 忽略FMPy日志DLL加载警告
warnings.filterwarnings("ignore", message="Failed to add logger proxy function")

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)
print(f"添加项目根目录到sys.path: {project_root}")

# 使用绝对导入
from fmpy_validator.validator import validate_fmu, get_fmu_info

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max-limit

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'fmu'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validate', methods=['POST'])
def validate():
    """处理FMU文件验证请求"""
    try:
        # 检查是否有文件
        if 'fmu_file' not in request.files and 'file' not in request.files:
            logger.error("没有上传文件")
            return jsonify({'success': False, 'error': '没有上传文件'}), 400
            
        file = request.files.get('fmu_file') or request.files.get('file')
        if file.filename == '':
            logger.error("没有选择文件")
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
            
        # 检查文件类型
        if not allowed_file(file.filename):
            logger.error(f"不支持的文件类型: {file.filename}")
            return jsonify({'success': False, 'error': '不支持的文件类型，请上传.fmu文件'}), 400
            
        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"文件已上传: {filename}")
        
        try:
            # 获取FMU信息
            fmu_info = get_fmu_info(filepath)
            logger.info(f"获取到FMU信息: {fmu_info}")
            
            # 检查文件有效性
            if 'error' in fmu_info:
                error_msg = fmu_info['error']
                # 如果错误消息提示不是关键错误，仍继续验证
                if "正在使用简化信息" in error_msg or "尝试解析" in error_msg:
                    logger.warning(f"FMU信息获取警告，将继续验证: {error_msg}")
                else:
                    logger.error(f"FMU信息获取失败: {error_msg}")
                    return jsonify({
                        'success': False, 
                        'error': f"无效的FMU文件: {error_msg}",
                        'summary': {
                            'status': 'error',
                            'message': '验证失败',
                            'errors': [f"无效的FMU文件: {error_msg}"]
                        }
                    }), 400
            
            # 执行验证
            validation_results = validate_fmu(
                filepath,
                validate_variable_names=True,
                validate_model_structure=True,
                strict_initial_unknowns=False
            )
            
            logger.info(f"验证完成，结果: {validation_results}")
            
            # 将验证结果转换为前端期望的格式
            formatted_results = {
                'success': validation_results.get('success', False),
                'file_structure': [],
                'model_description': [],
                'dll_validation': [],
                'functional_validation': []
            }
            
            # 收集所有错误和警告
            errors = []
            warnings = []
            
            # 将各类验证结果格式化
            for category in ['file_structure', 'model_description', 'dll_validation', 'functional_validation']:
                if category in validation_results:
                    for result in validation_results[category]:
                        formatted_result = {
                            'status': result.status,
                            'message': result.message,
                            'details': result.details
                        }
                        formatted_results[category].append(formatted_result)
                        
                        # 收集错误和警告
                        if result.status == 'error':
                            errors.append(f"{category}: {result.message}")
                        elif result.status == 'warning':
                            warnings.append(f"{category}: {result.message}")
            
            # 确保success字段与错误状态一致
            formatted_results['success'] = len(errors) == 0
            
            # 添加汇总信息
            if errors:
                formatted_results['summary'] = {
                    'status': 'error',
                    'message': '验证失败',
                    'errors': errors,
                    'warnings': warnings
                }
            elif warnings:
                formatted_results['summary'] = {
                    'status': 'warning',
                    'message': '验证通过，但有警告',
                    'warnings': warnings
                }
            else:
                formatted_results['summary'] = {
                    'status': 'success',
                    'message': '验证完全通过'
                }
            
            # 清理文件
            os.remove(filepath)
            
            return jsonify(formatted_results)
            
        except Exception as e:
            # 确保清理文件
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.error(f"验证处理异常: {str(e)}")
            raise e
            
    except Exception as e:
        logger.error(f"验证过程发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'summary': {
                'status': 'error',
                'message': '验证过程发生错误',
                'errors': [str(e)]
            },
            'file_structure': [],
            'model_description': [],
            'dll_validation': [],
            'functional_validation': []
        }), 500

# 添加直接运行支持
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000) 