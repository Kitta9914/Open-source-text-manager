import os
import configparser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFormLayout, QMessageBox, QFontDialog
)
from PyQt5.QtGui import QFont, QIntValidator

class Plugin:
    name = "配置管理器(功能模拟)"
    description = "管理系统配置设置"
    author = "刘续延"
    version = "1.0"
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.load_config()

    def execute(self):
        self.dialog = self.ConfigDialog(self.main_window, self)
        self.dialog.exec_()

    def load_config(self):
        self.config = configparser.ConfigParser()
        
        # 默认配置
        self.config['GENERAL'] = {
            'font_family': '宋体',
            'font_size': '10',
            'default_encoding': 'UTF-8',
            'auto_save_interval': '5',
            'recent_files': '5'
        }
        
        # 如果配置文件存在，加载它
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        
        # 应用配置
        self.apply_config()

    def save_config(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.apply_config()
        QMessageBox.information(self.main_window, "配置已保存", "配置更改已保存并应用！")

    def apply_config(self):
        # 应用字体设置
        font_family = self.config['GENERAL'].get('font_family', '宋体')
        font_size = int(self.config['GENERAL'].get('font_size', '10'))
        self.main_window.font = QFont(font_family, font_size)

    class ConfigDialog(QDialog):
        def __init__(self, main_window, plugin):
            super().__init__(main_window)
            self.plugin = plugin
            self.main_window = main_window
            self.setWindowTitle("系统配置管理器")
            self.setMinimumSize(500, 300)
            self.create_ui()
            self.load_settings()

        def create_ui(self):
            layout = QVBoxLayout()
            
            # 常规设置
            form_layout = QFormLayout()
            
            # 字体设置
            self.font_button = QPushButton("选择字体")
            self.font_button.clicked.connect(self.select_font)
            form_layout.addRow(QLabel("默认字体:"), self.font_button)
            
            # 编码设置
            self.encoding_combo = QComboBox()
            self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312", "ISO-8859-1", "Windows-1252"])
            form_layout.addRow(QLabel("默认编码:"), self.encoding_combo)
            
            # 自动保存
            self.auto_save_spin = QLineEdit()
            self.auto_save_spin.setValidator(QIntValidator(0, 60))
            form_layout.addRow(QLabel("自动保存间隔(分钟):"), self.auto_save_spin)
            
            # 最近文件
            self.recent_files_spin = QLineEdit()
            self.recent_files_spin.setValidator(QIntValidator(0, 20))
            form_layout.addRow(QLabel("最近文件数量:"), self.recent_files_spin)
            
            layout.addLayout(form_layout)
            
            # 按钮区域
            button_layout = QHBoxLayout()
            self.save_button = QPushButton("保存配置")
            self.save_button.clicked.connect(self.save_settings)
            button_layout.addWidget(self.save_button)
            
            self.cancel_button = QPushButton("取消")
            self.cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_button)
            
            layout.addLayout(button_layout)
            self.setLayout(layout)

        def load_settings(self):
            # 加载常规设置
            self.encoding_combo.setCurrentText(self.plugin.config['GENERAL'].get('default_encoding', 'UTF-8'))
            self.auto_save_spin.setText(self.plugin.config['GENERAL'].get('auto_save_interval', '5'))
            self.recent_files_spin.setText(self.plugin.config['GENERAL'].get('recent_files', '5'))

        def select_font(self):
            current_font = QFont(
                self.plugin.config['GENERAL'].get('font_family', '宋体'),
                int(self.plugin.config['GENERAL'].get('font_size', '10'))
            )
            font, ok = QFontDialog.getFont(current_font, self)
            if ok:
                self.plugin.config['GENERAL']['font_family'] = font.family()
                self.plugin.config['GENERAL']['font_size'] = str(font.pointSize())

        def save_settings(self):
            # 保存常规设置
            self.plugin.config['GENERAL']['default_encoding'] = self.encoding_combo.currentText()
            self.plugin.config['GENERAL']['auto_save_interval'] = self.auto_save_spin.text()
            self.plugin.config['GENERAL']['recent_files'] = self.recent_files_spin.text()
            
            # 保存配置
            self.plugin.save_config()
            self.accept()