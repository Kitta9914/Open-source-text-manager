#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py - PyInstaller 单文件打包脚本
支持中文路径和中文文件名
"""

import os
import sys
import shutil
import subprocess
import configparser
from PyInstaller.__main__ import run as pyinstaller_run  # 直接导入PyInstaller运行函数

def build_single_file():
    # 清理之前的构建
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
    
    # 确保插件目录存在
    plugin_dir = 'plugins'
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
    
    # 添加示例插件（可选）
    example_plugin = os.path.join(plugin_dir, 'example_plugin.py')
    if not os.path.exists(example_plugin):
        with open(example_plugin, 'w', encoding='utf-8') as f:
            f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from PyQt5.QtGui import QTextCursor

class Plugin:
    name = "示例插件"
    description = "这是一个示例插件，用于演示插件系统功能"
    author = "系统开发者"
    version = "1.0"
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def execute(self):
        active_text_edit = self.main_window.getActiveTextEdit()
        if active_text_edit:
            # 添加当前时间戳
            cursor = active_text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.insertText(f"[插件执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\\n")
            
            # 添加自定义文本
            text, ok = QInputDialog.getText(
                self.main_window, 
                "添加文本", 
                "请输入要添加的文本:"
            )
            if ok and text:
                cursor.insertText(f"{text}\\n\\n")
                
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
""")
    
    # 创建默认配置文件
    config_path = 'config.ini'
    if not os.path.exists(config_path):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'encoding': 'UTF-8',
            'font': '宋体',
            'font_size': '10'
        }
        with open(config_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    
    # 构建 PyInstaller 参数
    pyi_args = [
        'main.py',
        '--name=文档处理系统',
        '--onefile',
        '--windowed',
        '--icon=app_icon.ico',
        f'--add-data={plugin_dir}{os.pathsep}{plugin_dir}',
        f'--add-data={config_path}{os.pathsep}.',
        '--hidden-import=pandas',
        '--hidden-import=pdfplumber',
        '--hidden-import=docx',
        '--hidden-import=lxml.etree',
        '--hidden-import=PyQt5',
        '--hidden-import=importlib',
        '--hidden-import=configparser',
        '--hidden-import=shutil',
        '--hidden-import=platform',
        '--hidden-import=datetime',
        '--hidden-import=importlib.util',
        '--hidden-import=importlib.machinery',
        '--hidden-import=pdfminer',
        '--hidden-import=pdfminer.psparser',
        '--hidden-import=pdfminer.pdfdocument',
        '--hidden-import=pdfminer.pdfpage',
        '--hidden-import=pdfminer.pdfinterp',
        '--hidden-import=pdfminer.pdfdevice',
        '--hidden-import=pdfminer.cmapdb',
        '--hidden-import=pdfminer.image',
        '--hidden-import=pdfminer.layout',
        '--hidden-import=pdfminer.utils',
        '--hidden-import=reportlab',
        '--hidden-import=et_xmlfile',
        '--hidden-import=jdcal',
        '--hidden-import=PIL',
        '--hidden-import=openpyxl',
        '--hidden-import=xlrd',
        '--hidden-import=xlwt',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtPrintSupport',
        '--exclude-module=tests',
        '--exclude-module=unittest',
        '--exclude-module=test',
        '--exclude-module=pytest',
        '--exclude-module=setuptools',
        '--clean',
        '--log-level=WARN',
        '--uac-admin'
    ]
    
    # 执行打包命令
    print("开始打包，这可能需要几分钟时间...")
    
    try:
        # 直接调用PyInstaller的run函数
        pyinstaller_run(pyi_args)
    except Exception as e:
        print(f"打包过程中发生错误: {str(e)}")
        return
    
    # 复制插件目录到dist目录（单文件模式需要）
    dist_dir = 'dist'
    if os.path.exists(dist_dir):
        plugins_dest = os.path.join(dist_dir, 'plugins')
        if os.path.exists(plugins_dest):
            shutil.rmtree(plugins_dest, ignore_errors=True)
        shutil.copytree(plugin_dir, plugins_dest)
        
        # 复制其他资源文件
        if os.path.exists(config_path):
            shutil.copy(config_path, dist_dir)
    
    print("\n打包完成！可执行文件位于 'dist' 目录")
    print("请将整个 'dist' 目录分发给用户")

if __name__ == '__main__':
    # 设置系统默认编码为 UTF-8
    if sys.version_info[0] < 3:
        reload(sys)
        sys.setdefaultencoding('utf-8')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
    
    build_single_file()
    int(input())