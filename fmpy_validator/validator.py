"""
FMU 验证器核心功能
提供全面的 FMU 文件验证，支持 FMI 1.0、2.0 和 3.0 标准
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Union, Optional, Any, IO
from dataclasses import dataclass
from fmpy.model_description import ModelDescription, read_model_description, ValidationError
import asyncio
import logging
from functools import lru_cache
import contextlib
from fmpy.util import fmu_info

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextlib.contextmanager
def open_fmu(filename: Union[str, IO]):
    """上下文管理器，确保FMU文件被正确关闭"""
    if isinstance(filename, str) and os.path.isfile(filename):
        with zipfile.ZipFile(filename, 'r') as zf:
            yield zf
    else:
        yield filename

@lru_cache(maxsize=10)
def cached_read_model_description(filename: str, validate: bool, validate_variable_names: bool, validate_model_structure: bool) -> ModelDescription:
    """缓存模型描述读取结果，避免重复读取"""
    return read_model_description(
        filename,
        validate=validate,
        validate_variable_names=validate_variable_names,
        validate_model_structure=validate_model_structure
    )

@dataclass
class ValidationResult:
    """验证结果数据类"""
    status: str  # 'success', 'error', 'warning'
    message: str
    details: Optional[str] = None

class FMUValidator:
    """FMU验证器类"""
    
    def __init__(self):
        self.validation_results = {
            'success': False,
            'file_structure': [],
            'model_description': [],
            'dll_validation': [],
            'functional_validation': []
        }
    
    def validate(self, fmu_path: str, validate_variable_names: bool = True,
                validate_model_structure: bool = True,
                strict_initial_unknowns: bool = False) -> Dict[str, Any]:
        """验证FMU文件"""
        try:
            # 文件结构验证
            self._validate_file_structure(fmu_path)
            
            # 模型描述验证
            self._validate_model_description(
                fmu_path, 
                validate_variable_names=validate_variable_names,
                validate_model_structure=validate_model_structure
            )
            
            # DLL验证
            self._validate_dll(fmu_path)
            
            # 功能验证
            self._validate_functionality(fmu_path)
            
            # 更新整体验证状态：只有error才算失败，warning不影响验证结果
            has_errors = any(result.status == 'error' for category in self.validation_results.values() 
                            if isinstance(category, list) for result in category)
            
            # 检查必要条件
            if 'model_description' in self.validation_results:
                model_description_results = self.validation_results['model_description']
                
                # 判断模型描述是否通过了基础验证 (包括带警告的基本验证通过)
                has_valid_model_description = any(
                    result.status == 'success' and ('模型描述验证通过' in result.message or '模型描述基本验证通过' in result.message)
                    for result in model_description_results
                )
                
                # 判断是否存在错误
                has_md_errors = any(
                    result.status == 'error'
                    for result in model_description_results
                )
                
                # 只有当既没有成功标记，也存在错误时，才认为验证失败
                if not has_valid_model_description and has_md_errors:
                    has_errors = True
                    
                    # 确保有明确的错误信息
                    if not any(result.status == 'error' for result in model_description_results):
                        self.validation_results['model_description'].append(
                            ValidationResult(
                                status='error',
                                message='模型描述验证未通过',
                                details='未能识别有效的FMI模型描述'
                            )
                        )
                # 有成功标记但也有错误时，根据宽松度决定是否通过
                elif has_valid_model_description and has_md_errors and not strict_initial_unknowns:
                    # 在宽松模式下，如果有成功标记，即使有错误也认为验证通过
                    logger.info("模型描述存在错误，但在宽松模式下仍认为验证通过")
                    # 错误已记录，不影响整体验证结果
            
            # 文件结构必须有效
            if 'file_structure' in self.validation_results:
                # 检查是否有modelDescription.xml文件
                has_model_description_file = any(
                    'modelDescription.xml文件存在' in result.message and result.status == 'success'
                    for result in self.validation_results['file_structure']
                )
                
                if not has_model_description_file:
                    has_errors = True
            
            # 模型必须有至少一种接口类型
            if not has_errors and 'functional_validation' in self.validation_results:
                has_interface = False
                for result in self.validation_results['functional_validation']:
                    if ('Co-Simulation接口有效' in result.message or 
                        'Model Exchange接口有效' in result.message) and result.status == 'success':
                        has_interface = True
                        break
                
                if not has_interface:
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='error',
                            message='缺少有效的接口类型',
                            details='FMU必须支持Co-Simulation或Model Exchange接口中的至少一种'
                        )
                    )
                    has_errors = True
            
            self.validation_results['success'] = not has_errors
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"验证过程中发生错误: {str(e)}")
            error_result = ValidationResult(
                status='error',
                message=f"验证过程中发生错误: {str(e)}",
                details=f"异常类型: {type(e).__name__}"
            )
            self.validation_results['model_description'].append(error_result)
            self.validation_results['success'] = False
            return self.validation_results
    
    def _validate_file_structure(self, fmu_path: str):
        """验证FMU文件结构"""
        try:
            with open_fmu(fmu_path) as zf:
                file_list = zf.namelist()
                
                # 检查modelDescription.xml
                if 'modelDescription.xml' not in file_list:
                    self.validation_results['file_structure'].append(
                        ValidationResult(
                            status='error',
                            message='缺少modelDescription.xml文件',
                            details='FMU必须包含modelDescription.xml文件'
                        )
                    )
                else:
                    # 验证XML文件格式
                    try:
                        with zf.open('modelDescription.xml') as xml_file:
                            content = xml_file.read()
                            # 检查是否为有效的XML
                            ET.fromstring(content)
                            
                        self.validation_results['file_structure'].append(
                            ValidationResult(
                                status='success',
                                message='modelDescription.xml文件存在且格式有效',
                            )
                        )
                    except Exception as xml_err:
                        self.validation_results['file_structure'].append(
                            ValidationResult(
                                status='error',
                                message='modelDescription.xml文件格式无效',
                                details=f'XML解析错误: {str(xml_err)}'
                            )
                        )
                
                # 检查资源目录
                if 'resources/' not in file_list and not any(f.startswith('resources/') for f in file_list):
                    self.validation_results['file_structure'].append(
                        ValidationResult(
                            status='warning',
                            message='缺少resources目录',
                            details='FMU应该包含resources目录用于存放相关资源'
                        )
                    )
                else:
                    self.validation_results['file_structure'].append(
                        ValidationResult(
                            status='success',
                            message='resources目录存在',
                        )
                    )
                
                # 检查文档
                has_documentation = any(f.startswith('documentation/') for f in file_list)
                if not has_documentation:
                    self.validation_results['file_structure'].append(
                        ValidationResult(
                            status='warning',
                            message='缺少documentation目录',
                            details='建议FMU包含documentation目录用于存放相关文档'
                        )
                    )
                else:
                    self.validation_results['file_structure'].append(
                        ValidationResult(
                            status='success',
                            message='documentation目录存在',
                        )
                    )
        except Exception as e:
            self.validation_results['file_structure'].append(
                ValidationResult(
                    status='error',
                    message=f'文件结构验证失败: {str(e)}',
                    details=f'异常类型: {type(e).__name__}'
                )
            )
    
    def _validate_model_description(self, fmu_path: str, validate_variable_names: bool = True,
                                  validate_model_structure: bool = True):
        """验证modelDescription.xml，使用与model_description.py类似的逻辑"""
        try:
            # 首先尝试不验证地读取模型描述，获取基本信息
            try:
                basic_model_description = read_model_description(
                    fmu_path, 
                    validate=False
                )
                
                # 记录基本信息
                has_basic_info = True
                basic_fmi_version = basic_model_description.fmiVersion
                basic_model_name = basic_model_description.modelName
                basic_var_count = len(basic_model_description.modelVariables)
                basic_model_type = self._get_model_type(basic_model_description)
            except Exception:
                has_basic_info = False
            
            # 再尝试带验证地读取
            try:
                model_description = read_model_description(
                    fmu_path,
                    validate=True,
                    validate_variable_names=validate_variable_names,
                    validate_model_structure=validate_model_structure
                )
                
                # 完全验证成功
                self.validation_results['model_description'].append(
                    ValidationResult(
                        status='success',
                        message='模型描述验证通过',
                        details=f'FMI版本: {model_description.fmiVersion}, 模型名称: {model_description.modelName}'
                    )
                )
                
                # 添加模型信息
                self.validation_results['model_description'].append(
                    ValidationResult(
                        status='success',
                        message=f'模型类型: {self._get_model_type(model_description)}',
                        details=f'变量数量: {len(model_description.modelVariables)}'
                    )
                )
                
            except ValidationError as ve:
                # 收集所有问题，并区分严重错误和警告
                has_errors = False
                has_warnings = False
                
                for problem in ve.problems:
                    # 检查是否为InitialUnknowns问题，如果是则降级为警告
                    if "ModelStructure/InitialUnknowns does not contain the expected set of variables" in problem:
                        has_warnings = True
                        self.validation_results['model_description'].append(
                            ValidationResult(
                                status='warning',
                                message='模型描述验证警告',
                                details=problem
                            )
                        )
                    else:
                        has_errors = True
                        self.validation_results['model_description'].append(
                            ValidationResult(
                                status='error',
                                message='模型描述验证失败',
                                details=problem
                            )
                        )
                
                # 如果有基本信息并且只有警告，添加一个成功验证结果
                if has_basic_info and not has_errors:
                    self.validation_results['model_description'].append(
                        ValidationResult(
                            status='success',
                            message='模型描述基本验证通过（存在警告）',
                            details=f'FMI版本: {basic_fmi_version}, 模型名称: {basic_model_name}'
                        )
                    )
                    
                    # 添加模型信息
                    self.validation_results['model_description'].append(
                        ValidationResult(
                            status='success',
                            message=f'模型类型: {basic_model_type}',
                            details=f'变量数量: {basic_var_count}'
                        )
                    )
                    
        except Exception as e:
            # 处理其他异常
            self.validation_results['model_description'].append(
                ValidationResult(
                    status='error',
                    message=f'模型描述验证过程异常: {str(e)}',
                    details=f'异常类型: {type(e).__name__}'
                )
            )
    
    def _get_model_type(self, model_description: ModelDescription) -> str:
        """确定模型类型"""
        types = []
        if model_description.coSimulation:
            types.append("Co-Simulation")
        if model_description.modelExchange:
            types.append("Model Exchange")
        if hasattr(model_description, 'scheduledExecution') and model_description.scheduledExecution:
            types.append("Scheduled Execution")
        return " & ".join(types) if types else "未知"
    
    def _validate_dll(self, fmu_path: str):
        """验证DLL文件"""
        try:
            with open_fmu(fmu_path) as zf:
                file_list = zf.namelist()
                
                # 检查是否存在binaries目录
                has_binaries = any(f.startswith('binaries/') for f in file_list)
                
                # 检查源代码目录
                has_sources = any(f.startswith('sources/') for f in file_list)
                
                # 必须至少有一个binaries或sources目录
                if not has_binaries and not has_sources:
                    self.validation_results['dll_validation'].append(
                        ValidationResult(
                            status='error',  # 升级为错误级别
                            message='未找到binaries或sources目录',
                            details='FMU必须包含预编译的二进制文件或源代码'
                        )
                    )
                    return
                elif not has_binaries:
                    self.validation_results['dll_validation'].append(
                        ValidationResult(
                            status='warning',
                            message='未找到binaries目录',
                            details='FMU不包含预编译的二进制文件，但包含源代码'
                        )
                    )
                
                # 检查平台特定的二进制文件
                platforms = {
                    'win32': 'binaries/win32/',
                    'win64': 'binaries/win64/',
                    'linux32': 'binaries/linux32/',
                    'linux64': 'binaries/linux64/',
                    'darwin64': 'binaries/darwin64/'
                }
                
                found_platforms = []
                for platform, path in platforms.items():
                    if any(f.startswith(path) for f in file_list):
                        found_platforms.append(platform)
                
                if found_platforms:
                    self.validation_results['dll_validation'].append(
                        ValidationResult(
                            status='success',
                            message=f'找到{len(found_platforms)}个平台的二进制文件',
                            details=f'支持平台: {", ".join(found_platforms)}'
                        )
                    )
                else:
                    self.validation_results['dll_validation'].append(
                        ValidationResult(
                            status='warning',
                            message='未找到任何平台的二进制文件',
                            details='FMU可能只包含源代码或不完整'
                        )
                    )
                
        except Exception as e:
            self.validation_results['dll_validation'].append(
                ValidationResult(
                    status='error',
                    message=f'二进制文件验证失败: {str(e)}',
                    details=f'异常类型: {type(e).__name__}'
                )
            )
    
    def _validate_functionality(self, fmu_path: str):
        """验证FMU功能"""
        try:
            # 获取基本FMU信息
            info = get_fmu_info(fmu_path)
            if 'error' in info:
                # 还是报告错误，但不阻止继续验证
                self.validation_results['functional_validation'].append(
                    ValidationResult(
                        status='warning',  # 降级为警告而不是错误
                        message='获取FMU信息存在问题',
                        details=info['error']
                    )
                )
            
            # 检查FMI版本是否有效
            fmi_version = info.get('fmi_version')
            if not fmi_version or fmi_version == "未知":
                self.validation_results['functional_validation'].append(
                    ValidationResult(
                        status='warning',  # 降级为警告
                        message='无法识别FMI版本',
                        details='将使用模型描述XML中的版本信息'
                    )
                )
            else:
                self.validation_results['functional_validation'].append(
                    ValidationResult(
                        status='success',
                        message='FMU基本信息验证通过',
                        details=f"模型名称: {info.get('model_name')}, FMI版本: {fmi_version}"
                    )
                )
            
            # 尝试读取模型描述以验证其功能完整性
            try:
                model_description = read_model_description(fmu_path, validate=False)
                
                # 检查变量数量
                var_count = len(model_description.modelVariables)
                if var_count == 0:
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='error',  # 升级为错误级别
                            message='FMU没有定义任何变量',
                            details='这是一个无效的FMU，必须定义至少一个变量'
                        )
                    )
                else:
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='success',
                            message=f'FMU定义了{var_count}个变量',
                            details='变量定义有效'
                        )
                    )
                
                # 检查接口类型
                has_interface = False
                
                # 根据FMI类型进行特定验证
                if model_description.coSimulation:
                    has_interface = True
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='success',
                            message='Co-Simulation接口有效',
                            details=f'模型标识符: {model_description.coSimulation.modelIdentifier}'
                        )
                    )
                    
                if model_description.modelExchange:
                    has_interface = True
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='success',
                            message='Model Exchange接口有效',
                            details=f'模型标识符: {model_description.modelExchange.modelIdentifier}'
                        )
                    )
                
                # 如果从info中获取了接口类型，但模型描述中没有找到，使用info中的信息
                if not has_interface:
                    is_cs = info.get('co_simulation', False)
                    is_me = info.get('model_exchange', False)
                    
                    if is_cs or is_me:
                        has_interface = True
                        if is_cs:
                            self.validation_results['functional_validation'].append(
                                ValidationResult(
                                    status='success',
                                    message='Co-Simulation接口有效（从FMU信息中检测）',
                                    details='无法从模型描述中获取模型标识符'
                                )
                            )
                        if is_me:
                            self.validation_results['functional_validation'].append(
                                ValidationResult(
                                    status='success',
                                    message='Model Exchange接口有效（从FMU信息中检测）',
                                    details='无法从模型描述中获取模型标识符'
                                )
                            )
                
                if not has_interface:
                    self.validation_results['functional_validation'].append(
                        ValidationResult(
                            status='error',
                            message='FMU未定义有效的接口类型',
                            details='FMU必须定义Co-Simulation或Model Exchange接口中的至少一种'
                        )
                    )
                
                # 额外信息验证（仅用于提供更多信息，不影响验证结果）
                if not info.get('error') and fmi_version != "未知":
                    # 验证info和model_description中的信息是否一致
                    if model_description.fmiVersion and fmi_version != model_description.fmiVersion:
                        self.validation_results['functional_validation'].append(
                            ValidationResult(
                                status='warning',
                                message='FMI版本信息不一致',
                                details=f'从FMU信息获取的版本为{fmi_version}，而模型描述中的版本为{model_description.fmiVersion}'
                            )
                        )
                
            except Exception as e:
                self.validation_results['functional_validation'].append(
                    ValidationResult(
                        status='error',  # 升级为错误级别
                        message='功能完整性验证失败',
                        details=f'错误: {str(e)}'
                    )
                )
            
        except Exception as e:
            self.validation_results['functional_validation'].append(
                ValidationResult(
                    status='error',
                    message=f'功能验证失败: {str(e)}',
                    details=f'异常类型: {type(e).__name__}'
                )
            )

def get_fmu_info(fmu_path: str) -> Dict[str, Any]:
    """
    获取FMU文件的基本信息
    
    参数:
        fmu_path: FMU文件路径
    
    返回:
        包含FMU信息的字典
    """
    try:
        logger.info(f"正在获取FMU信息: {fmu_path}")
        
        # 调用FMPy的fmu_info函数获取信息
        info_str = fmu_info(fmu_path)
        
        # 检查返回值是否为字符串（而非字典）
        if isinstance(info_str, str):
            logger.warning(f"fmu_info返回了字符串而不是字典: {info_str}")
            
            # 从字符串中解析信息
            info = {}
            
            # 提取FMI版本
            if "FMI Version" in info_str:
                version_match = info_str.split("FMI Version")[1].strip().split("\n")[0].strip()
                info['fmi_version'] = version_match
            
            # 提取模型名称
            if "Model Name" in info_str:
                model_match = info_str.split("Model Name")[1].strip().split("\n")[0].strip()
                info['model_name'] = model_match
            
            # 提取工具名称
            if "Generation Tool" in info_str:
                tool_match = info_str.split("Generation Tool")[1].strip().split("\n")[0].strip()
                info['generation_tool'] = tool_match
            
            # 提取变量命名约定
            info['variable_naming_convention'] = "未知"
            
            # 提取事件指示符数量
            if "Event Indicators" in info_str:
                event_match = info_str.split("Event Indicators")[1].strip().split("\n")[0].strip()
                try:
                    info['number_of_event_indicators'] = int(event_match)
                except ValueError:
                    info['number_of_event_indicators'] = 0
            
            # 提取连续状态数量
            if "Continuous States" in info_str:
                states_match = info_str.split("Continuous States")[1].strip().split("\n")[0].strip()
                try:
                    info['number_of_continuous_states'] = int(states_match)
                except ValueError:
                    info['number_of_continuous_states'] = 0
            
            # 提取变量数量
            if "Variables" in info_str:
                vars_match = info_str.split("Variables")[1].strip().split("\n")[0].strip()
                try:
                    info['number_of_variables'] = int(vars_match)
                except ValueError:
                    info['number_of_variables'] = 0
            
            # 判断FMI类型
            info['co_simulation'] = "Co-Simulation" in info_str
            info['model_exchange'] = "Model Exchange" in info_str
            info['scheduled_execution'] = "Scheduled Execution" in info_str
            
            # 提取支持的平台
            if "Platforms" in info_str:
                platforms_match = info_str.split("Platforms")[1].strip().split("\n")[0].strip()
                info['platforms'] = [p.strip() for p in platforms_match.split(',')]
            
            # 保存原始信息以备参考
            info['original_info'] = info_str
            
            return info
            
        # 如果是字典，直接返回
        if isinstance(info_str, dict):
            return info_str
        
        # 如果都不是，则返回错误
        return {
            'error': f'无法解析FMU信息，返回类型: {type(info_str).__name__}',
            'raw_info': str(info_str)
        }
        
    except Exception as e:
        logger.error(f"获取FMU信息时发生错误: {str(e)}")
        return {
            'error': f'获取FMU信息失败: {str(e)}',
            'traceback': str(e.__traceback__)
        }

def validate_fmu(fmu_path: str, validate_variable_names: bool = True,
                validate_model_structure: bool = True,
                strict_initial_unknowns: bool = False) -> Dict[str, Any]:
    """验证FMU文件的主函数"""
    validator = FMUValidator()
    return validator.validate(
        fmu_path,
        validate_variable_names=validate_variable_names,
        validate_model_structure=validate_model_structure,
        strict_initial_unknowns=strict_initial_unknowns
    )

# 异步验证（推荐）
async def validate_and_show_progress(filename):
    validator = FMUValidator()
    
    # 启动验证任务
    validation_task = asyncio.create_task(
        asyncio.to_thread(validator.validate, filename)
    )
    
    # 显示进度
    progress_steps = ["文件结构验证", "模型描述验证", "DLL验证", "功能验证"]
    total_steps = len(progress_steps)
    
    for i, step in enumerate(progress_steps):
        if validation_task.done():
            break
            
        print(f"进度: {int((i/total_steps)*100)}% - {step}")
        await asyncio.sleep(0.5)
    
    # 获取结果
    results = await validation_task
    return results

# 同步验证（保持向后兼容）
def validate_sync(filename: Union[str, IO],
                 validate_variable_names: bool = True,
                 validate_model_structure: bool = True,
                 strict_initial_unknowns: bool = False) -> Dict[str, Any]:
    """同步验证FMU文件
    
    Args:
        filename: FMU文件路径或文件对象
        validate_variable_names: 是否验证变量名
        validate_model_structure: 是否验证模型结构
        strict_initial_unknowns: 是否严格验证初始未知量
        
    Returns:
        包含验证结果的字典
    """
    validator = FMUValidator()
    try:
        # 1. 基础文件验证
        if isinstance(filename, str):
            if not os.path.exists(filename):
                return {'success': False, 'error': '文件不存在'}
            if not filename.endswith('.fmu'):
                return {'success': False, 'error': '文件格式错误，不是FMU文件'}
        
        # 2. 执行验证
        return validator.validate(
            filename,
            validate_variable_names=validate_variable_names,
            validate_model_structure=validate_model_structure,
            strict_initial_unknowns=strict_initial_unknowns
        )
        
    except Exception as e:
        logger.error(f"验证过程中发生错误: {str(e)}")
        return {'success': False, 'error': f'验证过程中发生错误: {str(e)}'}

# 在文件末尾添加导出函数
__all__ = [
    'validate_fmu',
    'validate_and_show_progress',
    'validate_sync',
    'get_fmu_info',
    'FMUValidator',
    'ValidationResult'
] 