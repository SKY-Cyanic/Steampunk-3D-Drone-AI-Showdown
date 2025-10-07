"""
게임 메커니즘 시스템
미사일, 충돌 감지, 전투 로직 등을 관리합니다.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import time
import uuid


@dataclass
class Missile:
    """미사일 데이터 클래스"""
    missile_id: str
    owner_id: str  # 발사한 플레이어/AI ID
    position: np.ndarray
    velocity: np.ndarray
    damage: int
    speed: float
    lifetime: float  # 생존 시간 (초)
    created_at: float
    max_distance: float = 100.0  # 최대 사거리
    
    def update(self, delta_time: float) -> bool:
        """
        미사일 위치 업데이트
        Returns: True if still alive, False if expired
        """
        self.position += self.velocity * delta_time
        current_time = time.time()
        
        # 생존 시간 체크
        if (current_time - self.created_at) > self.lifetime:
            return False
        
        # 최대 사거리 체크
        distance_traveled = np.linalg.norm(self.velocity) * (current_time - self.created_at)
        if distance_traveled > self.max_distance:
            return False
        
        return True
    
    def to_dict(self) -> Dict:
        """미사일 정보를 딕셔너리로 변환"""
        return {
            'missile_id': self.missile_id,
            'owner_id': self.owner_id,
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'damage': self.damage
        }


class CombatSystem:
    """전투 시스템 관리"""
    
    def __init__(self):
        self.missiles: Dict[str, Missile] = {}
        self.hit_detection_radius = 2.0  # 충돌 감지 반경
        
    def create_missile(
        self,
        owner_id: str,
        position: List[float],
        direction: List[float],
        damage: int = 20,
        speed: float = 2.0,
        lifetime: float = 5.0
    ) -> Missile:
        """
        새로운 미사일 생성
        
        Args:
            owner_id: 미사일 발사자 ID
            position: 시작 위치
            direction: 발사 방향 (정규화된 벡터)
            damage: 데미지
            speed: 속도
            lifetime: 생존 시간
        """
        missile_id = f"missile_{uuid.uuid4().hex[:8]}"
        
        # 위치와 속도를 numpy 배열로 변환
        pos = np.array(position, dtype=np.float32)
        dir_normalized = np.array(direction, dtype=np.float32)
        
        # 방향 벡터 정규화
        dir_length = np.linalg.norm(dir_normalized)
        if dir_length > 0:
            dir_normalized = dir_normalized / dir_length
        
        velocity = dir_normalized * speed
        
        missile = Missile(
            missile_id=missile_id,
            owner_id=owner_id,
            position=pos,
            velocity=velocity,
            damage=damage,
            speed=speed,
            lifetime=lifetime,
            created_at=time.time()
        )
        
        self.missiles[missile_id] = missile
        return missile
    
    def update_missiles(self, delta_time: float = 0.016) -> List[str]:
        """
        모든 미사일 업데이트
        Returns: 제거된 미사일 ID 리스트
        """
        removed_missiles = []
        
        for missile_id, missile in list(self.missiles.items()):
            if not missile.update(delta_time):
                removed_missiles.append(missile_id)
                del self.missiles[missile_id]
        
        return removed_missiles
    
    def check_collision(
        self,
        missile: Missile,
        target_position: List[float],
        target_radius: float = 2.0
    ) -> bool:
        """
        미사일과 타겟 간 충돌 체크
        
        Args:
            missile: 체크할 미사일
            target_position: 타겟 위치
            target_radius: 타겟 충돌 반경
        """
        target_pos = np.array(target_position, dtype=np.float32)
        distance = np.linalg.norm(missile.position - target_pos)
        
        return distance <= (self.hit_detection_radius + target_radius)
    
    def check_all_collisions(
        self,
        targets: Dict[str, Dict]
    ) -> List[Dict]:
        """
        모든 미사일과 타겟 간 충돌 체크
        
        Args:
            targets: {target_id: {'position': [x,y,z], 'radius': float}}
        
        Returns:
            충돌 정보 리스트 [{'missile_id', 'target_id', 'damage', 'attacker_id'}]
        """
        collisions = []
        missiles_to_remove = []
        
        for missile_id, missile in self.missiles.items():
            for target_id, target_data in targets.items():
                # 자기 자신은 맞지 않음
                if missile.owner_id == target_id:
                    continue
                
                if self.check_collision(missile, target_data['position'], target_data.get('radius', 2.0)):
                    collisions.append({
                        'missile_id': missile_id,
                        'target_id': target_id,
                        'damage': missile.damage,
                        'attacker_id': missile.owner_id,
                        'position': missile.position.tolist()
                    })
                    missiles_to_remove.append(missile_id)
                    break  # 한 번 맞으면 미사일 소멸
        
        # 충돌한 미사일 제거
        for missile_id in missiles_to_remove:
            if missile_id in self.missiles:
                del self.missiles[missile_id]
        
        return collisions
    
    def get_all_missiles(self) -> List[Dict]:
        """모든 활성 미사일 정보 가져오기"""
        return [missile.to_dict() for missile in self.missiles.values()]
    
    def clear_missiles(self) -> None:
        """모든 미사일 제거"""
        self.missiles.clear()


class RewardSystem:
    """보상 시스템"""
    
    # 행동별 보상
    REWARDS = {
        'kill': {'score': 100, 'exp': 50, 'coins': 10},
        'assist': {'score': 50, 'exp': 25, 'coins': 5},
        'hit': {'score': 10, 'exp': 5, 'coins': 1},
        'survive_minute': {'score': 20, 'exp': 10, 'coins': 2},
        'win_game': {'score': 500, 'exp': 200, 'coins': 50}
    }
    
    @staticmethod
    def calculate_kill_reward(
        killer_level: int,
        victim_level: int,
        streak: int = 0
    ) -> Dict:
        """
        킬 보상 계산 (레벨 차이 고려)
        
        Args:
            killer_level: 킬러 레벨
            victim_level: 희생자 레벨
            streak: 연속 킬 수
        """
        base_reward = RewardSystem.REWARDS['kill'].copy()
        
        # 레벨 차이 보너스/페널티
        level_diff = victim_level - killer_level
        if level_diff > 0:
            # 높은 레벨 처치 시 보너스
            multiplier = 1 + (level_diff * 0.1)
        else:
            # 낮은 레벨 처치 시 페널티
            multiplier = max(0.5, 1 + (level_diff * 0.05))
        
        # 연속 킬 보너스
        streak_bonus = 1 + (streak * 0.2)
        
        # 최종 배율 적용
        total_multiplier = multiplier * streak_bonus
        
        return {
            'score': int(base_reward['score'] * total_multiplier),
            'exp': int(base_reward['exp'] * total_multiplier),
            'coins': int(base_reward['coins'] * total_multiplier),
            'multiplier': round(total_multiplier, 2)
        }
    
    @staticmethod
    def calculate_match_reward(
        won: bool,
        kills: int,
        deaths: int,
        damage_dealt: float,
        match_duration: float
    ) -> Dict:
        """
        매치 종료 시 전체 보상 계산
        
        Args:
            won: 승리 여부
            kills: 킬 수
            deaths: 데스 수
            damage_dealt: 입힌 총 데미지
            match_duration: 매치 시간 (초)
        """
        total_score = 0
        total_exp = 0
        total_coins = 0
        
        # 승리 보상
        if won:
            win_reward = RewardSystem.REWARDS['win_game']
            total_score += win_reward['score']
            total_exp += win_reward['exp']
            total_coins += win_reward['coins']
        
        # 킬 보상
        total_score += kills * RewardSystem.REWARDS['kill']['score']
        total_exp += kills * RewardSystem.REWARDS['kill']['exp']
        total_coins += kills * RewardSystem.REWARDS['kill']['coins']
        
        # 생존 시간 보상
        minutes_survived = int(match_duration / 60)
        survive_reward = RewardSystem.REWARDS['survive_minute']
        total_score += minutes_survived * survive_reward['score']
        total_exp += minutes_survived * survive_reward['exp']
        total_coins += minutes_survived * survive_reward['coins']
        
        # 데미지 보너스 (100 데미지당 1 코인)
        damage_coins = int(damage_dealt / 100)
        total_coins += damage_coins
        
        # 무사망 보너스
        if deaths == 0 and kills > 0:
            total_score += 200
            total_exp += 100
            total_coins += 20
        
        return {
            'total_score': total_score,
            'total_exp': total_exp,
            'total_coins': total_coins,
            'breakdown': {
                'win': won,
                'kills': kills,
                'deaths': deaths,
                'damage_dealt': int(damage_dealt),
                'minutes_survived': minutes_survived,
                'no_death_bonus': deaths == 0 and kills > 0
            }
        }


class EloRatingSystem:
    """ELO 레이팅 시스템"""
    
    K_FACTOR = 32  # ELO 변동 계수
    
    @staticmethod
    def calculate_expected_score(rating_a: int, rating_b: int) -> float:
        """
        기대 승률 계산
        
        Args:
            rating_a: 플레이어 A 레이팅
            rating_b: 플레이어 B 레이팅
        
        Returns:
            플레이어 A의 기대 승률 (0~1)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    @staticmethod
    def calculate_new_rating(
        current_rating: int,
        opponent_rating: int,
        won: bool,
        k_factor: int = None
    ) -> Tuple[int, int]:
        """
        새로운 레이팅 계산
        
        Args:
            current_rating: 현재 레이팅
            opponent_rating: 상대 레이팅
            won: 승리 여부
            k_factor: K 계수 (None이면 기본값 사용)
        
        Returns:
            (새로운 레이팅, 레이팅 변동량)
        """
        k = k_factor or EloRatingSystem.K_FACTOR
        
        expected = EloRatingSystem.calculate_expected_score(current_rating, opponent_rating)
        actual = 1.0 if won else 0.0
        
        rating_change = int(k * (actual - expected))
        new_rating = max(0, current_rating + rating_change)  # 레이팅은 0 이하로 떨어지지 않음
        
        return new_rating, rating_change
    
    @staticmethod
    def calculate_rating_with_performance(
        current_rating: int,
        opponent_rating: int,
        won: bool,
        kills: int,
        deaths: int
    ) -> Tuple[int, int]:
        """
        전투 성과를 반영한 레이팅 계산
        
        Args:
            current_rating: 현재 레이팅
            opponent_rating: 상대 레이팅
            won: 승리 여부
            kills: 킬 수
            deaths: 데스 수
        """
        # 기본 레이팅 변동
        new_rating, base_change = EloRatingSystem.calculate_new_rating(
            current_rating, opponent_rating, won
        )
        
        # 성과 보너스/페널티
        kda = kills / max(1, deaths)
        if kda >= 3.0:
            performance_bonus = 5
        elif kda >= 2.0:
            performance_bonus = 3
        elif kda >= 1.0:
            performance_bonus = 0
        else:
            performance_bonus = -3
        
        # 최종 레이팅
        final_rating = max(0, new_rating + performance_bonus)
        total_change = final_rating - current_rating
        
        return final_rating, total_change


