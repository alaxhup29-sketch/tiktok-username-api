import os
import re
import json
import html
import requests

from flask import Flask, request, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

COUNTRIES = {
    "US": ("United States", "🇺🇸"),
    "GB": ("United Kingdom", "🇬🇧"),
    "BD": ("Bangladesh", "🇧🇩"),
    "IN": ("India", "🇮🇳"),
    "CA": ("Canada", "🇨🇦"),
    "AU": ("Australia", "🇦🇺"),
    "BR": ("Brazil", "🇧🇷"),
    "FR": ("France", "🇫🇷"),
    "DE": ("Germany", "🇩🇪"),
    "IT": ("Italy", "🇮🇹"),
    "ES": ("Spain", "🇪🇸"),
    "JP": ("Japan", "🇯🇵"),
    "CN": ("China", "🇨🇳"),
    "RU": ("Russia", "🇷🇺"),
    "MX": ("Mexico", "🇲🇽"),
    "ZA": ("South Africa", "🇿🇦"),
    "KR": ("South Korea", "🇰🇷"),
    "NG": ("Nigeria", "🇳🇬"),
    "PK": ("Pakistan", "🇵🇰"),
    "EG": ("Egypt", "🇪🇬"),
    "TR": ("Turkey", "🇹🇷"),
    "ID": ("Indonesia", "🇮🇩"),
    "PH": ("Philippines", "🇵🇭"),
    "VN": ("Vietnam", "🇻🇳"),
    "TH": ("Thailand", "🇹🇭"),
    "AR": ("Argentina", "🇦🇷"),
    "CL": ("Chile", "🇨🇱"),
    "CO": ("Colombia", "🇨🇴"),
    "PE": ("Peru", "🇵🇪"),
    "NZ": ("New Zealand", "🇳🇿"),
    "SG": ("Singapore", "🇸🇬"),
    "MY": ("Malaysia", "🇲🇾"),
    "SA": ("Saudi Arabia", "🇸🇦"),
    "AE": ("United Arab Emirates", "🇦🇪"),
    "IE": ("Ireland", "🇮🇪"),
    "NL": ("Netherlands", "🇳🇱"),
    "BE": ("Belgium", "🇧🇪"),
    "CH": ("Switzerland", "🇨🇭"),
    "SE": ("Sweden", "🇸🇪"),
    "NO": ("Norway", "🇳🇴"),
    "DK": ("Denmark", "🇩🇰"),
    "FI": ("Finland", "🇫🇮"),
}


def find_user_info(data):
    """Find TikTok user and stats in known page-data structures."""
    if isinstance(data, dict):
        info = data.get("userInfo")
        if isinstance(info, dict):
            user = info.get("user")
            stats = info.get("stats")
            if isinstance(user, dict) and isinstance(stats, dict) and user:
                return user, stats

        user_module = data.get("UserModule")
        if isinstance(user_module, dict):
            users = user_module.get("users", {})
            stats_list = user_module.get("stats", {})
            if isinstance(users, dict) and isinstance(stats_list, dict):
                for uid, user in users.items():
                    if isinstance(user, dict) and uid in stats_list:
                        stats = stats_list[uid]
                        if isinstance(stats, dict):
                            return user, stats

        for value in data.values():
            found = find_user_info(value)
            if found:
                return found

    elif isinstance(data, list):
        for value in data:
            found = find_user_info(value)
            if found:
                return found

    return None


def get_info(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tiktok.com/",
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        page = response.text

        patterns = [
            r'<script[^>]+id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>',
            r'<script[^>]+id=["\']SIGI_STATE["\'][^>]*>(.*?)</script>',
        ]

        found = None
        for pattern in patterns:
            match = re.search(pattern, page, re.DOTALL | re.IGNORECASE)
            if not match:
                continue
            try:
                page_data = json.loads(html.unescape(match.group(1)))
                found = find_user_info(page_data)
                if found:
                    break
            except (ValueError, TypeError):
                continue

        if not found:
            return {
                "error": "TikTok user data not found. The account may be unavailable or TikTok may have blocked the request."
            }

        user, stats = found
        user_id = str(user.get("id", ""))
        country = user.get("region", "")

        created_date = ""
        try:
            # TikTok IDs can encode an approximate creation timestamp.
            timestamp = int(user_id) >> 32
            created_date = datetime.fromtimestamp(
                timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError):
            pass

        country_name, country_flag = COUNTRIES.get(country, (country, ""))

        return {
            "username": user.get("uniqueId", username),
            "secuid": user.get("secUid", ""),
            "name": user.get("nickname", ""),
            "followers": stats.get("followerCount", 0),
            "following": stats.get("followingCount", 0),
            "likes": stats.get("heart", 0),
            "videos": stats.get("videoCount", 0),
            "private": user.get("privateAccount", False),
            "country": country_name,
            "country_flag": country_flag,
            "created_date": created_date,
            "id": user_id,
            "bio": user.get("signature", ""),
            "Api_Owner": "@Al_Nayeem756",
            "Telegram": "@Cyber_Force756",
            "Developer": "@Al_Nayeem756",
        }

    except requests.exceptions.Timeout:
        return {"error": "TikTok request timed out"}
    except requests.exceptions.RequestException as exc:
        return {"error": "Failed to fetch TikTok data", "details": str(exc)}
    except Exception as exc:
        return {"error": "Something went wrong", "details": str(exc)}


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def home():
    username = request.args.get("username", "").strip().lstrip("@")

    if not username:
        return jsonify({
            "error": "Please provide username",
            "example": "/?username=tiktok",
        }), 400

    if not re.fullmatch(r"[A-Za-z0-9._]{1,50}", username):
        return jsonify({"error": "Invalid username"}), 400

    return jsonify(get_info(username))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
