# grabscreen.py

import tkinter as tk
from PIL import ImageGrab

def capture_screenshot(output_path="screenshot.jpg"):
    """
    允许用户通过鼠标手动选择截图区域，并保存截图。
    :param output_path: 截图保存的路径。
    """
    class ScreenGrab(tk.Tk):
        def __init__(self):
            super().__init__()
            self.attributes('-fullscreen', True)
            self.attributes('-alpha', 0.3)  # 半透明
            self.attributes("-topmost", True)
            self.config(cursor="cross")
            self.start_x = None
            self.start_y = None
            self.rect = None
            self.canvas = tk.Canvas(self, cursor="cross", bg="grey")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.canvas.bind("<ButtonPress-1>", self.on_button_press)
            self.canvas.bind("<B1-Motion>", self.on_move_press)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
            self.selected_bbox = None

        def on_button_press(self, event):
            # 保存鼠标拖拽的起始位置（绝对屏幕坐标）
            self.start_x = event.x_root
            self.start_y = event.y_root
            # 在 Canvas 上创建一个矩形
            self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='red', width=2)

        def on_move_press(self, event):
            # 更新矩形的大小（相对于 Canvas 的坐标）
            cur_x, cur_y = event.x, event.y
            self.canvas.coords(self.rect, self.start_x - self.winfo_rootx(), self.start_y - self.winfo_rooty(), cur_x, cur_y)

        def on_button_release(self, event):
            # 记录最终位置并关闭窗口
            end_x = event.x_root
            end_y = event.y_root
            self.selected_bbox = (self.start_x, self.start_y, end_x, end_y)
            self.destroy()

    # 创建并运行截图界面
    app = ScreenGrab()
    app.mainloop()

    if app.selected_bbox:
        bbox = app.selected_bbox
        # 确保左上角坐标小于右下角坐标
        left = min(bbox[0], bbox[2])
        top = min(bbox[1], bbox[3])
        right = max(bbox[0], bbox[2])
        bottom = max(bbox[1], bbox[3])

        # 截取选定区域
        try:
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            screenshot.save(output_path)
        except Exception as e:
            print(f"截图失败: {e}")
    else:
        print("未选择任何区域，截图取消。")

if __name__ == "__main__":
    capture_screenshot()
