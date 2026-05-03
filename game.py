import pickle
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────
# 맵 정의 (행=0이 위, 열=0이 왼쪽)
# ─────────────────────────────────────────
MAP = [
    ["종합관",       "본관",       "경영관",      "노천극장",    "새천년관",   "이윤재관"],
    ["백양관",       "백양로5",    "대강당",       "음악관",      "알렌관",     "ABMRC"],
    ["중앙도서관",   "독수리상",   "학생회관",     "루스채플",    "재활병원",   "치과대학"],
    ["체육관",       "백양로3",    "공터2",        "광혜원",      "어린이병원", "세브란스"],
    ["공학관",       "백양로2",    "백주년기념관", "안과병원",    "제중관",     None],
    ["공학원",       "백양로1",    "공터1",        "암병원",      "의과대학",   None],
    ["연대앞버스정류장", "정문",   "스타벅스",     "세브란스버스정류장", None, None],
]

ROWS = len(MAP)
COLS = len(MAP[0])

# 장소명 → (행, 열) 매핑
PLACE_TO_POS = {}
for r in range(ROWS):
    for c in range(COLS):
        if MAP[r][c] is not None:
            PLACE_TO_POS[MAP[r][c]] = (r, c)

# ─────────────────────────────────────────
# 아이템 정의
# ─────────────────────────────────────────
ITEMS = {
    "두쫀쿠":   {"hp": 10},
    "카페라떼": {"hp": 5},
}

# ─────────────────────────────────────────
# 장소별 구매/판매 가격 정의
# ─────────────────────────────────────────
BUY_PRICES = {
    "학생회관": {"두쫀쿠": 5000, "카페라떼": 3000},
    "스타벅스": {"두쫀쿠": 4000, "카페라떼": 2000},
    "ABMRC":    {"두쫀쿠": 4000, "카페라떼": 2000},
}

SELL_PRICES_HIGH = {"두쫀쿠": 7000, "카페라떼": 4000}
SELL_PRICES_LOW  = {"두쫀쿠": 6000, "카페라떼": 3000}

HIGH_SELL_PLACES = {"체육관", "공학관", "공학원", "재활병원", "어린이병원", "종합관", "노천극장"}
LOW_SELL_PLACES  = {
    "중앙도서관", "백양관", "대강당", "백주년기념관", "안과병원", "암병원",
    "새천년관", "알렌관", "제중관", "의과대학", "치과대학", "세브란스",
    "본관", "경영관"
}

def get_sell_prices(place_name):
    if place_name in HIGH_SELL_PLACES:
        return SELL_PRICES_HIGH
    elif place_name in LOW_SELL_PLACES:
        return SELL_PRICES_LOW
    return None

# ─────────────────────────────────────────
# Quest 클래스
# ─────────────────────────────────────────
class Quest:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.completed = False

    def __repr__(self):
        return f"{self.name} - {self.description}"

# ─────────────────────────────────────────
# Place 클래스
# ─────────────────────────────────────────
class Place:
    def __init__(self, name, buy_prices=None, sell_prices=None,
                 event_info=None, quest_give=None, quest_resolve=None):
        self.name = name
        self.buy_prices = buy_prices        # dict {아이템명: 가격}
        self.sell_prices = sell_prices      # dict {아이템명: 가격}
        self.event_info = event_info        # str
        self.quest_give = quest_give        # list of Quest
        self.quest_resolve = quest_resolve  # dict {quest_name: (질문, 정답, 완료메시지)}

    def get_interactions(self):
        result = []
        if self.buy_prices:
            result.append("구매")
        if self.sell_prices:
            result.append("판매")
        if self.quest_give or self.quest_resolve:
            result.append("임무")
        return result

