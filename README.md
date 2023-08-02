# 接受客户端音频流进行对话流式语音识别，同时将对话问题检索问答数据库相似信息，将信息构成提示词给gpt得到结果返回客户端
## 项目描述
>  详细的项目描述
1. 创建问答数据库，默认使用moka的m3e模型对问题进行embedding
2. 服务端接收音频数据，调用火山流式语音识别api进行实时语音识别
3. 提取对话识别结果中的问题，同时调用m3e模型进行embedding，再与问答数据库中的问题向量计算相似度，返回最相近且相似度＞0.81的问题给客户端
4. 将问答数据和对话问题构成提示词给大模型得到结果返回给客户端


## 运行说明
> 说明如何运行和使用你的项目，建议给出具体的步骤说明
* 项目克隆到本地```git clone git@codeup.aliyun.com:yiliang/algorithm/realtime_question_match.git```
* 进入项目文件夹
* 安装依赖 ```pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple```
* 使用model文件夹中的model.py创建一个本地embedding模型，默认模型为moka的m3e，文件名为embedding_model
* websocket_server 中设置如下参数，火山引擎语音技术应用管理可查

appid = "xxx"    # 项目的 appid

token = "xxx"    # 项目的 token

cluster = "xxx"  # 请求的集群

* 将websocket_client.py中audio_path 设置为本地音频文件地址即可
* 分别在两个终端先运行websocket_server 再运行websocket_client


## 文档说明
* qa_db 是一个问答数据加载类，存储问答数据以及问题的embedding。可以添加、显示问答数据
* questio_match 接受一个qa_db对象，query方法接收一个问题并匹配最大相似度且大于0.81的问答对
* qa_test 创建一个qa_db对象，存入百答数据。注释掉了chatgpt返回结果的部分。

## 测试说明
* test文件夹里的test_server和test_client用于批量测试。
* 将文件放入主目录，需要调用qa_db,question_match,qa_test
* 其他操作同上
