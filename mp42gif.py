from moviepy.editor import VideoFileClip

def mp4_to_gif(mp4_path, gif_path, size=(512, 512), fps=15):
    # 加载 mp4 文件
    clip = VideoFileClip(mp4_path)
    
    # 获取原始帧率
    original_fps = clip.fps
    print(f"原始帧率: {original_fps} FPS")
    
    # 调整视频大小
    resized_clip = clip.resize(size)
    
    # 计算新的帧率（确保不超过原始帧率）
    new_fps = min(fps, original_fps)
    print(f"转换为 GIF 的帧率: {new_fps} FPS")
    
    # 将视频转换为 gif，并设置帧率
    resized_clip.write_gif(gif_path, fps=10,  opt='OptimizePlus')
    
    # 释放资源
    clip.close()
    print(f"GIF 已保存到: {gif_path}, 帧率: {new_fps} FPS")

if __name__ == "__main__":
    # MP4 文件的路径
    mp4_path = r"D:\AI\desktopAI\b.mp4"  # 替换为你的 MP4 路径
    # 输出 GIF 的路径
    gif_path = r"D:\AI\desktopAI\assets\o2.gif"  # 替换为你想保存的 GIF 路径
    
    mp4_to_gif(mp4_path, gif_path, fps=15)  # 调整帧率为 15 FPS