# ─────────────────────────────────────────
# Player 클래스
# ─────────────────────────────────────────
class Player:
    def __init__(self):
        self.hp = 10
        self.money = 10000
        self.pos = (6, 0)   # 연대앞버스정류장
        self.bag = {}        # {아이템명: 수량}
        self.quests = []     # 현재 진행중인 Quest 목록
        self.completed_quests = []

    @property
    def location(self):
        return MAP[self.pos[0]][self.pos[1]]

    def move(self, direction, hp_decrease):
        r, c = self.pos
        dr, dc = {"북": (-1, 0), "남": (1, 0), "서": (0, -1), "동": (0, 1)}[direction]
        nr, nc = r + dr, c + dc
        if nr < 0 or nr >= ROWS or nc < 0 or nc >= COLS or MAP[nr][nc] is None:
            return False, "그 방향은 막혔어."
        self.pos = (nr, nc)
        self.hp -= hp_decrease
        return True, MAP[nr][nc]

    def print_status(self):
        r, c = self.pos
        neighbors = {
            "북": MAP[r-1][c] if r-1 >= 0 and MAP[r-1][c] else "막힘",
            "남": MAP[r+1][c] if r+1 < ROWS and MAP[r+1][c] else "막힘",
            "서": MAP[r][c-1] if c-1 >= 0 and MAP[r][c-1] else "막힘",
            "동": MAP[r][c+1] if c+1 < COLS and MAP[r][c+1] else "막힘",
        }
        lines = [
            f"계좌의 잔액 = {self.money:,}원",
            f"HP = {self.hp}",
            f"현재위치 = {self.location}",
            f"동서남북 = {neighbors['동']}, {neighbors['서']}, {neighbors['남']}, {neighbors['북']}",
        ]
        return "\n".join(lines)

    def add_to_bag(self, item):
        self.bag[item] = self.bag.get(item, 0) + 1

    def remove_from_bag(self, item):
        if self.bag.get(item, 0) > 0:
            self.bag[item] -= 1
            if self.bag[item] == 0:
                del self.bag[item]
            return True
        return False

    def bag_str(self):
        if not self.bag:
            return "가방이 비어있습니다."
        return ", ".join(f"{k} x{v}" for k, v in self.bag.items())

# ─────────────────────────────────────────
# 입출력 기록
# ─────────────────────────────────────────
io_log = []
io_counter = [0]

def log(text, is_input=False):
    io_counter[0] += 1
    io_log.append((io_counter[0], text, is_input))
    print(text)

def get_input(prompt="입력: "):
    text = input(prompt)
    io_counter[0] += 1
    io_log.append((io_counter[0], f"입력: {text}", True))
    return text

# ─────────────────────────────────────────
# 이벤트 데이터 로드
# ─────────────────────────────────────────
def load_event_data(path="event.bin"):
    if not os.path.exists(path):
        # 기본값
        return {
            "events": {
                "노천극장": "아카라카 공연 티켓 암표 거래가 이루어지고 있다.",
                "대강당": "행사 도시락이 상온에 오래 방치되어 식중독 의심 증상이 보고되었다."
            },
            "answers": {
                "교내 부조리 수사": "노천극장",
                "교내 위생사건 수사": "대강당"
            }
        }
    with open(path, "rb") as f:
        return pickle.load(f)

