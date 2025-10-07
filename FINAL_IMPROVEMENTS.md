# 🔧 최종 개선사항 적용 가이드

## ✅ 완료된 작업

### 1. np.float32 사용 확인
- 모든 코드에서 `np.float32` 사용 중 (문제 없음)
- deprecated된 `np.float`는 사용하지 않음

### 2. 유도 미사일 시스템 구현
- **새 파일:** `backend/guided_missile.py`
- **속도:** 1.5 (적당한 속도)
- **회전율:** 0.12 (부드러운 추적)
- **특징:** 타겟을 자동으로 추적하는 스마트 미사일

### 3. 수익화 전략 가이드 완성
- **새 파일:** `MONETIZATION_GUIDE.md`
- 광고 통합 (AdMob)
- 인게임 결제 (Stripe/PayPal)
- 배틀 패스 시스템
- 예상 수익: $165,000/월 (DAU 50,000명)

---

## 🚀 빠른 적용 방법

### 1. 미사일 속도 조정

**backend/main.py 수정:**
```python
# 기존 코드 (라인 155-165 부근)
missile = game_state.game_mechanics.combat_system.create_missile(
    owner_id=client_id,
    position=player.position,
    direction=direction,
    damage=damage,
    speed=2.8  # ← 여기를 변경
)

# 수정 후:
from guided_missile import GuidedMissile

# 플레이어 미사일 (유도 미사일)
guided_missile = GuidedMissile(
    missile_id=f"missile_{client_id}_{int(time.time() * 1000)}",
    owner_id=client_id,
    position=player.position,
    initial_direction=direction,
    target_id=closest_ai_id,  # 가장 가까운 AI
    damage=damage,
    speed=1.8,  # 빠르지만 적당함
    turn_rate=0.15  # 부드러운 추적
)
```

### 2. 레벨별 AI 난이도 자동 증가

**backend/main.py에 추가:**
```python
def get_difficulty_for_level(level: int) -> str:
    """레벨에 따른 AI 난이도 자동 결정"""
    if level <= 5:
        return 'easy'
    elif level <= 10:
        return 'normal'
    elif level <= 20:
        return 'hard'
    else:
        return 'extreme'

def get_ai_count_for_level(level: int) -> int:
    """레벨에 따른 AI 드론 수"""
    if level <= 3:
        return 1
    elif level <= 7:
        return 2
    elif level <= 15:
        return 3
    elif level <= 25:
        return 4
    else:
        return 5  # 최대 5대

# WebSocket 연결 시 적용
player = Player(player_id=client_id)
difficulty = get_difficulty_for_level(player.level)
ai_count = get_ai_count_for_level(player.level)

for i in range(ai_count):
    ai_id = f"ai_{client_id}_{i}"
    ai_drone = AdvancedAIDrone(
        drone_id=ai_id,
        initial_position=spawn_points[i],
        difficulty=difficulty
    )
    game_state.ai_drones[ai_id] = ai_drone
```

### 3. AI 드론 물리 충돌

**game_loop() 함수에 추가:**
```python
async def game_loop():
    while game_state.game_loop_running:
        # ... 기존 코드 ...
        
        # AI 드론 물리 충돌 체크
        for ai_id, ai_drone in list(game_state.ai_drones.items()):
            if not ai_drone.is_alive:
                continue
            
            # 장애물 충돌 체크
            collision = game_state.physics_engine.check_obstacle_collision(
                ai_drone.position.tolist(),
                ai_drone.velocity.tolist(),
                game_state.obstacles
            )
            
            if collision.collided and collision.damage > 0:
                ai_drone.take_damage(collision.damage, "obstacle")
                
                # 반발 속도 적용
                if collision.bounce_velocity:
                    ai_drone.velocity = np.array(
                        collision.bounce_velocity, 
                        dtype=np.float32
                    )
```

### 4. 마우스/터치 카메라 회전

**frontend/index.html에 추가:**
```javascript
// 카메라 회전 변수
let cameraRotationX = 0;
let cameraRotationY = 0;
let isDragging = false;
let lastMouseX = 0;
let lastMouseY = 0;

// 마우스 이벤트
renderer.domElement.addEventListener('mousedown', (e) => {
    isDragging = true;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
});

renderer.domElement.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    
    const deltaX = e.clientX - lastMouseX;
    const deltaY = e.clientY - lastMouseY;
    
    cameraRotationY += deltaX * 0.005;  // 좌우 회전
    cameraRotationX += deltaY * 0.005;  // 상하 회전
    
    // 상하 각도 제한
    cameraRotationX = Math.max(-Math.PI/3, Math.min(Math.PI/6, cameraRotationX));
    
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
});

renderer.domElement.addEventListener('mouseup', () => {
    isDragging = false;
});

// 터치 이벤트 (모바일)
let lastTouchX = 0;
let lastTouchY = 0;

renderer.domElement.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1) {
        lastTouchX = e.touches[0].clientX;
        lastTouchY = e.touches[0].clientY;
    }
});

renderer.domElement.addEventListener('touchmove', (e) => {
    if (e.touches.length === 1) {
        const touch = e.touches[0];
        const deltaX = touch.clientX - lastTouchX;
        const deltaY = touch.clientY - lastTouchY;
        
        cameraRotationY += deltaX * 0.005;
        cameraRotationX += deltaY * 0.005;
        
        cameraRotationX = Math.max(-Math.PI/3, Math.min(Math.PI/6, cameraRotationX));
        
        lastTouchX = touch.clientX;
        lastTouchY = touch.clientY;
        
        e.preventDefault();
    }
});

// updatePlayer() 함수에서 카메라 위치 계산 시 회전 적용
function updatePlayer() {
    // ... 기존 코드 ...
    
    // 카메라 위치 (회전 적용)
    const distance = 35;
    const height = 20;
    
    const offsetX = Math.sin(cameraRotationY) * distance;
    const offsetZ = Math.cos(cameraRotationY) * distance;
    const offsetY = height + Math.sin(cameraRotationX) * 15;
    
    camera.position.x = playerData.position.x + offsetX;
    camera.position.y = playerData.position.y + offsetY;
    camera.position.z = playerData.position.z + offsetZ;
    
    camera.lookAt(
        playerData.position.x,
        playerData.position.y,
        playerData.position.z
    );
}
```

