'''改自'''
#coding=utf-8

"""
requires Python 3.6 or later

pip install asyncio
pip install websockets
"""
from qa_test import test
import base64
import gzip
import hmac
import json
import uuid
import wave
from enum import Enum
from hashlib import sha256
from io import BytesIO
from urllib.parse import urlparse
import websockets
import asyncio
import websockets
import csv
import time

IP = '0.0.0.0'
PORT = 8000


appid = ""    # 项目的 appid
token = ""    # 项目的 token
cluster = ""  # 请求的集群

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

PROTOCOL_VERSION_BITS = 4
HEADER_BITS = 4
MESSAGE_TYPE_BITS = 4
MESSAGE_TYPE_SPECIFIC_FLAGS_BITS = 4
MESSAGE_SERIALIZATION_BITS = 4
MESSAGE_COMPRESSION_BITS = 4
RESERVED_BITS = 8

# Message Type:
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000  # no check sequence
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_SEQUENCE_1 = 0b0011

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111

# Message Compression
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111

 # 生成请求头
def generate_header(
    version=PROTOCOL_VERSION,
    message_type=CLIENT_FULL_REQUEST,
    message_type_specific_flags=NO_SEQUENCE,
    serial_method=JSON,
    compression_type=GZIP,
    reserved_data=0x00,
    extension_header=bytes()
):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    """
    header = bytearray()
    header_size = int(len(extension_header) / 4) + 1
    header.append((version << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    header.extend(extension_header)
    return header


def generate_full_default_header():
    return generate_header()


def generate_audio_default_header():
    return generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST
    )


def generate_last_audio_default_header():
    return generate_header(
        message_type=CLIENT_AUDIO_ONLY_REQUEST,
        message_type_specific_flags=NEG_SEQUENCE
    )

def parse_response(res):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    payload 类似与http 请求体
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    result = {}
    payload_msg = None
    payload_size = 0
    if message_type == SERVER_FULL_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result['payload_msg'] = payload_msg
    result['payload_size'] = payload_size
    return result


def read_wav_info(data: bytes = None) -> (int, int, int, int, int):
    with BytesIO(data) as _f:
        wave_fp = wave.open(_f, 'rb')
        nchannels, sampwidth, framerate, nframes = wave_fp.getparams()[:4]
        wave_bytes = wave_fp.readframes(nframes)
    return nchannels, sampwidth, framerate, nframes, len(wave_bytes)

class AudioType(Enum):
    LOCAL = 1  # 使用本地音频文件

class AsrWsClient:
    def __init__(self, **kwargs):
        """
        :param config: config
        """

        self.cluster = "volcengine_streaming_common" # cluster 直接给
        self.success_code = 1000  # success code, default is 1000
        self.seg_duration = int(kwargs.get("seg_duration", 100))
        self.nbest = int(kwargs.get("nbest", 1))
        self.appid = kwargs.get("appid", "5558640763")
        self.token = kwargs.get("token", "CrHkhrK3St4mxI2536UT5JSBMhqXx_84")
        self.ws_url = kwargs.get("ws_url", "wss://openspeech.bytedance.com/api/v2/asr")
        self.uid = kwargs.get("uid", "streaming_asr_demo")
        self.workflow = kwargs.get("workflow", "audio_in,resample,partition,vad,fe,decode,itn,nlu_ddc,nlu_punctuate")
        self.show_language = kwargs.get("show_language", False)
        self.show_utterances = kwargs.get("show_utterances", True)
        self.result_type = kwargs.get("result_type", "single")
        self.format = kwargs.get("format", "wav")
        self.rate = kwargs.get("sample_rate", 16000)
        self.language = kwargs.get("language", "zh-CN")
        self.bits = kwargs.get("bits", 16)
        self.channel = kwargs.get("channel", 2)
        self.codec = kwargs.get("codec", "raw")
        self.audio_type = kwargs.get("audio_type", AudioType.LOCAL)
        self.secret = kwargs.get("secret", "access_secret")
        self.auth_method = kwargs.get("auth_method", "token")
        self.mp3_seg_size = int(kwargs.get("mp3_seg_size", 10000))

    # 生成请求数据
    def construct_request(self, reqid):
        req = {
            'app': {
                'appid': self.appid,
                'cluster': self.cluster,
                'token': self.token,
            },
            'user': {
                'uid': self.uid
            },
            'request': {
                'reqid': reqid,
                'nbest': self.nbest,
                'workflow': self.workflow,
                'show_language': self.show_language,
                'show_utterances': self.show_utterances,
                'result_type': self.result_type,
                "sequence": 1
            },
            'audio': {
                'format': self.format,
                'rate': self.rate,
                'language': self.language,
                'bits': self.bits,
                'channel': self.channel,
                'codec': self.codec
            }
        }
        return req

    def _real_processor(self, request_params: dict) -> dict:
        pass

    def token_auth(self):
        return {'Authorization': 'Bearer; {}'.format(self.token)}

    def signature_auth(self, data):
        header_dicts = {
            'Custom': 'auth_custom',
        }

        url_parse = urlparse(self.ws_url)
        input_str = 'GET {} HTTP/1.1\n'.format(url_parse.path)
        auth_headers = 'Custom'
        for header in auth_headers.split(','):
            input_str += '{}\n'.format(header_dicts[header])
        input_data = bytearray(input_str, 'utf-8')
        input_data += data
        mac = base64.urlsafe_b64encode(
            hmac.new(self.secret.encode('utf-8'), input_data, digestmod=sha256).digest())
        header_dicts['Authorization'] = 'HMAC256; access_token="{}"; mac="{}"; h="{}"'.format(self.token,
                                                                                              str(mac, 'utf-8'), auth_headers)
        return header_dicts

    async def data_processor(self, websocket):
        print('data_processor start')
        reqid = str(uuid.uuid4())

        # 构建 full client request，并序列化压缩
        request_params = self.construct_request(reqid)
        payload_bytes = str.encode(json.dumps(request_params))
        payload_bytes = gzip.compress(payload_bytes)
        full_client_request = bytearray(generate_full_default_header())
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
        full_client_request.extend(payload_bytes)  # payload
        header = None
        if self.auth_method == "token":
            header = self.token_auth()
        elif self.auth_method == "signature":
            header = self.signature_auth(full_client_request)
        async with websockets.connect(self.ws_url, extra_headers=header, max_size=1000000000) as ws:
            # 发送 full client request
            await ws.send(full_client_request)
            # print('发送 full client request 成功')
            res = await ws.recv()
            result = parse_response(res)
            if 'payload_msg' in result and result['payload_msg']['code'] != self.success_code:
                return result

            while True:
                message = await websocket.recv()
                data = json.loads(message)  # 解析JSON数据
                encoded_audio = data["audio"]
                audio_segment = base64.b64decode(encoded_audio)

                # 如果不需要进行压缩，请将下面这行注释掉
                payload_bytes = gzip.compress(audio_segment)
                audio_only_request = bytearray(generate_audio_default_header())
                
                if data["last_segment"]:
                    print('over')
                    audio_only_request = bytearray(generate_last_audio_default_header())
                    
                audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size（4个字节）
                audio_only_request.extend(payload_bytes)  # payload
                
                # 发送 audio-only client request
                await ws.send(audio_only_request)
                res = await ws.recv()
                result = parse_response(res)
                if len(result['payload_msg']) == 6:
                    text = result['payload_msg']['result'][0]['text']
                    if '？' in text:
                        response = test(text)
                        if response:
                            dic = {"识别结果": text}
                            dic.update(response)
                            await websocket.send(json.dumps(dic))
                            print(dic)
                        else:
                            await websocket.send(json.dumps({"识别结果": text}))
                    else:
                        await websocket.send(json.dumps({"识别结果": text}))
                else:
                    await websocket.send(json.dumps({"识别结果": ''}))

                if 'payload_msg' in result and result['payload_msg']['code'] != self.success_code:
                    print(result)
                    return result
        print(result)

asr  = AsrWsClient()
async def start_server():
    server = await websockets.serve(asr.data_processor, IP, PORT, ping_interval=None)
    print(f"Server is listening on {IP}:{PORT}")
    await server.wait_closed()


asyncio.run(start_server())
