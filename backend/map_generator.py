"""
맵 생성기 - 레벨별 동적 확장 지원
다양한 장애물과 지형지물을 생성합니다.
"""

import random
from typing import List, Dict


class MapGenerator:
    """맵 생성 및 관리 - 레벨별 확장"""
    
    @staticmethod
    def get_map_config_for_level(level: int) -> Dict:
        """
        레벨에 따른 맵 설정 반환
        
        레벨 1-5:    200x200, 35개 장애물
        레벨 6-10:   300x300, 50개 장애물
        레벨 11-20:  400x400, 70개 장애물
        레벨 21-30:  500x500, 100개 장애물
        레벨 31+:    600x600, 130개 장애물
        """
        if level <= 5:
            return {'size': 200, 'obstacles': 35}
        elif level <= 10:
            return {'size': 300, 'obstacles': 50}
        elif level <= 20:
            return {'size': 400, 'obstacles': 70}
        elif level <= 30:
            return {'size': 500, 'obstacles': 100}
        else:
            return {'size': 600, 'obstacles': 130}
    
    @staticmethod
    def generate_dynamic_map(level: int) -> Dict:
        """
        레벨에 맞는 동적 맵 생성
        
        Returns:
            {'obstacles': [...], 'map_size': int, 'spawn_points': [...]}
        """
        config = MapGenerator.get_map_config_for_level(level)
        obstacles = MapGenerator.generate_large_map(
            size=config['size'],
            obstacle_count=config['obstacles']
        )
        spawn_points = MapGenerator.get_spawn_points(
            map_size=config['size'],
            count=max(8, level // 3)  # 스폰 포인트도 증가
        )
        
        return {
            'obstacles': obstacles,
            'map_size': config['size'],
            'spawn_points': spawn_points
        }
    
    @staticmethod
    def generate_large_map(size: int = 200, obstacle_count: int = 30) -> List[Dict]:
        """
        대형 맵 생성
        다양한 장애물 랜덤 배치
        
        Args:
            size: 맵 크기 (한 변의 길이)
            obstacle_count: 장애물 개수
            
        Returns:
            장애물 리스트 (충돌 박스 포함)
        """
        obstacles = []
        half_size = size // 2
        
        # 중앙 타워 (랜드마크)
        obstacles.append({
            'type': 'tower',
            'position': [0, 20, 0],
            'rotation': 0,
            'size': [8, 40, 8],
            'color': 0x8b4513,
            'collision_radius': 8  # 충돌 반경
        })
        
        # 거대 톱니바퀴
        gear_count = max(6, obstacle_count // 6)
        for i in range(gear_count):
            x = random.uniform(-half_size + 20, half_size - 20)
            z = random.uniform(-half_size + 20, half_size - 20)
            y = random.uniform(8, 18)
            radius = random.uniform(4, 8)
            
            obstacles.append({
                'type': 'gear',
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [radius, random.uniform(1, 2), radius],
                'color': 0xb45309,
                'rotation_speed': random.uniform(0.005, 0.02),
                'collision_radius': radius
            })
        
        # 파이프 네트워크
        pipe_count = max(7, obstacle_count // 5)
        for i in range(pipe_count):
            x = random.uniform(-half_size + 15, half_size - 15)
            z = random.uniform(-half_size + 15, half_size - 15)
            y = random.uniform(10, 20)
            length = random.uniform(20, 35)
            
            obstacles.append({
                'type': 'pipe',
                'position': [x, y, z],
                'rotation': random.choice([0, 90]),
                'size': [2.5, length, 2.5],
                'color': 0x475569,
                'collision_radius': 3
            })
        
        # 큐브 장애물 (산재)
        cube_count = max(15, obstacle_count // 3)
        for i in range(cube_count):
            x = random.uniform(-half_size + 20, half_size - 20)
            z = random.uniform(-half_size + 20, half_size - 20)
            y = random.uniform(5, 25)
            size = random.uniform(3, 8)
            
            obstacles.append({
                'type': 'cube',
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [size, size, size],
                'color': random.choice([0x6b7280, 0x9ca3af, 0x4b5563, 0x374151]),
                'collision_radius': size * 0.866  # sqrt(3)/2 for cube diagonal
            })
        
        # 링 구조물
        ring_count = max(4, obstacle_count // 10)
        for i in range(ring_count):
            x = random.uniform(-half_size + 30, half_size - 30)
            z = random.uniform(-half_size + 30, half_size - 30)
            y = random.uniform(15, 30)
            
            obstacles.append({
                'type': 'ring',
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [15, 15, 2],
                'color': 0xfbbf24,
                'collision_radius': 2  # 링 두께만 충돌
            })
        
        # 스팀펑크 크리스탈
        crystal_count = max(4, obstacle_count // 12)
        for i in range(crystal_count):
            x = random.uniform(-half_size + 25, half_size - 25)
            z = random.uniform(-half_size + 25, half_size - 25)
            y = random.uniform(5, 10)
            
            obstacles.append({
                'type': 'crystal',
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [3, 8, 3],
                'color': random.choice([0x06b6d4, 0x8b5cf6, 0xec4899, 0x10b981]),
                'emissive': True,
                'collision_radius': 3
            })
        
        # 플랫폼
        platform_count = max(4, obstacle_count // 15)
        for i in range(platform_count):
            x = random.uniform(-half_size + 30, half_size - 30)
            z = random.uniform(-half_size + 30, half_size - 30)
            
            obstacles.append({
                'type': 'platform',
                'position': [x, 3, z],
                'rotation': 0,
                'size': [12, 1, 12],
                'color': 0x334155,
                'collision_radius': 12
            })
        
        # 스파이크 (위험 지역)
        spike_count = max(4, obstacle_count // 20)
        for i in range(spike_count):
            x = random.uniform(-half_size + 20, half_size - 20)
            z = random.uniform(-half_size + 20, half_size - 20)
            
            obstacles.append({
                'type': 'spike',
                'position': [x, 3, z],
                'rotation': 0,
                'size': [4, 6, 4],
                'color': 0xdc2626,
                'damage_multiplier': 2.0,
                'collision_radius': 4
            })
        
        # 추가 랜덤 장애물 (목표 개수 채우기)
        current_count = len(obstacles)
        remaining = obstacle_count - current_count
        
        for i in range(max(0, remaining)):
            obstacle_type = random.choice(['cube', 'crystal', 'gear'])
            x = random.uniform(-half_size + 20, half_size - 20)
            z = random.uniform(-half_size + 20, half_size - 20)
            y = random.uniform(5, 25)
            size = random.uniform(3, 7)
            
            obstacles.append({
                'type': obstacle_type,
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [size, size, size],
                'color': random.choice([0x6b7280, 0x8b5cf6, 0xfbbf24, 0x10b981]),
                'collision_radius': size
            })
        
        return obstacles
    
    @staticmethod
    def get_spawn_points(map_size: int = 200, count: int = 8) -> List[List[float]]:
        """
        안전한 스폰 포인트 생성
        
        Args:
            map_size: 맵 크기
            count: 스폰 포인트 개수
            
        Returns:
            스폰 포인트 리스트
        """
        spawn_points = []
        half_size = map_size // 2
        
        # 맵 가장자리를 따라 고르게 배치
        for i in range(count):
            angle = (i / count) * 2 * 3.14159
            radius = half_size * 0.7
            
            x = radius * (random.uniform(0.8, 1.0) * (1 if random.random() > 0.5 else -1))
            z = radius * (random.uniform(0.8, 1.0) * (1 if random.random() > 0.5 else -1))
            y = random.uniform(10, 20)
            
            spawn_points.append([x, y, z])
        
        return spawn_points
