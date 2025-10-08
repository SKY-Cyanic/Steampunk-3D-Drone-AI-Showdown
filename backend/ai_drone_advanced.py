"""
고도화된 AI 드론 로직 모듈
다양한 행동 패턴과 전략을 구사하는 지능형 AI
"""

import torch
import numpy as np
from typing import Dict, List, Tuple
import time


class AdvancedAIDrone:
    """
    고도화된 AI 드론 클래스
    다양한 행동 패턴 (공격/방어/회피)과 전략적 의사결정을 수행합니다.
    """
    
    def __init__(self, drone_id: str, initial_position: List[float], difficulty: str = 'normal', player_level: int = 1):
        """
        AI 드론 초기화
        
        Args:
            drone_id: 드론의 고유 ID
            initial_position: 초기 위치 [x, y, z]
            difficulty: 난이도 ('easy', 'normal', 'hard', 'extreme')
            player_level: 플레이어 레벨 (스케일링용)
        """
        self.drone_id = drone_id
        self.position = np.array(initial_position, dtype=float)
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=float)
        
        # 레벨 정보
        self.player_level = player_level
        
        # 난이도 설정
        self.difficulty = difficulty
        self._apply_difficulty_settings()
        
        # 레벨 스케일링 적용
        self._apply_level_scaling()
        
        # 전투 관련 속성 (레벨 스케일링 후 설정됨)
        self.is_alive = True
        self.last_missile_time = 0
        self.missile_cooldown = 1.5
        self.attack_range = 35.0
        
        # 통계
        self.kills = 0
        self.damage_dealt = 0
        self.missiles_fired = 0
        
        # AI 행동 상태
        self.behavior_mode = 'aggressive'  # aggressive, defensive, evasive
        self.last_behavior_change = 0
        self.behavior_change_interval = 3.0
        
        # 회피 기동
        self.evasive_maneuver_active = False
        self.evasive_maneuver_timer = 0
        self.evasive_direction = np.array([0.0, 0.0, 0.0], dtype=float)
        
        # 학습 메모리 (간단한 강화학습)
        self.memory = {
            'successful_attacks': 0,
            'avoided_damage': 0,
            'total_encounters': 0
        }
        
        # PyTorch 신경망
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._build_simple_network()
        
    def _apply_difficulty_settings(self) -> None:
        """난이도에 따른 설정 적용"""
        difficulty_settings = {
            'easy': {
                'max_speed': 0.25,
                'acceleration': 0.04,
                'reaction_time': 0.8,
                'aim_accuracy': 0.5,
                'hp_multiplier': 0.8,
                'aggression': 0.3
            },
            'normal': {
                'max_speed': 0.35,
                'acceleration': 0.06,
                'reaction_time': 0.5,
                'aim_accuracy': 0.75,
                'hp_multiplier': 1.0,
                'aggression': 0.6
            },
            'hard': {
                'max_speed': 0.45,
                'acceleration': 0.08,
                'reaction_time': 0.3,
                'aim_accuracy': 0.9,
                'hp_multiplier': 1.3,
                'aggression': 0.8
            },
            'extreme': {
                'max_speed': 0.6,
                'acceleration': 0.12,
                'reaction_time': 0.15,
                'aim_accuracy': 0.98,
                'hp_multiplier': 1.6,
                'aggression': 1.0
            }
        }
        
        settings = difficulty_settings.get(self.difficulty, difficulty_settings['normal'])
        self.max_speed = settings['max_speed']
        self.acceleration = settings['acceleration']
        self.reaction_time = settings['reaction_time']
        self.aim_accuracy = settings['aim_accuracy']
        self.aggression = settings['aggression']
        # 기본 HP와 데미지 (레벨 스케일링 전)
        self.base_max_hp = int(100 * settings['hp_multiplier'])
        self.base_missile_damage = 20
        
    def _apply_level_scaling(self) -> None:
        """플레이어 레벨에 따른 AI 능력치 스케일링"""
        level = self.player_level
        
        # 레벨당 HP 증가: 레벨 1 = 100%, 레벨 10 = 180%, 레벨 20 = 260%
        hp_scaling = 1.0 + (level - 1) * 0.08  # 레벨당 8% 증가
        self.max_hp = int(self.base_max_hp * hp_scaling)
        self.hp = self.max_hp
        
        # 레벨당 데미지 증가: 레벨 1 = 20, 레벨 10 = 32, 레벨 20 = 46
        damage_scaling = 1.0 + (level - 1) * 0.06  # 레벨당 6% 증가
        self.missile_damage = int(self.base_missile_damage * damage_scaling)
        
        print(f"🤖 AI 드론 생성: 레벨 {level} | HP {self.max_hp} | 데미지 {self.missile_damage}")
        
    def _build_simple_network(self) -> torch.nn.Module:
        """간단한 신경망 구조 정의 (강화학습용)"""
        class DecisionNetwork(torch.nn.Module):
            def __init__(self):
                super(DecisionNetwork, self).__init__()
                self.fc1 = torch.nn.Linear(12, 64)  # 확장된 입력
                self.fc2 = torch.nn.Linear(64, 32)
                self.fc3 = torch.nn.Linear(32, 16)
                self.fc4 = torch.nn.Linear(16, 4)  # 4가지 행동
                
            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = torch.relu(self.fc2(x))
                x = torch.relu(self.fc3(x))
                x = torch.softmax(self.fc4(x), dim=-1)
                return x
        
        return DecisionNetwork().to(self.device)
    
    def decide_behavior(self, player_position: List[float], player_hp: int, current_time: float) -> None:
        """
        상황에 따라 행동 패턴 결정
        HP, 거리, 상대 HP 등을 고려
        """
        if current_time - self.last_behavior_change < self.behavior_change_interval:
            return
        
        target_pos = np.array(player_position, dtype=float)
        distance = np.linalg.norm(target_pos - self.position)
        hp_ratio = self.hp / self.max_hp
        player_hp_ratio = player_hp / 100.0
        
        # 전략적 의사결정
        if hp_ratio < 0.25:
            # 매우 낮은 HP: 무조건 회피
            self.behavior_mode = 'evasive'
            self.activate_evasive_maneuver()
        elif hp_ratio < 0.5:
            if player_hp_ratio < 0.3:
                # 상대도 약하면 공격
                self.behavior_mode = 'aggressive'
            else:
                # 방어적
                self.behavior_mode = 'defensive'
        else:
            # HP가 높을 때
            if distance < 15:
                # 가까우면 공격
                self.behavior_mode = 'aggressive'
            elif player_hp_ratio < 0.5:
                # 상대가 약하면 적극적
                self.behavior_mode = 'aggressive'
            else:
                # 난이도에 따른 기본 성향
                if np.random.random() < self.aggression:
                    self.behavior_mode = 'aggressive'
                else:
                    self.behavior_mode = 'defensive'
        
        self.last_behavior_change = current_time
        self.memory['total_encounters'] += 1
    
    def activate_evasive_maneuver(self) -> None:
        """긴급 회피 기동 활성화"""
        if not self.evasive_maneuver_active:
            self.evasive_maneuver_active = True
            self.evasive_maneuver_timer = 2.5
            
            # 랜덤 회피 방향 (위로 도망)
            self.evasive_direction = np.random.randn(3).astype(float)
            self.evasive_direction[1] = abs(self.evasive_direction[1]) * 2  # 위로 크게
            length = np.linalg.norm(self.evasive_direction)
            if length > 0:
                self.evasive_direction = self.evasive_direction / length
    
    def update_position(self, player_position: List[float], player_hp: int, obstacles: List[Dict], 
                       current_time: float = None, delta_time: float = 0.016) -> Dict:
        """
        AI 드론 위치 업데이트 (고도화된 로직)
        """
        if not self.is_alive:
            return self.get_state()
        
        # 행동 패턴 결정
        if current_time:
            self.decide_behavior(player_position, player_hp, current_time)
        
        # 회피 기동 타이머
        if self.evasive_maneuver_active:
            self.evasive_maneuver_timer -= delta_time
            if self.evasive_maneuver_timer <= 0:
                self.evasive_maneuver_active = False
        
        # 플레이어 방향 계산
        target_position = np.array(player_position, dtype=float)
        direction_to_player = target_position - self.position
        distance_to_player = np.linalg.norm(direction_to_player)
        
        if distance_to_player > 0.1:
            direction_normalized = direction_to_player / distance_to_player
            
            # 행동 패턴별 이동 로직
            if self.behavior_mode == 'aggressive':
                # 공격적: 적절한 거리에서 스트레이핑
                optimal_distance = 18.0
                if distance_to_player > optimal_distance:
                    desired_velocity = direction_normalized * self.max_speed
                else:
                    # 옆으로 이동하며 공격 위치 선점
                    perpendicular = np.array([-direction_normalized[2], 0.2, direction_normalized[0]])
                    desired_velocity = perpendicular * self.max_speed * 0.9
                    
            elif self.behavior_mode == 'defensive':
                # 방어적: 거리 유지하며 기회 엿보기
                safe_distance = 25.0
                if distance_to_player < safe_distance:
                    # 후퇴하며 측면 이동
                    retreat = -direction_normalized * 0.6
                    perpendicular = np.array([-direction_normalized[2], 0, direction_normalized[0]])
                    desired_velocity = (retreat + perpendicular * 0.4) * self.max_speed
                else:
                    # 원을 그리며 이동
                    perpendicular = np.array([-direction_normalized[2], 0.1, direction_normalized[0]])
                    desired_velocity = perpendicular * self.max_speed * 0.7
                    
            else:  # evasive
                # 회피: 빠르게 도망치며 지그재그
                if self.evasive_maneuver_active:
                    desired_velocity = self.evasive_direction * self.max_speed * 1.3
                else:
                    escape_direction = -direction_normalized + np.random.randn(3).astype(float) * 0.3
                    escape_direction[1] = abs(escape_direction[1])  # 위로
                    escape_length = np.linalg.norm(escape_direction)
                    if escape_length > 0:
                        escape_direction = escape_direction / escape_length
                    desired_velocity = escape_direction * self.max_speed * 1.1
            
            # 장애물 회피
            avoidance_force = np.array([0.0, 0.0, 0.0], dtype=float)
            for obstacle in obstacles:
                obs_pos = np.array(obstacle['position'], dtype=float)
                to_obstacle = obs_pos - self.position
                dist_to_obstacle = np.linalg.norm(to_obstacle)
                
                danger_radius = 5.0
                if dist_to_obstacle < danger_radius and dist_to_obstacle > 0.1:
                    repulsion = (1.0 - dist_to_obstacle / danger_radius) ** 2
                    avoidance_force -= (to_obstacle / dist_to_obstacle) * repulsion
            
            desired_velocity += avoidance_force * self.max_speed * 0.8
            
            # 속도 업데이트
            velocity_change = (desired_velocity - self.velocity) * self.acceleration
            self.velocity += velocity_change
            
            # 속도 제한
            speed = np.linalg.norm(self.velocity)
            if speed > self.max_speed:
                self.velocity = (self.velocity / speed) * self.max_speed
            
            # 위치 업데이트
            self.position += self.velocity
            
            # 경계 제한 (확장된 맵)
            boundary = 95.0  # 200x200 맵에서 약간 여유
            self.position = np.clip(self.position, -boundary, boundary)
            # y축은 별도 제한
            self.position[1] = np.clip(self.position[1], 3, 60)
        
        return self.get_state()
    
    def should_fire_missile(self, player_position: List[float], current_time: float) -> bool:
        """미사일 발사 판단 (향상된 로직)"""
        if not self.is_alive or not self.can_fire_missile(current_time):
            return False
        
        target_pos = np.array(player_position, dtype=float)
        distance = np.linalg.norm(target_pos - self.position)
        
        # 사거리 및 행동 패턴 고려
        if distance <= self.attack_range:
            if self.behavior_mode == 'aggressive':
                # 공격적: 자주 발사
                fire_chance = self.aim_accuracy * 1.2
            elif self.behavior_mode == 'defensive':
                # 방어적: 확실할 때만
                fire_chance = self.aim_accuracy * 0.8
            else:  # evasive
                # 회피: 거의 발사 안함
                fire_chance = self.aim_accuracy * 0.3
            
            if np.random.random() < fire_chance:
                self.last_missile_time = current_time
                self.missiles_fired += 1
                self.memory['successful_attacks'] += 1
                return True
        
        return False
    
    def get_firing_direction(self, player_position: List[float], player_velocity: List[float] = None) -> List[float]:
        """예측 사격 (향상된 정확도)"""
        target_pos = np.array(player_position, dtype=float)
        
        # 예측 사격
        if player_velocity is not None and self.aim_accuracy > 0.6:
            player_vel = np.array(player_velocity, dtype=float)
            distance = np.linalg.norm(target_pos - self.position)
            missile_speed = 2.5
            prediction_time = distance / missile_speed
            
            # 난이도에 따라 예측 정확도 다름
            predicted_pos = target_pos + (player_vel * prediction_time * self.aim_accuracy)
            target_pos = predicted_pos
        
        # 조준 오차
        if self.aim_accuracy < 1.0:
            error_magnitude = (1.0 - self.aim_accuracy) * 3.0
            error = np.random.randn(3) * error_magnitude
            target_pos += error
        
        direction = target_pos - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 0.1:
            direction = direction / distance
        
        return direction.tolist()
    
    def take_damage(self, damage: int, attacker_id: str = None) -> Dict:
        """데미지 받기 (회피 기동 트리거)"""
        if not self.is_alive:
            return {'already_dead': True}
        
        self.hp = max(0, self.hp - damage)
        
        # 데미지 받으면 회피 기동 활성화 (확률적)
        if self.hp > 0 and np.random.random() < 0.4:
            self.activate_evasive_maneuver()
            self.memory['avoided_damage'] += 1
        
        result = {
            'drone_id': self.drone_id,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'damage_taken': damage,
            'attacker_id': attacker_id,
            'died': False
        }
        
        if self.hp <= 0:
            self.is_alive = False
            result['died'] = True
        
        return result
    
    def can_fire_missile(self, current_time: float) -> bool:
        """미사일 발사 가능 여부"""
        return (current_time - self.last_missile_time) >= self.missile_cooldown
    
    def respawn(self, position: List[float] = None) -> None:
        """리스폰"""
        self.hp = self.max_hp
        self.is_alive = True
        self.behavior_mode = 'aggressive'
        self.evasive_maneuver_active = False
        
        if position is not None:
            self.position = np.array(position, dtype=float)
        else:
            # 랜덤 위치
            self.position = np.random.uniform(-80, 80, 3).astype(float)
            self.position[1] = np.random.uniform(10, 30)
        
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=float)
    
    def get_state(self) -> Dict:
        """현재 상태 반환"""
        return {
            'drone_id': self.drone_id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'hp': self.hp,
            'max_hp': self.max_hp,
            'is_alive': self.is_alive,
            'difficulty': self.difficulty,
            'behavior_mode': self.behavior_mode,
            'stats': {
                'kills': self.kills,
                'damage_dealt': self.damage_dealt,
                'missiles_fired': self.missiles_fired
            },
            'memory': self.memory
        }


# 이전 버전과의 호환성을 위한 별칭
AIDrone = AdvancedAIDrone
