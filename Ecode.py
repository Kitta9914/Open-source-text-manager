# encoding_plugin.py

import os
from PyQt5.QtWidgets import QAction, QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class Plugin:
    def __init__(self, parent):
        self.parent = parent  # 主窗口实例
        self.name = "文档编码转换"
        self.description = "更改当前文档的编码方式"
        self.author = "AI Assistant"
        self.version = "1.0"
        self.icon = "encoding_icon.png"  # 图标文件（需要放在插件目录）
        
        # 支持的编码列表
        self.encodings = [
            "UTF-8",
            "UTF-16",
            "UTF-32",
            "GBK",
            "GB2312",
            "GB18030",
            "BIG5",
            "ISO-8859-1",
            "Windows-1252",
            "ASCII",
            "Shift_JIS",
            "EUC-JP",
            "KOI8-R",
            "CP1251"
        ]

    def execute(self):
        """执行插件功能"""
        # 获取当前活动的文本编辑区域
        active_text_edit = self.parent.getActiveTextEdit()
        if not active_text_edit:
            QMessageBox.warning(self.parent, "无活动文档", "请先打开或创建一个文档！")
            return
            
        # 创建编码选择对话框
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("选择编码方式")
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # 当前编码标签
        current_label = QLabel(f"当前编码: {self.parent.current_encoding}")
        layout.addWidget(current_label)
        
        # 编码选择下拉框
        layout.addWidget(QLabel("选择新编码:"))
        encoding_combo = QComboBox()
        encoding_combo.addItems(self.encodings)
        
        # 设置当前编码为选中项
        current_index = encoding_combo.findText(self.parent.current_encoding)
        if current_index >= 0:
            encoding_combo.setCurrentIndex(current_index)
            
        layout.addWidget(encoding_combo)
        
        # 确认按钮
        btn_layout = QVBoxLayout()
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(lambda: self.apply_encoding(
            encoding_combo.currentText(), 
            dialog, 
            active_text_edit
        ))
        btn_layout.addWidget(apply_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec_()

    def apply_encoding(self, new_encoding, dialog, text_edit):
        """应用新的编码方式"""
        # 更新主窗口的当前编码
        self.parent.current_encoding = new_encoding
        
        # 更新状态栏
        self.parent.updateStatusBar()
        
        # 显示成功消息
        QMessageBox.information(
            self.parent, 
            "编码已更改", 
            f"文档编码已更改为: {new_encoding}\n"
            "此设置将应用于后续的保存操作。"
        )
        
        # 关闭对话框
        dialog.accept()

    def create_menu_action(self, menu):
        """在菜单中创建操作项（可选）"""
        action = QAction("更改文档编码", self.parent)
        action.triggered.connect(self.execute)
        menu.addAction(action)
        return action