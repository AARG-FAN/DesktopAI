from PIL import Image, ImageFilter
import imageio
import numpy as np

def remove_green_background(image, green_threshold=150, diff_threshold=100):
    """
    移除GIF的绿色背景，保留人像中的绿色部分（如果有）。
    
    :param image: 输入的PIL图像
    :param green_threshold: 绿色通道的最低阈值，超过此值的像素可能是背景
    :param diff_threshold: 绿色通道与红蓝通道的差异阈值，确保是明显的绿色
    :return: 移除背景后的图像
    """
    image = image.convert("RGBA")
    datas = image.getdata()

    new_data = []
    for item in datas:
        red, green, blue, alpha = item
        # 判断是否为绿色背景
        if green > green_threshold and (green - red) > diff_threshold and (green - blue) > diff_threshold:
            # 透明化绿色背景
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    image.putdata(new_data)
    
    # 羽化处理（减少模糊强度）
    image = image.filter(ImageFilter.GaussianBlur(0.5))
    return image

def process_gif(input_gif, output_gif, green_threshold=150, diff_threshold=100, default_duration=100):
    """
    处理GIF图像，去除绿色背景。
    
    :param input_gif: 输入的GIF文件路径
    :param output_gif: 输出的GIF文件路径
    :param green_threshold: 绿色通道的最低阈值
    :param diff_threshold: 绿色与红蓝通道的差异阈值
    :param default_duration: 若无法获取帧的持续时间，则使用默认时长
    """
    reader = imageio.get_reader(input_gif)
    frames = []
    durations = []
    
    for i, frame in enumerate(reader):
        # 将每一帧转换为Pillow图像对象
        frame_image = Image.fromarray(frame)
        processed_frame = remove_green_background(frame_image, green_threshold, diff_threshold)
        frames.append(processed_frame)
        
        # 获取每帧的持续时间，若没有则使用默认值
        try:
            meta_data = reader.get_meta_data(index=i)
            duration = meta_data.get('duration', default_duration)
        except IndexError:
            duration = default_duration
        durations.append(duration)
    
    # 保存为GIF
    frames[0].save(
        output_gif,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,  # 确保透明区域正确渲染
        transparency=0  # 设置透明颜色索引
    )

# 使用示例
if __name__ == "__main__":
    input_gif = r'D:\AI\desktopAI\assets\o2.gif'      # 输入GIF路径
    output_gif = r'D:\AI\desktopAI\assets\gif2.gif'   # 输出GIF路径
    process_gif(input_gif, output_gif, green_threshold=20, diff_threshold=20)
    print("处理完成，生成的GIF已保存到:", output_gif)
