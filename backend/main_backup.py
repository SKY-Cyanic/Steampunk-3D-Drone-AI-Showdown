"""
3D 드론 AI 대전 시뮬레이터 - 백엔드 서버
FastAPI와 WebSocket을 사용하여 실시간 게임 서버를 구현합니다.
전투 시스템, 점수 시스템, 티어 시스템을 포함합니다.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict
import json
import asyncio
from pathlib import Path
import time

# 게임 모듈 임포트
from ai_drone import AIDrone
from player import Player
from game_mechanics import GameMechanics

# FastAPI 앱 초기화
app = FastAPI(title="3D Drone AI Battle Simulator")

# 게임 상태 관리를 위한 전역 변수
class GameState:
    """게임 상태를 관리하는 클래스"""
    
    def __init__(self):
        self.connected_clients: Dict[str, WebSocket] = {}  # {client_id: websocket}
        self.players: Dict[str, Player] = {}  # {player_id: Player 객체}
        self.ai_drones: Dict[str, AIDrone] = {}  # {ai_id: AIDrone 객체}
        self.obstacles: List[Dict] = self._initialize_obstacles()
        self.game_mechanics = GameMechanics()
        self.game_loop_running = False
        self.match_start_time = time.time()
        
    def _initialize_obstacles(self) -> List[Dict]:
        """
        스팀펑크 스타일의 장애물 초기화
        """
        return [
            {'type': 'gear', 'position': [15, 5, 10], 'rotation': 0, 'size': [4, 1, 4]},
            {'type': 'gear', 'position': [-20, 8, -15], 'rotation': 0, 'size': [5, 1, 5]},
            {'type': 'pipe', 'position': [0, 10, 0], 'rotation': 0, 'size': [2, 15, 2]},
            {'type': 'pipe', 'position': [25, 7, -20], 'rotation': 90, 'size': [2, 20, 2]},
            {'type': 'gear', 'position': [-10, 3, 20], 'rotation': 0, 'size': [3, 1, 3]}
        ]

# 전역 게임 상태 객체
game_state = GameState()


@app.get("/", response_class=HTMLResponse)
async def serve_game():
    """게임 HTML 페이지 제공"""
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
        "active_players": len(game_state.players),
        "ai_drones": len(game_state.ai_drones),
        "active_missiles": len(game_state.game_mechanics.combat_system.missiles)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 연결 처리
    플레이어와 AI 드론 간의 실시간 전투를 관리합니다.
    """
    await websocket.accept()
    
    # 클라이언트 ID 생성
    client_id = f"player_{int(time.time() * 1000)}"
    game_state.connected_clients[client_id] = websocket
    
    # 플레이어 객체 생성
    player = Player(player_id=client_id, username=f"Player_{len(game_state.players) + 1}")
    game_state.players[client_id] = player
    
    # AI 드론 생성
    ai_drone_id = f"ai_{client_id}"
    ai_drone = AIDrone(
        drone_id=ai_drone_id,
        initial_position=[-10.0, 10.0, -10.0],
        difficulty='normal'  # 난이도: easy, normal, hard
    )
    game_state.ai_drones[ai_drone_id] = ai_drone
    
    # 게임 메커니즘에 플레이어 등록
    game_state.game_mechanics.register_player(client_id, {
        'position': player.position,
        'is_alive': player.is_alive
    })
    
    # 초기 게임 상태 전송
    await websocket.send_json({
        'type': 'init',
        'client_id': client_id,
        'ai_drone_id': ai_drone_id,
        'obstacles': game_state.obstacles,
        'player_data': player.to_dict(),
        'ai_data': ai_drone.get_state(),
        'message': f'{player.username}님, 게임에 오신 것을 환영합니다!'
    })
    
    # 게임 루프 시작
    if not game_state.game_loop_running:
        game_state.game_loop_running = True
        asyncio.create_task(game_loop())
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 플레이어 위치 업데이트
            if message['type'] == 'player_update':
                if client_id in game_state.players:
                    player = game_state.players[client_id]
                    player.position = message['position']
                    player.velocity = message.get('velocity', [0, 0, 0])
                    
                    # 게임 메커니즘 업데이트
                    game_state.game_mechanics.update_player_position(client_id, player.position)
                    
                    # AI 드론 위치 업데이트
                    if ai_drone_id in game_state.ai_drones:
                        ai_drone = game_state.ai_drones[ai_drone_id]
                        ai_state = ai_drone.update_position(
                            player_position=player.position,
                            obstacles=game_state.obstacles
                        )
                        
                        # AI가 미사일 발사 결정
                        current_time = time.time()
                        if ai_drone.should_fire_missile(player.position, current_time):
                            # AI 미사일 발사
                            firing_direction = ai_drone.get_firing_direction(
                                player.position,
                                player.velocity
                            )
                            
                            missile = game_state.game_mechanics.combat_system.create_missile(
                                owner_id=ai_drone_id,
                                position=ai_drone.position.tolist(),
                                direction=firing_direction,
                                damage=ai_drone.missile_damage,
                                speed=2.0
                            )
                            
                            # 클라이언트에 AI 미사일 발사 알림
                            await websocket.send_json({
                                'type': 'ai_missile_fired',
                                'missile': missile.to_dict()
                            })
                        
                        # AI 상태 전송
                        await websocket.send_json({
                            'type': 'ai_update',
                            'ai_state': ai_state
                        })
            
            # 플레이어 미사일 발사
            elif message['type'] == 'fire_missile':
                if client_id in game_state.players:
                    player = game_state.players[client_id]
                    current_time = time.time()
                    
                    if player.fire_missile(current_time):
                        # 미사일 생성
                        direction = message.get('direction', [0, 0, 1])
                        damage = player.upgrades.get_damage_bonus()
                        
                        missile = game_state.game_mechanics.combat_system.create_missile(
                            owner_id=client_id,
                            position=player.position,
                            direction=direction,
                            damage=damage,
                            speed=2.5
                        )
                        
                        # 발사 성공 응답
                        await websocket.send_json({
                            'type': 'missile_fired',
                            'success': True,
                            'missile': missile.to_dict()
                        })
                    else:
                        # 쿨다운 중
                        await websocket.send_json({
                            'type': 'missile_fired',
                            'success': False,
                            'reason': 'cooldown'
                        })
            
            # 업그레이드 요청
            elif message['type'] == 'upgrade':
                if client_id in game_state.players:
                    player = game_state.players[client_id]
                    upgrade_type = message.get('upgrade_type')
                    cost = player.upgrades.get_upgrade_cost(upgrade_type)
                    
                    if player.coins >= cost:
                        if player.upgrades.upgrade(upgrade_type):
                            player.coins -= cost
                            
                            # 업그레이드 성공
                            await websocket.send_json({
                                'type': 'upgrade_result',
                                'success': True,
                                'upgrade_type': upgrade_type,
                                'player_data': player.to_dict()
                            })
                        else:
                            await websocket.send_json({
                                'type': 'upgrade_result',
                                'success': False,
                                'reason': 'max_level'
                            })
                    else:
                        await websocket.send_json({
                            'type': 'upgrade_result',
                            'success': False,
                            'reason': 'insufficient_coins'
                        })
            
            # 핑/퐁
            elif message['type'] == 'ping':
                await websocket.send_json({'type': 'pong'})
                
    except WebSocketDisconnect:
        # 클라이언트 연결 해제
        if client_id in game_state.connected_clients:
            del game_state.connected_clients[client_id]
        if client_id in game_state.players:
            del game_state.players[client_id]
        if ai_drone_id in game_state.ai_drones:
            del game_state.ai_drones[ai_drone_id]
        
        game_state.game_mechanics.unregister_player(client_id)
        
        print(f"Client {client_id} disconnected")


