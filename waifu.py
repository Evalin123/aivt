import tkinter as tk
import os
import asyncio
import tempfile
import threading
import pygame
import edge_tts
from google import genai


class WaifuChat:
    """AI 對話和語音播放管理類別"""
    
    def __init__(self, vts_api=None):
        self.vts_api = vts_api
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key="AIzaSyBn_Ah21Byc_-1wgNYuZ2tGAfhhYakhSVA",
        )
        
        # 讀取角色設定檔案
        self.character_prompt = ""
        self.character_files_path = "./character_files"
        self._load_character_prompt()
        
        # 建立聊天會話，角色設定作為初始內容
        self.chat_contents = [{"text": self.character_prompt}] if self.character_prompt else []
        
        # 初始化 pygame 音頻
        pygame.mixer.init()
    
    def _load_character_prompt(self):
        """載入角色設定檔案"""
        if os.path.exists(self.character_files_path):
            for filename in os.listdir(self.character_files_path):
                if filename.endswith(".txt"):
                    with open(os.path.join(self.character_files_path, filename), "r", encoding='UTF-8') as file:
                        self.character_prompt += file.read() + "\n"
    
    async def speak_text(self, text):
        """使用 edge-tts 生成並播放語音到 VB-CABLE，並觸發 VTS 動作"""
        try:
            # 觸發 VTS 開始說話動作
            if self.vts_api and self.vts_api.connection_status and self.vts_api.authenticated:
                await self.vts_api.start_speaking()
            
            # 創建臨時檔案
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
            
            # 使用 edge-tts 生成語音（中文女聲）
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            await communicate.save(temp_path)
            
            # 使用 pygame 播放到 VB-CABLE
            await self.play_to_vbcable_pygame(temp_path)
            
            # 觸發 VTS 停止說話動作
            if self.vts_api and self.vts_api.connection_status and self.vts_api.authenticated:
                await self.vts_api.stop_speaking()
            
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

    async def play_to_vbcable_pygame(self, audio_file):
        """使用 pygame 播放音頻到系統預設設備（推薦的 Mac/pygame 邏輯）"""
        try:
            # 1. 忽略設備名稱，使用系統預設設定
            pygame.mixer.quit() 
            pygame.mixer.init()  # 使用最簡單的初始化，它會使用 macOS 當前的預設輸出裝置
            print("成功初始化 pygame mixer，聲音將輸出到 macOS 預設播放設備。")
            
            # 2. 播放音頻
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # 3. 等待播放完成
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
        except pygame.error as e:
            print(f"初始化 pygame 失敗: {e}")
            return
        except Exception as e:
            print(f"音頻播放錯誤: {e}")
    
    def send_message(self, message_entry, chat_display):
        """發送訊息並處理 AI 回應"""
        message = message_entry.get()
        if message:
            # 顯示用戶訊息
            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, f"你: {message}\n")
            
            # 調用 Gemini API（角色設定 + 用戶訊息）
            try:
                # 組合內容：角色設定 + 用戶訊息
                contents = self.chat_contents + [{"text": message}]
                
                # 生成回應
                response = self.client.models.generate_content(
                    model="models/gemini-2.0-flash-exp",
                    contents=contents
                )
                
                ai_response = response.text if hasattr(response, 'text') else str(response)
                chat_display.insert(tk.END, f"AI: {ai_response}\n\n")
                
                # 播放 AI 回應的語音
                try:
                    # 使用 threading + asyncio.run 在背景線程中運行協程
                    threading.Thread(target=lambda: asyncio.run(self.speak_text(ai_response)), daemon=True).start()
                except Exception as voice_error:
                    chat_display.insert(tk.END, f"語音播放錯誤: {str(voice_error)}\n\n")
                    
            except Exception as e:
                chat_display.insert(tk.END, f"AI: 錯誤 - {str(e)}\n\n")
            
            chat_display.config(state=tk.DISABLED)
            chat_display.see(tk.END)
            message_entry.delete(0, tk.END)
    
    def create_chat_gui(self, root):
        """創建聊天 GUI"""
        root.title("簡易聊天視窗")

        chat_display = tk.Text(root, height=15, width=50, state=tk.DISABLED)
        chat_display.pack(padx=10, pady=10)

        message_entry = tk.Entry(root, width=40)
        message_entry.pack(side=tk.LEFT, padx=10, pady=10)

        send_button = tk.Button(
            root, 
            text="發送", 
            command=lambda: self.send_message(message_entry, chat_display)
        )
        send_button.pack(side=tk.RIGHT, padx=10, pady=10)
        
        return chat_display, message_entry, send_button
    
    async def send_text_input(self):
        """文字輸入處理（用於 AudioLoop）"""
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            return text or "."
