# 🚀 웹사이트 배포 가이드

## 🎯 목표
**실제 웹사이트로 배포하여 검색 가능하고 링크로 공유 가능하게 만들기**

---

## 📋 배포 옵션

### ✅ 추천 방법: Railway (백엔드) + Vercel (프론트엔드)
- **장점:** 무료, 빠름, 간단, 자동 배포
- **비용:** 프리 티어로 시작 가능
- **시간:** 30분

### 대안 1: Render + Netlify
- **장점:** 무료, 간단
- **단점:** 첫 로딩이 느림 (cold start)

### 대안 2: DigitalOcean / AWS
- **장점:** 완전 제어, 고성능
- **단점:** 복잡, 유료

### 대안 3: Heroku
- **장점:** 간단
- **단점:** 최근 무료 플랜 종료

---

## 🚀 방법 1: Railway + Vercel (추천!)

### A. 백엔드 배포 (Railway)

#### 1단계: Railway 계정 생성
```
1. https://railway.app 접속
2. GitHub로 로그인
3. "New Project" 클릭
```

#### 2단계: 프로젝트 설정

**1) GitHub 연결**
```bash
# 1. GitHub에 코드 푸시
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_URL
git push -u origin main
```

**2) Railway에서 프로젝트 생성**
```
1. Railway 대시보드
2. "New Project" → "Deploy from GitHub repo"
3. 레포지토리 선택
```

#### 3단계: 환경 설정

**`railway.json` 생성** (프로젝트 루트에)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd backend && python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**`Procfile` 생성** (프로젝트 루트에)
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

**`nixpacks.toml` 생성** (프로젝트 루트에)
```toml
[phases.setup]
nixPkgs = ["python310", "pip"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = []

[start]
cmd = "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

#### 4단계: 환경 변수 설정

Railway 대시보드에서:
```
Settings → Variables

PORT = 8000
PYTHON_VERSION = 3.10
```

#### 5단계: 배포 확인
```
Deploy 후 URL 받기
예: https://your-app.railway.app
```

---

### B. 프론트엔드 배포 (Vercel)

#### 1단계: Vercel 계정 생성
```
1. https://vercel.com 접속
2. GitHub로 로그인
```

#### 2단계: 프론트엔드 분리

**`vercel.json` 생성** (프로젝트 루트에)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/index.html",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/frontend/index.html"
    }
  ],
  "env": {
    "BACKEND_URL": "https://your-backend.railway.app"
  }
}
```

#### 3단계: 프론트엔드 수정

**`frontend/index.html` 수정** (WebSocket URL)
```javascript
// 기존 (로컬)
const wsUrl = `ws://localhost:8000/ws`;

// 배포용 (환경 변수)
const BACKEND_URL = 'https://your-backend.railway.app';
const wsUrl = BACKEND_URL.replace('https', 'wss') + '/ws';
```

**또는 자동 감지:**
```javascript
function connectWebSocket() {
    // 개발: localhost, 배포: 실제 URL
    const isLocal = window.location.hostname === 'localhost';
    const backendUrl = isLocal 
        ? 'ws://localhost:8000' 
        : 'wss://your-backend.railway.app';
    
    const wsUrl = `${backendUrl}/ws`;
    websocket = new WebSocket(wsUrl);
    // ...
}
```

#### 4단계: Vercel 배포
```bash
# Vercel CLI 설치
npm install -g vercel

# 배포
cd your-project
vercel

# 프로덕션 배포
vercel --prod
```

**또는 Vercel 대시보드에서:**
```
1. "New Project"
2. GitHub 레포지토리 선택
3. Build Settings:
   - Framework Preset: Other
   - Root Directory: frontend
   - Output Directory: frontend