async def game_loop():
    """
    게임 메인 루프
    전투, 충돌 감지, 게임 상태 업데이트를 관리합니다.
    """
    print("🎮 Game loop started!")
    
    while game_state.game_loop_running:
        try:
            current_time = time.time()
            
            # 게임 메커니즘 업데이트
            mechanics_update = game_state.game_mechanics.update(0.016)
            
            # 충돌 처리
            for collision in mechanics_update['collisions']:
                missile_id = collision['missile_id']
                target_id = collision['target_id']
                damage = collision['damage']
                attacker_id = collision['attacker_id']
                
                # 플레이어가 맞은 경우
                if target_id in game_state.players:
                    player = game_state.players[target_id]
                    damage_result = player.take_damage(damage, attacker_id)
                    
                    # 플레이어에게 데미지 알림
                    if target_id in game_state.connected_clients:
                        await game_state.connected_clients[target_id].send_json({
                            'type': 'damage_taken',
                            'damage': damage,
                            'hp': player.hp,
                            'max_hp': player.max_hp,
                            'attacker_id': attacker_id,
                            'explosion_position': collision['position']
                        })
                    
                    # 플레이어 사망 처리
                    if damage_result.get('died'):
                        # AI가 킬한 경우
                        if attacker_id in game_state.ai_drones:
                            ai_drone = game_state.ai_drones[attacker_id]
                            ai_drone.kills += 1
                        
                        # 사망 알림
                        if target_id in game_state.connected_clients:
                            await game_state.connected_clients[target_id].send_json({
                                'type': 'player_died',
                                'killer_id': attacker_id
                            })
                        
                        # 3초 후 리스폰
                        asyncio.create_task(respawn_player(target_id, 3.0))
                
                # AI가 맞은 경우
                elif target_id in game_state.ai_drones:
                    ai_drone = game_state.ai_drones[target_id]
                    damage_result = ai_drone.take_damage(damage, attacker_id)
                    
                    # 공격자가 플레이어인 경우
                    if attacker_id in game_state.players:
                        player = game_state.players[attacker_id]
                        player.record_missile_hit()
                        player.deal_damage(target_id, damage)
                        
                        # 명중 알림
                        if attacker_id in game_state.connected_clients:
                            await game_state.connected_clients[attacker_id].send_json({
                                'type': 'hit_confirmed',
                                'target_id': target_id,
                                'damage': damage,
                                'target_hp': ai_drone.hp,
                                'explosion_position': collision['position']
                            })
                    
                    # AI 사망 처리
                    if damage_result.get('died'):
                        # 플레이어가 킬한 경우
                        if attacker_id in game_state.players:
                            player = game_state.players[attacker_id]
                            kill_reward = player.record_kill(target_id)
                            
                            # 킬 보상 알림
                            if attacker_id in game_state.connected_clients:
                                await game_state.connected_clients[attacker_id].send_json({
                                    'type': 'kill_confirmed',
                                    'target_id': target_id,
                                    'rewards': kill_reward,
                                    'player_data': player.to_dict()
                                })
                        
                        # AI 리스폰
                        asyncio.create_task(respawn_ai(target_id, 5.0))
            
            # 게임 상태 브로드캐스트
            game_update = {
                'type': 'game_state',
                'timestamp': current_time,
                'missiles': mechanics_update['active_missiles'],
                'match_duration': game_state.game_mechanics.get_match_duration()
            }
            
            # 모든 클라이언트에게 전송
            disconnected_clients = []
            for client_id, websocket in game_state.connected_clients.items():
                try:
                    await websocket.send_json(game_update)
                except Exception as e:
                    print(f"Error sending to {client_id}: {e}")
                    disconnected_clients.append(client_id)
            
            # 연결 끊긴 클라이언트 제거
            for client_id in disconnected_clients:
                if client_id in game_state.connected_clients:
                    del game_state.connected_clients[client_id]
            
            # 60 FPS 유지
            await asyncio.sleep(0.016)
            
        except Exception as e:
            print(f"Game loop error: {e}")
            await asyncio.sleep(0.1)
    
    print("Game loop stopped!")


