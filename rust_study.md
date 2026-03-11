# Rust 학습 노트 — ChzzkChatTauri 기반

Java/JS/Python/C# 경험자가 Rust 입문할 때 자주 막히는 포인트를 실제 코드(`lib.rs`) 기반으로 정리.

---

## 목차

1. [Mutex\<Option\<T\>\> 패턴](#1-mutexoptiont-패턴)
2. [Tuple Struct (뉴타입 패턴)](#2-tuple-struct-뉴타입-패턴)
3. [.ancestors().nth() — 경로 탐색](#3-ancestorsnth--경로-탐색)
4. [Option::map과 클로저 |p| p.to_path_buf()](#4-optionmap과-클로저)
5. [let-else 패턴: let Ok(x) = ... else { return }](#5-let-else-패턴)
6. [unwrap_or_default()](#6-unwrap_or_default)
7. [let _ = 반환값 무시](#7-let-_--반환값-무시)
8. [#[tauri::command] — Attribute Macro](#8-tauricommand--attribute-macro)
9. [tauri::State\<'_, T\> — 라이프타임 파라미터](#9-tauristate_-t--라이프타임-파라미터)
10. [matches! 매크로](#10-matches-매크로)
11. [if let Some(x) = ... — 패턴 매칭](#11-if-let-somex----패턴-매칭)
12. [tokio::try_join! — 비동기 병렬 실행](#12-tokiotry_join--비동기-병렬-실행)
13. [MutexGuard와 역참조 *state.0.lock().unwrap()](#13-mutexguard와-역참조)
14. [move 클로저 — 소유권 캡처](#14-move-클로저--소유권-캡처)
15. [#[cfg(debug_assertions)] — 컴파일 타임 분기](#15-cfgdebug_assertions--컴파일-타임-분기)
16. [? 연산자 — 에러 전파](#16--연산자--에러-전파)
17. [가상 스크롤 (@tanstack/react-virtual)](#17-가상-스크롤-tanstackreact-virtual)

---

## 1. Mutex\<Option\<T\>\> 패턴

```rust
struct ChatState(Mutex<Option<tokio::task::AbortHandle>>);
```

### 왜 이렇게 쓰나?

| 레이어 | 역할 |
|--------|------|
| `AbortHandle` | 비동기 task를 취소할 수 있는 핸들 |
| `Option<AbortHandle>` | 핸들이 "없을 수도 있음" (연결 안 된 상태 = None) |
| `Mutex<Option<AbortHandle>>` | 여러 스레드에서 동시에 접근할 때 데이터 경쟁 방지 |

Python 비유:
```python
# Python은 GIL이 있어서 이런 걸 신경 안 써도 되지만,
# Rust는 스레드 안전을 명시해야 함
self.abort_handle: Optional[AbortHandle] = None
# 이걸 thread-safe하게 만들면 Mutex<Option<T>>
```

### 사용 방법:
```rust
// lock() → MutexGuard 획득 → 내부 Option 접근
let mut guard = state.0.lock().unwrap();  // lock 획득 (다른 스레드 블로킹)
*guard = Some(handle);                     // Option에 값 넣기
let old = guard.take();                    // Option에서 꺼내고 None으로 만들기
// guard가 scope 끝에서 drop → lock 자동 해제
```

---

## 2. Tuple Struct (뉴타입 패턴)

```rust
struct ChatState(Mutex<Option<tokio::task::AbortHandle>>);
//              ^^^
//              필드 이름 없이 타입만 — "tuple struct"
```

### 일반 struct vs tuple struct:
```rust
// 일반 struct: 필드에 이름 있음
struct Point { x: f32, y: f32 }
let p = Point { x: 1.0, y: 2.0 };
p.x;  // 이름으로 접근

// tuple struct: 인덱스로 접근
struct ChatState(Mutex<Option<AbortHandle>>);
let cs = ChatState(Mutex::new(None));
cs.0;  // 첫 번째 필드 접근 (0-indexed)
```

### 왜 쓰나? (뉴타입 패턴)
기존 타입을 래핑해서 **Tauri의 `manage()` 시스템에 등록**하기 위한 고유 타입 생성.
`Mutex<Option<AbortHandle>>`를 그대로 쓰면 다른 플러그인과 타입 충돌 가능 → 고유 타입으로 감싸기.

```rust
// ✅ ChatState라는 고유 타입으로 감싸서 등록
.manage(ChatState(Mutex::new(None)))

// 커맨드에서 꺼낼 때도 고유 타입으로 꺼냄
fn my_cmd(state: tauri::State<'_, ChatState>) { ... }
```

---

## 3. .ancestors().nth() — 경로 탐색

```rust
if let Some(dir) = exe.ancestors().nth(4) {
    return Ok(dir.to_path_buf());
}
```

### ancestors()란?
경로의 모든 부모 디렉토리를 순서대로 순회하는 이터레이터.

```
exe 경로: /home/user/project/src-tauri/target/debug/app
.ancestors() 순서:
  nth(0) = /home/user/project/src-tauri/target/debug/app  (자기 자신)
  nth(1) = /home/user/project/src-tauri/target/debug
  nth(2) = /home/user/project/src-tauri/target
  nth(3) = /home/user/project/src-tauri
  nth(4) = /home/user/project  ← 프로젝트 루트
```

### 더 안전한 방법은 없나?
`ancestors().nth(4)`는 실제로 Rust에서 흔히 쓰이는 관용구(idiom)다.
대안으로 `parent()`를 4번 연속 호출할 수도 있지만 더 장황하다:

```rust
// 대안: parent() 4번 체이닝 (더 명시적이지만 길다)
exe.parent()
   .and_then(|p| p.parent())  // debug
   .and_then(|p| p.parent())  // target
   .and_then(|p| p.parent())  // src-tauri
   .and_then(|p| p.parent())  // 프로젝트 루트
   .map(|p| p.to_path_buf())
   .ok_or_else(|| "경로 없음".to_string())

// 현재 코드: 더 간결하고 Rust 표준적
exe.ancestors().nth(4)
```

→ **`ancestors().nth()`가 Rust 권장 방식이 맞다.**

---

## 4. Option::map과 클로저

```rust
exe.parent()
    .map(|p| p.to_path_buf())
    .ok_or_else(|| "실행 파일 경로를 찾을 수 없습니다".to_string())
```

### 단계별 설명:

**`exe.parent()`**
- 반환 타입: `Option<&Path>` — 부모 경로가 있으면 `Some(&Path)`, 없으면 `None`

**`.map(|p| p.to_path_buf())`**
- `Option::map`은 `Some(값)` 안의 값을 변환한다. `None`이면 그냥 `None` 유지.
- `|p| p.to_path_buf()` → `p`는 `&Path`, `.to_path_buf()`는 소유권 있는 `PathBuf`로 변환
- 결과 타입: `Option<PathBuf>`

Python 비유:
```python
parent = exe.parent()  # None or Path
result = parent.to_path_buf() if parent else None
# Rust는 이걸 .map(|p| p.to_path_buf())로 표현
```

**`.ok_or_else(|| "메시지".to_string())`**
- `Option<T>` → `Result<T, E>` 변환
- `Some(값)` → `Ok(값)`, `None` → `Err("메시지")`
- `ok_or()`: 에러값이 이미 있을 때
- `ok_or_else()`: 에러값을 클로저로 지연 생성 (None일 때만 String을 생성하므로 불필요한 비용 절약)

### 클로저 문법 `|p| p.to_path_buf()`:
```rust
// |인자| 표현식  — 한 줄짜리 클로저
|p| p.to_path_buf()

// 여러 줄이면 중괄호
|p| {
    let buf = p.to_path_buf();
    buf
}

// Java 람다: (p) -> p.toPathBuf()
// Python 람다: lambda p: p.to_path_buf()
```

---

## 5. let-else 패턴

```rust
let Ok(size) = win.inner_size() else { return };
```

### 이게 뭔가?
`let-else`는 Rust 1.65+에서 추가된 문법.
값이 패턴에 매칭되면 변수를 바인딩하고,
**매칭 실패 시 else 블록 실행** (반드시 함수를 벗어나야 함: return/break/panic 등).

```rust
// 전통적인 match 방식:
let size = match win.inner_size() {
    Ok(s) => s,
    Err(_) => return,  // 실패 시 함수 종료
};

// let-else로 더 간결하게:
let Ok(size) = win.inner_size() else { return };
// 성공 → size에 바인딩
// 실패 → 함수 종료
```

### `Ok(size)`는 무슨 구문?
**패턴(pattern)** 이다. Rust의 패턴 매칭은 값의 구조를 분해할 수 있다:
```rust
// Result<T, E>는 Ok(value) 또는 Err(e) 형태
// Ok(size) = "Ok 변형(variant)이고, 안의 값을 size라는 변수에 바인딩"
let Ok(size) = result else { return };
//   ^^^^^^^  패턴 (Ok인 경우만 매칭)
//      ^^^^  내부 값의 변수명
```

---

## 6. unwrap_or_default()

```rust
app_dir()
    .map(|dir| settings::load(&dir))
    .unwrap_or_default()
```

### `unwrap_or_default()`란?
`Option<T>` 또는 `Result<T, E>`에서:
- `Some(값)` / `Ok(값)` → 그 값 반환
- `None` / `Err(_)` → `T::default()` 반환 (Default 트레이트의 기본값)

```rust
let x: Option<i32> = None;
x.unwrap_or_default()  // 0 (i32의 기본값)

let x: Option<String> = None;
x.unwrap_or_default()  // "" (빈 문자열)

let x: Option<Settings> = None;
x.unwrap_or_default()  // Settings::default() 호출
```

### Settings::default()는 어디서?
```rust
// settings.rs에 직접 구현됨
impl Default for Settings {
    fn default() -> Self {
        Self { font_size: 13, show_timestamp: true, ... }
    }
}
```

### 관련 메서드 비교:
```rust
option.unwrap()              // None이면 panic! (사용 지양)
option.unwrap_or(값)         // None이면 지정한 값
option.unwrap_or_default()   // None이면 Default::default()
option.unwrap_or_else(|| 값) // None이면 클로저 실행 (지연 평가)
```

---

## 7. let _ = 반환값 무시

```rust
let _ = win.hide();
```

### 왜 `win.hide()`가 아니라 `let _ = win.hide()`?

`win.hide()`는 `Result<(), Error>`를 반환한다.
Rust는 **반환값을 그냥 버리면 컴파일러가 경고**를 낸다:
```
warning: unused `Result` that must be used
note: this `Result` may be an `Err` variant, which should be handled
```

`let _ = ...`로 의도적으로 무시함을 명시하면 경고가 사라진다.

```rust
// ❌ 경고 발생
win.hide();

// ✅ 의도적으로 무시 (실패해도 괜찮다는 의도 명시)
let _ = win.hide();

// ✅ 에러를 실제로 처리하고 싶으면
if let Err(e) = win.hide() {
    eprintln!("창 숨기기 실패: {}", e);
}
```

**언제 `let _ =`를 쓰나?**
에러가 발생해도 프로그램 흐름에 영향 없는 경우 (Best-effort 동작).
트레이 숨기기, 포커스 설정 등 — 실패해도 앱이 계속 동작해야 하는 경우.

---

## 8. #[tauri::command] — Attribute Macro

```rust
#[tauri::command]
async fn connect_chat(...) -> Result<serde_json::Value, String> { ... }
```

### Python의 데코레이터와 같은가?

**거의 맞다.** 하지만 실행 시점이 다르다:
- Python `@decorator`: **런타임**에 함수를 감싸서 동작 변경
- Rust `#[attribute]`: **컴파일 타임**에 코드를 생성/변환 → 런타임 오버헤드 없음

```python
# Python 데코레이터 (런타임)
@app.route("/chat")
def connect_chat(): ...
```

```rust
// Rust attribute macro (컴파일 타임에 코드 생성)
#[tauri::command]
async fn connect_chat(...) { ... }
```

### `#[tauri::command]`가 하는 일:
1. 함수 시그니처를 분석해서 JSON 직렬화/역직렬화 코드 자동 생성
2. snake_case 함수명을 camelCase invoke 이름으로 변환 (`connect_chat` → `"connect_chat"`)
3. `tauri::State<T>` 같은 특수 파라미터를 Tauri 내부 상태에서 자동으로 주입

### 아무 fn에나 붙이면 invoke 가능한가?

아니다. **두 가지가 모두 필요**하다:
```rust
// ① attribute 붙이기
#[tauri::command]
fn my_func() { ... }

// ② invoke_handler에 등록하기
.invoke_handler(tauri::generate_handler![
    my_func,  // ← 이게 없으면 프론트엔드에서 invoke 불가
])
```

---

## 9. tauri::State\<'_, T\> — 라이프타임 파라미터

```rust
async fn connect_chat(
    state: tauri::State<'_, ChatState>,
    //                 ^^^
    //                 라이프타임 파라미터
```

### 라이프타임이란?
Rust는 **참조가 얼마나 오래 유효한지** 컴파일러에게 알려줘야 한다.
Java/Python은 GC가 알아서 관리하지만, Rust는 컴파일 타임에 검증한다.

### `'_`는 뭔가?
"익명 라이프타임" — "컴파일러, 네가 알아서 추론해" 라는 뜻.

```rust
// 풀어서 쓰면:
async fn connect_chat<'a>(
    state: tauri::State<'a, ChatState>,
)
// 'a: state 참조가 'a만큼 살아있어야 함

// '_로 줄이면: 컴파일러가 알아서 적절한 라이프타임 추론
state: tauri::State<'_, ChatState>
```

### 왜 `State`에 라이프타임이 필요한가?
`State<T>`는 내부적으로 `&T` (참조)를 담고 있다.
참조는 원본 데이터보다 오래 살 수 없으므로 라이프타임을 명시해야 한다.
실용적으로는 `'_` 쓰면 컴파일러가 알아서 처리해주니 신경 안 써도 된다.

---

## 10. matches! 매크로

```rust
if matches!(win.is_visible(), Ok(true)) {
    // 창이 보이는 상태
}
```

### matches!가 없으면 왜 에러가 발생했나?

```rust
// ❌ 이렇게 쓰면 컴파일 에러
if win.is_visible() == Ok(true) {
    // is_visible()은 Result<bool, Error>를 반환
    // Result를 == 로 비교하려면 Error 타입이 PartialEq를 구현해야 함
    // Tauri의 Error 타입은 PartialEq 미구현 → 컴파일 에러
}

// ✅ if let으로 우회 (가능하지만 조금 장황)
if let Ok(true) = win.is_visible() { ... }

// ✅ matches! 매크로 (PartialEq 없어도 패턴으로 비교)
if matches!(win.is_visible(), Ok(true)) { ... }
```

### matches! 매크로 문법:
```rust
matches!(표현식, 패턴)
// 표현식이 패턴에 매칭되면 true, 아니면 false

matches!(x, Some(_))           // x가 Some이면 true (값은 무시)
matches!(x, Ok(true))          // x가 Ok(true)면 true
matches!(x, 1 | 2 | 3)        // x가 1, 2, 3 중 하나면 true
matches!(x, Some(n) if n > 0)  // x가 Some이고 값이 양수면 true
```

---

## 11. if let Some(x) = ... — 패턴 매칭

```rust
if let Some(win) = app_handle.get_webview_window("main") {
    // win 사용 가능
}
```

### 왜 이렇게 쓰나?
`get_webview_window()`는 `Option<WebviewWindow>`를 반환한다.
창이 없을 수도 있으므로 `None` 처리가 필요하다.

```rust
// Java로 생각하면: if (win != null) { ... }
// 하지만 Rust에는 null이 없음 → Option으로 표현

// match로 풀어쓰면:
match app_handle.get_webview_window("main") {
    Some(win) => { /* win 사용 */ }
    None => { /* 무시 */ }
}

// if let: Some 케이스만 처리하고 싶을 때 더 간결
if let Some(win) = app_handle.get_webview_window("main") {
    // win 사용
}
```

---

## 12. tokio::try_join! — 비동기 병렬 실행

```rust
let (channel_name, chat_channel_id) = tokio::try_join!(
    api::fetch_channel_name(&streamer_uid),
    api::fetch_chat_channel_id(&streamer_uid, &cookies.nid_aut, &cookies.nid_ses),
)?;
```

### 순차 실행 vs 병렬 실행:

```rust
// 순차 실행: 첫 번째 완료 후 두 번째 시작 (느림)
let a = api::fetch_channel_name().await?;
let b = api::fetch_chat_channel_id().await?;

// 병렬 실행: 둘 다 동시에 시작, 둘 다 끝나면 진행 (빠름)
let (a, b) = tokio::try_join!(
    api::fetch_channel_name(),
    api::fetch_chat_channel_id(),
)?;
```

### `try_join!` vs `join!`:
- `join!`: 모든 Future 완료 대기. 에러가 있어도 계속 진행.
- `try_join!`: 하나라도 `Err` 반환하면 즉시 전체 취소. `?`와 궁합이 좋음.

뒤의 `?`는 `try_join!` 자체가 `Result`를 반환하기 때문에 에러 전파용.

---

## 13. MutexGuard와 역참조

```rust
*state.0.lock().unwrap() = Some(task.abort_handle());
```

### 단계별 분해:

```rust
state                         // ChatState (뉴타입)
state.0                       // Mutex<Option<AbortHandle>> (첫 번째 필드)
state.0.lock()                // Result<MutexGuard<Option<AbortHandle>>, PoisonError>
state.0.lock().unwrap()       // MutexGuard<Option<AbortHandle>>
*state.0.lock().unwrap()      // Option<AbortHandle> (역참조 — 내부 값에 접근)
*state.0.lock().unwrap() = .. // Option에 새 값 할당
```

### 왜 `*` (역참조)가 필요한가?
`MutexGuard`는 스마트 포인터다. 내부 값에 접근하려면 역참조(`*`)가 필요하다.

```rust
// 읽을 때: MutexGuard는 자동 역참조 (Deref 트레이트)
let val = state.0.lock().unwrap().take();  // OK, * 없어도 됨

// 할당할 때: * 명시적 역참조 필요 (DerefMut)
*state.0.lock().unwrap() = Some(...);     // * 필수
```

---

## 14. move 클로저 — 소유권 캡처

```rust
let win_for_close = win.clone();
let dir_for_close = dir.clone();
win.on_window_event(move |event| {
    // win_for_close, dir_for_close 사용
});
```

### 왜 `move`가 필요한가?
클로저가 외부 변수를 캡처할 때:
- `move` 없음: **참조(borrow)**로 캡처 — 원본이 살아있어야 함
- `move` 있음: **소유권**을 클로저 안으로 이동 — 원본 없어도 됨

```rust
// 문제 상황 (move 없을 때):
let win = get_window();
win.on_window_event(|event| {
    save_win_state(&win, &dir);  // win을 빌려쓰려 함
});
// 컴파일 에러: 클로저는 나중에(이벤트 발생 시) 실행되는데,
// 그때 win이 살아있다는 보장 없음 (라이프타임 불일치)

// 해결: move로 소유권 이동
let win_for_close = win.clone();  // 복사본 생성
win.on_window_event(move |event| {
    save_win_state(&win_for_close, &dir_for_close);
    // win_for_close는 클로저가 소유 → 클로저가 살아있는 한 안전
});
```

### 왜 `win`을 직접 이동 안 하고 `.clone()`을 쓰나?
`win.on_window_event()`를 호출할 때 `win`을 이미 사용하고 있으므로,
클로저에 넘기려면 복사본(clone)이 필요하다.
Tauri의 `WebviewWindow`는 `Clone`을 구현하므로 복사가 가능하다.

---

## 15. #[cfg(debug_assertions)] — 컴파일 타임 분기

```rust
#[cfg(debug_assertions)]
{
    if let Some(dir) = exe.ancestors().nth(4) {
        return Ok(dir.to_path_buf());
    }
}
```

### 컴파일 타임 vs 런타임 분기:

```rust
// 런타임 분기 (if): 실행 시 조건 평가 — 두 브랜치 모두 컴파일됨
if std::env::var("DEBUG").is_ok() { ... }

// 컴파일 타임 분기 (cfg): 빌드 시 조건 평가 — 해당 브랜치만 최종 바이너리에 포함
#[cfg(debug_assertions)]
{ ... }  // release 빌드에는 이 코드가 아예 존재하지 않음
```

Python에는 컴파일 타임 분기가 없다. 가장 가까운 건 C의 `#ifdef`:
```c
// C 전처리기 (컴파일 타임)
#ifdef DEBUG
    // 디버그 코드
#endif
```

### `debug_assertions`가 켜지는 때:
| 빌드 명령 | debug_assertions |
|-----------|-----------------|
| `cargo build` (debug) | **켜짐** |
| `cargo build --release` | 꺼짐 |
| `npm run tauri dev` | **켜짐** |
| `npm run tauri build` | 꺼짐 |

---

## 16. ? 연산자 — 에러 전파

```rust
fn load_cookies() -> Result<Cookies, String> {
    let path = app_dir()?.join("cookies.json");
    //                 ^
    let content = fs::read_to_string(&path)
        .map_err(|e| format!("..."))?;
    //                              ^
    serde_json::from_str::<Cookies>(&content).map_err(|e| e.to_string())
}
```

### `?`가 하는 일:
```rust
// ? 없이 쓰면:
let dir = match app_dir() {
    Ok(d) => d,
    Err(e) => return Err(e),  // 에러면 즉시 반환
};

// ?로 줄이면:
let dir = app_dir()?;  // Err이면 자동으로 return Err(e)
```

### Python의 try/except와 비교:
```python
# Python: 예외 기반
try:
    path = app_dir() / "cookies.json"
    content = open(path).read()
    return json.loads(content)
except Exception as e:
    raise  # 또는 return None
```

```rust
// Rust: 값 기반 + ? 연산자
let path = app_dir()?.join("cookies.json");         // 실패 시 return Err(...)
let content = fs::read_to_string(&path)?;            // 실패 시 return Err(...)
serde_json::from_str(&content).map_err(|e| e.to_string())  // 마지막은 ? 없이 반환
```

---

## 17. 가상 스크롤 (`@tanstack/react-virtual`)

```tsx
// ChatList.tsx
const virtualizer = useVirtualizer({
  count: visible.length,
  getScrollElement: () => containerRef.current,
  estimateSize: () => 28,
  overscan: 10,
});
```

### 왜 가상 스크롤이 필요한가?

일반 렌더링은 항목 수만큼 DOM 노드가 생긴다:
```
채팅 10,000건 → <div> 10,000개 → <img> ~15,000개 (배지 포함)
→ Chromium 이미지 디코드 캐시가 누적 → 수 GB 메모리 증가
```

가상 스크롤은 **뷰포트에 보이는 항목만 DOM에 렌더링**한다:
```
채팅 10,000건이지만 DOM에는 ~30~50개만 존재
→ 뷰포트 밖 항목은 DOM에서 제거 → 이미지 캐시 해제 가능
```

### 동작 원리

```
┌──────────────────────────────┐ ← 스크롤 컨테이너 (overflow-y: auto)
│  position: relative          │
│  height: 전체 항목 합산 높이  │ ← 스크롤바가 전체 길이를 정확히 표시
│                              │
│  ┌────────────────────────┐  │
│  │ item (translateY: 0px) │  │ ← DOM에 실제 존재하는 항목들
│  ├────────────────────────┤  │   (뷰포트 근처만)
│  │ item (translateY: 28px)│  │
│  └────────────────────────┘  │
│                              │
│   ... (DOM에 없음, 공간만)   │
└──────────────────────────────┘
```

각 항목은 `position: absolute` + `transform: translateY(offset)` 으로 정확한 위치에 배치된다. DOM 노드는 없어도 스크롤 높이는 유지되므로 스크롤바가 자연스럽게 동작한다.

### 코드 구조 분해

```tsx
// ① 스크롤 컨테이너 ref
const containerRef = useRef<HTMLDivElement>(null);

// ② virtualizer 생성
const virtualizer = useVirtualizer({
  count: visible.length,           // 전체 항목 수 (DOM 수 아님)
  getScrollElement: () => containerRef.current,  // 스크롤 감지할 요소
  estimateSize: () => 28,          // 항목 높이 추정값 (실제값은 측정으로 보정)
  overscan: 10,                    // 뷰포트 위아래 10개 추가 렌더링 (빠른 스크롤 공백 방지)
});

// ③ 전체 높이 컨테이너 (스크롤바용)
<div style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}>

  // ④ 실제 렌더링: 뷰포트 근처 항목만
  {virtualizer.getVirtualItems().map((virtualItem) => (
    <div
      key={virtualItem.key}
      data-index={virtualItem.index}
      ref={virtualizer.measureElement}   // 실제 높이 측정 → estimateSize 오차 보정
      style={{
        position: "absolute",
        top: 0,
        transform: `translateY(${virtualItem.start}px)`,  // 위치 지정
      }}
    >
      <ChatItem chat={visible[virtualItem.index]} ... />
    </div>
  ))}
</div>
```

### 자동 스크롤과 `isProgrammaticRef`

```tsx
// 새 메시지 도착 시 맨 아래로 스크롤
useEffect(() => {
  if (!atBottomRef.current || visible.length === 0) return;

  isProgrammaticRef.current = true;                          // ← 플래그 ON
  virtualizer.scrollToIndex(visible.length - 1, { behavior: "auto" });
  setTimeout(() => { isProgrammaticRef.current = false; }, 0); // ← 플래그 OFF
}, [visible.length]);

const handleScroll = () => {
  if (isProgrammaticRef.current) return;  // ← 코드가 스크롤한 경우 무시
  const el = containerRef.current;
  atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
};
```

**왜 `isProgrammaticRef`가 필요한가?**

`scrollToIndex()`가 스크롤을 이동시키면 브라우저가 `scroll` 이벤트를 발생시킨다.
`handleScroll`이 이 이벤트를 받아 `atBottomRef`를 계산하는데, 레이아웃 반영 전이라면
"아직 맨 아래가 아님"으로 잘못 판정 → `atBottomRef = false` → 다음 메시지부터 자동 스크롤 중단.

플래그로 코드가 유발한 scroll 이벤트를 무시하면 이 오판을 막을 수 있다.

### `React.memo`와의 조합

```tsx
// ChatItem.tsx
export default memo(function ChatItem({ chat, showTimestamp, showBadges, ... }) {
  ...
});
```

가상 스크롤로 새 메시지가 추가되면 `visible` 배열이 바뀌어 `ChatList`가 리렌더된다.
`memo` 없이는 뷰포트에 보이는 모든 ChatItem이 매번 재렌더된다.
`memo`를 쓰면 **props가 바뀐 항목만** 재렌더 → 새로 추가된 항목만 렌더링.

---

## 보너스: Rust 핵심 개념 한눈에 보기

| 개념 | 설명 | 타 언어 비교 |
|------|------|-------------|
| **소유권(Ownership)** | 값은 한 번에 하나의 소유자만 가짐 | C++ RAII와 유사, GC 없음 |
| **빌림(Borrowing)** | `&T`로 참조 (읽기), `&mut T`로 가변 참조 | C++ const ref / ref |
| **Option\<T\>** | null 없음 — 값이 없음을 타입으로 표현 | Java Optional, Python None |
| **Result\<T, E\>** | 예외 없음 — 에러를 값으로 표현 | Haskell Either, Python try/except |
| **트레이트(Trait)** | 인터페이스 + 기본 구현 | Java interface, Python ABC |
| **매크로(Macro)** | 컴파일 타임 코드 생성 (`println!`, `vec!`, `matches!`) | Java 어노테이션의 강화판 |
| **라이프타임** | 참조의 유효 범위를 컴파일 타임에 검증 | 타 언어에 없음 (GC가 대신 처리) |

---

*ChzzkChatTauri/src-tauri/src/lib.rs 실제 코드 기반 학습 노트*
