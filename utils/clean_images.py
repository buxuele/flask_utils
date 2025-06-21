import os
import uuid
from PIL import Image # pip install Pillow

# 下面这一行，实际上用了！
# 目的是为了能读取 .avif 类型的图片
import pillow_avif # pip install pillow-avif-plugin
# https://stackoverflow.com/questions/74527775/how-to-convert-avif-to-png-with-python


"""
目的: 解决这个问题, [Windows照片查看器无法显示此图片，因为计算机上的可用内存可能不足...]
做法: 把一个文件夹全部的图片，都转为 jpg, 然后写入到一个新的文件夹，放到桌面。
"""



# 把全部的图片，都转为 jpg, 然后保存到桌面
def convert_image_to_jpg(source="./", output_suffix="jpg"):
    output_dir = r"C:\Users\Administrator\Desktop\temp_" + str(uuid.uuid4())[:8]
    os.makedirs(output_dir, exist_ok=True)

    # 1. source is a folder
    if os.path.isdir(source):
        print("source is a dir: ", source)

        for img_name in os.listdir(source):
            # 1. 输入文件名
            img_path = os.path.join(source, img_name)

            # 2. 输出文件名
            prefix, suffix = os.path.splitext(img_name)
            output_name = os.path.join(output_dir, f"{prefix}.{output_suffix}")
            print("output_name:", output_name)

            # 3. 文件类型转换
            im = Image.open(img_path)
            rgb_im = im.convert('RGB')  # OSError: cannot write mode RGBA as JPEG
            rgb_im.save(output_name)
            print()

    # 2. source is a single image
    else:
        print("source is a file: ", source)
        prefix, suffix = os.path.splitext(source)
        out_name = os.path.join(prefix, output_suffix)
        im = Image.open(source)
        im.save(out_name)
    print("Done")


if __name__ == '__main__':
    p = r" C:\Users\Administrator\Work\imgs ".strip()
    convert_image_to_jpg(p)
