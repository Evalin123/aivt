import json
import websockets
import asyncio


class VTSAPI:
    """VTube Studio API 連接類別"""
    
    def __init__(self, host="localhost", port=8001):
        self.host = host
        self.port = port
        self.websocket = None
        self.authenticated = False
        self.api_token = None
        self.connection_status = False
        
    async def connect(self):
        """連接到 VTS API"""
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri)
            self.connection_status = True
            print(f"已連接到 VTS API: {uri}")
            
            # 開始監聽訊息
            await self.listen_for_messages()
            
        except Exception as e:
            print(f"VTS API 連接失敗: {e}")
            self.connection_status = False
    
    async def authenticate(self):
        """VTS API 認證"""
        try:
            # 發送認證請求
            auth_request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "auth_request",
                "messageType": "AuthenticationRequest",
                "data": {
                    "pluginName": "AI Chat Assistant",
                    "pluginDeveloper": "AI Assistant",
                    "pluginIcon": ""
                }
            }
            
            print(f"發送認證請求: {json.dumps(auth_request, indent=2)}")
            await self.websocket.send(json.dumps(auth_request))
            print("已發送 VTS 認證請求")
            
        except Exception as e:
            print(f"VTS 認證失敗: {e}")
    
    async def listen_for_messages(self):
        """監聽 VTS API 訊息"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("VTS API 連接已關閉")
            self.connection_status = False
        except Exception as e:
            print(f"VTS 訊息監聽錯誤: {e}")
    
    async def handle_message(self, data):
        """處理 VTS API 訊息"""
        print(f"收到 VTS 訊息: {json.dumps(data, indent=2)}")
        
        message_type = data.get("messageType", "")
        
        if message_type == "AuthenticationResponse":
            if data.get("data", {}).get("authenticated"):
                self.authenticated = True
                self.api_token = data.get("data", {}).get("authenticationToken")
                print("VTS API 認證成功！")
            else:
                print("VTS API 認證失敗")
                print(f"失敗原因: {data.get('data', {}).get('reason', '未知')}")
        
        elif message_type == "APIStateResponse":
            print("VTS API 狀態更新")
        
        else:
            print(f"收到其他訊息類型: {message_type}")
    
    async def trigger_expression(self, expression_name="Happy"):
        """觸發表情"""
        if not self.authenticated:
            print("VTS API 未認證，無法觸發表情")
            return
        
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": f"expression_{expression_name}",
                "messageType": "ExpressionActivationRequest",
                "data": {
                    "expressionFile": expression_name,
                    "active": True
                }
            }
            
            await self.websocket.send(json.dumps(request))
            print(f"已觸發表情: {expression_name}")
            
        except Exception as e:
            print(f"觸發表情失敗: {e}")
    
    async def trigger_hotkey(self, hotkey_name="Speaking"):
        """觸發熱鍵"""
        if not self.authenticated:
            print("VTS API 未認證，無法觸發熱鍵")
            return
        
        try:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": f"hotkey_{hotkey_name}",
                "messageType": "HotkeyTriggerRequest",
                "data": {
                    "hotkeyID": hotkey_name
                }
            }
            
            print(f"發送熱鍵請求: {json.dumps(request, indent=2)}")
            await self.websocket.send(json.dumps(request))
            print(f"已觸發熱鍵: {hotkey_name}")
            
        except Exception as e:
            print(f"觸發熱鍵失敗: {e}")
    
    async def start_speaking(self):
        """開始說話動作"""
        await self.trigger_hotkey("Speaking")
        await self.trigger_expression("Happy")
    
    async def stop_speaking(self):
        """停止說話動作"""
        await self.trigger_hotkey("Idle")
        await self.trigger_expression("Neutral")
    
    async def disconnect(self):
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
            self.connection_status = False
            print("已斷開 VTS API 連接")
