"""
플레이어 데이터 관리 모듈
플레이어의 스탯, 레벨, 티어, 업그레이드 정보를 관리합니다.
"""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json


# 티어 정의
TIERS = [
    {'name': 'Bronze', 'display': '브론즈', 'min_rating': 0, 'max_rating': 999, 'color': '#cd7f32'},
    {'name': 'Silver', 'display': '실버', 'min_rating': 1000, 'max_rating': 1499, 'color': '#c0c0c0'},
    {'name': 'Gold', 'display': '골드', 'min_rating': 1500, 'max_rating': 1999, 'color': '#ffd700'},
    {'name': 'Platinum', 'display': '플래티넘', 'min_rating': 2000, 'max_rating': 2499, 'color': '#e5e4e2'},
    {'name': 'Diamond', 'display': '다이아몬드', 'min_rating': 2500, 'max_rating': 2999, 'color': '#b9f2ff'},
    {'name': 'Master', 'display': '마스터', 'min_rating': 3000, 'max_rating': 3499, 'color': '#9d4edd'},
    {'name': 'Legend', 'display': '레전드', 'min_rating': 3500, 'max_rating': 999999, 'color': '#ff006e'}
]


@dataclass
class PlayerStats:
    """플레이어 통계"""
    kills: int = 0
    deaths: int = 0
    games_played: int = 0
    wins: int = 0
    total_damage_dealt: float = 0
    total_damage_taken: float = 0
    missiles_fired: int = 0
    missiles_hit: int = 0
    
    def get_kda(self) -> float:
        """KDA (Kill/Death/Assist) 비율 계산"""
        if self.deaths == 0:
            return float(self.kills)
        return round(self.kills / self.deaths, 2)
    
    def get_accuracy(self) -> float:
        """명중률 계산"""
        if self.missiles_fired == 0:
            return 0.0
        return round((self.missiles_hit / self.missiles_fired) * 100, 1)
    
    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.games_played == 0:
            return 0.0
        return round((self.wins / self.games_played) * 100, 1)


@dataclass
class PlayerUpgrades:
    """플레이어 업그레이드"""
    speed_level: int = 0
    armor_level: int = 0
    damage_level: int = 0
    fire_rate_level: int = 0
    
    # 최대 레벨
    MAX_LEVEL = 10
    
    # 레벨당 증가량
    SPEED_PER_LEVEL = 0.05  # 5% 속도 증가
    ARMOR_PER_LEVEL = 10    # 10 HP 증가
    DAMAGE_PER_LEVEL = 5    # 5 데미지 증가
    FIRE_RATE_PER_LEVEL = 0.05  # 쿨다운 5% 감소
    
    def get_speed_bonus(self) -> float:
        """속도 보너스 계산"""
        return 1.0 + (self.speed_level * self.SPEED_PER_LEVEL)
    
    def get_max_hp_bonus(self) -> int:
        """최대 HP 보너스 계산"""
        return 100 + (self.armor_level * self.ARMOR_PER_LEVEL)
    
    def get_damage_bonus(self) -> int:
        """데미지 보너스 계산"""
        return 20 + (self.damage_level * self.DAMAGE_PER_LEVEL)
    
    def get_fire_rate_bonus(self) -> float:
        """발사 속도 보너스 계산 (쿨다운 감소)"""
        return 1.0 - (self.fire_rate_level * self.FIRE_RATE_PER_LEVEL)
    
    def can_upgrade(self, upgrade_type: str) -> bool:
        """업그레이드 가능 여부 확인"""
        level = getattr(self, f"{upgrade_type}_level", 0)
        return level < self.MAX_LEVEL
    
    def upgrade(self, upgrade_type: str) -> bool:
        """업그레이드 실행"""
        if self.can_upgrade(upgrade_type):
            current_level = getattr(self, f"{upgrade_type}_level", 0)
            setattr(self, f"{upgrade_type}_level", current_level + 1)
            return True
        return False
    
    def get_upgrade_cost(self, upgrade_type: str) -> int:
        """업그레이드 비용 계산"""
        level = getattr(self, f"{upgrade_type}_level", 0)
        # 레벨이 높아질수록 비용 증가
        return 100 + (level * 50)


