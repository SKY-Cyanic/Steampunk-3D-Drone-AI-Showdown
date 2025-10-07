# 🚁 3D 드론 AI 대전 시뮬레이터

실시간 3D 웹 게임 프로토타입 - Three.js, Python FastAPI, PyTorch를 활용한 AI 대전 시뮬레이터

![Game Preview](https://img.shields.io/badge/Status-Prototype-orange)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Three.js](https://img.shields.io/badge/Three.js-r128-green)
![PyTorch](https://img.shields.io/badge/PyTorch-2.1.0-red)

---

## 📋 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [핵심 기술 개념](#-핵심-기술-개념)
3. [프로젝트 구조](#-프로젝트-구조)
4. [설치 및 실행](#-설치-및-실행)
5. [게임 플레이](#-게임-플레이)
6. [기술 상세](#-기술-상세)
7. [향후 발전 방향](#-향후-발전-방향)
8. [라이선스](#-라이선스)

---

## 🎯 프로젝트 개요

### 최상위 목표
사용자들이 AI와의 치열한 3D 드론 대전을 통해 경쟁심을 느끼고, 더 높은 티어로 올라가기 위해 계속해서 게임에 접속하게 만들어 **광고 수익을 극대화하는 웹 게임** 제작

### MVP (Minimum Viable Product)
- ✅ **플레이어 조종**: 키보드로 조종하는 3D 드론
- ✅ **AI 대전**: PyTorch 기반 AI가 조종하는 적 드론
- ✅ **실시간 통신**: WebSocket을 통한 서버-클라이언트 동기화
- ✅ **3D 환경**: Three.js로 구현한 스팀펑크 스타일 배틀필드
- ✅ **장애물**: 톱니바퀴와 파이프가 있는 복잡한 지형

### 게임 컨셉
**Agar.io**나 **Slither.io**의 3D 전투 버전과 유사한 메커니즘:
- 간단한 조작으로 즉각적인 피드백
- AI의 실시간 반응으로 긴장감 조성
- 끊임없는 추격전과 회피 액션

---

## 🧠 핵심 기술 개념

### 1️⃣ Three.js의 3대 핵심 요소

#### **Scene (장면)**
```javascript
scene = new THREE.Scene();
```
- 모든 3D 객체(드론, 장애물, 조명)를 담는 컨테이너
- 무대(Stage)라고 생각하면 이해하기 쉬움
- 배경색, 안개 효과 등도 Scene에서 설정

#### **Camera (카메라)**
```javascript
camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
```
- 어떤 시점에서 장면을 볼지 결정
- PerspectiveCamera: 원근감이 있는 카메라 (일반적인 3D 게임 시점)
- 플레이어 드론을 따라다니며 3인칭 시점 제공

#### **Renderer (렌더러)**
```javascript
renderer = new THREE.WebGLRenderer({ antialias: true });
```
- Scene과 Camera를 받아서 실제로 화면에 그림
- WebGL을 사용해 GPU 가속으로 고성능 렌더링
- 매 프레임마다 `renderer.render(scene, camera)` 호출

### 2️⃣ WebSocket 실시간 통신

#### **기존 HTTP vs WebSocket**

| 구분 | HTTP | WebSocket |
|------|------|-----------|
| 연결 방식 | 요청-응답 (단방향) | 지속적 연결 (양방향) |
| 오버헤드 | 매번 새로운 연결 | 한 번 연결 후 유지 |
| 실시간성 | ❌ 폴링 필요 | ✅ 즉시 전송 |
| 사용 사례 | 웹사이트, API | 게임, 채팅, 실시간 대시보드 |

#### **통신 흐름**
```
[브라우저]                    [FastAPI 서버]
    |                              |
    |--- WebSocket 연결 요청 -----> |
    | <--- 연결 승인 (client_id) ---|
    |                              |
    |--- 플레이어 위치 전송 -------> |
    |                              | (AI 계산)
    | <--- AI 드론 위치 수신 --------|
    |                              |
   (매 프레임마다 반복, 약 60fps)
```

### 3️⃣ PyTorch AI 의사결정

현재는 **규칙 기반 추적 로직**을 사용하지만, PyTorch 구조를 포함하여 향후 **강화학습**으로 쉽게 발전 가능:

```python
# 현재: 간단한 벡터 계산으로 플레이어 추적
direction_to_player = target_position - self.position
desired_velocity = direction_normalized * self.max_speed

# 향후: 신경망으로 복잡한 전략 학습
state = torch.FloatTensor([position, velocity, player_position])
action = neural_network(state)  # 강화학습으로 학습된 최적의 행동
```

---

## 📁 프로젝트 구조

```
3d-drone-ai-battle/
│
├── backend/                    # 백엔드 (Python)
│   ├── main.py                # FastAPI 서버, WebSocket 엔드포인트
│   └── ai_drone.py            # PyTorch 기반 AI 드론 로직
│
├── frontend/                   # 프론트엔드 (HTML/JavaScript)
│   └── index.html             # Three.js 3D 게임 화면
│
├── requirements.txt            # Python 라이브러리 목록
└── README.md                   # 이 파일
```

### 파일별 역할

| 파일 | 역할 | 주요 기술 |
|------|------|----------|
| `backend/main.py` | 게임 서버, WebSocket 통신 관리 | FastAPI, WebSocket |
| `backend/ai_drone.py` | AI 의사결정 로직 | PyTorch, NumPy |
| `frontend/index.html` | 3D 게임 화면, 플레이어 조종 | Three.js, WebSocket |
| `requirements.txt` | 필요한 Python 패키지 목록 | - |

---

## 🚀 설치 및 실행

### 필수 요구사항
- **Python 3.8 이상**
- **모던 웹 브라우저** (Chrome, Firefox, Edge 권장)

### 1단계: 저장소 클론
```bash
git clone <repository-url>
cd 3d-drone-ai-battle
```

### 2단계: Python 가상환경 생성 (권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3단계: 라이브러리 설치
```bash
pip install -r requirements.txt
```

설치되는 라이브러리:
- `fastapi==0.104.1` - 웹 서버 프레임워크
- `uvicorn[standard]==0.24.0` - ASGI 서버 (FastAPI 실행용)
- `websockets==12.0` - WebSocket 통신
- `torch==2.1.0` - PyTorch (AI 로직)
- `numpy==1.26.0` - 수치 계산

### 4단계: 서버 실행
```bash
cd backend
python main.py
```

또는:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

성공하면 다음과 같은 메시지가 출력됩니다:
```
============================================================
🚁 3D 드론 AI 대전 시뮬레이터 서버 시작!
============================================================
서버 주소: http://localhost:8000
WebSocket: ws://localhost:8000/ws
------------------------------------------------------------
브라우저에서 http://localhost:8000 을 열어주세요!
============================================================
```

### 5단계: 게임 플레이
웹 브라우저에서 접속:
```
http://localhost:8000
```

---

## 🎮 게임 플레이

### 조작법

| 키 | 동작 |
|----|------|
| **W** | 전진 |
| **S** | 후진 |
| **A** | 좌측 이동 |
| **D** | 우측 이동 |
| **Space** | 상승 |
| **Shift** | 하강 |

### 게임 화면 구성

1. **왼쪽 상단**: 드론 정보 패널
   - 플레이어 위치 (x, y, z 좌표)
   - AI와의 거리
   - 현재 속도
   - FPS (초당 프레임)

2. **오른쪽 상단**: 서버 연결 상태
   - 🟢 녹색: 정상 연결
   - 🔴 빨간색: 연결 끊김

3. **왼쪽 하단**: 조작법 가이드

4. **중앙**: 3D 게임 화면
   - 녹색 드론: 플레이어 (당신)
   - 빨간색 드론: AI
   - 갈색 톱니바퀴, 회색 파이프: 장애물

### 게임 목표 (현재 프로토타입)
- AI 드론이 당신을 추적합니다
- 장애물을 활용해 AI를 따돌리세요
- AI와의 거리를 유지하며 생존하세요

---

## 🔧 기술 상세

### 프론트엔드 (Three.js)

#### 드론 모델링
```javascript
// 육면체 몸체 + 4개의 원통형 프로펠러
const bodyGeometry = new THREE.BoxGeometry(2, 0.5, 2);
const propellerGeometry = new THREE.CylinderGeometry(0.5, 0.5, 0.1, 8);
```

#### 물리 시뮬레이션
```javascript
// 가속도와 항력을 적용한 부드러운 이동
playerVelocity.x += acceleration;
playerPosition.x += playerVelocity.x;
playerVelocity.x *= DRAG;  // 감속 효과
```

#### 카메라 추적
```javascript
// 플레이어를 따라다니는 3인칭 시점
camera.position.set(
    playerPosition.x,
    playerPosition.y + 15,  // 위에서
    playerPosition.z + 25   // 뒤에서
);
camera.lookAt(playerPosition.x, playerPosition.y, playerPosition.z);
```

### 백엔드 (FastAPI + PyTorch)

#### WebSocket 엔드포인트
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 클라이언트와 실시간 통신
```

#### AI 추적 알고리즘
```python
# 플레이어를 향한 방향 벡터 계산
direction_to_player = target_position - self.position
distance = np.linalg.norm(direction_to_player)

# 정규화된 방향으로 이동
direction_normalized = direction_to_player / distance
desired_velocity = direction_normalized * self.max_speed
```

#### 장애물 회피
```python
# 장애물과 가까우면 반대 방향으로 힘 적용
if dist_to_obstacle < danger_radius:
    avoidance_force -= (to_obstacle / dist) * repulsion_strength
```

---

## 🚀 향후 발전 방향

### Phase 1: 게임 메커니즘 확장 (1-2주)

#### 1. **전투 시스템**
```javascript
// 미사일 발사 기능
if (keys['KeyF']) {
    fireMissile(playerDrone.position, targetDirection);
}
```
- 미사일/레이저 발사 기능
- 체력(HP) 시스템
- 충돌 감지 및 대미지 처리
- 폭발 이펙트

#### 2. **점수 및 보상 시스템**
```python
player_score += 100  # AI 격추 시
player_level = calculate_level(player_score)
```
- AI 격추 시 점수 획득
- 레벨업 시스템
- 업그레이드 (속도, 방어력, 공격력)
- 인게임 재화 및 상점

#### 3. **티어 시스템**
```python
TIERS = ['브론즈', '실버', '골드', '플래티넘', '다이아몬드', '레전드']
player_tier = get_tier_from_rating(player_rating)
```
- ELO 레이팅 시스템 도입
- 티어별 보상 (스킨, 이펙트)
- 리더보드 (주간/월간 랭킹)
- 티어 승급/강등 애니메이션

### Phase 2: AI 고도화 (2-4주)

#### 강화학습 도입
```python
# Deep Q-Network (DQN) 구현
class DQNAgent:
    def __init__(self):
        self.model = self._build_model()
        self.memory = ReplayBuffer(10000)
    
    def train(self, state, action, reward, next_state):
        # 경험 재생 기반 학습
        self.memory.store(state, action, reward, next_state)
        batch = self.memory.sample(32)
        loss = self._compute_loss(batch)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
```

**학습 보상 설계:**
- (+) 플레이어에게 가까이 가기
- (+) 플레이어를 명중시키기
- (-) 장애물에 충돌
- (-) 플레이어의 공격에 맞기
- (+) 회피 기동 성공

#### 다양한 AI 난이도
```python
AI_PRESETS = {
    'easy': {'max_speed': 0.2, 'reaction_time': 0.5},
    'normal': {'max_speed': 0.3, 'reaction_time': 0.3},
    'hard': {'max_speed': 0.5, 'reaction_time': 0.1},
    'extreme': {'model': 'trained_dqn.pth'}  # 강화학습 모델
}
```

### Phase 3: 멀티플레이어 (4-8주)

```python
# 방 시스템
class GameRoom:
    def __init__(self, room_id, max_players=4):
        self.players = {}
        self.ai_drones = []
        self.game_state = {}
    
    def add_player(self, player_id, websocket):
        self.players[player_id] = websocket
    
    async def broadcast_game_state(self):
        # 모든 플레이어에게 게임 상태 전송
        pass
```

**기능:**
- 4명 동시 접속 배틀로얄
- 팀 대전 모드 (2vs2)
- 관전 모드
- 채팅 시스템

### Phase 4: 수익화 전략 (진행 중 적용)

#### 1. **광고 통합**
```javascript
// 게임 오버 시 보상형 광고
if (playerHP <= 0) {
    showRewardedAd(() => {
        // 부활 아이템 지급
        playerHP = 100;
        playerPosition = getRandomSpawnPoint();
    });
}
```
- Google AdSense 배너 광고 (게임 화면 하단)
- 보상형 동영상 광고 (부활, 부스터)
- 게임 오버 시 전면 광고

#### 2. **인게임 결제**
```javascript
const ITEMS = {
    premium_drone: { price: 4.99, benefits: '+20% 속도' },
    exp_booster: { price: 2.99, benefits: '2시간 동안 경험치 2배' },
    vip_pass: { price: 9.99, benefits: '광고 제거 + 전용 스킨' }
}
```
- 프리미엄 드론 스킨
- 경험치 부스터
- VIP 패스 (광고 제거)

#### 3. **배틀 패스 시스템**
```python
BATTLE_PASS = {
    'free_tier': [item1, item2, ...],  # 무료 보상
    'premium_tier': [item1, item2, ...],  # 유료 보상 ($9.99)
}
```
- 시즌별 배틀 패스 ($9.99)
- 50레벨 보상 체계
- 독점 스킨 및 이펙트

### Phase 5: 기술적 최적화 (지속적)

#### 성능 향상
```javascript
// 인스턴싱으로 많은 객체 효율적 렌더링
const instancedMesh = new THREE.InstancedMesh(geometry, material, 1000);

// LOD (Level of Detail) - 거리에 따라 모델 품질 조정
const lod = new THREE.LOD();
lod.addLevel(highPolyMesh, 0);
lod.addLevel(mediumPolyMesh, 50);
lod.addLevel(lowPolyMesh, 100);
```

#### 서버 스케일링
```python
# Redis를 이용한 세션 관리
redis_client = redis.Redis(host='localhost', port=6379)

# 여러 게임 서버 인스턴스 로드 밸런싱
# Kubernetes / Docker Swarm 활용
```

#### 데이터 분석
```python
# 플레이어 행동 로깅
analytics.log_event('game_start', {
    'player_id': player_id,
    'tier': player_tier,
    'timestamp': datetime.now()
})

# 이탈률, 평균 플레이 시간, 인기 기능 분석
```

---

## 📈 예상 개발 타임라인

```
Week 1-2  : ✅ MVP 완성 (현재 단계)
Week 3-4  : 전투 시스템 + 점수 시스템
Week 5-6  : 티어 시스템 + UI/UX 개선
Week 7-8  : 강화학습 AI 초기 버전
Week 9-10 : 멀티플레이어 베타 테스트
Week 11-12: 광고 통합 + 수익화 구현
Week 13+  : 정식 출시 + 마케팅
```

---

## 🎨 디자인 발전 방향

### 현재 (프로토타입)
- 기본 도형 (큐브, 실린더)
- 단순 색상

### 향후
- **3D 모델**: Blender로 제작한 정교한 드론 모델
- **텍스처**: 금속, 녹, 먼지 효과
- **파티클 시스템**: 추진 불꽃, 폭발, 연기
- **후처리 효과**: Bloom, 모션 블러, 피사계 심도
- **사운드**: 드론 프로펠러 소리, 미사일 발사음, 폭발음

```javascript
// Bloom 효과 (빛나는 효과)
const bloomPass = new THREE.UnrealBloomPass();
composer.addPass(bloomPass);

// 파티클 시스템 (추진 효과)
const particleSystem = new THREE.GPUParticleSystem({
    maxParticles: 250000
});
```

---

## 🐛 트러블슈팅

### 문제: 서버가 실행되지 않음
```bash
# 포트가 이미 사용 중일 때
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### 문제: WebSocket 연결 실패
- 방화벽 설정 확인
- 브라우저 콘솔에서 오류 메시지 확인
- `localhost` 대신 `127.0.0.1` 시도

### 문제: 낮은 FPS
```javascript
// 그림자 품질 낮추기
renderer.shadowMap.enabled = false;

// 안개 효과로 먼 거리 렌더링 줄이기
scene.fog = new THREE.Fog(0x1a1a2e, 30, 80);
```

---

## 🤝 기여 방법

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자유롭게 사용, 수정, 배포할 수 있습니다.

---

## 📞 연락처

프로젝트 관련 문의: [이메일 주소]

프로젝트 링크: [GitHub Repository URL]

---

## 🙏 감사의 말

- **Three.js**: 훌륭한 3D 라이브러리 제공
- **FastAPI**: 빠르고 현대적인 웹 프레임워크
- **PyTorch**: 강력한 딥러닝 프레임워크
- **Agar.io / Slither.io**: 게임 메커니즘 영감

---

## 🎓 학습 자료

### Three.js
- [공식 문서](https://threejs.org/docs/)
- [Three.js Journey](https://threejs-journey.com/)
- [Three.js Fundamentals](https://threejsfundamentals.org/)

### FastAPI
- [공식 문서](https://fastapi.tiangolo.com/)
- [Real Python - FastAPI Tutorial](https://realpython.com/fastapi-python-web-apis/)

### PyTorch 강화학습
- [PyTorch 공식 튜토리얼](https://pytorch.org/tutorials/)
- [Spinning Up in Deep RL](https://spinningup.openai.com/)
- [Deep Reinforcement Learning Hands-On](https://www.packtpub.com/product/deep-reinforcement-learning-hands-on-second-edition/9781838826994)

---

**⭐ 이 프로젝트가 마음에 드셨다면 Star를 눌러주세요!**

**Happy Coding! 🚁✨**
