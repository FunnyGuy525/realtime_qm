# 将embedding 使用的模型保存到本地，方便调用，模型类型可以自己更改，此处使用的是moka的m3e-base，默认使用GPU加速

from sentence_transformers import SentenceTransformer

model_name = 'moka-ai/m3e-base'
model_path = './model/embedding_model'

m3e_model = SentenceTransformer(model_name, device="cuda")
m3e_model.save(model_path)
