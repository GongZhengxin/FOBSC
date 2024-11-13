import sys
import os
import time
import subprocess
import pandas as pd
import numpy as np
import matlab.engine
import h5py
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtGui import QPixmap, QDesktopServices, QAction
from PyQt6 import uic, QtCore, QtWidgets
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QListWidget, QTableView, QTextBrowser
from PyQt6.QtCore import QAbstractTableModel, Qt, QThread, pyqtSignal
import pathlib
from scipy.stats import zscore
from scipy.stats import linregress
import scipy.stats as stats
from PIL import Image, ImageOps

# 更新 PreprocessingThread 以接受 MATLAB 引擎实例
class PreprocessingThread(QThread):
    progress = pyqtSignal(str)  # 定义一个信号用于传递进度信息
    finishedsignal = pyqtSignal(np.ndarray)
    def __init__(self, selections, parameters, matlab_engine, parent=None):
        super().__init__(parent)
        self.selections = selections
        self.parameters = parameters
        self.matlab_engine = matlab_engine  # 接收并使用主窗口中的 MATLAB 引擎实例

    def run(self):
        try:
            self.progress.emit("[MATLAB] 预处理进程成功接收引擎")
            current_directory = self.matlab_engine.pwd()
            self.progress.emit(f"[MATLAB] pwd: {current_directory}")
            # 根据用户选择执行不同的预处理
            if self.selections['data_check']:
                self.progress.emit("[Process] 执行 Data Check...")

                self.matlab_engine.run("datacheck.m", nargout=0)  # 假设 MATLAB 中有名为 data_check 的函数
            
            if self.selections['good_unit_strc']:
                pre_onset, post_onset, psth_window_size = self.parameters
                self.progress.emit(f"[Process] 执行 GoodUnitStrc Process... \n     [Parameter] pre_onset={pre_onset}\n     [Parameter] post_onset={post_onset}\n     [Parameter] psth_window_size={psth_window_size}")
                self.matlab_engine.workspace['pre_onset'] = pre_onset
                self.matlab_engine.workspace['post_onset'] = post_onset
                self.matlab_engine.workspace['psth_window_size'] = psth_window_size
                self.matlab_engine.run("good_unit_strc_process.m", nargout=0)
            
            if self.selections['lfp_process']:
                self.progress.emit("[Process] 执行 LFP Process...")
                self.progress.emit(f"预处理发生错误: 当前没有完成 LFP 预处理模块")
                # self.matlab_engine.lfp_process(nargout=0)  # 假设 MATLAB 中有名为 lfp_process 的函数
            time.sleep(0.5)
            processde_dir = os.path.join(current_directory, "processed")
            self.progress.emit(f"[Process] reading {processde_dir}")
            if os.path.exists(processde_dir):
                Respfile = [_ for _ in os.listdir(processde_dir) if ('RespMat_' in _ ) and ('.npy' in _)]
                if len(Respfile) == 1:
                    main_data = np.load(os.path.join(processde_dir, Respfile[0]))
                    self.progress.emit(f"[Process] Get data {main_data.shape} ")
                elif len(Respfile) == 0:
                    self.progress.emit("[Process] No successful response matrix produced!")
                    main_data = np.array([])
                else:
                    self.progress.emit("[Process] More than 1 successful response matrix existed!")
                    main_data = np.array([])
            self.finishedsignal.emit(main_data)

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

class ProcessThread(QThread):
    output_signal = pyqtSignal(str)  # 用于传递进程输出的信号

    def __init__(self, command, procname="Process", working_directory=None, parent=None):
        super().__init__(parent)
        self.command = command
        self.working_directory = working_directory
        self._running = True
        self.procname = procname

    def run(self):
        try:
            # 启动外部进程
            process = subprocess.Popen(
                self.command,
                cwd=self.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # 行缓冲模式
            )

            # 逐行读取进程输出
            while self._running:
                output = process.stdout.readline()
                if output:
                    self.output_signal.emit(output.strip())
                if process.poll() is not None:
                    break

            # 确保读取所有剩余输出
            remaining_output = process.stdout.read()
            if remaining_output:
                self.output_signal.emit(remaining_output.strip())

            # 等待进程结束
            process.wait()
            self.output_signal.emit(f"[{self.procname}] 进程完成。")
        except Exception as e:
            self.output_signal.emit(f"[{self.procname}] 进程出错: {str(e)}")

    def stop(self):
        self._running = False

class LogWatcherThread(QThread):
    log_updated = pyqtSignal(str)

    def __init__(self, log_file_path, parent=None):
        super().__init__(parent)
        self.log_file_path = log_file_path
        self._running = True
        self._last_position = 0  # 记录上次读取的位置

    def run(self):
        while self._running:
            try:
                # 检查日志文件是否存在
                if not os.path.exists(self.log_file_path):
                    time.sleep(1)  # 如果日志文件不存在，等待一段时间再检查
                    continue

                # 尝试打开日志文件
                with open(self.log_file_path, "r", encoding="utf-8") as file:
                    # 将文件指针移动到上次读取的位置
                    file.seek(self._last_position)

                    # 读取新内容
                    new_lines = file.readlines()
                    if new_lines:
                        for line in new_lines:
                            self.log_updated.emit(line.strip())  # 发送新行内容

                    # 更新最后读取的位置
                    self._last_position = file.tell()

            except (UnicodeDecodeError, IOError) as e:
                # 处理文件读取错误（例如文件被占用或编码错误）
                # self.log_updated.emit(f"日志监视线程出错: {str(e)}")
                time.sleep(0.5)  # 等待一段时间再重试

            # 等待一段时间再检查日志文件的更新
            time.sleep(0.1)

    def stop(self):
        self._running = False

class FobscparamDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, param_dict=None):
        super().__init__(parent)
        # Load the UI file
        self.home = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(self.home, "plotparams.ui")
        uic.loadUi(ui_file, self)
        self.paramdict = param_dict
        # Initialize UI components with default values and connect signals
        self.initUI()

    def initUI(self):
        if self.paramdict is None:
            # Set default values for firing window
            self.lower_bound_edit.setText("60")  # Default lower bound
            self.upper_bound_edit.setText("220")  # Default upper bound

            # Set default values for redplot vmin and vmax
            self.vmin_spinbox.setValue(-2.)  # Default vmin
            self.vmax_spinbox.setValue(2.)  # Default vmax

            # Set checkbox exclusivity between by_depth and by_dprime
            self.by_depth_checkbox.setChecked(True)  # Default selection
            self.by_dprime_checkbox.setChecked(False)
            
            # Set default values for line scatter plot parameters
            self.linethreshold_spinbox.setValue(0.2)  # Default threshold
            self.linewidth_spinbox.setValue(1.0)  # Default width
            self.spinBox_markersize.setValue(40)  # Default ms
        else:
            # Set default values for firing window
            self.lower_bound_edit.setText(str(self.paramdict["firing_window"]["lower_bound"]))  # Default lower bound
            self.upper_bound_edit.setText(str(self.paramdict["firing_window"]["upper_bound"]))  # Default upper bound

            # Set default values for redplot vmin and vmax
            self.vmin_spinbox.setValue(self.paramdict["redplot"]["vmin"])  # Default vmin
            self.vmax_spinbox.setValue(self.paramdict["redplot"]["vmax"])  # Default vmax

            # Set checkbox exclusivity between by_depth and by_dprime
            self.by_depth_checkbox.setChecked(self.paramdict["redplot"]["by_depth"])  # Default selection
            self.by_dprime_checkbox.setChecked(self.paramdict["redplot"]["by_dprime"])

            # Set default values for line scatter plot parameters
            self.checkBox_linfit.setChecked(self.paramdict["line_scatter"]["linfit"])  
            self.linethreshold_spinbox.setValue(self.paramdict["line_scatter"]["linethreshold"])  # Default threshold
            self.linewidth_spinbox.setValue(self.paramdict["line_scatter"]["linewidth"])  # Default width
            self.spinBox_markersize.setValue(self.paramdict["line_scatter"]["markersize"])  # Default ms
            self.marker_combo.setCurrentText(self.paramdict["line_scatter"]["marker"])
            self.linestyle_combo.setCurrentText(self.paramdict["line_scatter"]["linestyle"])
            self.cum_checkbox.setChecked(self.paramdict["line_scatter"]["cumplot"])
            self.prb_checkbox.setChecked(self.paramdict["line_scatter"]["prbplot"])
        # Set checkbox exclusivity between by_depth and by_dprime
        self.by_depth_checkbox.toggled.connect(self.toggle_checkbox)
        self.by_dprime_checkbox.toggled.connect(self.toggle_checkbox)
        self.cum_checkbox.toggled.connect(self.toggle_checkbox2)
        self.prb_checkbox.toggled.connect(self.toggle_checkbox2)
        # OK and Cancel button connections
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def toggle_checkbox(self):
        # Toggle checkboxes to ensure only one is selected
        if self.sender() == self.by_depth_checkbox:
            self.by_dprime_checkbox.setChecked(not self.by_depth_checkbox.isChecked())
        else:
            self.by_depth_checkbox.setChecked(not self.by_dprime_checkbox.isChecked())
    def toggle_checkbox2(self):
        # Toggle checkboxes to ensure only one is selected
        if self.sender() == self.cum_checkbox:
            self.prb_checkbox.setChecked(not self.cum_checkbox.isChecked())
        else:
            self.cum_checkbox.setChecked(not self.prb_checkbox.isChecked())

    def get_values(self):
        # Collecting values into a dictionary
        param_dict = {
            "firing_window": {
                "lower_bound": int(self.lower_bound_edit.text()),
                "upper_bound": int(self.upper_bound_edit.text())
            },
            "redplot": {
                "vmin": self.vmin_spinbox.value(),
                "vmax": self.vmax_spinbox.value(),
                "by_depth": self.by_depth_checkbox.isChecked(),
                "by_dprime": self.by_dprime_checkbox.isChecked()
            },
            "line_scatter": {
                "linfit": self.checkBox_linfit.isChecked(),
                "marker": self.marker_combo.currentText(),
                "markersize": self.spinBox_markersize.value(),
                "linestyle": self.linestyle_combo.currentText(),
                "linethreshold": self.linethreshold_spinbox.value(),
                "linewidth": self.linewidth_spinbox.value(),
                "cumplot" : self.cum_checkbox.isChecked(),
                "prbplot" : self.prb_checkbox.isChecked()
            }
        }
        return param_dict

