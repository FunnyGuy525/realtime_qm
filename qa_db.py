from sentence_transformers import SentenceTransformer
import numpy as np

model_path = './model/embedding_model'
m3e_model = SentenceTransformer.load(model_path)

# 定义一个问答数据库加载类
class qa_data:
  # 接受一个列表作为初始数据
  def __init__(self, data = []):
    # 将数据存储在一个属性中
    self.data = data

  # 用于向数据框中添加新的数据
  def add(self, new_data):
    new_data.append(m3e_model.encode(new_data[0]))
    self.data.append(new_data)
  
  # 用于删除指定数据
  def delete(self, data):
    pass

  # 用于显示数据框中的所有数据
  def show(self):
    for item in self.data:
      print(item[:2])
