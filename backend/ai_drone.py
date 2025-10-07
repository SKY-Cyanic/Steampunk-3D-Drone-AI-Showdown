"""
AI 드론 로직 모듈
PyTorch를 사용하여 AI 드론의 의사결정 로직을 처리합니다.
현재는 간단한 추적 로직을 구현하되, 향후 강화학습으로 발전시킬 수 있는 구조로 설계되었습니다.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple


class AIDrone:
    """
    AI 드론 클래스
    플레이어 드론을 추적하고, 장애물을 회피하는 기본 로직을 담당합니다.
    """
    
    def __init__(self, drone_id: str, initial_position: List[float]):
        """
        AI 드론 초기화
        
        Args:
            drone_id: 드론의 고유 ID
            initial_position: 초기 위치 [x, y, z]
        """
        self.drone_id = drone_id
        self.position = np.array(initial_position, dtype=np.float32)
        self.velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.max_speed = 0.3  # 최대 이동 속도
        self.acceleration = 0.05  # 가속도
        
        # PyTorch를 사용한 기본 신경망 구조 (향후 강화학습용)
        # 현재는 사용하지 않지만, 구조를 미리 준비해둡니다
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._build_simple_network()
        
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
        # 1. 플레이어를 향한 방향 벡터 계산
        target_position = np.array(player_position, dtype=np.float32)
        direction_to_player = target_position - self.position
        distance_to_player = np.linalg.norm(direction_to_player)
        
        # 거리가 너무 가까우면 살짝 멀어지기 (최소 유지 거리)
        min_distance = 5.0
        
        if distance_to_player > 0.1:  # 0으로 나누기 방지
            direction_normalized = direction_to_player / distance_to_player
            
            # 2. 기본 추적 로직: 플레이어를 향해 이동
            if distance_to_player > min_distance:
                # 플레이어에게 다가가기
                desired_velocity = direction_normalized * self.max_speed
            else:
                # 너무 가까우면 원을 그리며 회전 (더 재미있는 AI 행동)
                perpendicular = np.array([-direction_normalized[2], 0, direction_normalized[0]])
                desired_velocity = perpendicular * self.max_speed * 0.7
            
            # 3. 장애물 회피 로직 (간단한 반발력)
            avoidance_force = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            for obstacle in obstacles:
                obs_pos = np.array(obstacle['position'], dtype=np.float32)
                to_obstacle = obs_pos - self.position
                dist_to_obstacle = np.linalg.norm(to_obstacle)
                
                # 장애물과 너무 가까우면 반대 방향으로 힘 적용
                danger_radius = 3.0
                if dist_to_obstacle < danger_radius and dist_to_obstacle > 0.1:
                    avoidance_force -= (to_obstacle / dist_to_obstacle) * (1.0 - dist_to_obstacle / danger_radius)
            
            # 회피력 적용
            desired_velocity += avoidance_force * self.max_speed * 0.5
            
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
        return {
            'drone_id': self.drone_id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'distance_to_player': float(distance_to_player)
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