class ImageLoaderThread(QThread):
    # 定义一个信号，用于通知主线程加载完成
    image_loaded = pyqtSignal(dict)
    progress = pyqtSignal(str)
    def __init__(self, stim_path, stimtsv_path, indo_df, selstim):
        super().__init__()
        self.stim_path = stim_path
        self.stimtsv_path = stimtsv_path
        self.indo_df = indo_df
        self.selstim = selstim

    def run(self):
        # 在子线程中读取图像
        # if not not self.select_stimname: # 如果 stimname 非空
        stimnames = pd.read_csv(self.stimtsv_path, sep='\t')['FileName'].values # TODO: delete replace
        unique_elements = np.unique(self.indo_df["FOB"].values)
        self.select_stimname = {}
        for iele, sel in enumerate(self.selstim):
            self.select_stimname[unique_elements[iele]] = stimnames[sel]
        self.progress.emit(f"[Stim] Collect selected imagenames {self.select_stimname} ")
        # load imgs
        select_stim = {}
        for element, imgname in self.select_stimname.items():
            cur_img = Image.open(os.path.join(self.stim_path, imgname)).resize((150,150))
            select_stim[element] = cur_img

        self.image_loaded.emit(select_stim)  # 将图像数组传递给主线程

# 假设：你已经创建了一个名为 base.ui 的文件，通过Qt Designer设计了基本界面。
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.home = os.path.dirname(os.path.abspath(__file__))
        ui_file = os.path.join(self.home, 'Base.ui') 
        uic.loadUi(ui_file, self)  # 动态加载 UI 文件
        self.fobscparams = self.default_fobscparam()
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
        self.fobListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        # self.fobListWidget.setAcceptDrops(True)
        self.boxAListWidget.setAcceptDrops(True)
        self.boxBListWidget.setAcceptDrops(True)
        self.boxAListWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.boxBListWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.boxAListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.boxBListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
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

        self.main_data = np.array([])  # Will store the resp_matrix for reuse
        
        self.FIGS_button = self.findChild(QtWidgets.QPushButton, 'pushButton_figs')
        self.graphicsView = self.findChild(QtWidgets.QGraphicsView, 'graphicsView')
        # Connect buttons to their functions
        self.FIGS_button.clicked.connect(self.load_figure)
        self.contrastListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.contrastListWidget.customContextMenuRequested.connect(self.show_contrast_context_menu)
        
        self.graphicsViewScene = QGraphicsScene()
        self.graphicsView.setScene(self.graphicsViewScene)
        
        self.fobscparam_button = self.findChild(QtWidgets.QPushButton, 'pushButton_fobparams')
        self.fobscparam_button.clicked.connect(self.open_fobscparam_dialog)
        self.firing_window = (60, 220)
        self.kilosort_button = self.findChild(QtWidgets.QPushButton, 'pushButton_kilosort')
        self.kilosort_button.clicked.connect(self.run_kilosort_gui)

        support_menu = self.findChild(QtWidgets.QMenu, 'menu_support')
        if support_menu:
            # Find and connect the Help action
            help_action = self.findChild(QAction, 'actionhelp')
            if help_action:
                help_action.triggered.connect(self.open_help_pdf)

            # Find and connect the Feedback action
            feedback_action = self.findChild(QAction, 'actionfeedback')
            if feedback_action:
                feedback_action.triggered.connect(self.open_feedback_page)

    def default_fobscparam(self):
        return {
            "firing_window": {
                "lower_bound": int(60),
                "upper_bound": int(220)
            },
            "redplot": {
                "vmin": -2.,
                "vmax": 2.,
                "by_depth": True,
                "by_dprime": False
            },
            "line_scatter": {
                "linfit": False,
                "marker": 'o',
                "markersize": int(40),
                "linestyle": "-",
                "linethreshold": 0.2,
                "linewidth": 1.5,
                "cumplot" : False,
                "prbplot" : True
            }
        }

    def open_help_pdf(self):
        pdf_path = os.path.join(self.home, 'FOBSC_document.pdf')  # Replace with the actual path to your help PDF
        if os.path.exists(pdf_path):
            os.startfile(pdf_path)
        else:
            QMessageBox.critical(self, 'Error', 'Help document not found.')

    def open_feedback_page(self):
        feedback_url = 'https://kdocs.cn/l/cctKe5YpjAaP'  # Replace with the actual feedback URL
        QDesktopServices.openUrl(QtCore.QUrl(feedback_url))

    def browse_check_load_folder(self):
        try:
            # 使用文件对话框选择文件夹
            folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
            if folder_path:
                self.folder_path = folder_path  # 保存选择的文件夹路径
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
                
                if ("NPX" in missing_files) or (".bhv2" in missing_files):
                    self.append_message(f"[file] 缺少以下文件: {', '.join(missing_files)}")
                    # 如果有缺少的文件，弹出警告窗口
                    QMessageBox.warning(self, "文件缺失", f"缺少以下文件: {', '.join(missing_files)}")
                else:
                    if " 'info.tsv' 文件" in missing_files:
                        self.append_message(f"[file] 缺少以下文件: {', '.join(missing_files)}")
                        info_file, _ = QFileDialog.getOpenFileName(self, 'Select Info TSV File', self.folder_path, 'TSV Files (*.tsv)')
                        info_file = [info_file]
                        if not info_file:
                            QMessageBox.critical(self, 'Error', 'No valid info.tsv file selected.')
                    else:
                        # 假设：info.tsv 文件中包含需要显示的数据
                        info_file = [f for f in os.listdir(self.folder_path) if '_info.tsv' in f]
                    if len(info_file) == 1: info_file = info_file[0]
                    else: QMessageBox.warning(self, "文件冗余", f"Info File 找到了 {len(info_file)} 个： {info_file}")
                    info_file_path = os.path.join(self.folder_path, info_file)
                    self.indo_df = pd.read_csv(info_file_path, sep='\t')  # 使用 pandas 读取 TSV 文件
                    # 假设：base.ui 中有一个 QTableView，名为 tableView
                    model = PandasModel(self.indo_df)  # 创建 Pandas 数据模型
                    self.tableView.setModel(model)  # 设置模型以显示数据
                    # 提取 FOB 列的 unique 元素
                    unique_elements = self.indo_df['FOB'].unique()
                    # 假设：base.ui 中有一个 QListWidget，名为 listWidget_FOB
                    self.listWidget_FOB.clear()
                    self.listWidget_FOB.addItems(unique_elements)  # 将 unique 元素添加到 QListWidget 中
                    self.append_message(f"[LOAD] {self.folder_path} !")
                    stim_indx, selstim = [], []
                    for element in unique_elements:
                        stim_indx.append(np.where(self.indo_df['FOB'].values == element)[0].min())
                        stim_indx.append(np.where(self.indo_df['FOB'].values == element)[0].max())
                        selstim.append(np.where(self.indo_df['FOB'].values == element)[0].min())
                    self.stim_start_end_indices = stim_indx
                    self.selstim = selstim
                    # get selected stimulus file name
                    self.select_stimname = {}
                    if "FileName" in self.indo_df.keys():
                        for iele, sel in enumerate(selstim):
                            self.select_stimname[unique_elements[iele]] = self.indo_df["FileName"].values[sel]
                        self.append_message(f"[Stim] Collect selected imagenames {self.select_stimname} ")
                processde_dir = os.path.join(self.folder_path, "processed")
                if os.path.exists(processde_dir):
                    Respfile = [_ for _ in os.listdir(processde_dir) if ('RespMat_' in _) and ('.npy' in _)]
                    if len(Respfile) == 1:
                        self.main_data = np.load(os.path.join(processde_dir, Respfile[0]))
                        self.append_message(f"[Data] Response Data {self.main_data.shape} Loaded, OK for FOB check")
                    else:
                        self.append_message(f"[Data] Fail to load Response Data")
                        pass # TODO : operatiosn needed if more than 1 file 
                    Spkfile = [_ for _ in os.listdir(processde_dir) if ('SpikePos_' in _) and ('.npy' in _)]
                    if len(Spkfile) == 1:
                        self.spikepos = np.load(os.path.join(processde_dir, Spkfile[0]))
                        self.append_message(f"[Data] Spike pos data loaded {self.spikepos.shape}")
                    else:
                        self.append_message(f"[Data] Fail to load Response Data")
                        pass # TODO : operatiosn needed if more than 1 file 
                    GoodUnitStr = [_ for _ in os.listdir(processde_dir) if ('GoodUnit_' in _ )and ('.mat' in _)]
                    if len(GoodUnitStr) == 1:
                        with h5py.File(os.path.join(processde_dir, GoodUnitStr[0]), 'r') as f:
                            self.pre_onset = np.squeeze(f["global_params"]['pre_onset'][:])
                            self.post_onset = np.squeeze(f["global_params"]['post_onset'][:])
                            self.psth_range = np.squeeze(f["global_params"]['PsthRange'][:])
                            self.stimtsv_path = ''.join([chr(int(num)) for num in np.squeeze(f["global_params"]['m_strImageListUsed'][()])]).replace('Z:', 'Y:')
                            self.stim_path = '/'.join(self.stimtsv_path.split('\\')[0:-1]).replace('Z:', 'Y:') # TODO: delete replace
                        self.append_message(f"[Data] Pre onset {self.pre_onset}; Post onset {self.post_onset}")
                        self.append_message(f"[Stim] Stim path {self.stim_path}")
                        if len(self.psth_range) != (self.pre_onset + self.post_onset):
                            QMessageBox.critical(self, "错误", f"发生错误: GoodUnit global parameter 中 psthrange 与 preonset & postonset 不匹配")
                        if not not self.select_stimname: # 如果 stimname 非空
                            self.image_loader = ImageLoaderThread(self.stim_path, self.stimtsv_path, self.indo_df, self.selstim)
                            self.image_loader.image_loaded.connect(self.on_imge_loaded)
                            self.image_loader.progress.connect(self.append_message)
                            self.image_loader.start()
                    else:
                        self.append_message(f"[Data] Fail to load meta data")
                        pass # TODO : operatiosn needed if more than 1 file 
                kilosort_dir = os.path.join(self.folder_path, 'kilosort_def_5block_97') # check file # TODO : more prepared
                if not os.path.exists(kilosort_dir):
                    self.start_kilosort_process()
                    pass
                else:
                    self.append_message(f"[Kilosort] Aready exists kilosort_def_5block_97")
            else: pass
        except Exception as e:
            QMessageBox.critical(self, "错误", f"Browser发生错误: {str(e)}")

    def generate_contrast(self):
        try:
            # 获取A和B中的元素
            a_items = [self.boxAListWidget.item(i).text() for i in range(self.boxAListWidget.count())]
            b_items = [self.boxBListWidget.item(i).text() for i in range(self.boxBListWidget.count())]
            if (len(a_items) > 0) and (len(b_items) > 0):
                # 生成对比字典条目
                print(a_items, type(a_items))
                if len(a_items) > 2: a_keys = '&'.join(a_items[0:2]) + '...'
                else: a_keys = '&'.join(a_items[0:2])
                if len(b_items) > 2: b_keys = '&'.join(b_items[0:2]) + '...'
                else: b_keys = '&'.join(b_items[0:2])
                contrast_key = f"{a_keys} — {b_keys}_{self.contrastListWidget.count() + 1}"
                contrast_value = (tuple(a_items), tuple(b_items))
                
                # 添加到对比列表
                self.contrastListWidget.addItem(contrast_key)
                self.contrastListWidget.item(self.contrastListWidget.count() - 1).setData(QtCore.Qt.ItemDataRole.UserRole, contrast_value)
            else:
                QMessageBox.critical(self, "错误", f"Generate contrast 发生错误: contrast 需要 categories")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"Generate contrast 发生错误: {str(e)}")

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
                if len(self.main_data) > 0:
                    self.calculate_dprime(item)
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
            if (self.matlab_engine is not None) and (self.folder_path is not None):
                self.matlab_engine.cd(self.folder_path)
                self.matlab_engine.addpath(self.home)
                utils_dir = os.path.join(self.home, 'util')
                utils_full_path = self.matlab_engine.genpath(utils_dir)
                self.matlab_engine.addpath(utils_full_path)
                self.preprocessing_thread = PreprocessingThread(selections, parameters, self.matlab_engine)
                self.mat_log_file = os.path.join(self.folder_path, 'process.log')
                with open(self.mat_log_file, 'w') as file: pass
                self.start_log_watcher(self.mat_log_file)
                self.preprocessing_thread.progress.connect(self.append_message)  # 将进度信息连接到 append_message 方法
                self.preprocessing_thread.finishedsignal.connect(self.on_preprocess_finished)
                self.preprocessing_thread.start()
                    
            else:
                if self.matlab_engine is None:
                    QMessageBox.warning(self, "Warning", f"Start processing Warning: 等待主进程激活 Matlab")
                if self.folder_path is None:
                    QMessageBox.warning(self, "Warning", f"Start processing Warning: 等待选择数据文件夹")

    def on_preprocess_finished(self, main_data):
        if len(main_data) > 0 :
            self.main_data = main_data
            self.append_message("[Process] Process done!")
            processde_dir = os.path.join(self.folder_path, 'processed')
            Spkfile = [_ for _ in os.listdir(processde_dir) if 'SpikePos_' in _ and '.npy' in _]
            if len(Spkfile) == 1:
                self.spikepos = np.load(os.path.join(processde_dir, Spkfile[0]))
                self.append_message(f"[Data] Spike pos data loaded {self.spikepos.shape}")
            else:
                self.append_message(f"[Data] Fail to load Response Data")
                pass # TODO : operatiosn needed if more than 1 file 
            GoodUnitStr = [_ for _ in os.listdir(processde_dir) if 'GoodUnit_' in _ and '.mat' in _]
            if len(GoodUnitStr) == 1:
                with h5py.File(os.path.join(processde_dir, GoodUnitStr[0]), 'r') as f:
                    self.pre_onset = np.squeeze(f["global_params"]['pre_onset'][:])
                    self.post_onset = np.squeeze(f["global_params"]['post_onset'][:])
                    self.psth_range = np.squeeze(f["global_params"]['PsthRange'][:])
                    stimtsv_path = ''.join([chr(int(num)) for num in np.squeeze(f["global_params"]['m_strImageListUsed'][()])])
                    self.stim_path = '/'.join(stimtsv_path.split('\\')[0:-1]).replace('Z:', 'Y:') # TODO: delete replace
                self.append_message(f"[Data] Pre onset {self.pre_onset}; Post onset {self.post_onset}")
                self.append_message(f"[Stim] Stim path {self.stim_path}")
                if len(self.psth_range) != (self.pre_onset + self.post_onset):
                    QMessageBox.critical(self, "错误", f"发生错误: GoodUnit global parameter 中 psthrange 与 preonset & postonset 不匹配")
                
                self.image_loader = ImageLoaderThread(self.stim_path, self.stimtsv_path, self.indo_df, self.selstim)
                self.image_loader.image_loaded.connect(self.on_imge_loaded)
                self.image_loader.progress.connect(self.append_message)
                self.image_loader.start()
                # if not self.select_stimname:
                #     stimnames = pd.read_csv(stimtsv_path, sep='\t')['FileName'].values
                #     unique_elements = np.unique(self.indo_df["FOB"].values)
                #     for iele, sel in enumerate(self.selstim):
                #         self.select_stimname[unique_elements[iele]] = stimnames[sel]
                #     self.append_message(f"[Stim] Collect selected imagenames {self.select_stimname} ")
                # # load imgs
                # self.select_stim = {}
                # for element, imgname in self.select_stimname.items():
                #     cur_img = Image.open(os.path.join(self.stim_path, imgname))
                #     self.select_stim[element] = cur_img
            else:
                self.append_message(f"[Data] Fail to load meta data")
                pass # TODO : operatiosn needed if more than 1 file 
            
        else:
            QMessageBox.critical(self, "Error", f"无法识别有效且唯一的 response_matrix_img 文件！请检查数据目录")

    def start_kilosort_process(self):
        try:
            self.append_message("[Kilosort] 进程准备启动... ")
            kilosort_script_path = os.path.join(self.home, "util/npxkilosort.py")
            npx_fodler = [_ for _ in os.listdir(self.folder_path) if 'NPX_' in _][0]
            
            # 创建并启动 Kilosort 线程
            self.kilosort_thread = ProcessThread(
                command=[sys.executable, kilosort_script_path, os.path.join('.', npx_fodler)],
                working_directory=self.folder_path,
                procname='Kilosort'
            )
            self.kilosort_thread.output_signal.connect(self.append_message)
            self.kilosort_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "Kilosort 启动错误", f"无法启动 Kilosort: {str(e)}")

    def start_log_watcher(self, log_file_path):

        # 创建日志监视线程
        self.log_watcher_thread = LogWatcherThread(log_file_path)
        # 连接日志更新信号到 textBrowser 控件的 append 方法
        self.log_watcher_thread.log_updated.connect(self.append_message)
        # 启动线程
        self.log_watcher_thread.start()

        # 向 textBrowser 添加一条启动消息
        self.append_message("[Log] 日志监视线程已启动...")

    def on_imge_loaded(self, select_stim):
        self.select_stim = select_stim
        self.append_message("[Stim] stim dict 已经加载。")

    def open_fobscparam_dialog(self):
        try:
            dialog = FobscparamDialog(self, param_dict=self.fobscparams)
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.fobscparams = dialog.get_values()
                if len(self.main_data) > 0:
                    if self.contrastListWidget.currentItem():
                        self.calculate_dprime(self.contrastListWidget.currentItem())
        except Exception as e:
            QMessageBox.critical(self, "对话框启动错误", f"{str(e)}")

    def run_kilosort_gui(self):
        try:
            kilosort_path = os.path.join(self.folder_path, 'kilosort_def_5block_97')# Replace with the correct path
            venv_name = pathlib.Path(sys.executable).parent.name  # Automatically find the virtual environment path
            venv_python = sys.executable  # Use the current Python executable
            cmd = f"cd {kilosort_path} && conda activate {venv_name} && phy template-gui {kilosort_path}/params.py"
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error run_kilosort_gui: {str(e)}")

    def closeEvent(self, event):
        try:
            # 释放图形视图中的所有项目
            self.graphicsViewScene.clear()
            # 当窗口关闭时，确保线程安全停止
            if hasattr(self, 'kilosort_thread'):
                if self.kilosort_thread.isRunning():
                    self.kilosort_thread.stop()
                    self.kilosort_thread.wait()
            # 当窗口关闭时，确保日志监视线程安全停止
            if hasattr(self, 'log_watcher_thread') :
                if self.log_watcher_thread.isRunning():
                    self.log_watcher_thread.stop()
                    self.log_watcher_thread.wait()
            super(MainWindow, self).closeEvent(event)
            event.accept()  # 确认窗口关闭
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def show_contrast_context_menu(self, position):
        try:
            menu = QtWidgets.QMenu()
            fobcs_action = menu.addAction("FOBCS")
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.contrastListWidget.viewport().mapToGlobal(position))
            
            selected_item = self.contrastListWidget.currentItem()
            if action == delete_action:
                if selected_item:
                    self.contrastListWidget.takeItem(self.contrastListWidget.row(selected_item))
            elif action == fobcs_action:
                if selected_item:
                    self.calculate_dprime(selected_item)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"show_contrast_context_menu 发生错误: {str(e)}")

    def calculate_dprime(self, contrast):
        try:
            # Check if maindata is available
            if  len(self.main_data) == 1:
                processed_path = [ os.path.join(self.folder_path, 'processed', _) \
                                  for _ in os.listdir(os.path.join(self.folder_path, 'processed')) if 'RespMat_' in _ and '.npy' in _][0] 
                if not os.path.exists(processed_path):
                    QMessageBox.warning(self, "Warning", ".mat not found in processed directory.")
                    return
                else:
                    self.main_data = np.load(processed_path)
            # Calculate dprime based on the contrast definition (example only)
            contrast_value = contrast.data(QtCore.Qt.ItemDataRole.UserRole)

            if (len(contrast_value[0]) > 0)  and (len(contrast_value[1]) > 0):
                a_items, b_items = contrast_value
                # print(a_items, b_items)
            fob_array = self.indo_df['FOB'].values
            a_indices, b_indices = [], []
            for a_cate in a_items:
                a_indices.append(np.where(fob_array==a_cate)[0])
            for b_cate in b_items:
                b_indices.append(np.where(fob_array==b_cate)[0])
            a_indices, b_indices = np.concatenate(a_indices), np.concatenate(b_indices)

            # Prefer & contrast
            prefer = "&".join(list(a_items))
            self.firing_window = (self.fobscparams['firing_window']["lower_bound"], self.fobscparams['firing_window']["upper_bound"])
            # Extract data from maindata for groups A and B # TODO: preonset post onset logic
            firing_window_ms = (self.firing_window[0], self.firing_window[1])
            fire_indices = np.where((self.psth_range >= firing_window_ms[0]) & (self.psth_range < firing_window_ms[1]))[0]
            fire_mat = self.main_data[:, fire_indices].mean(axis=1)
            data_a = self.main_data[a_indices][:, fire_indices].mean(axis=1)
            data_b = self.main_data[b_indices][:, fire_indices].mean(axis=1)
            title = f"{contrast.text()}_window({firing_window_ms[0]},{firing_window_ms[1]})ms"
            # Calculate dprime
            mean_diff = np.mean(data_a, axis=0) - np.mean(data_b, axis=0)
            pooled_sd = np.sqrt((np.var(data_a, axis=0) + np.var(data_b, axis=0)) / 2)
            dprime = mean_diff / pooled_sd

            #
            N_a, N_b = len(a_items), len(b_items)
            images_path_a = [ self.select_stim[_] for _ in a_items]
            imgA = stitch_images_with_border(images_path_a, N_a, border_color="#d91619")
            images_path_b = [ self.select_stim[_] for _ in b_items]
            imgB = stitch_images_with_border(images_path_b, N_b, border_color="#1717d9")
            width, height = imgA.size
            # 计算拼接后图像的尺寸
            gap = 15
            new_width = width * 2 + gap
            new_height = height
            # 创建新图像
            new_image = Image.new('RGB', (new_width, new_height), 'white')
            # 粘贴图像到新图像的指定位置
            new_image.paste(imgA, (0, 0))
            new_image.paste(imgB, (width + gap, 0))
            # 转换为 NumPy 数组
            new_image_array = np.array(new_image)
            # Plot 
            self.plot_mainfigure(fire_mat, dprime, new_image_array, prefer, title)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error calculating dprime: {str(e)}")

    def get_random_color(self):
        import random
        r = lambda: random.randint(0, 255)
        return f'#{r():02x}{r():02x}{r():02x}'
    
    def plot_mainfigure(self, fire_mat, dprime, image_array, prefer='Pref', title='Contrast'):
        try:
            # Plot the dprime values and display in graphicsView
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            from matplotlib import pyplot as plt

            # 创建一个1行2列的图
            # 目标像素大小
            width_px = 1370
            height_px = 500
            # 设置 DPI（例如 100）
            dpi = 100
            figure = Figure(figsize=(width_px / dpi, height_px / dpi))
            # 第1个子图：imshow
            ax1 = figure.add_subplot(1, 4, 1)
            if self.fobscparams['redplot']["by_depth"]:
                draw_data = fire_mat[:, np.argsort(np.squeeze(self.spikepos)[1,:])[::-1]]
                ax1.set_ylabel(f"Neurons (sorted by depth)")
            elif self.fobscparams['redplot']["by_dprime"]:
                draw_data = fire_mat[:, np.argsort(dprime)[::-1]]
                ax1.set_ylabel(f"Neurons (sorted by {prefer} d')")
            draw_data = zscore(draw_data, axis=0)
            vmin, vmax = self.fobscparams['redplot']['vmin'], self.fobscparams['redplot']['vmax'] 
            im = ax1.imshow(draw_data.transpose(), cmap='RdBu_r', vmin=vmin, vmax=vmax, aspect='auto')
            ax1.set_title('RedPlot')
            ax1.set_xlabel('Pictures')
            pos = ax1.get_position()
            cax = figure.add_axes([pos.x1-0.065, pos.y0 + 0.15, 0.005, 0.5 * pos.height])
            cb = plt.colorbar(im, cax=cax)
            cb.ax.yaxis.set_ticks_position('right')
            cb.ax.yaxis.set_ticks([draw_data.min(), 0, draw_data.max()])
            cb.ax.tick_params(direction='out', labelsize=9)
            for x in self.stim_start_end_indices:
                ax1.axvline(x=x, lw=0.5, ls="--", color='k')
            # 第2个子图：plot
            param_LSC = self.fobscparams['line_scatter']
            msize, marker = param_LSC['markersize'], param_LSC['marker']
            lwidth, lthres, lstyle = param_LSC['linewidth'], param_LSC['linethreshold'], param_LSC['linestyle']
            ax2 = figure.add_subplot(1, 4, 2)
            if param_LSC["cumplot"]:
                ax2.plot(np.sort(dprime), np.arange(len(dprime)), lw=lwidth, ls=lstyle, color=self.get_random_color())
            elif param_LSC["prbplot"]:
                # 计算数据的最小值和最大值
                min_val = np.min(dprime)
                max_val = np.max(dprime)
                step = 0.05
                # 生成区间的边界（包括右边界）
                bins = np.arange(min_val, max_val + step, step)
                # 计算每个区间的计数
                counts, _ = np.histogram(dprime, bins=bins)
                # 计算每个区间的中值
                mid_points = (bins[:-1] + bins[1:]) / 2
                ax2.plot(mid_points, counts, lw=lwidth, ls=lstyle, color=self.get_random_color())
            else:
                ax2.plot(np.sort(dprime), np.arange(len(dprime)), lw=lwidth, ls=lstyle, color=self.get_random_color())
            ax2.axvline(x=-lthres, lw=1, color='k')
            ax2.axvline(x=lthres, lw=1, color='k')
            ax2.set_xlabel(f"{prefer} d'")
            ax2.set_ylabel(f"Neurons")
            ax2.set_title(f"d' Rank")
            xlim = ax2.get_xlim()
            ax2.set_xlim([-np.abs(xlim).max(), np.abs(xlim).max()])
            # 第3个子图：plot
            ax3 = figure.add_subplot(1, 4, 3)
            x = dprime
            y = np.squeeze(self.spikepos)[1,:]
            ax3color = self.get_random_color()
            ax3.scatter(x, y, s=msize, color=ax3color, marker=marker, edgecolors='k', lw=0.5, alpha=0.5, zorder=4)
            if param_LSC['linfit']:
                slope, intercept = np.polyfit(y, x, 1)
                x_fit = slope * y + intercept
                # # 线性回归拟合
                # slope, intercept, r_value, _, std_err = linregress(y, x)
                # # 计算置信区间
                # confidence = 0.95
                # t_value = stats.t.ppf((1 + confidence) / 2, df=len(x) - 2)  # t 分布的临界值
                # slope_ci = t_value * std_err  # 置信区间的宽度
                # x_fit = slope * y + intercept
                ax3.plot(x_fit, y, color=ax3color, ls=lstyle, lw=lwidth, zorder=5)
                # # 绘制置信区间
                # x_upper = (slope + slope_ci) * y + intercept
                # x_lower = (slope - slope_ci) * y + intercept
                # ax3.fill_betweenx(y, x_lower, x_upper, color='gray', alpha=0.2)
            ax3.axvline(x=lthres, ls='--', color='k', alpha=0.7)
            ax3.set_title("d' ~ Depth")
            ax3.set_xlabel(f"{prefer} d'")
            ax3.set_ylabel(f"Depth (μm)")
            xlim = ax3.get_xlim()
            ax3.set_xlim([-np.abs(xlim).max(), np.abs(xlim).max()])

            ax4 = figure.add_subplot(1, 4, 4)
            ax4.imshow(image_array, aspect='auto')
            ax4.axis('off')
            ax4.set_title('Contrat Example Stim')
            # 自动调整布局
            # figure.tight_layout()
            # 设置子图之间的水平间距
            figure.suptitle(fr"{title}")
            figure.subplots_adjust(wspace=0.4) 
            figure.subplots_adjust(left=0.05, right=0.95)
            canvas = FigureCanvas(figure)
            # canvas.setFixedSize(self.graphicsViewScene.sceneRect().size().toSize())
            self.graphicsViewScene.clear()
            self.graphicsViewScene.addWidget(canvas)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"plot_mainfigure 发生错误: {str(e)}")

    def load_figure(self):
        try:
            processed_path = os.path.join(self.folder_path, 'processed')
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", processed_path, "Image Files (*.png *.jpg *.jpeg *.svg *.tiff)")
            
            if file_name:
                pixmap = QPixmap(file_name)
                # Get the size of graphicsView and scale the pixmap to fit without keeping the aspect ratio
                target_size = self.graphicsView.size()
                scaled_pixmap = pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                self.graphicsViewScene.clear()
                self.graphicsViewScene.addPixmap(scaled_pixmap)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"load_figure 发生错误: {str(e)}")

