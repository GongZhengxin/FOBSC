import sys
import os
import time
import subprocess
import pandas as pd
import matlab.engine
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6 import uic, QtCore, QtWidgets
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QListWidget, QTableView, QTextBrowser
from PyQt6.QtCore import QAbstractTableModel, Qt, QThread, pyqtSignal

# 更新 PreprocessingThread 以接受 MATLAB 引擎实例
class PreprocessingThread(QThread):
    progress = pyqtSignal(str)  # 定义一个信号用于传递进度信息

    def __init__(self, selections, parameters, matlab_engine, parent=None):
        super().__init__(parent)
        self.selections = selections
        self.parameters = parameters
        self.matlab_engine = matlab_engine  # 接收并使用主窗口中的 MATLAB 引擎实例

    def run(self):
        try:
            self.progress.emit("[MATLAB] 预处理进程成功接收引擎")

            # 根据用户选择执行不同的预处理
            if self.selections['data_check']:
                self.progress.emit("[Process] 执行 Data Check...")
                # self.matlab_engine.data_check(nargout=0)  # 假设 MATLAB 中有名为 data_check 的函数
            
            if self.selections['good_unit_strc']:
                pre_onset, post_onset, psth_window_size = self.parameters
                self.progress.emit(f"[Process] 执行 GoodUnitStrc Process... \n     [Parameter] pre_onset={pre_onset}\n     [Parameter] post_onset={post_onset}\n     [Parameter] psth_window_size={psth_window_size}")
                # self.matlab_engine.good_unit_strc_process(pre_onset, post_onset, psth_window_size, nargout=0)  # 假设 MATLAB 函数
            
            if self.selections['lfp_process']:
                self.progress.emit("[Process] 执行 LFP Process...")
                # self.matlab_engine.lfp_process(nargout=0)  # 假设 MATLAB 中有名为 lfp_process 的函数

            self.progress.emit("[Process] Process Done!")

        except Exception as e:
            self.progress.emit(f"预处理发生错误: {str(e)}")

class PreprocessingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(current_dir, 'PreprocessDialog.ui') 
        # 加载 .ui 文件
        uic.loadUi(ui_file, self)

        # 假设 PreprocessDialog.ui 中包含的勾选框和输入框已经命名
        # 使用 Qt Designer 设置好每个组件的对象名，以下是一些可能的对象名示例：
        self.data_check = self.findChild(QtWidgets.QCheckBox, 'dataCheck')
        self.data_check.setChecked(True)
        self.good_unit_strc = self.findChild(QtWidgets.QCheckBox, 'goodUnitStrc')
        # self.good_unit_strc.setChecked(True)
        self.lfp_process = self.findChild(QtWidgets.QCheckBox, 'lfpProcess')

        # 参数设置的 SpinBox
        self.pre_onset = self.findChild(QtWidgets.QSpinBox, 'preOnsetSpinBox')
        self.post_onset = self.findChild(QtWidgets.QSpinBox, 'postOnsetSpinBox')
        self.psth_window_size = self.findChild(QtWidgets.QSpinBox, 'psthWindowSizeSpinBox')

        # 设置默认值和行为（如果需要）
        self.good_unit_strc.stateChanged.connect(self.toggle_parameters)
        self.pre_onset.setValue(50)
        self.post_onset.setValue(300)
        self.psth_window_size.setValue(20)

        # 确认按钮
        self.button_box = self.findChild(QtWidgets.QDialogButtonBox, 'comfirmButton')
        self.button_box.accepted.connect(self.accept)  # Ok 按钮连接到 accept 方法
        self.button_box.rejected.connect(self.reject)  # Cancel 按钮连接到 reject 方法

    def toggle_parameters(self):
        # 当勾选 GoodUnitStrc Process 时显示参数设置
        enabled = self.good_unit_strc.isChecked()
        self.pre_onset.setEnabled(enabled)
        self.post_onset.setEnabled(enabled)
        self.psth_window_size.setEnabled(enabled)

