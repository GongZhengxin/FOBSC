@echo off
:: 设置应用名称和主程序文件
set APP_NAME=FOBSC
set MAIN_SCRIPT=interface.py

:: 设置图标文件路径（如果没有图标文件，可以删除这一行）
set ICON_PATH=FOBSC_icon.ico

:: 清理之前的构建文件夹
rd /s /q build
rd /s /q dist
del /f /q %APP_NAME%.spec

:: 增加递归深度限制
set PYTHONRECURSIONLIMIT=5000

:: PyQt5 和 PyQt6 插件和翻译目录
set PYQT5_PLUGIN_PATH=D:\anaconda3\envs\fob_kilosort\Lib\site-packages\PyQt5\Qt5\plugins
set PYQT5_TRANSLATION_PATH=D:\anaconda3\envs\fob_kilosort\Lib\site-packages\PyQt5\Qt5\translations
set PYQT6_PLUGIN_PATH=D:\anaconda3\envs\fob_kilosort\Lib\site-packages\PyQt6\Qt6\plugins
set PYQT6_TRANSLATION_PATH=D:\anaconda3\envs\fob_kilosort\Lib\site-packages\PyQt6\Qt6\translations

:: 打包命令
pyinstaller --onedir --windowed --name %APP_NAME% --icon=%ICON_PATH% --additional-hooks-dir=. --log-level=DEBUG^
    --add-data "%PYQT5_PLUGIN_PATH%;PyQt5/Qt5/plugins" ^
    --add-data "%PYQT5_TRANSLATION_PATH%;PyQt5/Qt5/translations" ^
    --add-data "%PYQT6_PLUGIN_PATH%;PyQt6/Qt6/plugins" ^
    --add-data "%PYQT6_TRANSLATION_PATH%;PyQt6/Qt6/translations" ^
    --add-data "util;util" ^
    --hidden-import=sip --hidden-import=PyQt5.sip --hidden-import=PyQt6.sip ^
    %MAIN_SCRIPT%

:: 提示打包完成
echo OK! dist\%APP_NAME%.exe
pause
