"""
3D 드론 AI 대전 시뮬레이터 - 레벨별 맵 확장 버전
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict
import json
import asyncio
from pathlib import Path
import time
import numpy as np

# 게임 모듈
from ai_drone_advanced import AdvancedAIDrone
from player import Player
from game_mechanics import GameMechanics, CombatSystem
from physics_engine import PhysicsEngine
from map_generator import MapGenerator

app = FastAPI(title="3D Drone Battle Simulator")

class GameState:
    def __init__(self):
        self.connected_clients: Dict[str, WebSocket] = {}
        self.players: Dict[str, Player] = {}
        self.ai_drones: Dict[str, AdvancedAIDrone] = {}
        self.player_maps: Dict[str, Dict] = {}  # 플레이어별 맵 정보
        self.physics_engine = PhysicsEngine()
        self.combat_system = CombatSystem()
        self.game_loop_running = False

game_state = GameState()

def get_difficulty_for_level(level: int) -> str:
    """레벨에 따른 난이도"""
    if level <= 5: return 'easy'
    elif level <= 10: return 'normal'
    elif level <= 20: return 'hard'
    else: return 'extreme'

def get_ai_count_for_level(level: int) -> int:
    """레벨에 따른 AI 수"""
    if level <= 3: return 1
    elif level <= 7: return 2
    elif level <= 15: return 3
    elif level <= 25: return 4
    else: return 5

@app.get("/", response_class=HTMLResponse)
async def serve_game():
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>Frontend not found!</h1></body></html>"

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "players": len(game_state.players),
        "ai_drones": len(game_state.ai_drones),
        "missiles": len(game_state.combat_system.missiles)
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    client_id = f"player_{int(time.time() * 1000)}"
    game_state.connected_clients[client_id] = websocket
    
    # 플레이어 생성
    player = Player(player_id=client_id, username=f"Player_{len(game_state.players) + 1}")
    game_state.players[client_id] = player
    
    # 레벨에 맞는 맵 생성
    map_data = MapGenerator.generate_dynamic_map(player.level)
    game_state.player_maps[client_id] = map_data
    
    # 스폰 위치 설정
    spawn_idx = len(game_state.players) % len(map_data['spawn_points'])
    player.position = map_data['spawn_points'][spawn_idx]
    
    # AI 드론 생성 (레벨 기반)
    difficulty = get_difficulty_for_level(player.level)
    ai_count = get_ai_count_for_level(player.level)
    
    ai_ids = []
    for i in range(ai_count):
        ai_id = f"ai_{client_id}_{i}"
        ai_spawn_idx = (spawn_idx + 4 + i) % len(map_data['spawn_points'])
        ai_spawn = map_data['spawn_points'][ai_spawn_idx]
        
        ai_drone = AdvancedAIDrone(
            drone_id=ai_id,
            initial_position=ai_spawn,
            difficulty=difficulty,
            player_level=player.level  # 레벨 전달!
        )
        game_state.ai_drones[ai_id] = ai_drone
        ai_ids.append(ai_id)
    
    # 초기 데이터 전송
    ai_drones_data = [game_state.ai_drones[ai_id].get_state() for ai_id in ai_ids]
    
    await websocket.send_json({
        'type': 'init',
        'client_id': client_id,
        'ai_ids': ai_ids,
        'obstacles': map_data['obstacles'],
        'map_size': map_data['map_size'],
        'spawn_points': map_data['spawn_points'],
        'player_data': player.to_dict(),
        'ai_drones': ai_drones_data,
        'difficulty': difficulty,
        'ai_count': ai_count,
        'message': f'환영합니다! 맵: {map_data["map_size"]}x{map_data["map_size"]}, AI: {ai_count}대 ({difficulty})'
    })
    
    # 게임 루프 시작
    if not game_state.game_loop_running:
        game_state.game_loop_running = True
        asyncio.create_task(game_loop())
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'player_update':
                if client_id not in game_state.players:
                    continue
                    
                player = game_state.players[client_id]
                player.position = message['position']
                player.velocity = message.get('velocity', [0, 0, 0])
                
                # 장애물 충돌 (맵별로 체크)
                player_map = game_state.player_maps.get(client_id, {})
                obstacles = player_map.get('obstacles', [])
                
                collision = game_state.physics_engine.check_obstacle_collision(
                    player.position, player.velocity, obstacles
                )
                
                if collision.collided and collision.damage > 0:
                    player.take_damage(collision.damage, "obstacle")
                    
                    await websocket.send_json({
                        'type': 'obstacle_collision',
                        'damage': collision.damage,
                        'hp': player.hp,
                        'bounce_velocity': collision.bounce_velocity,
                        'explosion_position': collision.impact_position
                    })
                    
                    if player.hp <= 0:
                        await websocket.send_json({
                            'type': 'player_died',
                            'killer_id': 'obstacle'
                        })
                        asyncio.create_task(respawn_player(client_id, 3.0))
                
                # AI 업데이트 (모든 AI 드론!)
                current_time = time.time()
                ai_updates = []
                
                # client_id에 속한 모든 AI 드론 찾기
                player_ai_drones = {aid: drone for aid, drone in game_state.ai_drones.items() 
                                   if aid.startswith(f"ai_{client_id}_")}
                
                for ai_id, ai_drone in player_ai_drones.items():
                    
                    # AI 물리 충돌 체크 (중요!)
                    ai_collision = game_state.physics_engine.check_obstacle_collision(
                        ai_drone.position.tolist(),
                        ai_drone.velocity.tolist(),
                        obstacles
                    )
                    
                    if ai_collision.collided and ai_collision.damage > 0:
                        ai_drone.take_damage(ai_collision.damage, "obstacle")
                        if ai_collision.bounce_velocity:
                            ai_drone.velocity = np.array(ai_collision.bounce_velocity, dtype=float)
                        
                        # AI 충돌 알림
                        await websocket.send_json({
                            'type': 'ai_collision',
                            'ai_id': ai_id,
                            'damage': ai_collision.damage,
                            'hp': ai_drone.hp,
                            'explosion_position': ai_collision.impact_position
                        })
                    
                    # AI 위치 업데이트
                    ai_state = ai_drone.update_position(
                        player_position=player.position,
                        player_hp=player.hp,
                        obstacles=obstacles,
                        current_time=current_time
                    )
                    
                    # AI 미사일 발사
                    if ai_drone.should_fire_missile(player.position, current_time):
                        direction = ai_drone.get_firing_direction(
                            player.position, player.velocity
                        )
                        
                        # 초고속 미사일
                        missile = game_state.combat_system.create_missile(
                            owner_id=ai_id,
                            position=ai_drone.position.tolist(),
                            direction=direction,
                            damage=ai_drone.missile_damage,
                            speed=15.0  # 초고속!
                        )
                        
                        await websocket.send_json({
                            'type': 'missile_fired',
                            'missile': missile.to_dict(),
                            'owner': 'ai'
                        })
                    
                    ai_updates.append(ai_state)
                
                if ai_updates:
                    await websocket.send_json({
                        'type': 'ai_updates',
                        'ai_states': ai_updates
                    })
            
            elif message['type'] == 'fire_missile':
                if client_id not in game_state.players:
                    continue
                    
                player = game_state.players[client_id]
                current_time = time.time()
                
                if player.fire_missile(current_time):
                    direction = message.get('direction', [0, 0, 1])
                    damage = player.upgrades.get_damage_bonus()
                    
                    # 플레이어 초고속 미사일
                    missile = game_state.combat_system.create_missile(
                        owner_id=client_id,
                        position=player.position,
                        direction=direction,
                        damage=damage,
                        speed=20.0  # 초고속!
                    )
                    
                    await websocket.send_json({
                        'type': 'missile_fired',
                        'success': True,
                        'missile': missile.to_dict(),
                        'owner': 'player'
                    })
                else:
                    await websocket.send_json({
                        'type': 'missile_fired',
                        'success': False,
                        'reason': 'cooldown'
                    })
            
            elif message['type'] == 'upgrade':
                if client_id not in game_state.players:
                    continue
                    
                player = game_state.players[client_id]
                upgrade_type = message.get('upgrade_type')
                cost = player.upgrades.get_upgrade_cost(upgrade_type)
                
                if player.coins >= cost and player.upgrades.upgrade(upgrade_type):
                    player.coins -= cost
                    await websocket.send_json({
                        'type': 'upgrade_result',
                        'success': True,
                        'upgrade_type': upgrade_type,
                        'player_data': player.to_dict()
                    })
                else:
                    await websocket.send_json({
                        'type': 'upgrade_result',
                        'success': False
                    })
            
            elif message['type'] == 'level_up':
                # 레벨업 시 맵 재생성
                if client_id in game_state.players:
                    player = game_state.players[client_id]
                    new_map = MapGenerator.generate_dynamic_map(player.level)
                    game_state.player_maps[client_id] = new_map
                    
                    await websocket.send_json({
                        'type': 'map_expanded',
                        'obstacles': new_map['obstacles'],
                        'map_size': new_map['map_size'],
                        'spawn_points': new_map['spawn_points'],
                        'message': f'맵이 {new_map["map_size"]}x{new_map["map_size"]}로 확장되었습니다!'
                    })
                    
    except WebSocketDisconnect:
        if client_id in game_state.connected_clients:
            del game_state.connected_clients[client_id]
        if client_id in game_state.players:
            del game_state.players[client_id]
        if client_id in game_state.player_maps:
            del game_state.player_maps[client_id]
        
        # AI 드론 제거
        for ai_id in list(game_state.ai_drones.keys()):
            if ai_id.startswith(f"ai_{client_id}"):
                del game_state.ai_drones[ai_id]
        
        print(f"Client {client_id} disconnected")

async def game_loop():
    """게임 메인 루프"""
    print("🎮 Game loop started!")
    
    while game_state.game_loop_running:
        try:
            # 미사일 업데이트
            removed = game_state.combat_system.update_missiles(0.016)
            
            # 충돌 감지
            targets = {}
            
            # 플레이어 타겟
            for player_id, player in game_state.players.items():
                if player.is_alive:
                    targets[player_id] = {
                        'position': player.position,
                        'radius': 2.0
                    }
            
            # AI 타겟
            for ai_id, ai_drone in game_state.ai_drones.items():
                if ai_drone.is_alive:
                    targets[ai_id] = {
                        'position': ai_drone.position.tolist(),
                        'radius': 2.0
                    }
            
            # 충돌 체크
            collisions = game_state.combat_system.check_all_collisions(targets)
            
            for collision in collisions:
                target_id = collision['target_id']
                damage = collision['damage']
                attacker_id = collision['attacker_id']
                
                # 플레이어가 맞음
                if target_id in game_state.players:
                    player = game_state.players[target_id]
                    player.take_damage(damage, attacker_id)
                    
                    if target_id in game_state.connected_clients:
                        await game_state.connected_clients[target_id].send_json({
                            'type': 'damage_taken',
                            'damage': damage,
                            'hp': player.hp,
                            'max_hp': player.max_hp,
                            'attacker_id': attacker_id,
                            'explosion_position': collision['position']
                        })
                        
                        if player.hp <= 0:
                            await game_state.connected_clients[target_id].send_json({
                                'type': 'player_died',
                                'killer_id': attacker_id
                            })
                            asyncio.create_task(respawn_player(target_id, 3.0))
                
                # AI가 맞음
                elif target_id in game_state.ai_drones:
                    ai_drone = game_state.ai_drones[target_id]
                    ai_drone.take_damage(damage, attacker_id)
                    
                    # 공격자가 플레이어면 보상 (미사일 적중 보상!)
                    if attacker_id in game_state.players:
                        player = game_state.players[attacker_id]
                        old_level = player.level
                        player.record_missile_hit()  # 10코인 + 10EXP 즉시 지급!
                        new_level = player.level
                        
                        if attacker_id in game_state.connected_clients:
                            await game_state.connected_clients[attacker_id].send_json({
                                'type': 'hit_confirmed',
                                'target_id': target_id,
                                'damage': damage,
                                'target_hp': ai_drone.hp,
                                'target_max_hp': ai_drone.max_hp,
                                'explosion_position': collision['position'],
                                'coin_reward': 10,
                                'exp_reward': 10,
                                'current_exp': player.experience,
                                'max_exp': player.get_experience_to_next_level()
                            })
                            
                            # 미사일 적중으로 레벨업 확인 + AI 추가
                            if new_level > old_level:
                                new_map = MapGenerator.generate_dynamic_map(new_level)
                                game_state.player_maps[attacker_id] = new_map
                                
                                # 새로운 AI 수 확인
                                old_ai_count = get_ai_count_for_level(old_level)
                                new_ai_count = get_ai_count_for_level(new_level)
                                
                                # AI 추가 생성 (수가 증가한 경우)
                                if new_ai_count > old_ai_count:
                                    new_difficulty = get_difficulty_for_level(new_level)
                                    for i in range(old_ai_count, new_ai_count):
                                        new_ai_id = f"ai_{attacker_id}_{i}"
                                        spawn_idx = (i + 4) % len(new_map['spawn_points'])
                                        new_ai_spawn = new_map['spawn_points'][spawn_idx]
                                        
                                        new_ai_drone = AdvancedAIDrone(
                                            drone_id=new_ai_id,
                                            initial_position=new_ai_spawn,
                                            difficulty=new_difficulty,
                                            player_level=new_level
                                        )
                                        game_state.ai_drones[new_ai_id] = new_ai_drone
                                        
                                        # 새 AI 알림
                                        await game_state.connected_clients[attacker_id].send_json({
                                            'type': 'ai_spawned',
                                            'ai_id': new_ai_id,
                                            'ai_data': new_ai_drone.get_state()
                                        })
                                
                                await game_state.connected_clients[attacker_id].send_json({
                                    'type': 'map_expanded',
                                    'obstacles': new_map['obstacles'],
                                    'map_size': new_map['map_size'],
                                    'spawn_points': new_map['spawn_points'],
                                    'new_level': new_level,
                                    'ai_count': new_ai_count,
                                    'message': f'🎉 레벨 {new_level}! 맵: {new_map["map_size"]}x{new_map["map_size"]}, AI: {new_ai_count}대'
                                })
                        
                        # AI 사망
                        if ai_drone.hp <= 0:
                            old_level = player.level
                            kill_reward = player.record_kill(target_id)  # 100코인 지급!
                            new_level = player.level
                            
                            if attacker_id in game_state.connected_clients:
                                await game_state.connected_clients[attacker_id].send_json({
                                    'type': 'kill_confirmed',
                                    'target_id': target_id,
                                    'rewards': kill_reward,
                                    'player_data': player.to_dict()
                                })
                                
                                # 레벨업 확인 및 맵 확장 + AI 추가!
                                if new_level > old_level:
                                    new_map = MapGenerator.generate_dynamic_map(new_level)
                                    game_state.player_maps[attacker_id] = new_map
                                    
                                    # 새로운 AI 수 확인
                                    old_ai_count = get_ai_count_for_level(old_level)
                                    new_ai_count = get_ai_count_for_level(new_level)
                                    
                                    # AI 추가 생성 (수가 증가한 경우)
                                    if new_ai_count > old_ai_count:
                                        new_difficulty = get_difficulty_for_level(new_level)
                                        for i in range(old_ai_count, new_ai_count):
                                            new_ai_id = f"ai_{attacker_id}_{i}"
                                            spawn_idx = (i + 4) % len(new_map['spawn_points'])
                                            new_ai_spawn = new_map['spawn_points'][spawn_idx]
                                            
                                            new_ai_drone = AdvancedAIDrone(
                                                drone_id=new_ai_id,
                                                initial_position=new_ai_spawn,
                                                difficulty=new_difficulty,
                                                player_level=new_level
                                            )
                                            game_state.ai_drones[new_ai_id] = new_ai_drone
                                            
                                            # 새 AI 알림
                                            await game_state.connected_clients[attacker_id].send_json({
                                                'type': 'ai_spawned',
                                                'ai_id': new_ai_id,
                                                'ai_data': new_ai_drone.get_state()
                                            })
                                    
                                    await game_state.connected_clients[attacker_id].send_json({
                                        'type': 'map_expanded',
                                        'obstacles': new_map['obstacles'],
                                        'map_size': new_map['map_size'],
                                        'spawn_points': new_map['spawn_points'],
                                        'new_level': new_level,
                                        'ai_count': new_ai_count,
                                        'message': f'🎉 레벨 {new_level}! 맵: {new_map["map_size"]}x{new_map["map_size"]}, AI: {new_ai_count}대'
                                    })
                            
                            asyncio.create_task(respawn_ai(target_id, 5.0))
            
            # 모든 미사일 상태 브로드캐스트
            all_missiles = game_state.combat_system.get_all_missiles()
            
            for client_id, websocket in list(game_state.connected_clients.items()):
                try:
                    await websocket.send_json({
                        'type': 'game_state',
                        'missiles': all_missiles,
                        'timestamp': time.time()
                    })
                except:
                    pass
            
            await asyncio.sleep(0.016)  # 60 FPS
            
        except Exception as e:
            print(f"Game loop error: {e}")
            await asyncio.sleep(0.1)

async def respawn_player(player_id: str, delay: float):
    await asyncio.sleep(delay)
    if player_id in game_state.players and player_id in game_state.player_maps:
        player = game_state.players[player_id]
        spawn_points = game_state.player_maps[player_id]['spawn_points']
        spawn_idx = hash(player_id) % len(spawn_points)
        player.position = spawn_points[spawn_idx]
        player.respawn()
        
        if player_id in game_state.connected_clients:
            await game_state.connected_clients[player_id].send_json({
                'type': 'respawned',
                'player_data': player.to_dict()
            })

async def respawn_ai(ai_id: str, delay: float):
    await asyncio.sleep(delay)
    if ai_id in game_state.ai_drones:
        # AI의 소유자 찾기
        owner_and_index = ai_id[3:]
        owner_id = owner_and_index.rsplit('_', 1)[0]
        
        if owner_id in game_state.player_maps:
            ai_drone = game_state.ai_drones[ai_id]
            spawn_points = game_state.player_maps[owner_id]['spawn_points']
            spawn_idx = (hash(ai_id) + 4) % len(spawn_points)
            ai_drone.respawn(spawn_points[spawn_idx])
            
            if owner_id in game_state.connected_clients:
                await game_state.connected_clients[owner_id].send_json({
                    'type': 'ai_respawned',
                    'ai_id': ai_id,
                    'ai_data': ai_drone.get_state()
                })

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("🚁 3D 드론 AI 대전 시뮬레이터 - 최종 버전")
    print("=" * 70)
    print("✨ 새로운 기능:")
    print("  - ✅ 레벨별 맵 확장 (200~600)")
    print("  - ✅ 초고속 미사일 (15~20)")
    print("  - ✅ AI 킬 100코인")
    print("  - ✅ 미사일 적중 10코인+10EXP")
    print("  - ✅ AI 충돌 데미지")
    print("  - ✅ 충돌 박스 개선")
    print("=" * 70)
    print("서버: http://localhost:8000")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
