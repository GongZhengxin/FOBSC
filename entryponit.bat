@echo off
:: 设置 conda 的基本路径
SET "CONDA_BASE=D:\anaconda3"  

:: 手动调用 activate.bat 脚本以初始化 conda 环境
CALL "%CONDA_BASE%\Scripts\activate.bat" "%CONDA_BASE%"

:: 激活指定的虚拟环境
CALL conda activate fob_kilosort

:: 运行 Python 脚本
python %FOBSC_PATH%\interface.py 

:: 保持窗口打开以查看错误信息
:: pause
