import re

def load_meta(meta_file_name):
    print(f'Loading meta data for {meta_file_name}')  # 打印正在加载的文件名
    meta_data = {}  # 初始化字典来存储元数据
    
    with open(meta_file_name, 'r') as file:
        lines = file.readlines()  # 读取所有行
        
    for line in lines:  # 遍历每一行
        line = line.strip()  # 去除行首尾空白
        if not line:  # 如果行为空，跳过
            continue
        
        key_value = line.split('=')  # 按'='分割键值对
        if len(key_value) != 2:  # 确保分割出两个部分
            continue
        
        key = key_value[0].strip()  # 键
        value = key_value[1].strip()  # 值
        
        # 处理值的类型
        if re.search(r'\d', value):  # 检查值是否包含数字
            if '.' in value:  # 如果值包含小数点
                value = float(value)  # 转换为浮点数
            else:
                value = int(value)  # 转换为整数
        elif value.lower() == 'true':  # 如果值是'true'
            value = True  # 转换为布尔值True
        elif value.lower() == 'false':  # 如果值是'false'
            value = False  # 转换为布尔值False
        
        if key.startswith('~'):  # 如果键以'~'开头，停止解析
            break
        meta_data[key] = value  # 将键值对存入字典
        
    return meta_data


# def load_meta(meta_file_name):
#     meta_data = {}
#     print(f'Loading meta data for {meta_file_name}')
    
#     with open(meta_file_name, 'r') as file:
#         lines = file.readlines()

#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue
        
#         key_value = line.split('=')
#         if len(key_value) != 2:
#             continue
        
#         key, value = key_value[0].strip(), key_value[1].strip()
        
#         if any(char.isdigit() for char in value):
#             if '.' in value:
#                 value = float(value)
#             else:
#                 value = int(value)
#         elif value.lower() == 'true':
#             value = True
#         elif value.lower() == 'false':
#             value = False
        
#         if key.startswith('~'):
#             break

#         meta_data[key] = value
        
#     return meta_data

import numpy as np
import mmap
import os
import scipy.signal

def load_NI_data(NIFileName):
    # 加载元数据
    NI_META = load_meta(f'{NIFileName}.meta')
    
    # 获取文件字节数、通道数和样本数
    n_file_bytes = NI_META['fileSizeBytes']
    n_chan = NI_META['nSavedChans']
    n_file_samp = int(n_file_bytes / (2 * n_chan))

    # 打印文件信息
    print(f'Load NI DATA\nn_channels: {n_chan}, n_file_samples: {n_file_samp}')
    record_seconds = n_file_samp / NI_META['niSampRate']
    print(f'Recording Last {int(record_seconds)} seconds {int(record_seconds / 60)} mins')

    # 使用内存映射读取二进制文件
    with open(f'{NIFileName}.bin', 'rb') as f:
        with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as m:
            raw_data = np.frombuffer(m, dtype=np.int16)
            raw_data = raw_data.reshape((n_chan, n_file_samp), order='F')

    # 数据转换比例
    fI2V = NI_META['niAiRangeMax'] / 32768

    # 提取元数据中的一些参数
    MN, MA, XA, DW = NI_META['snsMnMaXaDw']
    dig_ch = MN + MA + XA + 1

    # 模拟输入通道数据转换为电压
    AIN = raw_data[0, :] * fI2V

    # 获取数字信号
    digital0 = raw_data[dig_ch - 1, :]

    # 计算数字信号的变化并提取事件代码的位置和值
    code_all = np.diff(digital0)
    code_loc = np.where(code_all > 0)[0]
    code_val = code_all[code_loc]

    # 修正事件代码
    code_val[code_val == 63] = 64
    code_val[code_val == 65] = 64
    code_val[code_val == 3] = 2

    # 打印事件数据
    print('Load Event Data')
    all_code = np.unique(code_val)
    for code_now in all_code:
        print(f'Event {int(code_now)} {np.sum(code_val == code_now)} times')

    # 将时间转换为毫秒
    code_time = 1000 * code_loc / NI_META['niSampRate']

    # 重新采样
    p, q = scipy.signal.resample_poly(AIN, up=1000, down=NI_META['niSampRate'])
    AIN_resampled = scipy.signal.resample_poly(AIN, p, q)

    # 返回处理的数据
    DCode = {
        'CodeLoc': code_loc,
        'CodeVal': code_val,
        'CodeTime': code_time
    }

    return NI_META, AIN_resampled, DCode