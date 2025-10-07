"""
3D 드론 AI 대전 시뮬레이터 - 백엔드 서버
FastAPI와 WebSocket을 사용하여 실시간 게임 서버를 구현합니다.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import json
import asyncio
from pathlib import Path
import sys

# AI 드론 모듈 임포트
from ai_drone import AIDrone

# FastAPI 앱 초기화
app = FastAPI(title="3D Drone AI Battle Simulator")

# 게임 상태 관리를 위한 전역 변수
class GameState:
    """게임 상태를 관리하는 클래스"""
    
    def __init__(self):
        self.connected_clients: List[WebSocket] = []  # 접속한 클라이언트 목록
        self.player_positions: Dict[str, List[float]] = {}  # 플레이어 드론 위치
        self.ai_drones: Dict[str, AIDrone] = {}  # AI 드론 객체들
        self.obstacles: List[Dict] = self._initialize_obstacles()  # 장애물
        self.game_loop_running = False
        
    def _initialize_obstacles(self) -> List[Dict]:
        """
        스팀펑크 스타일의 장애물 초기화
        거대한 톱니바퀴, 파이프 등을 배치합니다.
        """
        return [
            {
                'type': 'gear',  # 톱니바퀴
                'position': [15, 5, 10],
                'rotation': 0,
                'size': [4, 1, 4]
            },
            {
                'type': 'gear',
                'position': [-20, 8, -15],
                'rotation': 0,
                'size': [5, 1, 5]
            },
            {
                'type': 'pipe',  # 파이프
                'position': [0, 10, 0],
                'rotation': 0,
                'size': [2, 15, 2]
            },
            {
                'type': 'pipe',
                'position': [25, 7, -20],
                'rotation': 90,
                'size': [2, 20, 2]
            },
            {
                'type': 'gear',
                'position': [-10, 3, 20],
                'rotation': 0,
                'size': [3, 1, 3]
            }
        ]

# 전역 게임 상태 객체
game_state = GameState()


@app.get("/", response_class=HTMLResponse)
async def serve_game():
    """
    게임 HTML 페이지 제공
    프론트엔드 index.html 파일을 읽어서 반환합니다.
    """
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    
    if frontend_path.exists():
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return """
        <html>
            <body>
                <h1>Frontend file not found!</h1>
                <p>Please make sure frontend/index.html exists.</p>
            </body>
        </html>
        """


@app.get("/health")
async def health_check():
    """서버 상태 확인용 엔드포인트"""
    return {
        "status": "healthy",
        "connected_clients": len(game_state.connected_clients),
        "ai_drones": len(game_state.ai_drones)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 연결 처리
    클라이언트와 실시간 양방향 통신을 담당합니다.
    """
    # 1. 클라이언트 연결 수락
    await websocket.accept()
    game_state.connected_clients.append(websocket)
    
    # 2. 클라이언트에게 고유 ID 부여
    client_id = f"player_{len(game_state.connected_clients)}"
    
    # 3. AI 드론 생성 (각 플레이어마다 하나씩)
    ai_drone_id = f"ai_{client_id}"
    game_state.ai_drones[ai_drone_id] = AIDrone(
        drone_id=ai_drone_id,
        initial_position=[-10.0, 10.0, -10.0]  # AI 드론 시작 위치
    )
    
    # 4. 초기 게임 상태 전송
    await websocket.send_json({
        'type': 'init',
        'client_id': client_id,
        'ai_drone_id': ai_drone_id,
        'obstacles': game_state.obstacles,
        'message': '게임에 접속했습니다!'
    })
    
    # 5. 게임 루프 시작 (첫 클라이언트 접속 시)
    if not game_state.game_loop_running:
        game_state.game_loop_running = True
        asyncio.create_task(game_loop())
    
    try:
        # 6. 클라이언트로부터 메시지 수신 대기
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 플레이어 드론 위치 업데이트 처리
            if message['type'] == 'player_update':
                player_position = message['position']
                game_state.player_positions[client_id] = player_position
                
                # AI 드론 위치 업데이트
                if ai_drone_id in game_state.ai_drones:
                    ai_drone = game_state.ai_drones[ai_drone_id]
                    ai_state = ai_drone.update_position(
                        player_position=player_position,
                        obstacles=game_state.obstacles
                    )
                    
                    # AI 드론의 업데이트된 위치를 클라이언트에 전송
                    await websocket.send_json({
                        'type': 'ai_update',
                        'ai_state': ai_state
                    })
            
            # 핑/퐁 메시지 처리 (연결 유지)
            elif message['type'] == 'ping':
                await websocket.send_json({'type': 'pong'})
                
    except WebSocketDisconnect:
        # 7. 클라이언트 연결 해제 처리
        game_state.connected_clients.remove(websocket)
        if client_id in game_state.player_positions:
            del game_state.player_positions[client_id]
        if ai_drone_id in game_state.ai_drones:
            del game_state.ai_drones[ai_drone_id]
        
        print(f"Client {client_id} disconnected")


async def game_loop():
    """
    게임 메인 루프
    모든 클라이언트에게 주기적으로 게임 상태를 브로드캐스트합니다.
    60 FPS (약 16ms마다 업데이트)를 목표로 합니다.
    """
    print("Game loop started!")
    
    while game_state.game_loop_running:
        try:
            # 게임 상태 수집
            game_update = {
                'type': 'game_state',
                'timestamp': asyncio.get_event_loop().time(),
                'players': game_state.player_positions,
                'ai_drones': {
                    drone_id: {
                        'position': drone.position.tolist(),
                        'velocity': drone.velocity.tolist()
                    }
                    for drone_id, drone in game_state.ai_drones.items()
                }
            }
            
            # 모든 연결된 클라이언트에게 브로드캐스트
            disconnected_clients = []
            for client in game_state.connected_clients:
                try:
                    await client.send_json(game_update)
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    disconnected_clients.append(client)
            
            # 연결 끊긴 클라이언트 제거
            for client in disconnected_clients:
                if client in game_state.connected_clients:
                    game_state.connected_clients.remove(client)
            
            # 60 FPS 유지를 위한 대기 (약 16ms)
            await asyncio.sleep(0.016)
            
        except Exception as e:
            print(f"Game loop error: {e}")
            await asyncio.sleep(0.1)
    
    print("Game loop stopped!")


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚁 3D 드론 AI 대전 시뮬레이터 서버 시작!")
    print("=" * 60)
    print("서버 주소: http://localhost:8000")
    print("WebSocket: ws://localhost:8000/ws")
    print("-" * 60)
    print("브라우저에서 http://localhost:8000 을 열어주세요!")
    print("=" * 60)
    
    # FastAPI 서버 실행
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
