from datetime import datetime


def build_markdown_report(headers, rows, top5, top10, chart_paths=None) -> str:
    """마크다운 형식의 상세 리포트 (이미지 추가 가능)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (KST)")

    lines = [
        "# 드림몰 Admin 현황 리포트",
        "",
        f"**실행**: {now}",
        "",
        "---",
        "",
        "## 로그인/신규회원 Summary (최근 1주)",
        "",
    ]

    if headers and rows:
        # 테이블 헤더
        lines.append("|" + "|".join(headers) + "|")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        # 테이블 데이터
        for row in rows:
            lines.append("|" + "|".join(str(cell).rjust(8) for cell in row) + "|")
    else:
        lines.append("데이터 없음")

    lines += ["", "---", ""]

    # TOP 5 상품
    lines += ["## TOP 5 상품 (최근 1주)", ""]
    if top5:
        for num, name in top5:
            lines.append(f"{num}. {name}")
    else:
        lines.append("데이터 없음")

    lines += ["", "---", ""]

    # TOP 10 검색키워드
    lines += ["## TOP 10 검색키워드 (최근 1주)", ""]
    if top10:
        for num, kw in top10:
            lines.append(f"{num}. {kw}")
    else:
        lines.append("데이터 없음")

    lines += ["", "---", ""]

    # 주문/클레임 차트
    lines += ["## 주문/클레임 차트 (최근 2주)", ""]
    if chart_paths:
        label_map = {
            "order_amount": "주문금액",
            "order_count": "주문수량",
            "claim": "클레임",
        }
        for key in ("order_amount", "order_count", "claim"):
            if key in chart_paths:
                label = label_map[key]
                lines += [f"### {label}", "", f"![{label} 차트]({chart_paths[key]})", ""]
    else:
        lines.append("차트 데이터 없음")

    return "\n".join(lines)