class MatlabEngineThread(QThread):
    started_signal = pyqtSignal(str)  # 用于传递启动状态的信号
    finished_signal = pyqtSignal(matlab.engine.MatlabEngine)  # 启动完成后传递 MATLAB 引擎实例

    def run(self):
        try:
            self.started_signal.emit("[MATLAB] 正在启动引擎，请稍候...")
            matlab_engine = matlab.engine.start_matlab()  # 启动 MATLAB 引擎
            self.started_signal.emit("[MATLAB] 引擎已成功启动。")
            self.finished_signal.emit(matlab_engine)  # 传递启动成功的 MATLAB 引擎实例
        except Exception as e:
            self.started_signal.emit(f"[MATLAB] 启动引擎失败: {str(e)}")

class KilosortThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)  # 定义一个信号，用于传递进度信息

    def __init__(self, kilosort_script_path, folder_path, log_file_path, parent=None):
        super().__init__(parent)
        self.kilosort_script_path = kilosort_script_path
        self.folder_path = folder_path
        self.log_file_path = log_file_path
        self._running = True

    def run(self):
        try:
            # 打开日志文件
            with open(self.log_file_path, "a") as log_file:
                # 启动 Kilosort 进程
                self.progress_signal.emit("[Kilosort] 进程启动中...")
                process = subprocess.Popen(
                    ["python", self.kilosort_script_path],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=self.folder_path,
                    bufsize=1
                )

                # # 监听 Kilosort 进程的运行状态
                # while process.poll() is None and self._running:
                #     time.sleep(1)  # 每秒检查一次
                #     with open(self.log_file_path, "r") as log:
                #         lines = log.readlines()
                #         if lines:
                #             self.progress_signal.emit(lines[-1])  # 将最新一行日志发送给主线程

                # 等待进程结束
                process.wait()
                self.finished_signal.emit("[Kilosort] 进程完成。")
        except Exception as e:
            self.progress_signal.emit(f"Kilosort 进程出错: {str(e)}")

    def stop(self):
        self._running = False

class LogWatcherThread(QThread):
    
    log_updated = pyqtSignal(str)  # 定义一个信号，用于传递新的日志信息

    def __init__(self, log_file_path, parent=None):
        super().__init__(parent)
        self.log_file_path = log_file_path
        self._running = True
        self.old_status = None

    def run(self):
        from collections import deque
        try:
            with open(self.log_file_path, "r") as file:
                while self._running:
                    last_lines = deque(file, maxlen=3)
                    if self.old_status is None: 
                        self.old_status = last_lines
                        for line in last_lines:
                            self.log_updated.emit(line.strip())
                    elif not last_lines == self.old_status:
                        newinfo_lines = [item for item in last_lines if item not in self.old_status]
                        for line in newinfo_lines:
                            self.log_updated.emit(line.strip())  # 逐行发送新日志
                        self.old_status = last_lines
                    else:
                        time.sleep(0.1)  # 如果没有新内容，等待 0.1 秒
        except Exception as e:
            self.log_updated.emit(f"日志监听线程出错: {str(e)}")

    def stop(self):
        self._running = False