4. Deploy!
```

#### 5단계: URL 받기
```
배포 완료 후:
https://your-app.vercel.app
```

---

## 🔧 CORS 설정 (중요!)

### 백엔드 CORS 허용

**`backend/main.py` 수정:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="3D Drone Battle Simulator")

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://your-app.vercel.app",  # 프론트엔드 URL
        "*"  # 또는 모든 출처 허용 (개발용)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... 기존 코드 ...
```

---

## 🌐 커스텀 도메인 설정

### Vercel 도메인 설정

**1) 도메인 구매 (선택사항)**
```
- Namecheap: $8/년
- GoDaddy: $10/년
- Cloudflare: $8/년
```

**2) Vercel에 도메인 연결**
```
1. Vercel 대시보드 → 프로젝트
2. Settings → Domains
3. "Add Domain" 클릭
4. 도메인 입력 (예: dronebattle.com)
5. DNS 설정 (Vercel이 자동으로 안내)
```

**3) DNS 레코드 설정** (도메인 제공업체에서)
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

**또는:**
```
Type: A
Name: @
Value: 76.76.19.19
```

**4) SSL 인증서** (자동)
```
Vercel이 자동으로 Let's Encrypt SSL 설정
https:// 즉시 사용 가능
```

### Railway 커스텀 도메인

**1) Railway 도메인 설정**
```
1. Railway 대시보드 → 프로젝트
2. Settings → Domains
3. "Custom Domain" 클릭
4. 도메인 입력 (예: api.dronebattle.com)
```

**2) DNS 레코드**
```
Type: CNAME
Name: api
Value: your-app.railway.app
```

---

## 📊 SEO 최적화 (검색 가능하게)

### 메타 태그 추가

**`frontend/index.html` `<head>`에 추가:**
```html
<!-- SEO 메타 태그 -->
<meta name="description" content="🚁 3D 드론 AI 대전 - 초고속 전투 게임! 실시간 멀티플레이어 드론 전투, AI와의 대결, 레벨 업그레이드.">
<meta name="keywords" content="드론 게임, 3D 게임, AI 대전, 멀티플레이어, 온라인 게임, 웹 게임">
<meta name="author" content="Your Name">

<!-- Open Graph (소셜 미디어) -->
<meta property="og:title" content="🚁 3D 드론 AI 대전">
<meta property="og:description" content="초고속 전투! AI 드론과 실시간 대결하세요!">
<meta property="og:image" content="https://your-app.vercel.app/preview.png">
<meta property="og:url" content="https://your-app.vercel.app">
<meta property="og:type" content="website">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="🚁 3D 드론 AI 대전">
<meta name="twitter:description" content="초고속 전투! AI 드론과 실시간 대결하세요!">
<meta name="twitter:image" content="https://your-app.vercel.app/preview.png">

<!-- 파비콘 -->
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚁</text></svg>">
```

### Google Search Console 등록

**1) 사이트 소유권 확인**
```
1. https://search.google.com/search-console 접속
2. 속성 추가 → URL 입력
3. 소유권 확인 (HTML 파일 업로드 또는 메타 태그)
```

**2) Sitemap 제출**

**`frontend/sitemap.xml` 생성:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://your-app.vercel.app</loc>
    <lastmod>2025-10-07</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

**Search Console에서 제출:**
```
Sitemaps → 새 사이트맵 추가 → /sitemap.xml
```

### robots.txt 생성

**`frontend/robots.txt`:**
```
User-agent: *
Allow: /
Sitemap: https://your-app.vercel.app/sitemap.xml
```

---

## 📈 Analytics 추가

### Google Analytics 4

**`frontend/index.html` `<head>`에 추가:**
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YOUR_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-YOUR_ID');
  
  // 커스텀 이벤트
  function trackEvent(category, action, label) {
    gtag('event', action, {
      'event_category': category,
      'event_label': label
    });
  }
  
  // 킬 추적
  function trackKill() {
    trackEvent('Game', 'kill', 'AI_Killed');
  }
  
  // 레벨업 추적
  function trackLevelUp(level) {
    trackEvent('Game', 'level_up', `Level_${level}`);
  }
