"""
3D 드론 AI 대전 시뮬레이터 - 백엔드 서버 (고도화)
전투 시스템, 물리 엔진, AI 고도화를 포함합니다.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict
import json
import asyncio
from pathlib import Path
import time

# 게임 모듈 임포트
from ai_drone_advanced import AdvancedAIDrone
from player import Player
from game_mechanics import GameMechanics
from physics_engine import PhysicsEngine
from map_generator import MapGenerator

# FastAPI 앱 초기화
app = FastAPI(title="3D Drone AI Battle Simulator - Advanced")

# 게임 상태 관리
class GameState:
    """게임 상태를 관리하는 클래스"""
    
    def __init__(self):
        self.connected_clients: Dict[str, WebSocket] = {}
        self.players: Dict[str, Player] = {}
        self.ai_drones: Dict[str, AdvancedAIDrone] = {}
        self.obstacles: List[Dict] = MapGenerator.generate_large_map(size=200, obstacle_count=35)
        self.spawn_points = MapGenerator.get_spawn_points(map_size=200, count=8)
        self.game_mechanics = GameMechanics()
        self.physics_engine = PhysicsEngine()
        self.game_loop_running = False
        self.match_start_time = time.time()

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
        return "<html><body><h1>Frontend file not found!</h1></body></html>"


@app.get("/health")
async def health_check():
    """서버 상태 확인용 엔드포인트"""
    return {
        "status": "healthy",
        "connected_clients": len(game_state.connected_clients),
        "active_players": len(game_state.players),
        "ai_drones": len(game_state.ai_drones),
        "active_missiles": len(game_state.game_mechanics.combat_system.missiles),
        "map_size": "200x200",
        "obstacles": len(game_state.obstacles)
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
    
    # 스폰 포인트에서 시작
    spawn_point = game_state.spawn_points[len(game_state.players) % len(game_state.spawn_points)]
    player.position = spawn_point
    
    game_state.players[client_id] = player
    
    # AI 드론 생성 (난이도 선택 가능)
    ai_drone_id = f"ai_{client_id}"
    ai_spawn = game_state.spawn_points[(len(game_state.players) + 4) % len(game_state.spawn_points)]
    
    ai_drone = AdvancedAIDrone(
        drone_id=ai_drone_id,
        initial_position=ai_spawn,
        difficulty='normal'  # 기본 난이도
    )
    game_state.ai_drones[ai_drone_id] = ai_drone
    
    # 게임 메커니즘에 등록
    game_state.game_mechanics.register_player(client_id, {
        'position': player.position,
        'is_alive': player.is_alive
    })
    
    # **버그 수정: AI 드론도 게임 메커니즘에 등록**
    game_state.game_mechanics.register_player(ai_drone_id, {
        'position': ai_drone.position.tolist(),
        'is_alive': ai_drone.is_alive
    })
    
    # 초기 게임 상태 전송
    await websocket.send_json({
        'type': 'init',
        'client_id': client_id,
        'ai_drone_id': ai_drone_id,
        'obstacles': game_state.obstacles,
        'player_data': player.to_dict(),
        'ai_data': ai_drone.get_state(),
        'map_size': 200,
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
                    
                    # **물리적 충돌 체크 (장애물)**
                    collision_result = game_state.physics_engine.check_obstacle_collision(
                        player.position,
                        player.velocity,
                        game_state.obstacles
                    )
                    
                    if collision_result.collided and collision_result.damage > 0:
                        # 장애물 충돌 데미지
                        damage_result = player.take_damage(collision_result.damage, "obstacle")
                        
                        await websocket.send_json({
                            'type': 'obstacle_collision',
                            'damage': collision_result.damage,
                            'hp': player.hp,
                            'impact_speed': collision_result.impact_speed,
                            'bounce_velocity': collision_result.bounce_velocity,
                            'explosion_position': collision_result.impact_position
                        })
                        
                        if damage_result.get('died'):
                            await websocket.send_json({
                                'type': 'player_died',
                                'killer_id': 'obstacle',
                                'cause': 'collision'
                            })
                            asyncio.create_task(respawn_player(client_id, 3.0))
                    
                    # AI 드론 위치 업데이트
                    if ai_drone_id in game_state.ai_drones:
                        ai_drone = game_state.ai_drones[ai_drone_id]
                        current_time = time.time()
                        
                        ai_state = ai_drone.update_position(
                            player_position=player.position,
                            player_hp=player.hp,
                            obstacles=game_state.obstacles,
                            current_time=current_time
                        )
                        
                        # **버그 수정: AI 위치를 게임 메커니즘에도 업데이트**
                        game_state.game_mechanics.update_player_position(
                            ai_drone_id, 
                            ai_drone.position.tolist()
                        )
                        
                        # AI 미사일 발사 결정
                        if ai_drone.should_fire_missile(player.position, current_time):
                            firing_direction = ai_drone.get_firing_direction(
                                player.position,
                                player.velocity
                            )
                            
                            missile = game_state.game_mechanics.combat_system.create_missile(
                                owner_id=ai_drone_id,
                                position=ai_drone.position.tolist(),
                                direction=firing_direction,
                                damage=ai_drone.missile_damage,
                                speed=2.5
                            )
                            
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
                        direction = message.get('direction', [0, 0, 1])
                        damage = player.upgrades.get_damage_bonus()
                        
                        missile = game_state.game_mechanics.combat_system.create_missile(
                            owner_id=client_id,
                            position=player.position,
                            direction=direction,
                            damage=damage,
                            speed=2.8
                        )
                        
                        await websocket.send_json({
                            'type': 'missile_fired',
                            'success': True,
                            'missile': missile.to_dict()
                        })
                    else:
                        await websocket.send_json({
                            'type': 'missile_fired',
                            'success': False,
                            'reason': 'cooldown'
                        })
            
            # AI 난이도 변경
            elif message['type'] == 'change_difficulty':
                difficulty = message.get('difficulty', 'normal')
                if ai_drone_id in game_state.ai_drones:
                    # 새 AI 드론 생성
                    ai_drone = AdvancedAIDrone(
                        drone_id=ai_drone_id,
                        initial_position=game_state.ai_drones[ai_drone_id].position.tolist(),
                        difficulty=difficulty
                    )
                    game_state.ai_drones[ai_drone_id] = ai_drone
                    
                    await websocket.send_json({
                        'type': 'difficulty_changed',
                        'difficulty': difficulty,
                        'ai_data': ai_drone.get_state()
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
        game_state.game_mechanics.unregister_player(ai_drone_id)
        
        print(f"Client {client_id} disconnected")


async def game_loop():
    """
    게임 메인 루프
    전투, 충돌 감지, 물리 시뮬레이션을 관리합니다.
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
                    
                    if target_id in game_state.connected_clients:
                        await game_state.connected_clients[target_id].send_json({
                            'type': 'damage_taken',
                            'damage': damage,
                            'hp': player.hp,
                            'max_hp': player.max_hp,
                            'attacker_id': attacker_id,
                            'explosion_position': collision['position']
                        })
                    
                    if damage_result.get('died'):
                        if attacker_id in game_state.ai_drones:
                            ai_drone = game_state.ai_drones[attacker_id]
                            ai_drone.kills += 1
                        
                        if target_id in game_state.connected_clients:
                            await game_state.connected_clients[target_id].send_json({
                                'type': 'player_died',
                                'killer_id': attacker_id
                            })
                        
                        asyncio.create_task(respawn_player(target_id, 3.0))
                
                # **버그 수정: AI가 맞은 경우 (제대로 처리)**
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
                                'target_max_hp': ai_drone.max_hp,
                                'explosion_position': collision['position']
                            })
                    
                    # AI 사망 처리
                    if damage_result.get('died'):
                        if attacker_id in game_state.players:
                            player = game_state.players[attacker_id]
                            kill_reward = player.record_kill(target_id)
                            
                            if attacker_id in game_state.connected_clients:
                                await game_state.connected_clients[attacker_id].send_json({
                                    'type': 'kill_confirmed',
                                    'target_id': target_id,
                                    'rewards': kill_reward,
                                    'player_data': player.to_dict()
                                })
                        
                        asyncio.create_task(respawn_ai(target_id, 5.0))
            
            # 게임 상태 브로드캐스트
            game_update = {
                'type': 'game_state',
                'timestamp': current_time,
                'missiles': mechanics_update['active_missiles'],
                'match_duration': game_state.game_mechanics.get_match_duration()
            }
            
            disconnected_clients = []
            for client_id, websocket in game_state.connected_clients.items():
                try:
                    await websocket.send_json(game_update)
                except Exception as e:
                    disconnected_clients.append(client_id)
            
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
        # 랜덤 스폰 포인트
        spawn_point = game_state.spawn_points[hash(player_id) % len(game_state.spawn_points)]
        player.position = spawn_point
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
        # 랜덤 스폰 포인트
        spawn_point = game_state.spawn_points[(hash(ai_id) + 4) % len(game_state.spawn_points)]
        ai_drone.respawn(spawn_point)
        
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
    
    print("=" * 70)
    print("🚁 3D 드론 AI 대전 시뮬레이터 서버 시작! (고도화 버전)")
    print("=" * 70)
    print("✨ 새로운 기능:")
    print("  - ⚔️  전투 시스템 (미사일 발사 & 충돌 감지)")
    print("  - 💥 물리 엔진 (장애물 충돌 시 데미지)")
    print("  - 🗺️  대형 맵 (200x200, 35+ 장애물)")
    print("  - 🤖 AI 고도화 (4가지 난이도, 다양한 행동 패턴)")
    print("  - 💯 점수 & 레벨 시스템")
    print("  - 🏆 티어 시스템 (브론즈 ~ 레전드)")
    print("  - 💪 업그레이드 시스템")
    print("=" * 70)
    print("서버 주소: http://localhost:8000")
    print("WebSocket: ws://localhost:8000/ws")
    print("-" * 70)
    print("브라우저에서 http://localhost:8000 을 열어주세요!")
    print("=" * 70)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
