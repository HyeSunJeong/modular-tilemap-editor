# Modular Tilemap Editor

언리얼/블렌더 모듈러 레벨 디자인을 위한 32×32 그리드 타일맵 에디터.
2D로 그린 그림을 JSON으로 저장 → Blender 스크립트가 3D 큐브로 자동 조립합니다.

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

- 좌측 팔레트에서 모듈 선택
- 좌클릭: 칠하기 / 드래그
- 우클릭: 지우개
- `Ctrl+Z` / `Ctrl+Y`: 되돌리기 / 다시 실행
- 5×5, 3×3 같은 멀티셀 모듈은 클릭 한 번에 영역 차지
- 우측 하단 좌표 표시로 위치 확인
- **JSON 저장** 버튼으로 다운로드

JSON 파일을 다시 캔버스에 드래그하면 편집 재개됩니다.

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
├── index.html                  # 에디터 (단일 파일, 의존성 없음)
├── examples/
│   └── sample_village.json     # 샘플 마을 (217 placements)
├── blender_scripts/
│   └── assemble_mockup.py      # JSON → Blender 큐브 조립
├── docs/
│   └── mockup_topdown.png      # 결과 미리보기
├── README.md
├── LICENSE
└── .gitignore
```

## JSON 포맷

```json
{
  "version": 1,
  "size": [32, 32],
  "tile_size_m": 1.0,
  "coord_system": {"origin": "top-left", "x_axis": "right", "y_axis": "down"},
  "modules_legend": [...],
  "placements": [
    {"module": "block_1m_grass", "x": 0, "y": 0, "footprint": [1, 1], "yaw": 0}
  ]
}
```

좌표는 이미지 기준 — 좌상단 (0,0), x는 오른쪽, y는 아래로 증가.
Blender에서 변환 시 y축이 반전되어 월드 +Y(북쪽) = 타일맵 위쪽으로 매핑됩니다.

## 모듈 라이브러리

현재 등록된 7종 (MVP):

| ID | Footprint | 색 | 용도 |
|---|---|---|---|
| `block_1m_grass` | 1×1 | 초록 | 잔디 타일 |
| `block_1m_dirt`  | 1×1 | 갈색 | 흙길 (낮음) |
| `block_1m_stone` | 1×1 | 회색 | 돌 타일 |
| `block_5m_stone` | 5×5 | 짙은 회색 | 큰 돌 플랫폼 |
| `tree`           | 1×1 | 진녹색 | 나무 (가는 기둥) |
| `building_3x3`   | 3×3 | 빨강 | 건물 |
| `mountain_5x5`   | 5×5 | 어두운 회색 | 산 |

### 모듈 추가/변경

두 곳을 동기화하면 됩니다:

1. `index.html` 의 `MODULES` 배열 (팔레트 표시용 색·이름·footprint)
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

- [x] MVP 32×32 에디터 + 절차적 큐브 검증
- [ ] 줌 / 팬 (128×128 지원)
- [ ] 레이어 분리 (지형 / 건물 / 식생)
- [ ] 모듈 썸네일 자동 생성 (Blender 측에서 일괄 렌더)
- [ ] 실제 Blender 모듈 라이브러리 연결 (큐브 → 실제 SM 메쉬)
- [ ] Unreal Engine 임포트 파이프라인 (FBX 일괄 익스포트)
- [ ] 랜덤 yaw / 변형 시드
- [ ] 높이맵 페인팅 (z 레벨)

## 라이선스

MIT — see [LICENSE](LICENSE)