# 假设：你已经创建了一个名为 base.ui 的文件，通过Qt Designer设计了基本界面。
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.home = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(self.home, 'Base.ui') 
        uic.loadUi(ui_file, self)  # 动态加载 UI 文件

        # 假设：base.ui中有 browseButton, checkFilesButton, displayButton, folderLabel, tableView, listWidget_FOB 等 UI 元素。
        # 绑定按钮点击事件
        self.folderLabel = self.findChild(QtWidgets.QLabel, 'folderLabel')
        self.browseButton = self.findChild(QtWidgets.QPushButton, 'browseButton')
        self.browseButton.clicked.connect(self.browse_check_load_folder)  # 连接文件夹选择按钮到 browse_folder 函数

        # 假设FOB元素已经加载到fobListWidget中
        self.fobListWidget = self.findChild(QtWidgets.QListWidget, 'listWidget_FOB')
        self.boxAListWidget = self.findChild(QtWidgets.QListWidget, 'listWidget_boxA')
        self.boxBListWidget = self.findChild(QtWidgets.QListWidget, 'listWidget_boxB')
        self.contrastListWidget = self.findChild(QtWidgets.QListWidget, 'listWidget_contrast')
        self.generateButton = self.findChild(QtWidgets.QPushButton, 'pushButton_gencontrast')
        self.clearButton = self.findChild(QtWidgets.QPushButton, 'pushButton_clearall')

        # 设置拖放行为
        self.fobListWidget.setDragEnabled(True)
        # self.fobListWidget.setAcceptDrops(True)
        self.boxAListWidget.setAcceptDrops(True)
        self.boxBListWidget.setAcceptDrops(True)
        self.boxAListWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.boxBListWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        
        # 连接按钮点击信号
        self.generateButton.clicked.connect(self.generate_contrast)
        self.contrastListWidget.itemDoubleClicked.connect(self.rename_contrast)
        self.contrastListWidget.itemClicked.connect(self.display_contrast)
        self.clearButton.clicked.connect(self.clear_all_boxes)

        # Enable removing items by dragging them out of the list
        self.boxAListWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.boxBListWidget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.boxAListWidget.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.boxBListWidget.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.boxAListWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.boxAListWidget.customContextMenuRequested.connect(self.open_context_menu_A)
        self.boxBListWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.boxBListWidget.customContextMenuRequested.connect(self.open_context_menu_B)


        # 获取 UI 中的 textBrowser
        self.text_browser = self.findChild(QtWidgets.QTextBrowser, 'textBrowser')

        # 初始化 MATLAB 引擎
        self.matlab_engine = None
        self.start_matlab_engine_async()  # 异步启动 MATLAB 引擎

        # 假设有一个开始预处理按钮（例如 pushButton_preprocess），用于开始预处理
        self.preprocessButton = self.findChild(QtWidgets.QPushButton, 'pushButton_preprocess')
        self.preprocessButton.clicked.connect(self.start_preprocessing)
        
        # 文件检查和 Kilosort 相关属性
        self.folder_path = None
        self.kilosort_log_file = None
        self.kilosort_process = None
        

    def browse_check_load_folder(self):
        try:
            # 使用文件对话框选择文件夹
            folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
            if folder_path:
                self.folder_path = folder_path  # 保存选择的文件夹路径
                self.kilosort_log_file = os.path.join(self.folder_path, "kilosort.log")
                # 假设：base.ui 中有一个用于显示当前选择路径的 QLabel，名为 folderLabel
                self.folderLabel.setText(folder_path)  # 更新 UI 显示当前选择的文件夹路径
            # 假设：我们需要检查 neural_data, bhv2_file.bhv2, info.tsv 是否存在于选定文件夹中
            # 定义必需的文件和文件夹的模式
            required_file_patterns = ["NPX_", ".bhv2", "_info.tsv"]
            missing_files = []

            # 检查必需的文件
            for pattern in required_file_patterns:
                matched_files = [f for f in os.listdir(self.folder_path) if pattern in f]
                if not matched_files:
                    warningpattern = pattern.replace('_','')
                    missing_files.append(f" '{warningpattern}' 文件")

            if missing_files:
                self.append_message("文件缺失", f"缺少以下文件: {', '.join(missing_files)}")
                # 如果有缺少的文件，弹出警告窗口
                # QMessageBox.warning(self, "文件缺失", f"缺少以下文件: {', '.join(missing_files)}")
            else:
                # 假设：info.tsv 文件中包含需要显示的数据
                info_file = [f for f in os.listdir(self.folder_path) if '_info.tsv' in f]
                if len(info_file) == 1: info_file = info_file[0]
                else: QMessageBox.warning(self, "文件冗余", f"Info File 找到了 {len(info_file)} 个： {info_file}")
                info_file_path = os.path.join(self.folder_path, info_file)
                if not os.path.exists(info_file_path):
                    raise FileNotFoundError(f"找不到文件: {info_file_path}")            
                df = pd.read_csv(info_file_path, sep='\t')  # 使用 pandas 读取 TSV 文件
                # 假设：base.ui 中有一个 QTableView，名为 tableView
                model = PandasModel(df)  # 创建 Pandas 数据模型
                self.tableView.setModel(model)  # 设置模型以显示数据
                # 提取 FOB 列的 unique 元素
                unique_elements = df['FOB'].unique()
                # 假设：base.ui 中有一个 QListWidget，名为 listWidget_FOB
                self.listWidget_FOB.clear()
                self.listWidget_FOB.addItems(unique_elements)  # 将 unique 元素添加到 QListWidget 中
                self.append_message(f"[LOAD] {self.folder_path} !")

            kilosort_dir = os.path.join(self.folder_path, 'kilosort_def_5block_97') # check file # TODO : more prepared
            if not os.path.exists(kilosort_dir):
                self.start_kilosort_process()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def generate_contrast(self):
        try:
            # 获取A和B中的元素
            a_items = [self.boxAListWidget.item(i).text() for i in range(self.boxAListWidget.count())]
            b_items = [self.boxBListWidget.item(i).text() for i in range(self.boxBListWidget.count())]

            # 生成对比字典条目
            contrast_key = f"Contrast {self.contrastListWidget.count() + 1}"
            contrast_value = (tuple(a_items), tuple(b_items))
            
            # 添加到对比列表
            self.contrastListWidget.addItem(contrast_key)
            self.contrastListWidget.item(self.contrastListWidget.count() - 1).setData(QtCore.Qt.ItemDataRole.UserRole, contrast_value)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def display_contrast(self, item):
        try:
            # 清空框A和框B
            self.boxAListWidget.clear()
            self.boxBListWidget.clear()

            # 获取对应的对比值
            contrast_value = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if contrast_value:
                a_items, b_items = contrast_value
                self.boxAListWidget.addItems(a_items)
                self.boxBListWidget.addItems(b_items)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def rename_contrast(self, item):
        text, ok = QtWidgets.QInputDialog.getText(self, "重命名对比", "输入新名称:", text=item.text())
        if ok and text:
            item.setText(text)

    def dragEnterEvent(self, event):
        """
        拖入事件，当拖入有效数据时，接受拖放。
        """
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        拖放事件处理 将元素从boxA或boxB拖出时进行删除。
        """
        source = event.source()
        if source in [self.boxAListWidget, self.boxBListWidget]:
            item = source.currentItem()
            if item:
                if event.target() == self.fobListWidget:
                    # 从当前列表中删除该项目
                    source.takeItem(source.row(item))  # 只删除，不进行添加到FOB
        event.accept()

    def clear_all_boxes(self):
        # Clear all items from boxes A and B
        self.boxAListWidget.clear()
        self.boxBListWidget.clear()
        print('clear!')

    def open_context_menu_A(self, pos):
        item = self.boxAListWidget.itemAt(pos)
        if item:
            menu = QtWidgets.QMenu(self)
            delete_action = menu.addAction("del")
            action = menu.exec(self.boxAListWidget.mapToGlobal(pos))
            if action == delete_action:
                self.boxAListWidget.takeItem(self.boxAListWidget.row(item))

    def open_context_menu_B(self, pos):
        item = self.boxBListWidget.itemAt(pos)
        if item:
            menu = QtWidgets.QMenu(self)
            delete_action = menu.addAction("del")
            action = menu.exec(self.boxBListWidget.mapToGlobal(pos))
            if action == delete_action:
                self.boxBListWidget.takeItem(self.boxBListWidget.row(item))

    def append_message(self, message):
        # 将消息添加到 textBrowser 中
        self.text_browser.append(message)
        self.text_browser.ensureCursorVisible()  # 确保最新消息始终可见

    def start_matlab_engine_async(self):
        # 创建 MATLAB 引擎启动线程
        self.matlab_engine_thread = MatlabEngineThread()
        self.matlab_engine_thread.started_signal.connect(self.append_message)  # 连接启动状态消息
        self.matlab_engine_thread.finished_signal.connect(self.on_matlab_engine_started)  # 连接 MATLAB 引擎启动完成信号
        self.matlab_engine_thread.start()  # 启动线程
    
    def on_matlab_engine_started(self, matlab_engine):
        # 保存启动完成的 MATLAB 引擎实例
        self.matlab_engine = matlab_engine
        self.append_message("[MATLAB] 引擎已准备就绪。")

    def start_preprocessing(self):
        # 弹出预处理设置窗口
        dialog = PreprocessingDialog(self)
        if dialog.exec():  # 用户确认
            # 获取用户选择和参数
            selections = {
                'data_check': dialog.data_check.isChecked(),
                'good_unit_strc': dialog.good_unit_strc.isChecked(),
                'lfp_process': dialog.lfp_process.isChecked()
            }
            parameters = (dialog.pre_onset.value(), dialog.post_onset.value(), dialog.psth_window_size.value())

            # 启动预处理线程
            if self.matlab_engine is not None:
                self.preprocessing_thread = PreprocessingThread(selections, parameters, self.matlab_engine)
                self.preprocessing_thread.progress.connect(self.append_message)  # 将进度信息连接到 append_message 方法
                self.preprocessing_thread.start()
            else:
                QMessageBox.warning(self, "Warning", f"稍后再试: 等待主进程激活 Matlab")

    def start_kilosort_process(self):
        try:
            self.append_message("[Kilosort] 进程准备启动...")
            kilosort_script_path = os.path.join(self.home, "npxkilosort.py")
            
            # 创建并启动 Kilosort 线程
            self.kilosort_thread = KilosortThread(
                kilosort_script_path=kilosort_script_path,
                folder_path=self.folder_path,
                log_file_path=self.kilosort_log_file,
            )
            self.kilosort_thread.finished_signal.connect(self.on_kilosort_finished)
            self.kilosort_thread.progress_signal.connect(self.append_message)
            self.kilosort_thread.start()
            # 启动日志监听线程
            self.start_kilolog_watcher()
        except Exception as e:
            QMessageBox.critical(self, "Kilosort 启动错误", f"无法启动 Kilosort: {str(e)}")

    def start_kilolog_watcher(self):
        # 启动日志监听线程
        self.kilolog_watcher_thread = LogWatcherThread(self.kilosort_log_file)
        self.kilolog_watcher_thread.log_updated.connect(self.append_message)
        self.kilolog_watcher_thread.start()

    def on_kilosort_finished(self, message):
        # 当 Kilosort 进程完成时，停止日志监听线程
        self.append_message(message)
        if self.kilolog_watcher_thread and self.kilolog_watcher_thread.isRunning():
            self.kilolog_watcher_thread.stop()
            self.kilolog_watcher_thread.wait()

    def closeEvent(self, event):
        # 当窗口关闭时，确保线程安全停止
        if hasattr(self, 'kilosort_thread')and self.kilosort_thread.isRunning():
            self.kilosort_thread.stop()
            self.kilosort_thread.wait()
        if hasattr(self, 'kilolog_watcher_thread') and self.kilolog_watcher_thread.isRunning():
            self.log_watcher_thread.stop()
            self.log_watcher_thread.wait()
        if self.kilosort_process and self.kilosort_process.poll() is None:
            self.kilosort_process.terminate()
        super(MainWindow, self).closeEvent(event)
        super(MainWindow, self).closeEvent(event)


# 自定义数据模型，用于将 Pandas DataFrame 与 QTableView 兼容
class PandasModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df  # 假设：你有一个 Pandas DataFrame 需要显示在 QTableView 中

    def rowCount(self, parent=None):
        return len(self._df.index)  # 返回行数

    def columnCount(self, parent=None):
        return len(self._df.columns)  # 返回列数

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        # 返回单元格数据
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        # 设置表头数据
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._df.columns[col]
        return None


# 使用 matplotlib 绘图的类，将绘图嵌入到 PyQt 界面中
class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()  # 创建一个 Figure
        self.axes = fig.add_subplot(111)  # 添加子图
        super(PlotCanvas, self).__init__(fig)  # 初始化绘图画布

    def plot_dprime(self, data):
        # 绘制 dprime 数据
        self.axes.clear()  # 清除当前图像
        self.axes.imshow(data)  # 绘制矩阵图
        self.draw()  # 更新图像

if __name__ == '__main__':

    # 主程序入口
    app = QApplication(sys.argv)
    window = MainWindow()  # 创建主窗口
    window.show()  # 显示主窗口
    sys.exit(app.exec())  # 运行应用程序

