from pydub import AudioSegment
import asyncio
import websockets
import base64
import json
import requests

import time
import csv

# 可以批量下载音频并处理，结果存到 audio_output.csv 文件，可以查看识别效果和时效性
txt_path = '音频网址.txt'
audio_path = 'audio'  # 本地音频路径

csv_f = open('audio_output.csv', mode='w', encoding='utf-8')
writer = csv.writer(csv_f)
writer.writerow(['相似度', '对话问题', '匹配问题', '答案', '时间/ms'])

async def upload_audio():
    audio = AudioSegment.from_file(audio_path, format="mp3")  # 加载MP3音频文件
    seg_duration = 40  # 部分持续时间 (ms)
    segment_size = int(seg_duration * audio.frame_rate / 1000)  # 计算每一部分的采样点数量

    last_segment = False
    
    async with websockets.connect('ws://0.0.0.0:8000/') as websocket:
        for i in range(0, len(audio), segment_size):
            audio_segment = audio[i:i+segment_size]  # 截取音频段
            
            if i + segment_size >= len(audio):
                last_segment = True  # 判断是否为最后一段音频
            
            # 导出音频段为PCM原始数据
            pcm_bytes = audio_segment.export(format='wav').read()
            
            # 对PCM原始数据进行Base64编码
            encoded_audio = base64.b64encode(pcm_bytes).decode("utf-8")
            
            await websocket.send(json.dumps({"audio": encoded_audio, "last_segment": last_segment}))  # 发送音频段
            start = time.time()

            response = await websocket.recv()  # 接收响应
            response = json.loads(response)
            if '相似度' in response:
                end = time.time()
                writer.writerow([str(response['相似度']), str(response['识别结果']), str(response['问题']), str(response['答案']), (end-start)*1000])

            print(response)


max_retry = 3

# 打开txt文件，读取每一行的网址
with open(txt_path, 'r') as f:
    for line in f:
        url = line.strip()  # 去掉换行符
        print(url)  # 打印网址
        
        # 下载网址对应的音频文件到本地
        retry = 0  # 当前重试次数
        success = False  # 是否下载成功
        
        while retry < max_retry and not success:  # 如果没有达到最大重试次数并且没有下载成功，就继续重试
            try:
                r = requests.get(url)  # 尝试获取网址的响应
                r.raise_for_status()  # 检查响应状态码是否正常，如果不正常，抛出异常
                
                with open(audio_path, 'wb') as f:
                    f.write(r.content)  # 如果正常，就把响应内容写入本地音频文件
                    
                success = True  # 标记下载成功
                
            except requests.exceptions.RequestException as e:  # 如果发生异常，就打印异常信息，并增加重试次数
                print(e)
                retry += 1
        
        if success:  # 如果下载成功，就对本地音频文件执行上传操作
            asyncio.get_event_loop().run_until_complete(upload_audio())
        else:  # 如果下载失败，就打印失败信息，并跳过这个网址
            print(f'Failed to download {url} after {max_retry} retries.')
csv_f.close()
