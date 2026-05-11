# Modular Tilemap Editor

언리얼/블렌더 모듈러 레벨 디자인을 위한 **128×128 그리드** 타일맵 에디터 (v0.2).
2D로 그린 그림을 JSON으로 저장 → Blender 스크립트가 3D 큐브로 자동 조립합니다.

> **v0.2 변경점**
> - 그리드 32×32 → **128×128** (1m × 1m / cell, 총 128m × 128m)
> - **64칸마다 굵은 그리드선** (4등분, 영역 가늠용)
> - **PNG 밑그림 참조** (드래그-앤-드롭, 투명도/표시 토글) — 언리얼 네비게이션 캡쳐 위에 트레이싱
> - 레이어 기반 **모듈 네이밍** (TRN/ELV/ENV/BLD)
> - placement에 **`z` 필드** 추가 (높이 시스템 사전 작업)
> - **v1 JSON 자동 마이그레이션** (구 ID → 신규 ID)

![preview](docs/mockup_topdown.png)

## 개요

모듈러 블럭(1m·5m 큐브, 산, 나무, 건물)을 2D 타일맵 형태로 그리고,
Blender Python 스크립트로 3D 씬에 자동 배치합니다.

**워크플로우**:

```
[index.html에서 그리기]
        ↓ JSON 저장
[examples/*.json]
        ↓ Blender Python 실행
[3D 목업 씬]
```

## 빠른 시작

### 1. 에디터 열기

`index.html` 더블클릭. 의존성 없음, 인터넷 불필요.

### 2. 타일맵 그리기

- 좌측 팔레트에서 모듈 선택 (레이어별로 그룹화됨: Base / Elevation / Environment)
- 좌클릭: 칠하기 / 드래그
- 우클릭: 지우개
- `Ctrl+Z` / `Ctrl+Y`: 되돌리기 / 다시 실행
- 5×5, 3×3 같은 멀티셀 모듈은 클릭 한 번에 영역 차지
- 굵은 그리드선이 64칸마다 표시되어 128×128 영역을 4분할 시각화
- **JSON 저장** 버튼으로 다운로드

파일을 창에 드래그하면 자동 처리됩니다:
- `.json` → 맵 로드 (v1은 자동 마이그레이션)
- `.png` / `.jpg` → 밑그림 참조 이미지 로드

### 2-1. 밑그림(PNG) 참조 사용법

언리얼 엔진 128×128m 영역의 네비게이션을 스크린샷으로 캡쳐 → 128×128 px PNG로 저장 →
에디터의 **이미지 불러오기** 또는 드래그-앤-드롭으로 로드. 비율 유지하며 캔버스에 맞춰지고,
**투명도 슬라이더** (0~100%, 기본 50%)로 모듈 색과의 가시성을 조절해 트레이싱 작업이 가능합니다.

### 3. Blender에서 조립

1. Blender 실행 (4.x 권장)
2. **Scripting** 탭 → 새 스크립트 → `blender_scripts/assemble_mockup.py` 내용 붙여넣기
   (또는 텍스트 에디터에서 파일 직접 열기)
3. 스크립트 상단의 `JSON_PATH` 변수를 본인 JSON 경로로 수정
   ```python
   JSON_PATH = r"C:\path\to\your\tilemap.json"
   ```
4. `Alt+P` 로 실행

→ 색상 큐브로 3D 목업 자동 생성. 탑다운 ortho 카메라 + 광원 자동 셋업.
F12로 렌더 가능.

## 파일 구조

```
.
├── index.html                       # 에디터 (단일 파일, 의존성 없음)
├── examples/
│   ├── sample_village.json          # v1 샘플 (32×32, 217 placements) — 로드시 자동 마이그레이션
│   └── sample_village_02.json       # v1 샘플 (32×32, 206 placements, 데모 영상용)
├── blender_scripts/
│   └── assemble_mockup.py           # JSON → Blender 큐브 조립
├── docs/
│   ├── mockup_topdown.png           # v0.1 결과 미리보기
│   └── stages/                      # v0.1 9단계 점진 렌더 (데모 영상 소스)
├── README.md
├── LICENSE
└── .gitignore
```

## JSON 포맷 (v2)

