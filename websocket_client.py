from pydub import AudioSegment
import asyncio
import websockets
import base64
import json

# 设置本地音频地址，模拟实时音频流
audio_path = ''  # 本地音频路径

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

            response = await websocket.recv()  # 接收响应
            response = json.loads(response)
            print(response)

asyncio.get_event_loop().run_until_complete(upload_audio())
