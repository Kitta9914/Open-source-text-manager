import sys, os, json, configparser, importlib.util, shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QVBoxLayout, QWidget, QTextEdit, 
                             QStatusBar, QMenuBar, QFileDialog, QMessageBox, QInputDialog, 
                             QFontDialog, QDockWidget, QToolBar, QPushButton, 
                             QHBoxLayout, QLineEdit, QTreeView, QFileSystemModel, 
                             QLabel, QComboBox, QMdiArea, QMdiSubWindow, QMenu, 
                             QScrollArea, QDialog, QFrame, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, QDir, QSize, QSettings, QByteArray, QDateTime
from PyQt5.QtGui import QFont, QIcon, QTextCursor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_encoding = "UTF-8"
        self.font = QFont("宋体", 10)
        self.plugins = {}
        self.plugin_buttons = []
        
        # 加载配置
        self.settings = QSettings("DocumentProcessor", "Main")
        self.loadConfig()
        
        self.initUI()
        self.loadAllPlugins()

    def loadConfig(self):
        """加载应用程序配置"""
        # 修复：检查设置值是否存在
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(QByteArray(geometry))
        
        state = self.settings.value("window_state")
        if state is not None:
            self.restoreState(QByteArray(state))
        
        # 插件目录
        self.plugin_dir = self.settings.value("plugin_dir", os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins"))
        
        # 创建插件目录
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
        
        # 插件配置文件路径
        self.plugin_config_path = os.path.join(self.plugin_dir, "plugins.ini")
        if not os.path.exists(self.plugin_config_path):
            config = configparser.ConfigParser()
            config['PLUGINS'] = {}
            with open(self.plugin_config_path, 'w') as configfile:
                config.write(configfile)
                
        # 加载插件配置
        self.plugin_config = configparser.ConfigParser()
        self.plugin_config.read(self.plugin_config_path)
        if 'PLUGINS' not in self.plugin_config:
            self.plugin_config['PLUGINS'] = {}

    def saveConfig(self):
        """保存应用程序配置"""
        # 窗口状态
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("window_state", self.saveState())
        
        # 插件目录
        self.settings.setValue("plugin_dir", self.plugin_dir)
        
        # 保存插件配置
        self.savePluginConfig()

    def savePluginConfig(self):
        """保存插件配置"""
        with open(self.plugin_config_path, 'w') as configfile:
            self.plugin_config.write(configfile)

    def closeEvent(self, event):
        """关闭应用程序时保存状态"""
        self.saveConfig()
        
        # 保存打开的文件状态
        open_files = []
        for sub_window in self.mdi_area.subWindowList():
            if hasattr(sub_window, 'file_path') and sub_window.file_path:
                # 修复：使用QByteArray保存几何信息
                geometry = sub_window.saveGeometry()
                open_files.append({
                    'path': sub_window.file_path,
                    'geometry': geometry.toHex().data().decode() if geometry else None,
                    'is_active': sub_window == self.mdi_area.activeSubWindow()
                })
        
        self.settings.setValue("open_files", json.dumps(open_files))
        event.accept()

    def restoreSession(self):
        """恢复上次会话状态"""
        open_files = self.settings.value("open_files", "")
        if open_files:
            try:
                files = json.loads(open_files)
                active_window = None
                
                for file_info in files:
                    file_path = file_info['path']
                    if os.path.exists(file_path):
                        self.loadFile(file_path, restore=True)
                        sub_window = self.mdi_area.subWindowList()[-1]
                        
                        # 修复：恢复几何信息
                        if file_info['geometry']:
                            geometry_bytes = QByteArray.fromHex(file_info['geometry'].encode())
                            sub_window.restoreGeometry(geometry_bytes)
                        
                        if file_info['is_active']:
                            active_window = sub_window
                
                if active_window:
                    self.mdi_area.setActiveSubWindow(active_window)
            except Exception as e:
                print(f"恢复会话失败: {str(e)}")

    def setPluginDirectory(self):
        """设置插件目录"""
        options = QFileDialog.Options()
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            '选择插件目录', 
            self.plugin_dir, 
            options=options
        )
        
        if dir_path:
            self.plugin_dir = dir_path
            self.plugin_config_path = os.path.join(self.plugin_dir, "plugins.ini")
            
            # 创建新目录
            if not os.path.exists(self.plugin_dir):
                os.makedirs(self.plugin_dir)
            
            # 如果配置文件不存在，创建它
            if not os.path.exists(self.plugin_config_path):
                config = configparser.ConfigParser()
                config['PLUGINS'] = {}
                with open(self.plugin_config_path, 'w') as configfile:
                    config.write(configfile)
            
            # 重新加载插件
            self.loadAllPlugins()
            QMessageBox.information(self, "插件目录已更改", f"插件目录已设置为: {self.plugin_dir}")

    def loadAllPlugins(self):
        """加载所有插件"""
        self.clearPluginButtons()
        
        # 确保插件目录存在
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
        
        for plugin_file in os.listdir(self.plugin_dir):
            if plugin_file.endswith(".py") and plugin_file != "__init__.py":
                plugin_name = plugin_file[:-3]
                enabled = self.plugin_config.getboolean('PLUGINS', plugin_name, fallback=True)
                
                if enabled:
                    try:
                        self.loadPlugin(plugin_name)
                    except Exception as e:
                        print(f"加载插件 {plugin_name} 失败: {str(e)}")
                        error_button = QPushButton(f"{plugin_name} (加载失败)")
                        error_button.setToolTip(f"加载插件失败: {str(e)}")
                        error_button.setEnabled(False)
                        error_button.setStyleSheet("color: red;")
                        self.plugin_buttons_layout.addWidget(error_button)
                        self.plugin_buttons.append(error_button)

    def loadPlugin(self, plugin_name):
        """加载单个插件"""
        spec = importlib.util.spec_from_file_location(
            plugin_name, 
            os.path.join(self.plugin_dir, f"{plugin_name}.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, 'Plugin'):
            raise ImportError(f"插件 {plugin_name} 缺少 Plugin 类")
        
        plugin_instance = module.Plugin(self)
        self.plugins[plugin_name] = plugin_instance
        
        plugin_button = QPushButton(plugin_instance.name)
        if hasattr(plugin_instance, 'icon') and plugin_instance.icon:
            icon_path = os.path.join(self.plugin_dir, plugin_instance.icon)
            if os.path.exists(icon_path):
                plugin_button.setIcon(QIcon(icon_path))
        
        plugin_button.setToolTip(plugin_instance.description)
        plugin_button.clicked.connect(plugin_instance.execute)
        
        self.plugin_buttons_layout.addWidget(plugin_button)
        self.plugin_buttons.append(plugin_button)
        print(f"插件 {plugin_name} 加载成功")

    def clearPluginButtons(self):
        """清除所有插件按钮"""
        for button in self.plugin_buttons:
            button.deleteLater()
        self.plugin_buttons = []
        
        while self.plugin_buttons_layout.count():
            item = self.plugin_buttons_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def reloadPlugins(self):
        """重新加载所有插件"""
        self.loadAllPlugins()
        QMessageBox.information(self, "插件已刷新", "所有插件已重新加载")

    def showPluginManager(self):
        """显示插件管理器对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("插件管理器")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 插件列表
        plugins_frame = QFrame()
        plugins_layout = QVBoxLayout(plugins_frame)
        plugins_layout.addWidget(QLabel("可用插件:"))
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 遍历插件
        for plugin_file in os.listdir(self.plugin_dir):
            if plugin_file.endswith(".py") and plugin_file != "__init__.py":
                plugin_name = plugin_file[:-3]
                enabled = self.plugin_config.getboolean('PLUGINS', plugin_name, fallback=True)
                
                plugin_frame = QFrame()
                plugin_frame.setFrameShape(QFrame.StyledPanel)
                plugin_layout = QHBoxLayout(plugin_frame)
                
                # 插件信息
                info_layout = QVBoxLayout()
                name_label = QLabel(f"<b>{plugin_name}</b>")
                info_layout.addWidget(name_label)
                
                # 获取插件描述
                description = "没有描述"
                if plugin_name in self.plugins:
                    plugin = self.plugins[plugin_name]
                    description = getattr(plugin, 'description', "没有描述")
                    author = getattr(plugin, 'author', "未知作者")
                    version = getattr(plugin, 'version', "1.0")
                    info_layout.addWidget(QLabel(f"版本: {version} | 作者: {author}"))
                else:
                    try:
                        spec = importlib.util.spec_from_file_location(
                            plugin_name, 
                            os.path.join(self.plugin_dir, f"{plugin_name}.py"))
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if hasattr(module, 'Plugin'):
                            plugin_cls = module.Plugin
                            description = getattr(plugin_cls, 'description', "没有描述")
                            author = getattr(plugin_cls, 'author', "未知作者")
                            version = getattr(plugin_cls, 'version', "1.0")
                            info_layout.addWidget(QLabel(f"版本: {version} | 作者: {author}"))
                    except Exception as e:
                        description = f"加载失败: {str(e)}"
                
                desc_label = QLabel(description)
                desc_label.setWordWrap(True)
                info_layout.addWidget(desc_label)
                plugin_layout.addLayout(info_layout, 1)
                
                # 开关和删除按钮
                toggle = QCheckBox("启用")
                toggle.setChecked(enabled)
                toggle.toggled.connect(lambda checked, pn=plugin_name: self.togglePlugin(pn, checked))
                plugin_layout.addWidget(toggle)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda _, pn=plugin_name: self.deletePlugin(pn, dialog))
                plugin_layout.addWidget(delete_btn)
                
                scroll_layout.addWidget(plugin_frame)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        plugins_layout.addWidget(scroll_area)
        layout.addWidget(plugins_frame)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        install_button = QPushButton("安装新插件")
        install_button.clicked.connect(lambda: self.installNewPlugin(dialog))
        buttons_layout.addWidget(install_button)
        
        set_dir_button = QPushButton("设置插件目录")
        set_dir_button.clicked.connect(self.setPluginDirectory)
        buttons_layout.addWidget(set_dir_button)
        
        buttons_layout.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_button)
        layout.addLayout(buttons_layout)
        
        dialog.exec_()

    def togglePlugin(self, plugin_name, checked):
        """切换插件状态"""
        self.plugin_config.set('PLUGINS', plugin_name, str(checked))
        self.savePluginConfig()
        
        if checked:
            try:
                self.loadPlugin(plugin_name)
            except Exception as e:
                QMessageBox.critical(self, "加载插件失败", f"无法加载插件 {plugin_name}: {str(e)}")
        else:
            if plugin_name in self.plugins:
                for button in self.plugin_buttons:
                    if button.text() == self.plugins[plugin_name].name:
                        button.deleteLater()
                        self.plugin_buttons.remove(button)
                        break
                del self.plugins[plugin_name]

    def deletePlugin(self, plugin_name, dialog):
        """删除插件"""
        reply = QMessageBox.question(
            self, 
            '删除插件', 
            f"确定要永久删除插件 '{plugin_name}' 吗?\n此操作无法撤销!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                plugin_path = os.path.join(self.plugin_dir, f"{plugin_name}.py")
                if os.path.exists(plugin_path):
                    os.remove(plugin_path)
                
                if plugin_name in self.plugins:
                    plugin = self.plugins[plugin_name]
                    if hasattr(plugin, 'icon') and plugin.icon:
                        icon_path = os.path.join(self.plugin_dir, plugin.icon)
                        if os.path.exists(icon_path):
                            os.remove(icon_path)
                
                if self.plugin_config.has_option('PLUGINS', plugin_name):
                    self.plugin_config.remove_option('PLUGINS', plugin_name)
                    self.savePluginConfig()
                
                if plugin_name in self.plugins:
                    del self.plugins[plugin_name]
                
                self.loadAllPlugins()
                dialog.accept()
                self.showPluginManager()
                QMessageBox.information(self, "删除成功", f"插件 {plugin_name} 已成功删除")
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除插件时出错: {str(e)}")

    def installNewPlugin(self, dialog=None):
        """安装新插件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择插件文件', 
            '', 
            'Python 文件 (*.py);;所有文件 (*)', 
            options=options
        )
        
        if file_path:
            try:
                plugin_name = os.path.basename(file_path).replace('.py', '')
                if plugin_name == "__init__":
                    raise ValueError("无效的插件名称")
                
                target_path = os.path.join(self.plugin_dir, os.path.basename(file_path))
                if os.path.exists(target_path):
                    reply = QMessageBox.question(
                        self, 
                        '覆盖插件', 
                        f"插件 {plugin_name} 已存在。是否覆盖?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                
                shutil.copy(file_path, target_path)
                self.plugin_config.set('PLUGINS', plugin_name, "True")
                self.savePluginConfig()
                self.loadAllPlugins()
                
                QMessageBox.information(self, "安装成功", f"插件 {plugin_name} 已成功安装并启用")
                
                if dialog:
                    dialog.accept()
                    self.showPluginManager()
            except Exception as e:
                QMessageBox.critical(self, "安装失败", f"插件安装失败: {str(e)}")

    # UI创建相关函数
    def initUI(self):
        self.setWindowTitle('文档处理系统')
        self.setGeometry(100, 100, 1200, 800)
        
        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi_area)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateStatusBar)
        self.timer.start(1000)
        
        self.createMenuBar()
        self.createToolBar()
        self.createFileTreeDock()
        self.createPropertiesDock()
        self.createPluginToolbar()
        self.createNewDocument()
        
        # 恢复会话
        self.restoreSession()

    def createMenuBar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        fileMenu = menubar.addMenu('文件(&F)')
        
        newAction = QAction('新建(&N)', self)
        newAction.setShortcut('Ctrl+N')
        newAction.triggered.connect(self.createNewDocument)
        fileMenu.addAction(newAction)
        
        openAction = QAction('打开(&O)', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.openFile)
        fileMenu.addAction(openAction)
        
        saveAction = QAction('保存(&S)', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAction)
        
        saveAsAction = QAction('另存为(&A)', self)
        saveAsAction.triggered.connect(self.saveFileAs)
        fileMenu.addAction(saveAsAction)
        
        fileMenu.addSeparator()
        
        pluginManagerAction = QAction('插件管理器', self)
        pluginManagerAction.triggered.connect(self.showPluginManager)
        fileMenu.addAction(pluginManagerAction)
        
        fileMenu.addSeparator()
        
        exitAction = QAction('退出(&X)', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)
        
        # 编辑菜单
        editMenu = menubar.addMenu('编辑(&E)')
        
        undoAction = QAction('撤销(&U)', self)
        undoAction.setShortcut('Ctrl+Z')
        undoAction.triggered.connect(self.undo)
        editMenu.addAction(undoAction)
        
        redoAction = QAction('重做(&R)', self)
        redoAction.setShortcut('Ctrl+Y')
        redoAction.triggered.connect(self.redo)
        editMenu.addAction(redoAction)
        
        editMenu.addSeparator()
        
        cutAction = QAction('剪切(&T)', self)
        cutAction.setShortcut('Ctrl+X')
        cutAction.triggered.connect(self.cut)
        editMenu.addAction(cutAction)
        
        copyAction = QAction('复制(&C)', self)
        copyAction.setShortcut('Ctrl+C')
        copyAction.triggered.connect(self.copy)
        editMenu.addAction(copyAction)
        
        pasteAction = QAction('粘贴(&P)', self)
        pasteAction.setShortcut('Ctrl+V')
        pasteAction.triggered.connect(self.paste)
        editMenu.addAction(pasteAction)
        
        # 视图菜单
        viewMenu = menubar.addMenu('视图(&V)')
        
        zoomInAction = QAction('放大', self)
        zoomInAction.setShortcut('Ctrl++')
        zoomInAction.triggered.connect(self.zoomIn)
        viewMenu.addAction(zoomInAction)
        
        zoomOutAction = QAction('缩小', self)
        zoomOutAction.setShortcut('Ctrl+-')
        zoomOutAction.triggered.connect(self.zoomOut)
        viewMenu.addAction(zoomOutAction)
        
        viewMenu.addSeparator()
        
        fullScreenAction = QAction('全屏', self)
        fullScreenAction.setShortcut('F11')
        fullScreenAction.triggered.connect(self.toggleFullScreen)
        viewMenu.addAction(fullScreenAction)
        
        # 工具菜单
        toolMenu = menubar.addMenu('工具(&T)')
        
        fontAction = QAction('字体设置', self)
        fontAction.triggered.connect(self.changeFont)
        toolMenu.addAction(fontAction)
        
        # 设置菜单
        settingsMenu = menubar.addMenu('设置(&S)')
        
        pluginDirAction = QAction('设置插件目录', self)
        pluginDirAction.triggered.connect(self.setPluginDirectory)
        settingsMenu.addAction(pluginDirAction)
        
        # 帮助菜单
        helpMenu = menubar.addMenu('帮助(&H)')
        
        aboutAction = QAction('关于系统', self)
        aboutAction.triggered.connect(self.about)
        helpMenu.addAction(aboutAction)

    def createToolBar(self):
        # 主工具栏
        mainToolBar = self.addToolBar('主工具栏')
        mainToolBar.setMovable(False)
        
        newBtn = QPushButton('新建')
        newBtn.clicked.connect(self.createNewDocument)
        mainToolBar.addWidget(newBtn)
        
        openBtn = QPushButton('打开')
        openBtn.clicked.connect(self.openFile)
        mainToolBar.addWidget(openBtn)
        
        saveBtn = QPushButton('保存')
        saveBtn.clicked.connect(self.saveFile)
        mainToolBar.addWidget(saveBtn)
        
        mainToolBar.addSeparator()
        
        cutBtn = QPushButton('剪切')
        cutBtn.clicked.connect(self.cut)
        mainToolBar.addWidget(cutBtn)
        
        copyBtn = QPushButton('复制')
        copyBtn.clicked.connect(self.copy)
        mainToolBar.addWidget(copyBtn)
        
        pasteBtn = QPushButton('粘贴')
        pasteBtn.clicked.connect(self.paste)
        mainToolBar.addWidget(pasteBtn)
        
        mainToolBar.addSeparator()
        
        undoBtn = QPushButton('撤销')
        undoBtn.clicked.connect(self.undo)
        mainToolBar.addWidget(undoBtn)
        
        redoBtn = QPushButton('重做')
        redoBtn.clicked.connect(self.redo)
        mainToolBar.addWidget(redoBtn)

    def createPluginToolbar(self):
        """创建插件工具栏"""
        self.plugin_toolbar = QToolBar("插件工具栏")
        self.plugin_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, self.plugin_toolbar)
        
        # 添加刷新插件按钮
        refresh_action = QAction("刷新插件", self)
        refresh_action.triggered.connect(self.reloadPlugins)
        self.plugin_toolbar.addAction(refresh_action)
        
        # 添加插件管理器按钮
        manager_action = QAction("插件管理器", self)
        manager_action.triggered.connect(self.showPluginManager)
        self.plugin_toolbar.addAction(manager_action)
        
        self.plugin_toolbar.addSeparator()
        
        # 添加插件按钮占位符
        self.plugin_buttons_container = QWidget()
        self.plugin_buttons_layout = QHBoxLayout(self.plugin_buttons_container)
        self.plugin_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.plugin_toolbar.addWidget(self.plugin_buttons_container)

    def createFileTreeDock(self):
        dockWidget = QDockWidget('文件浏览器', self)
        dockWidget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dockWidget)
        
        fileTreeContent = QWidget()
        layout = QVBoxLayout(fileTreeContent)
        
        # 文件系统模型
        self.fileModel = QFileSystemModel()
        self.fileModel.setRootPath(QDir.homePath())
        
        # 树状视图
        self.treeView = QTreeView()
        self.treeView.setModel(self.fileModel)
        self.treeView.setRootIndex(self.fileModel.index(QDir.homePath()))
        self.treeView.doubleClicked.connect(self.openFileFromTree)
        
        layout.addWidget(self.treeView)
        
        # 快速访问按钮
        homeBtn = QPushButton('主目录')
        homeBtn.clicked.connect(lambda: self.treeView.setRootIndex(self.fileModel.index(QDir.homePath())))
        
        docBtn = QPushButton('文档')
        docBtn.clicked.connect(lambda: self.treeView.setRootIndex(self.fileModel.index(QDir.homePath() + "/Documents")))
        
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(homeBtn)
        btnLayout.addWidget(docBtn)
        
        layout.addLayout(btnLayout)
        dockWidget.setWidget(fileTreeContent)

    def createPropertiesDock(self):
        dockWidget = QDockWidget('文档属性', self)
        dockWidget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dockWidget)
        
        propertiesContent = QWidget()
        layout = QVBoxLayout(propertiesContent)
        
        # 文档信息
        infoGroup = QWidget()
        infoLayout = QVBoxLayout(infoGroup)
        
        self.docTitleLabel = QLabel("标题: 无标题")
        self.docTypeLabel = QLabel("类型: 未保存")
        self.docSizeLabel = QLabel("大小: 0 KB")
        
        infoLayout.addWidget(self.docTitleLabel)
        infoLayout.addWidget(self.docTypeLabel)
        infoLayout.addWidget(self.docSizeLabel)
        
        layout.addWidget(infoGroup)
        
        # 统计信息
        statsGroup = QWidget()
        statsLayout = QVBoxLayout(statsGroup)
        
        self.charCountLabel = QLabel("字符数: 0")
        self.wordCountLabel = QLabel("字数: 0")
        self.lineCountLabel = QLabel("行数: 0")
        
        statsLayout.addWidget(self.charCountLabel)
        statsLayout.addWidget(self.wordCountLabel)
        statsLayout.addWidget(self.lineCountLabel)
        
        layout.addWidget(statsGroup)
        layout.addStretch()
        
        dockWidget.setWidget(propertiesContent)

    def createNewDocument(self):
        subWindow = QMdiSubWindow()
        textEdit = QTextEdit()
        textEdit.setFont(self.font)
        textEdit.textChanged.connect(self.updateStats)
        
        subWindow.setWidget(textEdit)
        subWindow.setWindowTitle("新文档")
        self.mdi_area.addSubWindow(subWindow)
        subWindow.show()
        
        # 更新属性面板
        self.updateDocumentProperties()

    def getActiveTextEdit(self):
        activeSubWindow = self.mdi_area.activeSubWindow()
        if activeSubWindow:
            return activeSubWindow.widget()
        return None

    def openFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(
            self, 
            '打开文件', 
            '', 
            '所有文件 (*);;文本文件 (*.txt)', 
            options=options
        )
        if fileName:
            self.loadFile(fileName)

    def loadFile(self, fileName, restore=False):
        try:
            with open(fileName, 'r', encoding=self.current_encoding) as file:
                content = file.read()
            
            # 在新窗口中打开
            subWindow = QMdiSubWindow()
            textEdit = QTextEdit()
            textEdit.setFont(self.font)
            textEdit.setText(content)
            textEdit.textChanged.connect(self.updateStats)
            
            subWindow.setWidget(textEdit)
            subWindow.setWindowTitle(os.path.basename(fileName))
            subWindow.file_path = fileName  # 保存文件路径
            self.mdi_area.addSubWindow(subWindow)
            subWindow.show()
            
            # 更新属性面板
            self.updateDocumentProperties()
            
        except Exception as e:
            QMessageBox.critical(self, "打开文件错误", f"无法打开文件: {str(e)}")

    def openFileFromTree(self, index):
        file_path = self.fileModel.filePath(index)
        if os.path.isfile(file_path):
            self.loadFile(file_path)

    def saveFile(self):
        activeTextEdit = self.getActiveTextEdit()
        if not activeTextEdit:
            return
            
        subWindow = self.mdi_area.activeSubWindow()
        if subWindow and hasattr(subWindow, 'file_path') and subWindow.file_path:
            # 文件已有名称，直接保存
            self.saveContent(subWindow.file_path, activeTextEdit.toPlainText())
            return
            
        # 否则执行另存为
        self.saveFileAs()

    def saveFileAs(self):
        activeTextEdit = self.getActiveTextEdit()
        if not activeTextEdit:
            return
            
        options = QFileDialog.Options()
        fileName, selectedFilter = QFileDialog.getSaveFileName(
            self, 
            '保存文件', 
            '', 
            '文本文件 (*.txt);;所有文件 (*)', 
            options=options
        )
        
        if fileName:
            # 添加默认扩展名
            if not '.' in fileName:
                fileName += '.txt'
            
            self.saveContent(fileName, activeTextEdit.toPlainText())
            
            # 更新窗口标题
            subWindow = self.mdi_area.activeSubWindow()
            if subWindow:
                subWindow.setWindowTitle(os.path.basename(fileName))
                subWindow.file_path = fileName  # 保存文件路径
                self.updateDocumentProperties()

    def saveContent(self, fileName, content):
        try:
            with open(fileName, 'w', encoding=self.current_encoding) as file:
                file.write(content)
                
            QMessageBox.information(self, "保存成功", f"文件已保存: {fileName}")
        except Exception as e:
            QMessageBox.critical(self, "保存文件错误", f"保存文件时出错: {str(e)}")

    def updateStatusBar(self):
        currentTime = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            cursor = activeTextEdit.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.statusBar.showMessage(f"时间: {currentTime} | 编码: {self.current_encoding} | 行: {line}, 列: {col}")
        else:
            self.statusBar.showMessage(f"时间: {currentTime} | 编码: {self.current_encoding}")

    def updateDocumentProperties(self):
        activeTextEdit = self.getActiveTextEdit()
        subWindow = self.mdi_area.activeSubWindow()
        
        if not activeTextEdit or not subWindow:
            return
            
        title = subWindow.windowTitle()
        self.docTitleLabel.setText(f"标题: {title}")
        
        if title.endswith('.txt'):
            doc_type = "文本文件"
        else:
            doc_type = "未保存文档"
            
        self.docTypeLabel.setText(f"类型: {doc_type}")
        
        content = activeTextEdit.toPlainText()
        size = len(content.encode(self.current_encoding)) / 1024.0
        self.docSizeLabel.setText(f"大小: {size:.2f} KB")
        self.updateStats()

    def updateStats(self):
        activeTextEdit = self.getActiveTextEdit()
        if not activeTextEdit:
            return
            
        content = activeTextEdit.toPlainText()
        char_count = len(content)
        word_count = len(content.split())
        line_count = content.count('\n') + 1 if content else 0
        
        self.charCountLabel.setText(f"字符数: {char_count}")
        self.wordCountLabel.setText(f"字数: {word_count}")
        self.lineCountLabel.setText(f"行数: {line_count}")

    def changeFont(self):
        font, ok = QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            activeTextEdit = self.getActiveTextEdit()
            if activeTextEdit:
                activeTextEdit.setFont(font)

    def undo(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            activeTextEdit.undo()

    def redo(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            activeTextEdit.redo()

    def cut(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            activeTextEdit.cut()

    def copy(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            activeTextEdit.copy()

    def paste(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            activeTextEdit.paste()

    def zoomIn(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            current_size = activeTextEdit.font().pointSize()
            activeTextEdit.setFont(QFont(self.font.family(), current_size + 1))

    def zoomOut(self):
        activeTextEdit = self.getActiveTextEdit()
        if activeTextEdit:
            current_size = activeTextEdit.font().pointSize()
            if current_size > 6:
                activeTextEdit.setFont(QFont(self.font.family(), current_size - 1))

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def about(self):
        QMessageBox.about(self, "关于:", 
                         "文档处理系统\n版本 1.0\n"
                         "支持文本文件处理和插件扩展\n"
                         "2025")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()