```json
{
  "version": 2,
  "size": [128, 128],
  "tile_size_m": 1.0,
  "coord_system": {"origin": "top-left", "x_axis": "right", "y_axis": "down", "z_axis": "up"},
  "modules_legend": [...],
  "placements": [
    {"module": "TRN_Base_Grass", "x": 0, "y": 0, "z": 0, "footprint": [1, 1], "yaw": 0}
  ]
}
```

- 좌표는 이미지 기준: 좌상단 (0,0), x는 오른쪽, y는 아래로 증가
- `z`는 높이 레이어 인덱스 (생략시 0). Blender에서 `z * tile_m` 만큼 위로 올려 배치
- Blender 변환 시 y축이 반전되어 월드 +Y(북쪽) = 타일맵 위쪽으로 매핑

**v1 호환성**: 구 ID (`block_1m_grass` 등) 가 들어있는 v1 JSON은 에디터/Blender 양쪽에서
자동으로 신규 ID로 마이그레이션되어 그대로 동작합니다.

## 모듈 라이브러리 (v2 네이밍)

레이어 기반 prefix로 정렬:

| ID | Layer | Footprint | 색 | 용도 |
|---|---|---|---|---|
| `TRN_Base_Grass`     | base        | 1×1 | 초록      | 잔디 평면 |
| `TRN_Base_Dirt`      | base        | 1×1 | 갈색      | 흙바닥 평면 |
| `TRN_Base_Stone`     | base        | 1×1 | 회색      | 돌바닥 평면 |
| `ELV_Platform_Stone` | elevation   | 5×5 | 짙은 회색 | 돌 단차 플랫폼 |
| `ENV_Tree_Pine`      | environment | 1×1 | 진녹색    | 나무 (가는 기둥) |
| `ENV_Mount_Peak`     | environment | 5×5 | 어두운 회색 | 통행 불가 배경산 |
| `BLD_House_Generic`  | environment | 3×3 | 빨강      | 일반 건물 |

**네이밍 규칙**: `[CATEGORY]_[Type]_[Material]`
- 카테고리: **TRN**(Terrain) / **ELV**(Elevation) / **ENV**(Environment) / **BLD**(Building) / **ZON**(Zone, v0.4 예정)
- footprint는 데이터 속성이지 ID의 일부가 아님 (3×3 → 5×5 변형 시 같은 ID 유지)

### 모듈 추가/변경

두 곳을 동기화하면 됩니다:

1. `index.html` 의 `MODULES` 배열 (팔레트: 색·이름·footprint·layer)
2. `blender_scripts/assemble_mockup.py` 의 `MODULE_STYLE` 딕셔너리 (3D 높이·색)

## 디자인 의도

**왜 큐브로 시작하는가**: 진짜 모듈 메쉬(나무·건물·산)를 바로 쓰면 결과가 이상할 때
"좌표 버그인지, 모듈 자체 문제인지" 분간이 안 됩니다. 단순 색상 큐브로 먼저 데이터
파이프라인(JSON 파싱 → 좌표 변환 → 배치)을 격리해서 검증한 뒤, 나중에 한 줄만 바꿔
실제 모듈 라이브러리로 교체하는 흐름입니다.

```python
# 지금: 큐브 생성
mesh = make_cube_mesh(...)

# 나중에: 라이브러리에서 진짜 모듈 가져오기
mesh = append_from_library("modules.blend", "SM_Tree_Pine_A")
```

## 로드맵

- [x] v0.1 — MVP 32×32 에디터 + 절차적 큐브 검증
- [x] v0.2 — **128×128 그리드 / 사분면 그리드선 / PNG 밑그림 / 레이어 네이밍 / z 필드**
- [ ] v0.3 — z 레이어 토글 UI / `ELV_Cliff_*` / `ELV_Slope_*` (yaw 회전) 모듈 추가
- [ ] v0.4 — `ZON_*` (Replace/Overlay 분리)
- [ ] v0.5 — 실제 Blender 모듈 라이브러리 연결 (큐브 → 실제 SM 메쉬)
- [ ] 모듈 썸네일 자동 생성 (Blender 측에서 일괄 렌더)
- [ ] Unreal Engine 임포트 파이프라인 (FBX 일괄 익스포트)
- [ ] 랜덤 yaw / 변형 시드

## 라이선스

MIT — see [LICENSE](LICENSE)
