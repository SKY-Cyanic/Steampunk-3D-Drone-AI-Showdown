"""
AI 드론 로직 모듈
PyTorch를 사용하여 AI 드론의 의사결정 로직을 처리합니다.
현재는 간단한 추적 로직을 구현하되, 향후 강화학습으로 발전시킬 수 있는 구조로 설계되었습니다.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple
import time


class AIDrone:
    """
    AI 드론 클래스
    플레이어 드론을 추적하고, 장애물을 회피하며, 전투를 수행하는 로직을 담당합니다.
    """
    
    def __init__(self, drone_id: str, initial_position: List[float], difficulty: str = 'normal'):
        """
        AI 드론 초기화
        
        Args:
            drone_id: 드론의 고유 ID
            initial_position: 초기 위치 [x, y, z]
            difficulty: 난이도 ('easy', 'normal', 'hard')
        """
        self.drone_id = drone_id
        self.position = np.array(initial_position, dtype=float)
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=float)
        
        # 난이도 설정
        self.difficulty = difficulty
        self._apply_difficulty_settings()
        
        # 전투 관련 속성
        self.hp = 100
        self.max_hp = 100
        self.is_alive = True
        self.last_missile_time = 0
        self.missile_cooldown = 1.5  # 초
        self.missile_damage = 20
        self.attack_range = 30.0  # 공격 사거리
        
        # 통계
        self.kills = 0
        self.damage_dealt = 0
        self.missiles_fired = 0
        
        # PyTorch를 사용한 기본 신경망 구조 (향후 강화학습용)
        # 현재는 사용하지 않지만, 구조를 미리 준비해둡니다
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._build_simple_network()
    
    def _apply_difficulty_settings(self) -> None:
        """난이도에 따른 설정 적용"""
        difficulty_settings = {
            'easy': {
                'max_speed': 0.2,
                'acceleration': 0.03,
                'reaction_time': 0.8,
                'aim_accuracy': 0.6
            },
            'normal': {
                'max_speed': 0.3,
                'acceleration': 0.05,
                'reaction_time': 0.5,
                'aim_accuracy': 0.75
            },
            'hard': {
                'max_speed': 0.4,
                'acceleration': 0.07,
                'reaction_time': 0.3,
                'aim_accuracy': 0.9
            }
        }
        
        settings = difficulty_settings.get(self.difficulty, difficulty_settings['normal'])
        self.max_speed = settings['max_speed']
        self.acceleration = settings['acceleration']
        self.reaction_time = settings['reaction_time']
        self.aim_accuracy = settings['aim_accuracy']
        
    def _build_simple_network(self) -> torch.nn.Module:
        """
        간단한 신경망 구조 정의
        향후 강화학습으로 발전시킬 때 사용할 수 있는 기본 구조
        
        Returns:
            PyTorch 신경망 모델
        """
        class SimpleDecisionNetwork(torch.nn.Module):
            def __init__(self):
                super(SimpleDecisionNetwork, self).__init__()
                # 입력: 현재 위치(3) + 목표 위치(3) + 속도(3) = 9
                # 출력: 이동 방향(3)
                self.fc1 = torch.nn.Linear(9, 32)
                self.fc2 = torch.nn.Linear(32, 16)
                self.fc3 = torch.nn.Linear(16, 3)
                
            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = torch.relu(self.fc2(x))
                x = torch.tanh(self.fc3(x))  # -1 ~ 1 범위로 정규화
                return x
        
        return SimpleDecisionNetwork().to(self.device)
    
    def update_position(self, player_position: List[float], obstacles: List[Dict], delta_time: float = 0.016) -> Dict:
        """
        플레이어 위치와 장애물 정보를 기반으로 AI 드론의 위치를 업데이트
        
        Args:
            player_position: 플레이어 드론의 현재 위치 [x, y, z]
            obstacles: 장애물 리스트
            delta_time: 프레임 간격 시간 (기본 60fps = 0.016초)
            
        Returns:
            업데이트된 드론 정보 딕셔너리
        """
        if not self.is_alive:
            return self.get_state()
        
        # 1. 플레이어를 향한 방향 벡터 계산
        target_position = np.array(player_position, dtype=float)
        direction_to_player = target_position - self.position
        distance_to_player = np.linalg.norm(direction_to_player)
        
        # 전투를 위한 최적 거리 (너무 가깝지도, 멀지도 않게)
        optimal_distance = 15.0
        min_distance = 8.0
        
        if distance_to_player > 0.1:  # 0으로 나누기 방지
            direction_normalized = direction_to_player / distance_to_player
            
            # 2. 전투적 이동 로직
            if distance_to_player > optimal_distance:
                # 최적 거리까지 접근
                desired_velocity = direction_normalized * self.max_speed
            elif distance_to_player < min_distance:
                # 너무 가까우면 후퇴
                desired_velocity = -direction_normalized * self.max_speed * 0.5
            else:
                # 최적 거리에서 스트레이핑(옆으로 이동)
                perpendicular = np.array([-direction_normalized[2], 0, direction_normalized[0]])
                desired_velocity = perpendicular * self.max_speed * 0.8
            
            # 3. 장애물 회피 로직 (간단한 반발력)
            avoidance_force = np.array([0.0, 0.0, 0.0], dtype=float)
            for obstacle in obstacles:
                obs_pos = np.array(obstacle['position'], dtype=float)
                to_obstacle = obs_pos - self.position
                dist_to_obstacle = np.linalg.norm(to_obstacle)
                
                # 장애물과 너무 가까우면 반대 방향으로 힘 적용
                danger_radius = 4.0
                if dist_to_obstacle < danger_radius and dist_to_obstacle > 0.1:
                    avoidance_force -= (to_obstacle / dist_to_obstacle) * (1.0 - dist_to_obstacle / danger_radius)
            
            # 회피력 적용
            desired_velocity += avoidance_force * self.max_speed * 0.6
            
            # 4. 속도 업데이트 (부드러운 가속/감속)
            velocity_change = (desired_velocity - self.velocity) * self.acceleration
            self.velocity += velocity_change
            
            # 최대 속도 제한
            speed = np.linalg.norm(self.velocity)
            if speed > self.max_speed:
                self.velocity = (self.velocity / speed) * self.max_speed
            
            # 5. 위치 업데이트
            self.position += self.velocity
            
            # 경기장 경계 제한 (-50 ~ 50)
            boundary = 50.0
            self.position = np.clip(self.position, -boundary, boundary)
        
        # 6. 업데이트된 정보 반환
        return self.get_state()
    
    def take_damage(self, damage: int, attacker_id: str = None) -> Dict:
        """
        데미지 받기
        
        Args:
            damage: 받는 데미지
            attacker_id: 공격자 ID
            
        Returns:
            전투 결과 정보
        """
        if not self.is_alive:
            return {'already_dead': True}
        
        self.hp = max(0, self.hp - damage)
        
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
        """미사일 발사 가능 여부 체크 (쿨다운)"""
        return (current_time - self.last_missile_time) >= self.missile_cooldown
    
    def should_fire_missile(self, player_position: List[float], current_time: float) -> bool:
        """
        미사일을 발사해야 하는지 판단 (AI 의사결정)
        
        Args:
            player_position: 플레이어 위치
            current_time: 현재 시간
            
        Returns:
            발사 여부
        """
        if not self.is_alive or not self.can_fire_missile(current_time):
            return False
        
        # 플레이어와의 거리 계산
        target_pos = np.array(player_position, dtype=float)
        distance = np.linalg.norm(target_pos - self.position)
        
        # 사거리 내에 있고, 쿨다운이 끝났으면 발사
        if distance <= self.attack_range:
            # 난이도에 따른 발사 확률
            if np.random.random() < self.aim_accuracy:
                self.last_missile_time = current_time
                self.missiles_fired += 1
                return True
        
        return False
    
    def get_firing_direction(self, player_position: List[float], player_velocity: List[float] = None) -> List[float]:
        """
        미사일 발사 방향 계산 (예측 사격)
        
        Args:
            player_position: 플레이어 현재 위치
            player_velocity: 플레이어 속도 (예측 사격용)
            
        Returns:
            발사 방향 벡터 (정규화됨)
        """
        target_pos = np.array(player_position, dtype=float)
        
        # 예측 사격: 플레이어의 이동을 예측
        if player_velocity is not None:
            player_vel = np.array(player_velocity, dtype=float)
            # 미사일 속도를 고려한 예측 시간
            distance = np.linalg.norm(target_pos - self.position)
            missile_speed = 2.0  # 미사일 속도 (game_mechanics.py와 일치)
            prediction_time = distance / missile_speed
            
            # 예측 위치 = 현재 위치 + (속도 * 예측 시간)
            predicted_pos = target_pos + (player_vel * prediction_time * self.aim_accuracy)
            target_pos = predicted_pos
        
        # 조준 오차 추가 (난이도에 따라)
        if self.aim_accuracy < 1.0:
            error_magnitude = (1.0 - self.aim_accuracy) * 5.0
            error = np.random.randn(3) * error_magnitude
            target_pos += error
        
        # 발사 방향 계산 및 정규화
        direction = target_pos - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 0.1:
            direction = direction / distance
        
        return direction.tolist()
    
    def respawn(self, position: List[float] = None) -> None:
        """
        AI 드론 리스폰
        
        Args:
            position: 리스폰 위치 (None이면 랜덤)
        """
        self.hp = self.max_hp
        self.is_alive = True
        
        if position is not None:
            self.position = np.array(position, dtype=float)
        else:
            # 랜덤 위치로 리스폰
            self.position = np.random.uniform(-40, 40, 3).astype(float)
            self.position[1] = np.random.uniform(5, 20)  # y 좌표는 5~20 사이
        
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=float)
    
    def get_state(self) -> Dict:
        """현재 AI 드론 상태 반환"""
        return {
            'drone_id': self.drone_id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'hp': self.hp,
            'max_hp': self.max_hp,
            'is_alive': self.is_alive,
            'difficulty': self.difficulty,
            'stats': {
                'kills': self.kills,
                'damage_dealt': self.damage_dealt,
                'missiles_fired': self.missiles_fired
            }
        }
    
    def predict_with_neural_network(self, player_position: List[float]) -> np.ndarray:
        """
        신경망을 사용한 예측 (향후 강화학습 구현용)
        현재는 참고용으로만 포함되어 있습니다.
        
        Args:
            player_position: 플레이어 위치
            
        Returns:
            예측된 이동 방향 벡터
        """
        # 입력 데이터 준비
        state = np.concatenate([
            self.position,
            player_position,
            self.velocity
        ])
        
        # PyTorch 텐서로 변환
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # 신경망으로 예측
        with torch.no_grad():
            action = self.model(state_tensor)
        
        # NumPy 배열로 변환하여 반환
        return action.cpu().numpy()[0]
