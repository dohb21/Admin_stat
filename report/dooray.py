from datetime import datetime
import requests


def build_dooray_message(headers, rows, top5, top10) -> str:
    """두레이 메신저용 간단한 실행 완료 알림"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (KST)")

    lines = [
        "✅ Onuri Admin 통계 생성 완료",
        f"실행: {now}",
    ]

    return "\n".join(lines)


def send_to_dooray(message: str, webhook_url: str, bot_name: str = "Admin 통계봇") -> bool:
    """두레이 메신저로 메시지 발송"""
    try:
        payload = {
            "botName": bot_name,
            "text": message,
        }
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 두레이 발송 실패: {e}")
        return False