class Player:
    """
    플레이어 클래스
    게임 내 모든 플레이어 정보를 관리합니다.
    """
    
    def __init__(self, player_id: str, username: str = None):
        self.player_id = player_id
        self.username = username or player_id
        
        # 기본 정보
        self.level = 1
        self.experience = 0
        self.rating = 1000  # ELO 레이팅
        self.coins = 0      # 게임 화폐
        
        # 전투 상태
        self.hp = 100
        self.max_hp = 100
        self.is_alive = True
        self.position = [0, 10, 30]
        self.velocity = [0, 0, 0]
        
        # 전투 정보
        self.last_missile_time = 0
        self.missile_cooldown = 1.0  # 초
        
        # 통계 및 업그레이드
        self.stats = PlayerStats()
        self.upgrades = PlayerUpgrades()
        
        # 세션 정보
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        
        # 현재 게임 세션 점수
        self.session_kills = 0
        self.session_score = 0
    
    def get_tier(self) -> Dict:
        """현재 티어 정보 가져오기"""
        for tier in TIERS:
            if tier['min_rating'] <= self.rating <= tier['max_rating']:
                return tier
        return TIERS[0]  # 기본값: 브론즈
    
    def get_tier_progress(self) -> float:
        """현재 티어 내 진행도 (0~100%)"""
        tier = self.get_tier()
        tier_range = tier['max_rating'] - tier['min_rating']
        current_progress = self.rating - tier['min_rating']
        return min(100, (current_progress / tier_range) * 100)
    
    def get_experience_to_next_level(self) -> int:
        """다음 레벨까지 필요한 경험치"""
        return self.level * 100
    
    def add_experience(self, amount: int) -> List[str]:
        """
        경험치 추가 및 레벨업 처리
        Returns: 레벨업 시 보상 메시지 리스트
        """
        self.experience += amount
        rewards = []
        
        # 레벨업 체크
        while self.experience >= self.get_experience_to_next_level():
            self.experience -= self.get_experience_to_next_level()
            self.level += 1
            
            # 레벨업 보상
            coin_reward = self.level * 50
            self.coins += coin_reward
            
            rewards.append(f"레벨 {self.level} 달성!")
            rewards.append(f"+ {coin_reward} 코인 획득!")
            
            # 특정 레벨에서 추가 보상
            if self.level % 5 == 0:
                bonus_coins = 500
                self.coins += bonus_coins
                rewards.append(f"🎉 레벨 {self.level} 달성 보너스: +{bonus_coins} 코인!")
        
        return rewards
    
    def add_rating(self, amount: int) -> Dict:
        """
        레이팅 추가/감소 및 티어 변동 체크
        Returns: 티어 변동 정보
        """
        old_tier = self.get_tier()
        self.rating = max(0, self.rating + amount)  # 레이팅은 0 이하로 떨어지지 않음
        new_tier = self.get_tier()
        
        tier_changed = old_tier['name'] != new_tier['name']
        promoted = tier_changed and new_tier['min_rating'] > old_tier['min_rating']
        
        return {
            'tier_changed': tier_changed,
            'promoted': promoted,
            'old_tier': old_tier,
            'new_tier': new_tier,
            'rating': self.rating
        }
    
    def take_damage(self, damage: int, attacker_id: str = None) -> Dict:
        """
        데미지 받기
        Returns: 전투 결과 정보
        """
        self.hp = max(0, self.hp - damage)
        self.stats.total_damage_taken += damage
        
        result = {
            'hp': self.hp,
            'is_alive': self.hp > 0,
            'damage_taken': damage,
            'attacker_id': attacker_id
        }
        
        if self.hp <= 0 and self.is_alive:
            self.is_alive = False
            self.stats.deaths += 1
            result['died'] = True
        
        return result
    
    def deal_damage(self, target_id: str, damage: int) -> None:
        """데미지 입히기 (통계 기록)"""
        self.stats.total_damage_dealt += damage
    
    def record_kill(self, target_id: str) -> Dict:
        """
        킬 기록 및 보상 지급
        Returns: 보상 정보
        """
        self.stats.kills += 1
        self.session_kills += 1
        
        # 킬 보상
        score_reward = 100
        exp_reward = 50
        coin_reward = 10
        
        self.session_score += score_reward
        self.coins += coin_reward
        
        # 경험치 추가 (레벨업 가능)
        level_up_rewards = self.add_experience(exp_reward)
        
        return {
            'kills': self.stats.kills,
            'session_kills': self.session_kills,
            'score_reward': score_reward,
            'exp_reward': exp_reward,
            'coin_reward': coin_reward,
            'level_up_rewards': level_up_rewards
        }
    
    def respawn(self) -> None:
        """리스폰"""
        self.hp = self.max_hp
        self.is_alive = True
        # 랜덤 위치로 리스폰 (향후 구현)
        self.position = [0, 10, 30]
        self.velocity = [0, 0, 0]
    
    def can_fire_missile(self, current_time: float) -> bool:
        """미사일 발사 가능 여부 체크 (쿨다운)"""
        cooldown = self.missile_cooldown * self.upgrades.get_fire_rate_bonus()
        return (current_time - self.last_missile_time) >= cooldown
    
    def fire_missile(self, current_time: float) -> bool:
        """미사일 발사"""
        if self.can_fire_missile(current_time):
            self.last_missile_time = current_time
            self.stats.missiles_fired += 1
            return True
        return False
    
    def record_missile_hit(self) -> None:
        """미사일 명중 기록"""
        self.stats.missiles_hit += 1
    
    def end_game_session(self, won: bool) -> Dict:
        """
        게임 세션 종료 및 보상 계산
        Returns: 최종 보상 정보
        """
        self.stats.games_played += 1
        if won:
            self.stats.wins += 1
        
        # 레이팅 변동 계산
        rating_change = 25 if won else -15
        if self.session_kills >= 5:
            rating_change += 10  # 5킬 이상 시 보너스
        
        tier_result = self.add_rating(rating_change)
        
        # 최종 보상
        final_coins = self.session_score // 10  # 점수 10당 1코인
        self.coins += final_coins
        
        result = {
            'session_score': self.session_score,
            'session_kills': self.session_kills,
            'rating_change': rating_change,
            'tier_result': tier_result,
            'coins_earned': final_coins,
            'total_coins': self.coins,
            'stats': {
                'kda': self.stats.get_kda(),
                'accuracy': self.stats.get_accuracy(),
                'win_rate': self.stats.get_win_rate()
            }
        }
        
        # 세션 초기화
        self.session_kills = 0
        self.session_score = 0
        
        return result
    
    def to_dict(self) -> Dict:
        """플레이어 정보를 딕셔너리로 변환"""
        return {
            'player_id': self.player_id,
            'username': self.username,
            'level': self.level,
            'experience': self.experience,
            'exp_to_next': self.get_experience_to_next_level(),
            'rating': self.rating,
            'tier': self.get_tier(),
            'tier_progress': self.get_tier_progress(),
            'coins': self.coins,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'is_alive': self.is_alive,
            'position': self.position,
            'velocity': self.velocity,
            'stats': {
                'kills': self.stats.kills,
                'deaths': self.stats.deaths,
                'kda': self.stats.get_kda(),
                'accuracy': self.stats.get_accuracy(),
                'win_rate': self.stats.get_win_rate(),
                'games_played': self.stats.games_played,
                'wins': self.stats.wins
            },
            'upgrades': {
                'speed': {
                    'level': self.upgrades.speed_level,
                    'bonus': self.upgrades.get_speed_bonus(),
                    'cost': self.upgrades.get_upgrade_cost('speed'),
                    'can_upgrade': self.upgrades.can_upgrade('speed')
                },
                'armor': {
                    'level': self.upgrades.armor_level,
                    'bonus': self.upgrades.get_max_hp_bonus(),
                    'cost': self.upgrades.get_upgrade_cost('armor'),
                    'can_upgrade': self.upgrades.can_upgrade('armor')
                },
                'damage': {
                    'level': self.upgrades.damage_level,
                    'bonus': self.upgrades.get_damage_bonus(),
                    'cost': self.upgrades.get_upgrade_cost('damage'),
                    'can_upgrade': self.upgrades.can_upgrade('damage')
                },
                'fire_rate': {
                    'level': self.upgrades.fire_rate_level,
                    'bonus': self.upgrades.get_fire_rate_bonus(),
                    'cost': self.upgrades.get_upgrade_cost('fire_rate'),
                    'can_upgrade': self.upgrades.can_upgrade('fire_rate')
                }
            },
            'session': {
                'kills': self.session_kills,
                'score': self.session_score
            }
        }
