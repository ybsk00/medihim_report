import resend
from config import RESEND_API_KEY, FROM_EMAIL, REPLY_TO_EMAIL, FRONTEND_URL

resend.api_key = RESEND_API_KEY


async def send_report_email(
    to_email: str,
    customer_name: str,
    access_token: str,
) -> dict:
    report_url = f"{FRONTEND_URL}/report/{access_token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Noto Sans JP', sans-serif; background: #FAFAFA; margin: 0; padding: 0; }}
            .container {{ max-width: 480px; margin: 40px auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #E8927C 0%, #D47B66 100%); padding: 32px 24px; text-align: center; color: white; }}
            .header h1 {{ font-size: 18px; margin: 0 0 4px 0; }}
            .header p {{ font-size: 12px; margin: 0; opacity: 0.9; }}
            .body {{ padding: 32px 24px; }}
            .body p {{ font-size: 14px; color: #2C3E50; line-height: 1.8; margin: 0 0 16px 0; }}
            .cta {{ display: block; background: #E8927C; color: white; text-decoration: none; padding: 14px 24px; border-radius: 8px; text-align: center; font-size: 14px; font-weight: bold; margin: 24px 0; }}
            .footer {{ padding: 20px 24px; border-top: 1px solid #f0f0f0; text-align: center; }}
            .footer p {{ font-size: 11px; color: #999; margin: 4px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>イッポ | 化粧相談リポート</h1>
                <p>韓国美容医療コンサルティング</p>
            </div>
            <div class="body">
                <p>{customer_name}様</p>
                <p>先日のカウンセリングにお越しいただき、誠にありがとうございました。</p>
                <p>ご相談内容をもとに、専門スタッフが丁寧にまとめたリポートをお届けいたします。</p>
                <a href="{report_url}" class="cta">リポートを確認する →</a>
                <p style="font-size: 12px; color: #999;">
                    ※本リポートの有効期限は30日間です。<br>
                    ※閲覧時に生年月日の入力が必要です。
                </p>
            </div>
            <div class="footer">
                <p>イッポ（イッポ）| 韓国美容医療コンサルティング</p>
                <p>本メールにお心当たりがない場合はお手数ですが削除してください。</p>
            </div>
        </div>
    </body>
    </html>
    """

    params = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": f"【イッポ】{customer_name}様 ご相談リポートが届きました",
        "html": html_content,
    }

    if REPLY_TO_EMAIL:
        params["reply_to"] = REPLY_TO_EMAIL

    result = resend.Emails.send(params)
    return result