# ─────────────────────────────────────────
# 장소 맵 초기화
# ─────────────────────────────────────────
def build_places(event_data):
    events  = event_data["events"]
    answers = event_data["answers"]

    corruption_answer  = answers["교내 부조리 수사"]
    sanitation_answer  = answers["교내 위생사건 수사"]

    places = {}

    # 모든 장소 기본 생성
    for r in range(ROWS):
        for c in range(COLS):
            name = MAP[r][c]
            if name is None:
                continue
            buy_p  = BUY_PRICES.get(name)
            sell_p = get_sell_prices(name)
            ev     = events.get(name)
            places[name] = Place(
                name=name,
                buy_prices=buy_p,
                sell_prices=sell_p,
                event_info=ev,
            )

    # 정문 - 임무 지급
    places["정문"].quest_give = [
        Quest("독수리상 방문",
              "학교에서 어떤 일들이 일어나고있는지 소식들이 모이는 독수리상에서 알아보자.")
    ]

    # 독수리상 - 임무 해결 + 새 임무 지급
    places["독수리상"].quest_resolve = {
        "독수리상 방문": ("", "", "")   # 특별 처리
    }
    places["독수리상"].quest_give = [
        Quest("교내 부조리 수사",
              "교내 어딘가에서 부조리가 일어나고있다. 이동하고 상호작용을 해서 부조리를 찾아서 본관에 보고하라."),
        Quest("교내 위생사건 수사",
              "학생들이 단체로 식중독에 걸렸다. 이동하고 상호작용을 해서 위생사건의 원인을 찾아서 세브란스에 보고하라.")
    ]

    # 본관 - 부조리 수사 해결
    places["본관"].quest_resolve = {
        "교내 부조리 수사": (
            "교내 어디에 부조리가 있나?",
            corruption_answer,
            "수업들으러 이윤재관 가야지!"
        )
    }

    # 세브란스 - 위생사건 수사 해결
    places["세브란스"].quest_resolve = {
        "교내 위생사건 수사": (
            "교내 어디에 식중독 원인이 있나?",
            sanitation_answer,
            "수업들으러 이윤재관 가야지!"
        )
    }

    # 이윤재관 - 최종 보고
    places["이윤재관"].quest_resolve = {
        "_final": ("", "", "")  # 특별 처리
    }

    return places

# ─────────────────────────────────────────
# 저장 / 불러오기
# ─────────────────────────────────────────
def save_game(player, difficulty, all_inputs):
    filename = f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
    data = {
        "hp":       player.hp,
        "money":    player.money,
        "pos":      player.pos,
        "bag":      player.bag,
        "quests":   [(q.name, q.description, q.completed) for q in player.quests],
        "completed_quests": player.completed_quests,
        "difficulty": difficulty,
        "all_inputs": all_inputs,
    }
    with open(filename, "wb") as f:
        pickle.dump(data, f)
    return filename

def load_game(player, difficulty_ref):
    save_files = [f for f in os.listdir(".") if f.startswith("save_") and f.endswith(".pkl")]

    if save_files:
        log("현재 폴더의 저장 파일:")
        for i, fn in enumerate(save_files, 1):
            log(f"  {i}) {fn}")
        log("숫자를 입력하면 해당 파일을 불러옵니다. 경로를 직접 입력할 수도 있습니다.")
    else:
        log("현재 폴더에 저장 파일이 없습니다. 경로를 직접 입력하세요.")

    choice = get_input("파일 선택: ")

    # 숫자 선택
    if choice.isdigit() and save_files:
        idx = int(choice) - 1
        if 0 <= idx < len(save_files):
            filepath = save_files[idx]
        else:
            log("잘못된 번호입니다.")
            return False, difficulty_ref[0]
    else:
        filepath = choice  # 상대/절대경로 직접 입력

    if not os.path.exists(filepath):
        log("파일을 찾을 수 없습니다.")
        return False, difficulty_ref[0]

    with open(filepath, "rb") as f:
        data = pickle.load(f)

    player.hp     = data["hp"]
    player.money  = data["money"]
    player.pos    = data["pos"]
    player.bag    = data["bag"]
    player.completed_quests = data.get("completed_quests", [])
    player.quests = []
    for (name, desc, comp) in data["quests"]:
        q = Quest(name, desc)
        q.completed = comp
        player.quests.append(q)

    loaded_diff = data.get("difficulty", "보통")
    difficulty_ref[0] = loaded_diff

    log(f"'{filepath}' 를 불러왔습니다. 난이도: {loaded_diff}")
    return True, data.get("all_inputs", [])

