"""
유도 미사일 시스템
타겟을 추적하는 스마트 미사일
"""

import numpy as np
from typing import List, Dict, Optional
import time


class GuidedMissile:
    """
    유도 미사일 클래스
    발사 후 타겟을 자동으로 추적합니다.
    """
    
    def __init__(
        self,
        missile_id: str,
        owner_id: str,
        position: List[float],
        initial_direction: List[float],
        target_id: Optional[str] = None,
        damage: int = 20,
        speed: float = 1.5,
        turn_rate: float = 0.15,
        lifetime: float = 8.0
    ):
        """
        유도 미사일 초기화
        
        Args:
            missile_id: 미사일 ID
            owner_id: 발사자 ID
            position: 초기 위치
            initial_direction: 초기 방향
            target_id: 추적할 타겟 ID (None이면 일반 미사일)
            damage: 데미지
            speed: 속도 (1.5 = 적당한 속도)
            turn_rate: 회전 속도 (0.15 = 부드러운 추적)
            lifetime: 생존 시간
        """
        self.missile_id = missile_id
        self.owner_id = owner_id
        self.position = np.array(position, dtype=np.float32)
        
        # 방향 정규화
        direction = np.array(initial_direction, dtype=np.float32)
        direction_length = np.linalg.norm(direction)
        if direction_length > 0:
            direction = direction / direction_length
        
        self.velocity = direction * speed
        self.target_id = target_id
        self.damage = damage
        self.speed = speed
        self.turn_rate = turn_rate
        self.lifetime = lifetime
        self.created_at = time.time()
        self.max_distance = 150.0
        self.is_guided = target_id is not None
        
    def update(
        self,
        delta_time: float,
        target_position: Optional[List[float]] = None
    ) -> bool:
        """
        미사일 위치 및 방향 업데이트
        
        Args:
            delta_time: 프레임 시간
            target_position: 타겟 위치 (유도 미사일인 경우)
            
        Returns:
            True if still alive, False if expired
        """
        current_time = time.time()
        
        # 생존 시간 체크
        if (current_time - self.created_at) > self.lifetime:
            return False
        
        # 최대 사거리 체크
        distance_traveled = self.speed * (current_time - self.created_at)
        if distance_traveled > self.max_distance:
            return False
        
        # 유도 미사일이고 타겟이 있으면 방향 조정
        if self.is_guided and target_position is not None:
            target_pos = np.array(target_position, dtype=np.float32)
            
            # 타겟을 향한 방향
            to_target = target_pos - self.position
            distance_to_target = np.linalg.norm(to_target)
            
            if distance_to_target > 0.1:
                desired_direction = to_target / distance_to_target
                
                # 현재 방향
                current_direction = self.velocity / self.speed
                
                # 부드러운 회전 (Slerp와 유사)
                # turn_rate만큼만 방향 전환
                new_direction = current_direction + (desired_direction - current_direction) * self.turn_rate
                
                # 정규화
                new_direction_length = np.linalg.norm(new_direction)
                if new_direction_length > 0:
                    new_direction = new_direction / new_direction_length
                
                # 속도 업데이트
                self.velocity = new_direction * self.speed
        
        # 위치 업데이트
        self.position += self.velocity * delta_time * 60  # 60fps 기준
        
        return True
    
    def to_dict(self) -> Dict:
        """미사일 정보를 딕셔너리로 변환"""
        return {
            'missile_id': self.missile_id,
            'owner_id': self.owner_id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'damage': self.damage,
            'is_guided': self.is_guided,
            'target_id': self.target_id
        }
