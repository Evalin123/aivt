import warnings
import os

# 抑制 macOS 系統警告
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

"""
## Documentation
Quickstart: https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py

## Setup

To install the dependencies for this script, run:

```
pip3 install google-genai opencv-python pyaudio pillow mss
```
"""

import os
import asyncio
import base64
import io
import traceback


import argparse
import threading
from dotenv import load_dotenv
from google import genai
from google.genai import types
from VTSController import VTSAPI
from waifu import WaifuChat

# 載入環境變量
load_dotenv()


MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025"

DEFAULT_MODE = "chat"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.getenv("GEMINI_API_KEY"),
)


# 文字模式的配置
TEXT_CONFIG = types.LiveConnectConfig(
    response_modalities=["TEXT"],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
)

# 初始化 VTS API
vts_api = VTSAPI()

class TextLoop:
    def __init__(self):
        self.session = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def receive_text(self):
        """接收 AI 的文字回應"""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if text := response.text:
                    print(text, end="")

    async def run(self):
        try:
            # 只使用文字模式配置
            config = TEXT_CONFIG
            
            async with (
                client.aio.live.connect(model=MODEL, config=config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.receive_text())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            traceback.print_exception(EG)
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["text", "chat"],
    )
    args = parser.parse_args()
    
    if args.mode == "chat":
        # 聊天模式
        import tkinter as tk
        
        # 初始化 WaifuChat
        waifu_chat = WaifuChat(vts_api)
        
        root = tk.Tk()
        waifu_chat.create_chat_gui(root)
        
        # 初始化 VTS API 連接
        async def init_vts():
            try:
                print("正在嘗試連接 VTS API...")
                await vts_api.connect()
                print("VTS API 連接成功，正在認證...")
                await vts_api.authenticate()
                print("VTS API 認證完成")
            except Exception as e:
                print(f"VTS API 初始化失敗: {e}")
                print("請確認 VTube Studio 正在運行且已開啟 API 功能")
        
        # 在背景線程中初始化 VTS
        threading.Thread(target=lambda: asyncio.run(init_vts()), daemon=True).start()

        root.mainloop()
    else:
        # 文字模式
        main = TextLoop()
        asyncio.run(main.run())