async def respawn_player(player_id: str, delay: float):
    """플레이어 리스폰"""
    await asyncio.sleep(delay)
    
    if player_id in game_state.players:
        player = game_state.players[player_id]
        player.respawn()
        
        if player_id in game_state.connected_clients:
            await game_state.connected_clients[player_id].send_json({
                'type': 'respawned',
                'player_data': player.to_dict(),
                'message': '리스폰되었습니다!'
            })


async def respawn_ai(ai_id: str, delay: float):
    """AI 드론 리스폰"""
    await asyncio.sleep(delay)
    
    if ai_id in game_state.ai_drones:
        ai_drone = game_state.ai_drones[ai_id]
        ai_drone.respawn()
        
        # AI 소유자에게 알림
        owner_id = ai_id.replace('ai_', '')
        if owner_id in game_state.connected_clients:
            await game_state.connected_clients[owner_id].send_json({
                'type': 'ai_respawned',
                'ai_data': ai_drone.get_state(),
                'message': 'AI 드론이 리스폰되었습니다!'
            })


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚁 3D 드론 AI 대전 시뮬레이터 서버 시작!")
    print("=" * 60)
    print("✨ 새로운 기능:")
    print("  - ⚔️  전투 시스템 (미사일 발사 & 충돌 감지)")
    print("  - 💯 점수 & 레벨 시스템")
    print("  - 🏆 티어 시스템 (브론즈 ~ 레전드)")
    print("  - 💪 업그레이드 시스템")
    print("=" * 60)
    print("서버 주소: http://localhost:8000")
    print("WebSocket: ws://localhost:8000/ws")
    print("-" * 60)
    print("브라우저에서 http://localhost:8000 을 열어주세요!")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
