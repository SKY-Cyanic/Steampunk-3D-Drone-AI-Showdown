"""
물리 엔진 모듈
장애물 충돌, 속도 기반 데미지 계산 등을 처리합니다.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CollisionResult:
    """충돌 결과 데이터"""
    collided: bool
    impact_speed: float
    impact_position: List[float]
    damage: int
    bounce_velocity: Optional[List[float]] = None


class PhysicsEngine:
    """
    물리 엔진
    드론-장애물 충돌, 속도 기반 데미지 계산
    """
    
    def __init__(self):
        self.collision_threshold = 0.5  # 충돌로 판정되는 최소 속도
        self.damage_multiplier = 50  # 속도당 데미지 배율
        self.bounce_factor = 0.7  # 반발 계수
        
    def check_obstacle_collision(
        self,
        position: List[float],
        velocity: List[float],
        obstacles: List[Dict]
    ) -> CollisionResult:
        """
        드론과 장애물 간 충돌 체크
        
        Args:
            position: 드론 위치
            velocity: 드론 속도
            obstacles: 장애물 리스트
            
        Returns:
            CollisionResult
        """
        pos = np.array(position, dtype=float)
        vel = np.array(velocity, dtype=float)
        speed = np.linalg.norm(vel)
        
        for obstacle in obstacles:
            obs_pos = np.array(obstacle['position'], dtype=float)
            obs_size = obstacle.get('size', [2, 2, 2])
            
            # AABB (Axis-Aligned Bounding Box) 충돌 감지
            half_size = np.array(obs_size, dtype=float) / 2
            collision_radius = 2.0  # 드론 반경
            
            # 각 축별 거리 계산
            distance_vec = pos - obs_pos
            clamped = np.clip(distance_vec, -half_size, half_size)
            closest_point = obs_pos + clamped
            
            # 가장 가까운 점까지의 거리
            distance = np.linalg.norm(pos - closest_point)
            
            if distance < collision_radius:
                # 충돌 발생!
                damage = 0
                
                # 속도 기반 데미지 계산
                if speed > self.collision_threshold:
                    damage = int((speed - self.collision_threshold) * self.damage_multiplier)
                
                # 반발 속도 계산
                collision_normal = pos - closest_point
                collision_normal_length = np.linalg.norm(collision_normal)
                
                if collision_normal_length > 0.001:
                    collision_normal = collision_normal / collision_normal_length
                    
                    # 속도를 법선과 접선 성분으로 분해
                    normal_component = np.dot(vel, collision_normal)
                    
                    if normal_component < 0:  # 장애물을 향해 이동 중
                        # 법선 방향 반전 (반발)
                        vel_reflected = vel - (1 + self.bounce_factor) * normal_component * collision_normal
                        bounce_velocity = vel_reflected.tolist()
                    else:
                        bounce_velocity = vel.tolist()
                else:
                    # 정확히 중심에 있는 경우 (희귀)
                    bounce_velocity = [-v * self.bounce_factor for v in velocity]
                
                return CollisionResult(
                    collided=True,
                    impact_speed=speed,
                    impact_position=closest_point.tolist(),
                    damage=damage,
                    bounce_velocity=bounce_velocity
                )
        
        return CollisionResult(
            collided=False,
            impact_speed=0,
            impact_position=[0, 0, 0],
            damage=0
        )
    
    def check_boundary_collision(
        self,
        position: List[float],
        velocity: List[float],
        boundary_size: float = 100.0
    ) -> CollisionResult:
        """
        맵 경계 충돌 체크
        
        Args:
            position: 드론 위치
            velocity: 드론 속도
            boundary_size: 맵 크기 (반경)
            
        Returns:
            CollisionResult
        """
        pos = np.array(position, dtype=float)
        vel = np.array(velocity, dtype=float)
        
        collided = False
        bounce_velocity = vel.copy()
        
        # 각 축별 경계 체크
        for i in range(3):
            if abs(pos[i]) > boundary_size:
                collided = True
                # 해당 축 속도 반전
                bounce_velocity[i] = -bounce_velocity[i] * self.bounce_factor
        
        if collided:
            speed = np.linalg.norm(vel)
            damage = int(speed * self.damage_multiplier * 0.5)  # 경계는 절반 데미지
            
            return CollisionResult(
                collided=True,
                impact_speed=speed,
                impact_position=pos.tolist(),
                damage=damage,
                bounce_velocity=bounce_velocity.tolist()
            )
        
        return CollisionResult(
            collided=False,
            impact_speed=0,
            impact_position=[0, 0, 0],
            damage=0
        )
    
    def calculate_explosion_damage(
        self,
        explosion_position: List[float],
        target_position: List[float],
        base_damage: int,
        blast_radius: float = 10.0
    ) -> int:
        """
        폭발 범위 데미지 계산
        
        Args:
            explosion_position: 폭발 위치
            target_position: 타겟 위치
            base_damage: 기본 데미지
            blast_radius: 폭발 반경
            
        Returns:
            최종 데미지
        """
        exp_pos = np.array(explosion_position, dtype=float)
        target_pos = np.array(target_position, dtype=float)
        
        distance = np.linalg.norm(target_pos - exp_pos)
        
        if distance > blast_radius:
            return 0
        
        # 거리에 반비례하는 데미지
        damage_ratio = 1.0 - (distance / blast_radius)
        return int(base_damage * damage_ratio)