# ─────────────────────────────────────────
# 구매 서브루틴
# ─────────────────────────────────────────
def do_buy(player, place, all_inputs):
    prices = place.buy_prices
    items  = list(prices.keys())
    while True:
        log("무엇을 구매하시겠습니까?")
        for i, item in enumerate(items, 1):
            hp_gain = ITEMS[item]["hp"]
            log(f"  {i}) {item}: {prices[item]:,}원, HP가 {hp_gain}만큼 증가한다.")
        log(f"  {len(items)+1}) 종료")

        cmd = get_input()
        all_inputs.append(cmd)

        if cmd == str(len(items)+1) or cmd == "종료":
            log("구매를 종료합니다.")
            break
        elif cmd.isdigit() and 1 <= int(cmd) <= len(items):
            item = items[int(cmd)-1]
            price = prices[item]
            if player.money < price:
                log(f"{item} 구매를 실패했다. 계좌 잔액이 부족하다.")
            else:
                player.money -= price
                player.add_to_bag(item)
                log(f"{item}를 구매해서 가방에 넣었다. 계좌 잔액 = {player.money:,}원")
        else:
            log("잘못된 입력입니다.")

# ─────────────────────────────────────────
# 판매 서브루틴
# ─────────────────────────────────────────
def do_sell(player, place, all_inputs):
    prices = place.sell_prices
    while True:
        sellable = {k: v for k, v in player.bag.items() if k in prices}
        if not sellable:
            log("팔 것이 없어서 종료합니다.")
            break
        log("무엇을 판매하시겠습니까?")
        items = list(sellable.keys())
        for i, item in enumerate(items, 1):
            log(f"  {i}) {item} x{sellable[item]}")
        log(f"  {len(items)+1}) 종료")

        cmd = get_input()
        all_inputs.append(cmd)

        if cmd == str(len(items)+1) or cmd == "종료":
            log("판매를 종료합니다.")
            break
        elif cmd.isdigit() and 1 <= int(cmd) <= len(items) and int(cmd) != len(items)+1:
            item = items[int(cmd)-1]
            gain = prices[item]
            player.remove_from_bag(item)
            player.money += gain
            hp_gain = ITEMS[item]["hp"]
            log(f"{item}를 판매해서 {gain:,}원을 벌었다. 계좌 잔액 = {player.money:,}원")
        else:
            log("잘못된 입력입니다.")

# ─────────────────────────────────────────
# 가방 서브루틴
# ─────────────────────────────────────────
def do_bag(player, all_inputs):
    log(f"가방을 엽니다 [{player.bag_str()}]")
    if not player.bag:
        return
    log("사용할 물건의 이름 또는 번호를 입력하세요. (없으면 엔터)")
    items = list(player.bag.keys())
    for i, item in enumerate(items, 1):
        log(f"  {i}) {item} x{player.bag[item]}")

    cmd = get_input()
    all_inputs.append(cmd)

    if cmd == "":
        return

    # 번호 또는 이름으로 선택
    target = None
    if cmd.isdigit() and 1 <= int(cmd) <= len(items):
        target = items[int(cmd)-1]
    elif cmd in player.bag:
        target = cmd

    if target:
        hp_gain = ITEMS.get(target, {}).get("hp", 0)
        player.remove_from_bag(target)
        player.hp += hp_gain
        log(f"{target}를 먹었습니다. HP={player.hp}")
    else:
        log("잘못된 입력입니다.")

