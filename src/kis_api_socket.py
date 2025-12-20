# -*- coding: utf-8 -*-
import os
import sys
import yaml
import json
import time
import requests
import asyncio
import websockets
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

# AES256 DECODE
def aes_cbc_base64_dec(key, iv, cipher_text):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))

class KISWebSocketClient:
    def __init__(self, stock_code: str, on_message):
        self.is_running = False
        self.stock_code = stock_code
        self.on_message = on_message
        self._load_config()
        self.approval_key = self._get_approval()

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'kis_devlp.yaml')
        try:
            with open(config_path, 'r', encoding='UTF-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            print("Warning: config/kis_devlp.yaml not found. Using dummy values.")
            config = {'virtual_appkey': 'YOUR_VIRTUAL_APP_KEY', 'virtual_appsecret': 'YOUR_VIRTUAL_APP_SECRET'}

        self.g_appkey = config.get('virtual_appkey')
        self.g_appsecret = config.get('virtual_appsecret')
        self.url = 'ws://ops.koreainvestment.com:31000' # 모의투자
        self.htsid = 'YOUR_HTS_ID' # HTS ID
        self.custtype = 'P'

    def _get_approval(self):
        url = 'https://openapivts.koreainvestment.com:29443' # 모의투자
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials",
                "appkey": self.g_appkey,
                "secretkey": self.g_appsecret}
        PATH = "oauth2/Approval"
        URL = f"{url}/{PATH}"
        res = requests.post(URL, headers=headers, data=json.dumps(body))
        res_data = res.json()
        print(f"KIS API Response: {res_data}")
        approval_key = res_data["approval_key"]
        return approval_key

    async def connect(self):
        self.is_running = True
        async with websockets.connect(self.url, ping_interval=None) as websocket:
            # 주식체결 등록
            tr_id = 'H0STCNT0'
            tr_type = '1'
            senddata = f'{{"header":{{"approval_key":"{self.approval_key}","custtype":"{self.custtype}","tr_type":"{tr_type}","content-type":"utf-8"}},"body":{{"input":{{"tr_id":"{tr_id}","tr_key":"{self.stock_code}"}}}}}}'
            
            await websocket.send(senddata)
            await asyncio.sleep(0.5)
            print(f"Subscribed to stock conclusions for {self.stock_code}")

            while self.is_running:
                try:
                    data = await websocket.recv()
                    if data[0] == '0' or data[0] == '1':
                        recvstr = data.split('|')
                        trid0 = recvstr[1]
                        if trid0 == "H0STCNT0":  # 주식체결 데이터 처리
                            self.on_message(recvstr[3])
                    else:
                        jsonObject = json.loads(data)
                        trid = jsonObject["header"]["tr_id"]
                        if trid != "PINGPONG":
                            rt_cd = jsonObject["body"]["rt_cd"]
                            if rt_cd != '0':
                                print(f"### ERROR: {jsonObject['body']['msg1']}")
                        elif trid == "PINGPONG":
                            await websocket.pong(data)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed, attempting to reconnect...")
                    await asyncio.sleep(5)
                    await self.connect()

    def stop(self):
        self.is_running = False

async def main():
    def my_message_handler(message):
        print(f"Received: {message}")

    client = KISWebSocketClient("005930", my_message_handler)
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
