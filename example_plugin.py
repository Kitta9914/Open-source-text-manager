# -*- coding: utf-8 -*-
import datetime
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from PyQt5.QtGui import QTextCursor

class Plugin:
    name = "示例插件"
    description = "这是一个示例插件，用于演示插件系统功能"
    author = "系统开发者 kitta"
    version = "1.0"
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def execute(self):
        active_text_edit = self.main_window.getActiveTextEdit()
        if active_text_edit:
            # 添加当前时间戳
            cursor = active_text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.insertText(f"[插件执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            
            # 添加自定义文本
            text, ok = QInputDialog.getText(
                self.main_window, 
                "添加文本", 
                "请输入要添加的文本:"
            )
            if ok and text:
                cursor.insertText(f"{text}\n\n")
                
            QMessageBox.information(
                self.main_window, 
                "插件执行", 
                f"{self.name} 已成功执行!"
            )
        else:
            QMessageBox.warning(
                self.main_window, 
                "插件错误", 
                "没有活动的文档窗口!"
            )
