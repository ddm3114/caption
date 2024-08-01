import os

# 获取当前脚本的绝对路径
current_path = os.path.abspath(__file__)

# 获取父目录
parent_directory = os.path.dirname(current_path)

print("当前路径：", current_path)
print("父目录：", parent_directory)