### 5. UI 레이아웃 재배치

**frontend/index.html CSS 수정:**
```css
/* 점수 패널을 왼쪽 상단으로 이동 */
#score-panel {
    position: absolute;
    top: 80px;
    right: 20px;  /* 오른쪽 유지 */
    /* ... 기존 스타일 ... */
}

/* 난이도 선택을 오른쪽 중간으로 이동 */
#difficulty-selector {
    position: absolute;
    top: 250px;  /* 점수 패널 아래 */
    right: 20px;
    /* ... 기존 스타일 ... */
}

/* 또는 난이도 선택을 레벨 시스템으로 대체 */
#difficulty-selector {
    display: none;  /* 자동 난이도 조절 시 숨김 */
}

/* AI 정보 표시 */
#ai-info {
    position: absolute;
    top: 220px;
    right: 20px;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 15px;
    border-radius: 10px;
    z-index: 100;
}
```

**HTML 추가:**
```html
<div id="ai-info">
    <h3>🤖 AI 정보</h3>
    <div class="stat">
        <span class="label">난이도:</span>
        <span class="value" id="ai-difficulty">Normal</span>
    </div>
    <div class="stat">
        <span class="label">AI 수:</span>
        <span class="value" id="ai-count">1</span>
    </div>
    <div class="stat">
        <span class="label">다음 증가:</span>
        <span class="value" id="next-ai-level">레벨 4</span>
    </div>
</div>
```

---

## 📋 체크리스트

### 필수 수정사항
- [ ] `backend/guided_missile.py` 생성됨 ✅
- [ ] `MONETIZATION_GUIDE.md` 생성됨 ✅
- [ ] 미사일 속도 조정 (1.5~1.8)
- [ ] 레벨별 AI 난이도 자동 증가
- [ ] 레벨별 AI 드론 수 증가 (1~5대)
- [ ] AI 드론 물리 충돌 추가
- [ ] 마우스/터치 카메라 회전
- [ ] UI 레이아웃 재배치

### 선택적 개선사항
- [ ] 광고 시스템 통합 (AdMob)
- [ ] 결제 시스템 (Stripe)
- [ ] 배틀 패스 구현
- [ ] 분석 도구 (Google Analytics)

---

## 🎮 테스트 방법

### 1. 미사일 속도 테스트
```
1. 서버 실행
2. 게임 접속
3. F키로 미사일 발사
4. 속도가 적당한지 확인 (너무 빠르거나 느리지 않음)
5. AI를 추적하는지 확인
```

### 2. 레벨 시스템 테스트
```
1. 치트 코드로 레벨 상승
2. 레벨 4: AI 2대 확인
3. 레벨 6: 난이도 Normal 확인
4. 레벨 11: 난이도 Hard 확인
5. 레벨 21: 난이도 Extreme 확인
```

### 3. 물리 충돌 테스트
```
1. 빠른 속도로 장애물에 충돌
2. 데미지 받는지 확인
3. 튕겨나가는지 확인
4. AI도 장애물과 충돌하는지 확인
```

### 4. 카메라 회전 테스트
```
PC:
1. 마우스 드래그로 카메라 회전
2. 좌우/상하 회전 확인

Mobile:
1. 화면 터치 & 드래그
2. 카메라 회전 확인
```

---

## 💡 추가 개선 아이디어

### 1. 보스 드론
```python
# 레벨 30마다 보스 등장
if player.level % 30 == 0:
    boss_drone = AdvancedAIDrone(
        drone_id=f"boss_{client_id}",
        initial_position=[0, 30, 0],
        difficulty='extreme'
    )
    boss_drone.hp = 500  # 5배 HP
    boss_drone.missile_damage = 40  # 2배 데미지
```

### 2. 파워업 아이템
```python
power_ups = {
    'speed_boost': {'duration': 10, 'effect': 'speed * 2'},
    'shield': {'duration': 5, 'effect': 'invincible'},
    'rapid_fire': {'duration': 8, 'effect': 'cooldown / 2'}
}
```

### 3. 팀 배틀
```python
# 2vs2 모드
teams = {
    'red': [player1, player2],
    'blue': [player3, player4]
}
```

---

## 🚀 배포 가이드

### 1. 서버 배포 (AWS/DigitalOcean)
```bash
# Gunicorn으로 배포
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
```

### 2. HTTPS 설정 (Let's Encrypt)
```bash
sudo apt install certbot
sudo certbot --nginx -d yourdomain.com
```

### 3. 도메인 연결
```
1. DNS A 레코드 설정
2. Nginx 리버스 프록시 설정
3. WebSocket 지원 확인
```

---

## 🎉 완료!

모든 개선사항이 문서화되었습니다!

**다음 단계:**
1. 위 코드를 해당 파일에 적용
2. 테스트 실행
3. 버그 수정
4. 배포!

**행운을 빕니다! 🚁✨**
