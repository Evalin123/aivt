import json
import websockets
from dotenv import load_dotenv, set_key
import os


class VTSAPI:
    """VTube Studio API 連接類別"""
    
    def __init__(self, host="localhost", port=8001, plugin_name="AI Chat Assistant", plugin_developer="AI Assistant"):
        self.base_info = {
            'pluginName': plugin_name,
            'pluginDeveloper': plugin_developer
        }
        self.host = host
        self.port = port
        self.vts_token = None
        self.websocket = None
        self.authenticated = False
        self.connection_status = False
    
    async def send_request(self, message_type: str, data: dict = None) -> dict:
        """發送請求到 VTS API"""
        if not self.websocket:
            raise Exception("未連接到 VTS API")
        
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "AIVtuberRequest",
            "messageType": message_type,
            "data": data
        }
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def authentication(self) -> None:
        """VTS API 認證"""
        self.update_dotenv()
        
        if not self.vts_token:
            # 請求新的 token
            res = await self.send_request(
                message_type='AuthenticationTokenRequest',
                data=self.base_info
            )
            
            if res['messageType'] == 'APIError':
                raise Exception(f"錯誤: {res['data']['message']}")
            
            self.__update_token(res['data']['authenticationToken'])
            print("已獲得認證 token，請在 VTS 中授權此插件")
            return
        
        # 使用現有 token 進行認證
        res = await self.send_request(
            message_type='AuthenticationRequest',
            data={**self.base_info, 'authenticationToken': self.vts_token}
        )
        
        if not res['data']['authenticated']:
            raise ConnectionError(f"認證失敗: {res['data']['reason']}")
        
        self.authenticated = True
        print("VTS API 認證成功")
    
    async def initialise(self) -> None:
        """初始化連接"""
        self.update_dotenv()
        
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri)
            self.connection_status = True
            print(f"已連接到 VTS API")
            
            # 檢查認證狀態
            res = await self.send_request(message_type='APIStateRequest')
            
            if not res['data']['currentSessionAuthenticated']:
                await self.authentication()
            else:
                self.authenticated = True
                print("會話已認證")
                
        except Exception as e:
            print(f"VTS API 初始化失敗: {e}")
            self.connection_status = False
    
    async def inject_params(self, parameters: list) -> None:
        """注入參數到 VTS"""
        if not self.authenticated:
            print("VTS API 未認證，無法注入參數")
            return
        
        data = {
            "faceFound": False,
            "mode": "set",
            "parameterValues": [{"id": param[0], "value": param[1]} for param in parameters]
        }
        
        await self.send_request(message_type='InjectParameterDataRequest', data=data)
    
    def update_dotenv(self) -> None:
        """更新環境變量"""
        load_dotenv(override=True)
        self.vts_token = os.getenv("VTS_TOKEN")
    
    def __update_token(self, token: str) -> None:
        """更新 token（私有方法）"""
        self.vts_token = token
        set_key('.env', 'VTS_TOKEN', token)
    
    async def disconnect(self) -> None:
        """斷開連接"""
        if self.websocket:
            await self.websocket.close()
            self.connection_status = False
            print("已斷開 VTS API 連接")
