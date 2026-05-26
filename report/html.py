from datetime import datetime


def build_html_report(headers, rows, top5, top10) -> str:
    """HTML 형식의 상세 리포트"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S (KST)")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Onuri Admin 현황 리포트</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        h1 {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
            color: #007bff;
        }}
        h2 {{
            border-left: 4px solid #007bff;
            padding-left: 10px;
            margin-top: 30px;
        }}
        .meta {{
            background-color: #e7f3ff;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        th {{
            background-color: #004085;
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .list {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .list ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .list li {{
            margin: 8px 0;
            line-height: 1.6;
        }}
        .empty {{
            color: #999;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <h1>📊 Onuri Admin 현황 리포트</h1>
    <div class="meta">
        <strong>실행:</strong> {now}
    </div>

    <h2>📈 로그인/신규회원 Summary (최근 1주)</h2>
"""

    # 테이블
    if headers and rows:
        html += """    <table>
        <thead>
            <tr>
"""
        for header in headers:
            html += f"                <th>{header}</th>\n"
        html += """            </tr>
        </thead>
        <tbody>
"""
        for row in rows:
            html += "            <tr>\n"
            for cell in row:
                html += f"                <td>{cell}</td>\n"
            html += "            </tr>\n"
        html += """        </tbody>
    </table>
"""
    else:
        html += '    <p class="empty">데이터 없음</p>\n'

    # TOP 5 상품
    html += """
    <h2>🏆 TOP 5 상품 (최근 1주)</h2>
    <div class="list">
"""
    if top5:
        html += "        <ol>\n"
        for num, name in top5:
            html += f"            <li>{name}</li>\n"
        html += "        </ol>\n"
    else:
        html += '        <p class="empty">데이터 없음</p>\n'
    html += "    </div>\n"

    # TOP 10 검색키워드
    html += """
    <h2>🔍 TOP 10 검색키워드 (최근 1주)</h2>
    <div class="list">
"""
    if top10:
        html += "        <ol>\n"
        for num, kw in top10:
            html += f"            <li>{kw}</li>\n"
        html += "        </ol>\n"
    else:
        html += '        <p class="empty">데이터 없음</p>\n'
    html += "    </div>\n"

    html += """
</body>
</html>
"""

    return html