# ─────────────────────────────────────────
# 임무 서브루틴
# ─────────────────────────────────────────
def do_quest(player, place, all_inputs):
    name = place.name

    # 정문: 임무 지급
    if place.quest_give and name == "정문":
        new_quest = place.quest_give[0]
        already = any(q.name == new_quest.name for q in player.quests)
        if not already and new_quest.name not in player.completed_quests:
            player.quests.append(new_quest)
            log(new_quest.description)
            log(f"[임무목록]에 임무가 추가되었습니다.")
        else:
            log("이미 받은 임무입니다.")
        return

    # 독수리상: 임무 해결 + 새 임무 지급
    if name == "독수리상":
        resolved = [q for q in player.quests if q.name == "독수리상 방문"]
        if resolved:
            for q in resolved:
                player.quests.remove(q)
                player.completed_quests.append(q.name)
                log(f"다음의 임무가 해결되었다! [{q.description}]")
            # 새 임무 지급
            for new_q in place.quest_give:
                already = any(q.name == new_q.name for q in player.quests)
                if not already and new_q.name not in player.completed_quests:
                    player.quests.append(new_q)
                    log(str(new_q))
            log("")
        elif player.quests or player.completed_quests:
            log("이미 임무를 받았습니다.")
        else:
            log("먼저 정문에서 임무를 받아오세요.")
        return

    # 이윤재관: 최종 보고
    if name == "이윤재관":
        done_c = "교내 부조리 수사" in player.completed_quests
        done_s = "교내 위생사건 수사" in player.completed_quests
        if done_c and done_s:
            log("부조리와 식중독 수사를 완료했구나! 수업은 이걸로 끝입니다. 또 만나요~")
            return "game_clear"
        elif done_c:
            log("부조리 수사를 완료했구나! 식중독 원인도 찾아주세요~")
        elif done_s:
            log("식중독 수사를 완료했구나! 부조리도 찾아주세요~")
        else:
            log("아직 수사를 완료하지 못했습니다. 독수리상에서 임무를 받고 수행하세요.")
        return

    # 본관 / 세브란스: 퀘스트 정답 제출
    if place.quest_resolve:
        handled = False
        for qname, (question, answer, done_msg) in place.quest_resolve.items():
            if qname == "_final":
                continue
            active = [q for q in player.quests if q.name == qname]
            if active:
                log(question)
                cmd = get_input()
                all_inputs.append(cmd)
                if cmd.strip() == answer:
                    for q in active:
                        player.quests.remove(q)
                        player.completed_quests.append(q.name)
                    log(f"다음의 임무가 해결되었다! [{qname}]")
                    if done_msg:
                        log(done_msg)
                else:
                    log("틀렸습니다. 다시 찾아보세요.")
                handled = True
                return
        if not handled:
            log("현재 이 장소에서 할 수 있는 임무가 없습니다.")
        return

    log("이 장소에서는 임무와 관련된 것이 없습니다.")

# ─────────────────────────────────────────
# 난이도 설정
# ─────────────────────────────────────────
DIFFICULTY_HP = {"쉬움": 0.5, "보통": 1, "어려움": 2}

def do_difficulty(difficulty_ref, all_inputs):
    log(f"현재 난이도: {difficulty_ref[0]} (이동 1칸 당 HP -{DIFFICULTY_HP[difficulty_ref[0]]})")
    log("변경하려면 '쉬움', '보통', '어려움' 중 하나를 입력하세요. (그냥 엔터: 유지)")
    cmd = get_input()
    all_inputs.append(cmd)
    if cmd in DIFFICULTY_HP:
        difficulty_ref[0] = cmd
        log(f"난이도가 '{cmd}'로 변경되었습니다.")
    elif cmd == "":
        log("난이도를 유지합니다.")
    else:
        log("잘못된 입력입니다. 난이도를 유지합니다.")

