"""配置映射：把 UI 控件值按类型写回 config dict。"""
from webui_app.helpers import common_textarea_handle


def _handle_int(value):
    if value.value == '' or value.value is None:
        return 0
    return int(value.value)

def _handle_float(value):
    if value.value == '' or value.value is None:
        return 0
    return round(float(value.value), 2)

def _handle_string(value):
    # 未选中的下拉框 value 是 None，直接 str() 会把字符串 "None" 写进 config.json，
    # 下次启动时它既不是合法选项、又看起来像用户真填了个标题
    return '' if value.value is None else str(value.value)

def _handle_bool(value):
    return bool(value.value)

def _handle_textarea(value):
    return common_textarea_handle(value.value)

# 处理器映射
type_handlers = {
    'int': _handle_int,
    'float': _handle_float,
    'str': _handle_string,
    'bool': _handle_bool,
    'textarea': _handle_textarea,
}

def update_nested_dict(target, keys, value):
    """递归更新嵌套字典"""
    if len(keys) == 1:
        target[keys[0]] = value
        return
    if keys[0] not in target:
        target[keys[0]] = {}
    update_nested_dict(target[keys[0]], keys[1:], value)

def process_config_mapping(config_data, mapping, show_card_check=None):
    """处理配置映射，支持不同层级的嵌套"""
    def recurse_mapping(current_mapping, current_path=None):
        current_path = [] if current_path is None else current_path
        for key, value in current_mapping.items():
            new_path = current_path + [key]
            if isinstance(value, dict):
                recurse_mapping(value, new_path)
            else:
                component, type_name = value
                handler = type_handlers[type_name]
                processed_value = handler(component)
                update_nested_dict(config_data, new_path, processed_value)

    recurse_mapping(mapping)
    return config_data


def update_config(config_mapping, config, config_data, type="common_config"):
    # 处理常规配置
    for section, section_mapping in config_mapping.items():
        if type is not None:
            if config.get("webui", "show_card", type, section):
                if section not in config_data:
                    config_data[section] = {}
                
                process_config_mapping(config_data[section], section_mapping)
        else:
            if section not in config_data:
                config_data[section] = {}
            
            process_config_mapping(config_data[section], section_mapping)

    return config_data
