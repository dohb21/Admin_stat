import os
from datetime import datetime

import requests

from ._solapi import solapi_auth_header


def build_sms_text(headers: list, rows: list, top5: list, top10: list) -> str:
    today = datetime.now().strftime("%m/%d")
    lines = [f"[드림몰 통계 {today}]"]

    # rows: [name, d7~d0, diff, month_acc]
    # 인덱스: 0=name, 7=금일, 8=전일대비, 9=당월누적
    for row in rows:
        if len(row) >= 10:
            lines.append(
                f"{row[0]}: 금일 {row[7]} / 전일대비 {row[8]} / 당월 {row[9]}"
            )

    if top5:
        lines.append("[TOP5]")
        for rank, name in top5[:3]:
            lines.append(f"{rank}.{name[:12]}")

    return "\n".join(lines)


def send_sms(text: str, to_numbers: list[str]) -> bool:
    api_key = os.getenv("SOLAPI_API_KEY", "")
    api_secret = os.getenv("SOLAPI_API_SECRET", "")
    from_number = os.getenv("SOLAPI_FROM_NUMBER", "")

    if not api_key or not api_secret or not from_number:
        print("⚠️ SMS 설정 없음 (.env에 SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_FROM_NUMBER 필요)")
        return False
    if not to_numbers:
        print("⚠️ SMS 수신자 없음 (.env에 SMS_TO 필요)")
        return False

    # 90바이트 초과 시 Solapi가 자동으로 LMS로 전환
    messages = [
        {"to": num.replace("-", ""), "from": from_number, "text": text, "type": "SMS"}
        for num in to_numbers
    ]

    try:
        resp = requests.post(
            "https://api.coolsms.co.kr/messages/v4/send-many",
            headers={
                "Authorization": solapi_auth_header(api_key, api_secret),
                "Content-Type": "application/json",
            },
            json={"messages": messages},
            timeout=15,
        )
        resp.raise_for_status()
        failed = resp.json().get("failedMessageList", [])
        if failed:
            print(f"⚠️ SMS 일부 실패: {len(failed)}건 → {[m.get('to') for m in failed]}")
        return True
    except Exception as e:
        print(f"❌ SMS 발송 실패: {e}")
        return False