# ─────────────────────────────────────────
# 메인 게임 루프
# ─────────────────────────────────────────
def main():
    # 이벤트 데이터 로드
    event_data = load_event_data()
    places = build_places(event_data)

    player = Player()
    all_inputs = []

    # 난이도 선택
    print("난이도를 선택하세요: 쉬움 / 보통 / 어려움")
    while True:
        diff_input = input("난이도: ").strip()
        if diff_input in DIFFICULTY_HP:
            break
        print("'쉬움', '보통', '어려움' 중 하나를 입력하세요.")
    difficulty_ref = [diff_input]

    # 조작법 안내
    print("\n" + "="*40)
    print("         🗺️  조작법 안내")
    print("="*40)
    print("  이동     : 동 / 서 / 남 / 북")
    print("  상태확인 : 상태  (HP, 돈, 위치 확인)")
    print("  가방     : 가방  (아이템 사용)")
    print("  구매     : 구매  (현재 위치에서 구매)")
    print("  판매     : 판매  (현재 위치에서 판매)")
    print("  임무     : 임무  (퀘스트 수행)")
    print("  임무목록 : 임무목록  (진행중인 임무 확인)")
    print("  난이도   : 난이도  (난이도 변경)")
    print("  저장     : 저장  (현재 진행상황 저장)")
    print("  불러오기 : 불러오기  (저장된 게임 불러오기)")
    print("  종료     : 종료  (게임 종료)")
    print("="*40 + "\n")

    # 시작 메시지 (번호 카운트 시작)
    log("송도 생활을 마치고 신촌에 처음 도착했다. 연대앞버스정류장이다.")
    log("배가 고프다. HP=10, 계좌 잔액=10,000원")
    log(f"난이도: {difficulty_ref[0]}")

    visited_first = set()  # 처음 방문 시 이벤트 출력용

    while True:
        cmd = get_input()
        all_inputs.append(cmd)

        # ── 이동 ──
        if cmd in ("동", "서", "남", "북"):
            hp_dec = DIFFICULTY_HP[difficulty_ref[0]]
            ok, result = player.move(cmd, hp_dec)
            if not ok:
                log(result)
                continue

            loc = player.location
            place = places[loc]
            interactions = place.get_interactions()
            interaction_str = f" [{', '.join(interactions)}]" if interactions else ""
            log(f"{loc}에 도착했다.{interaction_str}")

            # 사건관련정보 (처음 방문 시)
            if loc not in visited_first and place.event_info:
                log(place.event_info)
                visited_first.add(loc)

            # HP 체크
            if player.hp <= 0:
                log(f"HP가 {player.hp}이 되었습니다. 게임 오버!")
                break

        # ── 상태 ──
        elif cmd == "상태":
            log(player.print_status())

        # ── 가방 ──
        elif cmd == "가방":
            do_bag(player, all_inputs)

        # ── 구매 ──
        elif cmd == "구매":
            place = places[player.location]
            if place.buy_prices:
                do_buy(player, place, all_inputs)
            else:
                log("이 장소에서는 구매할 수 없습니다.")

        # ── 판매 ──
        elif cmd == "판매":
            place = places[player.location]
            if place.sell_prices:
                do_sell(player, place, all_inputs)
            else:
                log("이 장소에서는 판매할 수 없습니다.")

        # ── 임무 ──
        elif cmd == "임무":
            place = places[player.location]
            result = do_quest(player, place, all_inputs)
            if result == "game_clear":
                break

        # ── 임무목록 ──
        elif cmd == "임무목록":
            if not player.quests:
                log("현재 진행 중인 임무가 없습니다.")
            else:
                for q in player.quests:
                    log(str(q))

        # ── 난이도 ──
        elif cmd == "난이도":
            do_difficulty(difficulty_ref, all_inputs)

        # ── 저장 ──
        elif cmd == "저장":
            filename = save_game(player, difficulty_ref[0], all_inputs)
            log(f"저장되었습니다: {filename}")

        # ── 불러오기 ──
        elif cmd == "불러오기":
            ok, loaded_inputs = load_game(player, difficulty_ref)
            if ok and loaded_inputs:
                all_inputs = loaded_inputs
                log("게임을 이어합니다.")

        # ── 종료 ──
        elif cmd == "종료":
            log("게임을 종료합니다.")
            break

        else:
            log("알 수 없는 입력입니다. (동/서/남/북/상태/가방/구매/판매/임무/임무목록/난이도/저장/불러오기/종료)")

    # ─────────────────────────────────────
    # 입출력 파일 저장
    # ─────────────────────────────────────
    input_lines  = []
    output_lines = []
    for (num, text, is_inp) in io_log:
        if is_inp:
            input_lines.append(f"[{num}] {text}")
        else:
            output_lines.append(f"[{num}] {text}")

    with open("player_input.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(input_lines))

    with open("game_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print("\n[플레이 기록이 player_input.txt / game_output.txt 에 저장되었습니다.]")

if __name__ == "__main__":
    main()
