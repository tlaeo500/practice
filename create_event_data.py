import pickle

data = {
    "events": {
        "노천극장": "아카라카 공연 티켓 암표 거래가 이루어지고 있다.",
        "대강당": "행사 도시락이 상온에 오래 방치되어 식중독 의심 증상이 보고되었다."
    },
    "answers": {
        "교내 부조리 수사": "노천극장",
        "교내 위생사건 수사": "대강당"
    }
}

with open("event_data.pkl", "wb") as f:
    pickle.dump(data, f)

print("event_data.pkl 생성 완료!")
print(data)