</script>
```

---

## 🔐 보안 설정

### 환경 변수 보호

**절대 GitHub에 올리지 말 것:**
```
.env
*.pem
*.key
secrets/
```

**`.gitignore` 확인:**
```
.env
__pycache__/
*.pyc
node_modules/
.vercel/
railway.json
```

### API 키 보호

**환경 변수 사용:**
```python
# backend/main.py
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "default-dev-key")
DATABASE_URL = os.environ.get("DATABASE_URL")
```

---

## 🎯 체크리스트

### 배포 전
- [ ] GitHub 레포지토리 생성
- [ ] 코드 푸시
- [ ] `.gitignore` 확인
- [ ] `requirements.txt` 최신화
- [ ] CORS 설정

### 백엔드 (Railway)
- [ ] Railway 계정 생성
- [ ] 프로젝트 생성
- [ ] 환경 변수 설정
- [ ] 배포 확인
- [ ] URL 받기

### 프론트엔드 (Vercel)
- [ ] Vercel 계정 생성
- [ ] WebSocket URL 수정
- [ ] 배포
- [ ] URL 받기
- [ ] 백엔드 연결 테스트

### SEO
- [ ] 메타 태그 추가
- [ ] 파비콘 설정
- [ ] Google Search Console 등록
- [ ] Sitemap 제출

### 도메인 (선택사항)
- [ ] 도메인 구매
- [ ] DNS 설정
- [ ] SSL 인증서 (자동)

---

## 💰 비용 예상

### 무료 티어
```
Railway: 월 $5 크레딧 (무료)
Vercel: Hobby 플랜 (무료)
→ 소규모 트래픽: 완전 무료!
```

### 유료 (트래픽 증가 시)
```
Railway Pro: $20/월
  - 무제한 배포
  - 8GB RAM
  
Vercel Pro: $20/월
  - 무제한 배포
  - 우선 지원
  
도메인: $8~15/년
```

### 고트래픽 (DAU 10,000+)
```
AWS EC2 (t3.medium): $30/월
Cloudflare (CDN): 무료
도메인: $10/년
→ 총 $40/월
```

---

## 🚀 빠른 배포 스크립트

### 자동 배포 스크립트

**`deploy.sh` 생성:**
```bash
#!/bin/bash

echo "🚀 3D Drone Battle 배포 시작..."

# 1. 코드 커밋
git add .
git commit -m "Deploy: $(date)"
git push origin main

# 2. Railway 배포 (자동)
echo "✅ Railway 배포 중..."

# 3. Vercel 배포
echo "✅ Vercel 배포 중..."
vercel --prod

echo "🎉 배포 완료!"
echo "🌐 프론트엔드: https://your-app.vercel.app"
echo "🔧 백엔드: https://your-backend.railway.app"
```

**실행:**
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 📞 문제 해결

### Railway 배포 실패
```bash
# 로그 확인
railway logs

# 재배포
railway up
```

### Vercel 빌드 실패
```bash
# 로컬 빌드 테스트
vercel dev

# 로그 확인
vercel logs
```

### WebSocket 연결 실패
```
1. CORS 설정 확인
2. WSS (https) 사용 확인
3. 백엔드 URL 확인
4. 방화벽 확인
```

---

## 🎊 완료!

**배포 성공 후:**
```
✅ 웹사이트 주소: https://your-app.vercel.app
✅ 공유 가능한 링크 생성
✅ Google 검색 가능 (1~2주 소요)
✅ 소셜 미디어 공유 (Open Graph)
```

**다음 단계:**
1. 친구들에게 링크 공유
2. SNS에 홍보
3. Reddit, Discord 커뮤니티에 공유
4. Google Ads (선택)
5. 수익화 시작!

**링크 예시:**
```
게임: https://dronebattle.vercel.app
API: https://dronebattle.railway.app/health
```

**행운을 빕니다! 🚁💰✨**
