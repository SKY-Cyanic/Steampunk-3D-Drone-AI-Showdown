"""
맵 생성기
다양한 장애물과 지형지물을 생성합니다.
"""

import random
from typing import List, Dict


class MapGenerator:
    """맵 생성 및 관리"""
    
    @staticmethod
    def generate_large_map(size: int = 200, obstacle_count: int = 30) -> List[Dict]:
        """
        대형 맵 생성 (200x200)
        다양한 장애물 배치
        
        Args:
            size: 맵 크기 (한 변의 길이)
            obstacle_count: 장애물 개수
            
        Returns:
            장애물 리스트
        """
        obstacles = []
        half_size = size // 2
        
        # 중앙 타워 (랜드마크)
        obstacles.append({
            'type': 'tower',
            'position': [0, 20, 0],
            'rotation': 0,
            'size': [8, 40, 8],
            'color': 0x8b4513
        })
        
        # 거대 톱니바퀴 (여러 개)
        gear_positions = [
            [30, 10, 30],
            [-40, 15, -20],
            [50, 12, -40],
            [-30, 8, 45],
            [60, 18, 10],
            [-50, 14, -50]
        ]
        
        for i, pos in enumerate(gear_positions):
            obstacles.append({
                'type': 'gear',
                'position': pos,
                'rotation': random.uniform(0, 360),
                'size': [random.uniform(4, 8), random.uniform(1, 2), random.uniform(4, 8)],
                'color': 0xb45309,
                'rotation_speed': random.uniform(0.005, 0.02)
            })
        
        # 파이프 네트워크
        pipe_configs = [
            {'pos': [0, 15, 40], 'rot': 0, 'length': 30},
            {'pos': [40, 12, 0], 'rot': 90, 'length': 25},
            {'pos': [-35, 18, -30], 'rot': 45, 'length': 35},
            {'pos': [25, 10, -50], 'rot': 0, 'length': 20},
            {'pos': [-50, 14, 20], 'rot': 90, 'length': 28},
            {'pos': [15, 8, 25], 'rot': 30, 'length': 22},
            {'pos': [-20, 16, -40], 'rot': 60, 'length': 26}
        ]
        
        for config in pipe_configs:
            obstacles.append({
                'type': 'pipe',
                'position': config['pos'],
                'rotation': config['rot'],
                'size': [2.5, config['length'], 2.5],
                'color': 0x475569
            })
        
        # 큐브 장애물 (산재)
        for i in range(15):
            x = random.uniform(-half_size + 20, half_size - 20)
            z = random.uniform(-half_size + 20, half_size - 20)
            y = random.uniform(5, 25)
            size = random.uniform(3, 7)
            
            obstacles.append({
                'type': 'cube',
                'position': [x, y, z],
                'rotation': random.uniform(0, 360),
                'size': [size, size, size],
                'color': random.choice([0x6b7280, 0x9ca3af, 0x4b5563])
            })
        
        # 링 구조물 (통과 가능한 장애물)
        ring_positions = [
            [70, 20, 0],
            [-70, 25, 30],
            [0, 30, -70],
            [50, 15, 60]
        ]
        
        for pos in ring_positions:
            obstacles.append({
                'type': 'ring',
                'position': pos,
                'rotation': random.uniform(0, 360),
                'size': [15, 15, 2],  # 외경, 내경, 두께
                'color': 0xfbbf24
            })
        
        # 스팀펑크 크리스탈 (발광 장애물)
        crystal_positions = [
            [35, 5, -25],
            [-45, 7, 35],
            [60, 6, -60],
            [-55, 8, -45]
        ]
        
        for pos in crystal_positions:
            obstacles.append({
                'type': 'crystal',
                'position': pos,
                'rotation': random.uniform(0, 360),
                'size': [3, 8, 3],
                'color': random.choice([0x06b6d4, 0x8b5cf6, 0xec4899]),
                'emissive': True
            })
        
        # 플랫폼 (착륙/휴식 공간)
        platform_positions = [
            [40, 3, 40],
            [-40, 3, -40],
            [60, 3, -30],
            [-50, 3, 50]
        ]
        
        for pos in platform_positions:
            obstacles.append({
                'type': 'platform',
                'position': pos,
                'rotation': 0,
                'size': [12, 1, 12],
                'color': 0x334155
            })
        
        # 스파이크 (위험 지역)
        spike_positions = [
            [20, 2, -60],
            [-30, 2, 55],
            [65, 2, 25],
            [-60, 2, -30]
        ]
        
        for pos in spike_positions:
            obstacles.append({
                'type': 'spike',
                'position': pos,
                'rotation': 0,
                'size': [4, 6, 4],
                'color': 0xdc2626,
                'damage_multiplier': 2.0  # 스파이크는 데미지 2배
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
            radius = half_size * 0.7  # 가장자리에서 약간 안쪽
            
            x = radius * (random.uniform(0.8, 1.0) * (1 if random.random() > 0.5 else -1))
            z = radius * (random.uniform(0.8, 1.0) * (1 if random.random() > 0.5 else -1))
            y = random.uniform(10, 20)
            
            spawn_points.append([x, y, z])
        
        return spawn_points