def optimize_image_layout(N, canvas_width=150, canvas_height=400):
    """
    计算在指定画布内放置 N 张等宽高图片的最佳图像大小和布局。

    参数:
    N : int - 需要放置的图像数量
    canvas_width : int - 画布宽度，默认为150px
    canvas_height : int - 画布高度，默认为400px

    返回:
    max_s : int - 最佳图像大小（宽高相等）
    final_cols : int - 每行的图像数量
    final_rows : int - 每列的图像数量
    """

    max_s = 1  # 初始化最大图像尺寸

    # 遍历不同的图像大小 s
    for s in range(1, min(canvas_width, canvas_height) + 1):
        # 计算在给定图像大小 s 下可以放置的列数和行数
        cols = canvas_width // s
        rows = canvas_height // s

        # 计算在当前图像大小下的最大可放置图片数量
        total_images = cols * rows

        # 如果当前尺寸能放下N张图片，更新最大图像大小 s
        if total_images >= N:
            max_s = s
        else:
            break

    # 计算最终行数和列数
    final_cols = canvas_width // max_s
    final_rows = canvas_height // max_s

    # 返回结果
    return max_s, final_cols, final_rows

def stitch_images_with_border(image_list, N, canvas_width=175, canvas_height=420, border_size=8, border_color='black'):
    # 优化图像布局
    max_s, final_cols, final_rows = optimize_image_layout(N, canvas_width, canvas_height)
    
    # 创建画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # 调整每张图片的大小并依次粘贴到画布
    for i, img in enumerate(image_list[:N]):

        # 为图像添加边框
        img_with_border = ImageOps.expand(img, border=border_size, fill=border_color)
        
        # 将图像调整到最大大小 max_s（包含边框）
        img_with_border = img_with_border.resize((max_s, max_s))
        
        # 计算图像在画布上的位置
        col = i % final_cols
        row = i // final_cols
        x = col * max_s
        y = row * max_s
        
        # 将带边框的图像粘贴到画布
        canvas.paste(img_with_border, (x, y))
    
    return canvas

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


if __name__ == '__main__':
    try:
        from PyQt6.QtGui import QIcon
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.setWindowIcon(QIcon('./FOBSC2.ico')) 
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application closed with error: {e}")