class GameMechanics:
    """
    게임 메커니즘 통합 관리 클래스
    전투, 보상, 레이팅 시스템을 통합 관리합니다.
    """
    
    def __init__(self):
        self.combat_system = CombatSystem()
        self.reward_system = RewardSystem()
        self.rating_system = EloRatingSystem()
        
        # 게임 세션 관리
        self.match_start_time = time.time()
        self.active_players: Dict[str, Dict] = {}  # player_id: player_data
        
    def update(self, delta_time: float = 0.016) -> Dict:
        """
        게임 메커니즘 업데이트 (매 프레임)
        
        Returns:
            업데이트 결과 (충돌, 제거된 미사일 등)
        """
        # 미사일 업데이트
        removed_missiles = self.combat_system.update_missiles(delta_time)
        
        # 충돌 체크
        targets = {
            player_id: {
                'position': data.get('position', [0, 0, 0]),
                'radius': 2.0
            }
            for player_id, data in self.active_players.items()
            if data.get('is_alive', True)
        }
        
        collisions = self.combat_system.check_all_collisions(targets)
        
        return {
            'removed_missiles': removed_missiles,
            'collisions': collisions,
            'active_missiles': self.combat_system.get_all_missiles()
        }
    
    def register_player(self, player_id: str, player_data: Dict) -> None:
        """플레이어 등록"""
        self.active_players[player_id] = player_data
    
    def unregister_player(self, player_id: str) -> None:
        """플레이어 등록 해제"""
        if player_id in self.active_players:
            del self.active_players[player_id]
    
    def update_player_position(self, player_id: str, position: List[float]) -> None:
        """플레이어 위치 업데이트"""
        if player_id in self.active_players:
            self.active_players[player_id]['position'] = position
    
    def get_match_duration(self) -> float:
        """현재 매치 진행 시간 (초)"""
        return time.time() - self.match_start_time
    
    def reset_match(self) -> None:
        """매치 초기화"""
        self.combat_system.clear_missiles()
        self.match_start_time = time.time()
        self.active_players.clear()
