import tkinter as tk

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
import tempfile

import cv2
import pyaudio
import PIL.Image
import mss
import pygame

import argparse
import threading
from dotenv import load_dotenv

import edge_tts
from google import genai
from google.genai import types

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

# 音頻模式的配置
AUDIO_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
)

pya = pyaudio.PyAudio()

# 讀取角色設定檔案
character_prompt = ""
character_files_path = "./character_files"
if os.path.exists(character_files_path):
    for filename in os.listdir(character_files_path):
        if filename.endswith(".txt"):
            with open(os.path.join(character_files_path, filename), "r", encoding='UTF-8') as file:
                character_prompt += file.read() + "\n"

# 建立聊天會話，角色設定作為初始內容（類似原始 start_chat 做法）
chat_contents = [{"text": character_prompt}] if character_prompt else []

# 初始化 pygame 音頻
pygame.mixer.init()

async def speak_text(text):
    """使用 edge-tts 生成並播放語音"""
    try:
        # 創建臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
        
        # 使用 edge-tts 生成語音（中文女聲）
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
        await communicate.save(temp_path)
        
        # 使用 pygame 播放
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        # 清理臨時檔案
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"語音播放錯誤: {e}")
        # 清理可能殘留的臨時檔案
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass


class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE):
        self.video_mode = video_mode

        self.audio_in_queue = None
        self.out_queue = None

        self.session = None

        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    def _get_frame(self, cap):
        # Read the frameq
        ret, frame = cap.read()
        # Check if the frame was read successfully
        if not ret:
            return None
        # Fix: Convert BGR to RGB color space
        # OpenCV captures in BGR but PIL expects RGB format
        # This prevents the blue tint in the video feed
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)  # Now using RGB frame
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        # This takes about a second, and will block the whole program
        # causing the audio pipeline to overflow if you don't to_thread it.
        cap = await asyncio.to_thread(
            cv2.VideoCapture, 0
        )  # 0 represents the default camera

        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

        # Release the VideoCapture object
        cap.release()

    def _get_screen(self):
        sct = mss.mss()
        monitor = sct.monitors[0]

        i = sct.grab(monitor)

        mime_type = "image/jpeg"
        image_bytes = mss.tools.to_png(i.rgb, i.size)
        img = PIL.Image.open(io.BytesIO(image_bytes))

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_screen(self):

        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            # 根據模式選擇配置
            config = AUDIO_CONFIG if self.video_mode != "none" else TEXT_CONFIG
            
            async with (
                client.aio.live.connect(model=MODEL, config=config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                if self.video_mode == "camera":
                    tg.create_task(self.get_frames())
                elif self.video_mode == "screen":
                    tg.create_task(self.get_screen())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            self.audio_stream.close()
            traceback.print_exception(EG)


def send_message():
    message = message_entry.get()
    if message:
        # 顯示用戶訊息
        chat_display.config(state=tk.NORMAL)
        chat_display.insert(tk.END, f"你: {message}\n")
        
        # 調用 Gemini API（角色設定 + 用戶訊息）
        try:
            # 組合內容：角色設定 + 用戶訊息
            contents = chat_contents + [{"text": message}]
            
            # 生成回應
            response = client.models.generate_content(
                model="models/gemini-2.0-flash-exp",
                contents=contents
            )
            
            ai_response = response.text if hasattr(response, 'text') else str(response)
            chat_display.insert(tk.END, f"AI: {ai_response}\n\n")
            
            # 播放 AI 回應的語音
            try:
                # 使用 threading + asyncio.run 在背景線程中運行協程
                import threading
                threading.Thread(target=lambda: asyncio.run(speak_text(ai_response)), daemon=True).start()
            except Exception as voice_error:
                chat_display.insert(tk.END, f"語音播放錯誤: {str(voice_error)}\n\n")
                
        except Exception as e:
            chat_display.insert(tk.END, f"AI: 錯誤 - {str(e)}\n\n")
        
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)
        message_entry.delete(0, tk.END)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none", "chat"],
    )
    args = parser.parse_args()
    
    if args.mode == "chat":
        # 聊天模式
        root = tk.Tk()
        root.title("簡易聊天視窗")

        chat_display = tk.Text(root, height=15, width=50, state=tk.DISABLED)
        chat_display.pack(padx=10, pady=10)

        message_entry = tk.Entry(root, width=40)
        message_entry.pack(side=tk.LEFT, padx=10, pady=10)

        send_button = tk.Button(root, text="發送", command=send_message)
        send_button.pack(side=tk.RIGHT, padx=10, pady=10)

        root.mainloop()
    else:
        # 原有模式
        main = AudioLoop(video_mode=args.mode)
        asyncio.run(main.run())




