import re
import os
from collections import Counter
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QPushButton, 
    QHeaderView, QLabel, QLineEdit, QComboBox, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt

class Plugin:
    name = "文档统计与词频分析"
    description = "提供文档统计数据、段落词频分析和关键词搜索功能"
    author = "智能助手"
    version = "1.0"
    icon = "stats_icon.png"  # 需要提供图标文件

    def __init__(self, main_window):
        self.main_window = main_window
    
    def execute(self):
        # 获取当前激活的文本编辑器
        text_edit = self.main_window.getActiveTextEdit()
        if not text_edit:
            QMessageBox.warning(self.main_window, "无活动文档", "请先打开或创建一个文档")
            return
        
        text = text_edit.toPlainText()
        if not text.strip():
            QMessageBox.information(self.main_window, "空文档", "文档内容为空")
            return
        
        # 创建统计对话框
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("文档统计与词频分析")
        dialog.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        
        # 基本信息标签
        active_window = self.main_window.mdi_area.activeSubWindow()
        if active_window:
            title = active_window.windowTitle()
        else:
            title = "未命名文档"
            
        info_label = QLabel(f"文档: {title}")
        main_layout.addWidget(info_label)
        
        # 选项卡
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 1. 总体统计选项卡
        overall_tab = QWidget()
        overall_layout = QVBoxLayout(overall_tab)
        
        # 创建统计表格
        stats_table = QTableWidget()
        stats_table.setRowCount(10)
        stats_table.setColumnCount(2)
        stats_table.setHorizontalHeaderLabels(["统计项目", "数值"])
        stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_table.verticalHeader().setVisible(False)
        stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 计算统计值
        char_count = len(text)
        word_count = len(re.findall(r'\b\w+\b', text))
        line_count = text.count('\n') + 1
        paragraph_count = len(re.split(r'\n\s*\n', text))
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        digit_count = len(re.findall(r'\d', text))
        space_count = text.count(' ')
        tab_count = text.count('\t')
        non_ascii_count = len([c for c in text if ord(c) > 127])
        
        # 填充表格
        stats = [
            ("总字符数", char_count),
            ("总字数", word_count),
            ("总行数", line_count),
            ("段落数", paragraph_count),
            ("中文字符", chinese_chars),
            ("英文单词", english_words),
            ("数字数量", digit_count),
            ("空格数量", space_count),
            ("制表符数量", tab_count),
            ("非ASCII字符", non_ascii_count)
        ]
        
        for i, (name, value) in enumerate(stats):
            stats_table.setItem(i, 0, QTableWidgetItem(name))
            stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        overall_layout.addWidget(stats_table)
        tab_widget.addTab(overall_tab, "总体统计")
        
        # 2. 段落词频分析选项卡
        freq_tab = QWidget()
        freq_layout = QVBoxLayout(freq_tab)
        
        # 词频分析设置
        settings_layout = QHBoxLayout()
        
        top_n_label = QLabel("显示最高频词语数量:")
        self.top_n_spin = QComboBox()
        self.top_n_spin.addItems(["5", "10", "15", "20", "25", "30"])
        self.top_n_spin.setCurrentIndex(1)  # 默认10
        
        word_len_label = QLabel("最小词语长度:")
        self.word_len_spin = QComboBox()
        self.word_len_spin.addItems(["1", "2", "3", "4", "5"])
        self.word_len_spin.setCurrentIndex(1)  # 默认2
        
        analyze_btn = QPushButton("分析段落")
        analyze_btn.clicked.connect(lambda: self.analyze_paragraphs(text, freq_tree))
        
        settings_layout.addWidget(top_n_label)
        settings_layout.addWidget(self.top_n_spin)
        settings_layout.addWidget(word_len_label)
        settings_layout.addWidget(self.word_len_spin)
        settings_layout.addWidget(analyze_btn)
        settings_layout.addStretch()
        
        freq_layout.addLayout(settings_layout)
        
        # 词频树形视图
        freq_tree = QTreeWidget()
        freq_tree.setHeaderLabels(["段落", "词语", "频率"])
        freq_tree.setColumnCount(3)
        freq_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        freq_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        freq_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        freq_tree.setSortingEnabled(True)
        
        freq_layout.addWidget(freq_tree)
        tab_widget.addTab(freq_tab, "段落词频")
        
        # 3. 关键词搜索选项卡
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        
        # 搜索设置
        search_settings = QHBoxLayout()
        
        keyword_label = QLabel("搜索关键词:")
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入要搜索的词语")
        
        case_sensitive = QCheckBox("区分大小写")
        self.case_checkbox = case_sensitive
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(lambda: self.search_keywords(text, search_table))
        
        search_settings.addWidget(keyword_label)
        search_settings.addWidget(self.keyword_input)
        search_settings.addWidget(case_sensitive)
        search_settings.addWidget(search_btn)
        
        search_layout.addLayout(search_settings)
        
        # 搜索结果表格
        search_table = QTableWidget()
        search_table.setColumnCount(4)
        search_table.setHorizontalHeaderLabels(["段落", "位置", "上下文", "频率"])
        search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        search_table.setEditTriggers(QTableWidget.NoEditTriggers)
        search_table.setSortingEnabled(True)
        
        search_layout.addWidget(search_table)
        tab_widget.addTab(search_tab, "关键词搜索")
        
        # 初始分析
        self.analyze_paragraphs(text, freq_tree)
        
        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
        # 显示对话框
        dialog.exec_()
    
    def analyze_paragraphs(self, text, tree_widget):
        """分析文档段落并显示词频"""
        tree_widget.clear()
        
        # 获取参数
        top_n = int(self.top_n_spin.currentText())
        min_len = int(self.word_len_spin.currentText())
        
        # 分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        
        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue
                
            # 清洗文本并分词
            words = re.findall(r'\b\w{%d,}\b' % min_len, para, re.UNICODE)
            if not words:
                continue
                
            # 计算词频
            word_counts = Counter(words)
            top_words = word_counts.most_common(top_n)
            
            # 添加段落节点
            para_node = QTreeWidgetItem(tree_widget, [f"段落 {i+1}", "", ""])
            para_node.setExpanded(True)
            
            # 添加词频子节点
            for word, count in top_words:
                word_item = QTreeWidgetItem(para_node, ["", word, str(count)])
                para_node.addChild(word_item)
        
        # 自动调整列宽
        for i in range(tree_widget.columnCount()):
            tree_widget.resizeColumnToContents(i)
    
    def search_keywords(self, text, table_widget):
        """搜索关键词并显示结果"""
        table_widget.clearContents()
        table_widget.setRowCount(0)
        
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self.main_window, "输入错误", "请输入搜索关键词")
            return
        
        # 设置搜索选项
        flags = re.UNICODE
        if not self.case_checkbox.isChecked():
            flags |= re.IGNORECASE
        
        # 分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        total_count = 0
        
        for para_idx, para in enumerate(paragraphs):
            if not para.strip():
                continue
                
            # 在段落中搜索关键词
            matches = list(re.finditer(re.escape(keyword), para, flags))
            if not matches:
                continue
                
            # 为每个匹配项添加到表格
            for match in matches:
                row = table_widget.rowCount()
                table_widget.insertRow(row)
                
                # 获取上下文 (前后20个字符)
                start, end = match.span()
                context_start = max(0, start - 20)
                context_end = min(len(para), end + 20)
                context = para[context_start:context_end]
                
                # 高亮显示关键词
                if context_start > 0:
                    context = "..." + context
                if context_end < len(para):
                    context = context + "..."
                
                # 添加表格项
                table_widget.setItem(row, 0, QTableWidgetItem(f"段落 {para_idx+1}"))
                table_widget.setItem(row, 1, QTableWidgetItem(f"位置 {start}-{end}"))
                table_widget.setItem(row, 2, QTableWidgetItem(context))
                table_widget.setItem(row, 3, QTableWidgetItem(str(len(matches))))
                
            total_count += len(matches)
        
        # 设置表格标题
        table_widget.setHorizontalHeaderLabels([
            "段落", 
            "位置", 
            f"上下文 (关键词: {keyword})", 
            f"频率 (总计: {total_count})"
        ])