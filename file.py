# cache_manager_plugin.py

import os
import shutil
from PyQt5.QtWidgets import (QAction, QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QMessageBox,
                            QListWidget, QListWidgetItem, QLineEdit, 
                            QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class CacheCleanerThread(QThread):
    """后台清理缓存的线程"""
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, cache_dir):
        super().__init__()
        self.cache_dir = cache_dir
        self.cancel_requested = False

    def run(self):
        total_size = 0
        file_count = 0
        
        # 计算缓存大小
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                if self.cancel_requested:
                    return
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                file_count += 1
        
        self.progress_updated.emit(0, f"准备清理: {file_count} 个文件 ({self.format_size(total_size)})")
        
        # 删除缓存文件
        processed = 0
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                if self.cancel_requested:
                    self.progress_updated.emit(100, "清理已取消")
                    return
                
                file_path = os.path.join(root, file)
                try:
                    os.unlink(file_path)
                    processed += 1
                    progress = int((processed / file_count) * 100) if file_count > 0 else 100
                    self.progress_updated.emit(
                        progress, 
                        f"清理中: {processed}/{file_count} 文件"
                    )
                except Exception as e:
                    self.progress_updated.emit(
                        progress, 
                        f"错误: 无法删除 {file} - {str(e)}"
                    )
        
        # 删除空目录
        for root, dirs, files in os.walk(self.cache_dir, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except:
                    pass
        
        self.progress_updated.emit(100, "缓存清理完成")
        self.finished.emit()

    def format_size(self, size_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} GB"

class Plugin:
    def __init__(self, parent):
        self.parent = parent  # 主窗口实例
        self.name = "缓存管理"
        self.description = "管理应用程序缓存设置"
        self.author = "AI Assistant"
        self.version = "1.2"
        self.icon = "cache_icon.png"  # 图标文件（需要放在插件目录）
        
        # 获取当前缓存目录
        self.settings = parent.settings
        self.cache_dir = self.settings.value("cache_dir", os.path.join(os.path.expanduser("~"), "DocumentProcessor_Cache"))
        
        # 确保缓存目录存在
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def execute(self):
        """执行插件功能"""
        self.show_cache_manager()

    def show_cache_manager(self):
        """显示缓存管理器对话框"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("缓存管理")
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # 当前缓存信息
        cache_info = self.get_cache_info()
        info_group = QGroupBox("当前缓存设置")
        info_layout = QVBoxLayout()
        
        current_dir_label = QLabel(f"缓存目录: {self.cache_dir}")
        current_dir_label.setWordWrap(True)
        info_layout.addWidget(current_dir_label)
        
        cache_size_label = QLabel(f"缓存大小: {cache_info['size']}")
        info_layout.addWidget(cache_size_label)
        
        cache_files_label = QLabel(f"文件数量: {cache_info['file_count']} 个文件")
        info_layout.addWidget(cache_files_label)
        
        cache_date_label = QLabel(f"最后修改: {cache_info['last_modified']}")
        info_layout.addWidget(cache_date_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 更改缓存目录部分
        change_group = QGroupBox("更改缓存目录")
        change_layout = QVBoxLayout()
        
        change_layout.addWidget(QLabel("新缓存目录:"))
        
        self.new_dir_edit = QLineEdit()
        self.new_dir_edit.setText(self.cache_dir)
        change_layout.addWidget(self.new_dir_edit)
        
        browse_layout = QHBoxLayout()
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(lambda: self.browse_cache_dir(self.new_dir_edit))
        browse_layout.addWidget(browse_button)
        browse_layout.addStretch()
        
        change_layout.addLayout(browse_layout)
        
        apply_button = QPushButton("应用更改")
        apply_button.clicked.connect(lambda: self.apply_cache_dir(self.new_dir_edit.text(), dialog))
        change_layout.addWidget(apply_button)
        
        change_group.setLayout(change_layout)
        layout.addWidget(change_group)
        
        # 缓存清理部分
        clean_group = QGroupBox("清理缓存")
        clean_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        clean_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        clean_layout.addWidget(self.status_label)
        
        clean_button = QPushButton("立即清理缓存")
        clean_button.clicked.connect(self.clean_cache)
        clean_layout.addWidget(clean_button)
        
        clean_group.setLayout(clean_layout)
        layout.addWidget(clean_group)
        
        # 缓存文件列表
        files_group = QGroupBox("缓存文件")
        files_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        
        # 显示缓存文件
        cache_files = []
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                cache_files.append(os.path.join(root, file))
        
        # 只显示前100个文件
        for file in cache_files[:100]:
            item = QListWidgetItem(os.path.relpath(file, self.cache_dir))
            item.setToolTip(file)
            self.file_list.addItem(item)
        
        if len(cache_files) > 100:
            self.file_list.addItem(f"... 和其他 {len(cache_files) - 100} 个文件")
        
        files_layout.addWidget(self.file_list)
        
        open_button = QPushButton("在文件管理器中打开")
        open_button.clicked.connect(self.open_cache_in_explorer)
        files_layout.addWidget(open_button)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec_()

    def get_cache_info(self):
        """获取缓存目录信息"""
        total_size = 0
        file_count = 0
        last_modified = "从未修改"
        
        if os.path.exists(self.cache_dir):
            # 计算缓存大小和文件数量
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            # 获取最后修改时间
            try:
                last_modified = os.path.getmtime(self.cache_dir)
                from datetime import datetime
                last_modified = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        # 格式化大小
        size_str = self.format_size(total_size)
        
        return {
            "size": size_str,
            "file_count": file_count,
            "last_modified": last_modified
        }

    def format_size(self, size_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} GB"

    def browse_cache_dir(self, line_edit):
        """浏览并选择新的缓存目录"""
        options = QFileDialog.Options()
        dir_path = QFileDialog.getExistingDirectory(
            self.parent, 
            '选择缓存目录', 
            line_edit.text(), 
            options=options
        )
        
        if dir_path:
            line_edit.setText(dir_path)

    def apply_cache_dir(self, new_dir, dialog):
        """应用新的缓存目录"""
        if not new_dir:
            QMessageBox.warning(self.parent, "无效目录", "请输入有效的目录路径")
            return
            
        if new_dir == self.cache_dir:
            QMessageBox.information(self.parent, "无变化", "缓存目录未更改")
            return
            
        # 检查是否可写
        try:
            test_file = os.path.join(new_dir, "write_test.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            QMessageBox.critical(self.parent, "目录不可写", f"无法写入到目录: {str(e)}")
            return
            
        # 迁移现有缓存
        reply = QMessageBox.question(
            self.parent, 
            '迁移缓存', 
            "是否要迁移现有缓存文件到新位置?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
            
        if reply == QMessageBox.Yes:
            # 迁移文件
            try:
                if os.path.exists(self.cache_dir):
                    if not os.path.exists(new_dir):
                        os.makedirs(new_dir)
                    
                    # 移动文件
                    for item in os.listdir(self.cache_dir):
                        s = os.path.join(self.cache_dir, item)
                        d = os.path.join(new_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
                
                QMessageBox.information(self.parent, "迁移成功", "缓存文件已成功迁移到新位置")
            except Exception as e:
                QMessageBox.critical(self.parent, "迁移失败", f"迁移缓存文件时出错: {str(e)}")
                return
        
        # 保存新设置
        self.settings.setValue("cache_dir", new_dir)
        self.cache_dir = new_dir
        
        # 更新UI
        cache_info = self.get_cache_info()
        QMessageBox.information(
            self.parent, 
            "设置已更新", 
            f"缓存目录已更改为: {new_dir}\n"
            f"新缓存大小: {cache_info['size']}\n"
            f"文件数量: {cache_info['file_count']}"
        )
        
        # 重新加载文件列表
        self.file_list.clear()
        cache_files = []
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                cache_files.append(os.path.join(root, file))
        
        for file in cache_files[:100]:
            item = QListWidgetItem(os.path.relpath(file, self.cache_dir))
            item.setToolTip(file)
            self.file_list.addItem(item)
        
        if len(cache_files) > 100:
            self.file_list.addItem(f"... 和其他 {len(cache_files) - 100} 个文件")

    def clean_cache(self):
        """清理缓存"""
        if not os.path.exists(self.cache_dir) or not os.listdir(self.cache_dir):
            QMessageBox.information(self.parent, "无需清理", "缓存目录为空")
            return
            
        reply = QMessageBox.question(
            self.parent, 
            '确认清理', 
            "确定要清理所有缓存文件吗?\n此操作不可撤销!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备清理...")
        
        # 创建并启动清理线程
        self.cleaner_thread = CacheCleanerThread(self.cache_dir)
        self.cleaner_thread.progress_updated.connect(self.update_clean_progress)
        self.cleaner_thread.finished.connect(self.clean_finished)
        self.cleaner_thread.start()

    def update_clean_progress(self, progress, message):
        """更新清理进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def clean_finished(self):
        """清理完成"""
        QMessageBox.information(self.parent, "清理完成", "缓存已成功清理")
        
        # 更新文件列表
        self.file_list.clear()
        self.file_list.addItem("缓存已清空")
        
        # 隐藏进度控件
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

    def open_cache_in_explorer(self):
        """在文件管理器中打开缓存目录"""
        if os.path.exists(self.cache_dir):
            import platform
            system = platform.system()
            
            if system == "Windows":
                os.startfile(self.cache_dir)
            elif system == "Darwin":  # macOS
                os.system(f'open "{self.cache_dir}"')
            elif system == "Linux":
                os.system(f'xdg-open "{self.cache_dir}"')
        else:
            QMessageBox.warning(self.parent, "目录不存在", "缓存目录不存在")

    def create_menu_action(self, menu):
        """在菜单中创建操作项（可选）"""
        action = QAction("缓存管理", self.parent)
        action.triggered.connect(self.execute)
        menu.addAction(action)
        return action