from sentence_transformers import SentenceTransformer
from qa_db import qa_data
import numpy as np
import json

model_path = './model/embedding_model'
m3e_model = SentenceTransformer.load(model_path)
class match:
  # __init__方法，接受一个qa_data对象作为参数
  def __init__(self, qa_data):
    # 将qa_data对象存储在一个属性中
    self.qa_data = qa_data
  
  # 定义一个方法，用于接收一个数据，然后和qa_data中的数据匹配，返回最相关的数据
  def query(self, data):
    # 对输入的数据进行编码，得到一个向量
    data_vec = m3e_model.encode(data)
    # 定义一个空列表，用于存储每个问答对的相似度
    sim_list = []
    # 遍历qa_data中的每个问答对
    for item in self.qa_data.data:
      # 计算输入数据和问答对问题的余弦相似度，并添加到列表中
      sim = np.dot(data_vec, item[2]) / (np.linalg.norm(data_vec) * np.linalg.norm(item[2]))
      sim_list.append(sim)
    # 找到最大相似度的索引
    max_index = np.argmax(sim_list)
    # 返回最大相似度对应的问答对
    if max(sim_list) > 0.81:
      match_data = {
        "问题": self.qa_data.data[max_index][:2][0],
        "答案": self.qa_data.data[max_index][:2][1],
        "相似度": str(max(sim_list))
      }
      return match_data
    else:
      return 0
