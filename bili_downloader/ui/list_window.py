"""解析列表弹窗 — 展示分P/合集/收藏夹解析结果。"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

from bili_downloader.bili_api import VideoEntry


class ListWindow:
    """解析列表弹窗。"""

    def __init__(self, root, videos: List[VideoEntry], title: str,
                 on_add_selected, mode_getter=lambda: "best"):
        """
        on_add_selected: callable(tasks: list) -> None
           接收已创建的 DownloadTask 列表。
        """
        self._videos = videos
        self._title = title
        self._on_add = on_add_selected
        self._mode_getter = mode_getter

        self.win = tk.Toplevel(root)
        self.win.title(f"解析结果 - {title[:40]}")
        self.win.geometry("750x600")
        self.win.minsize(700, 500)
        self.win.transient(root)
        self.win.grab_set()

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.win, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main, text=self._title[:80],
                  font=("", 10, "bold")).pack(side=tk.TOP, anchor=tk.W)
        ttk.Label(main, text=f"共 {len(self._videos)} 个视频").pack(
            side=tk.TOP, anchor=tk.W, pady=(0, 5))

        # 全选/取消
        btn_frame = ttk.Frame(main)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        # TreeView
        tree_frame = ttk.Frame(main)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("idx", "title", "dur"),
            show="headings",
            selectmode=tk.EXTENDED,
        )
        self.tree.heading("idx", text="#")
        self.tree.heading("title", text="标题")
        self.tree.heading("dur", text="时长")
        self.tree.column("idx", width=50)
        self.tree.column("title", width=450)
        self.tree.column("dur", width=80)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._video_map = {}  # tree_id -> VideoEntry
        for v in self._videos:
            dur = v.duration
            dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "-"
            item = self.tree.insert("", tk.END, values=(v.index, v.title[:80], dur_str))
            self._video_map[item] = v

        ttk.Button(btn_frame, text="全选",
                   command=lambda: self.tree.selection_add(
                       list(self.tree.get_children()))).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="取消全选",
                   command=lambda: self.tree.selection_remove(
                       self.tree.selection())).pack(side=tk.LEFT, padx=3)

        # 底部操作
        action_frame = ttk.Frame(main)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        ttk.Button(action_frame, text="添加选中到下载队列",
                   command=self._add_selected, width=22).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="导出全部信息(TXT)",
                   command=self._export_txt, width=20).pack(side=tk.LEFT, padx=10)

    def _add_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择视频", parent=self.win)
            return

        selected = [self._video_map[item] for item in sel]
        self._on_add(selected)
        self.win.destroy()

    def _export_txt(self):
        path = filedialog.asksaveasfilename(
            parent=self.win, title="导出列表信息",
            defaultextension=".txt", initialfile="播放列表导出.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"列表: {self._title}\n")
                f.write("=" * 50 + "\n")
                for v in self._videos:
                    dur = v.duration
                    dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "-"
                    f.write(f"P{v.index} | {dur_str} | {v.title} | {v.url}\n")
            messagebox.showinfo("成功", f"导出成功:\n{path}", parent=self.win)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.win)