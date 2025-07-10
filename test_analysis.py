import pandas as pd
import datetime

# ✅ 너가 준 이상감지 함수
def detect_anomaly_dynamic(df, date_column='날짜', recent_days=10, window=3):
    daily_counts = df[date_column].value_counts().sort_index()
    daily_counts.index = pd.to_datetime(daily_counts.index, errors='coerce')
    daily_counts = daily_counts.dropna().sort_index()

    if len(daily_counts) == 0:
        return [], None, daily_counts, None, None, None

    latest_date = daily_counts.index.max()
    cutoff_date = latest_date - pd.Timedelta(days=recent_days - 1)
    daily_counts_recent = daily_counts[daily_counts.index >= cutoff_date]

    if len(daily_counts_recent) == 0:
        return [], None, daily_counts, None, None, None

    total_count = len(df)
    recent_dates_str = daily_counts_recent.index.strftime('%Y-%m-%d')
    recent_count = len(df[df[date_column].isin(recent_dates_str)])
    recent_ratio = recent_count / total_count if total_count > 0 else 0

    if recent_ratio > 0.8:
        k = 1.0
        attention_factor = 1.2
    elif recent_ratio > 0.5:
        k = 1.2
        attention_factor = 1.25
    elif recent_ratio > 0.2:
        k = 1.5
        attention_factor = 1.3
    else:
        k = 2.0
        attention_factor = 1.5

    moving_avg = daily_counts_recent.rolling(window=window, min_periods=1).mean()
    moving_std = daily_counts_recent.rolling(window=window, min_periods=1).std().fillna(0)
    threshold_series = moving_avg + k * moving_std

    anomalies_idx = daily_counts_recent[daily_counts_recent > threshold_series].index
    anomalies = anomalies_idx.strftime("%Y-%m-%d").tolist()

    today_str = str(datetime.date.today())
    today_count = daily_counts_recent.get(pd.to_datetime(today_str), 0)
    threshold_today = threshold_series.get(pd.to_datetime(today_str), None)

    return anomalies, threshold_today, daily_counts_recent, k, attention_factor, recent_ratio


# ✅ 급락 감지 함수
def detect_drop_alert(daily_counts_recent, drop_ratio=0.3):
    if len(daily_counts_recent) < 3:
        return None, None

    today = pd.to_datetime(datetime.date.today())
    if today not in daily_counts_recent.index:
        return None, None

    today_count = daily_counts_recent.get(today, 0)
    peak_count = daily_counts_recent.drop(today, errors='ignore').max()

    if peak_count == 0:
        return None, None

    ratio = today_count / peak_count

    if ratio < drop_ratio:
        return ratio, peak_count
    else:
        return None, peak_count
    
def get_anomaly_level(today_count, threshold_today, attention_factor):
    if threshold_today is None:
        return "데이터없음"
    if today_count <= threshold_today:
        return "✅ 양호"
    elif today_count <= threshold_today * attention_factor:
        return "⚠️ 주의"
    else:
        return "❗ 경고"


# ✅ ===============================
# ✅ 여기가 메인 분석 코드
# ✅ ===============================
import os
def main():
    # ✅ 엑셀 경로
    
    EXCEL_PATH = os.path.join(os.getcwd(), "trend_data.xlsx") # 너가 올린 거 이름 맞춰서 바꿔

    # ✅ 오늘 날짜 강제 설정 (실험용)
    today_date = datetime.date.today()
    # today_date = datetime.date(2025, 7, 10)

    df = pd.read_excel(EXCEL_PATH)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])

    # ✅ 총 크롤링 건수
    total_count = len(df)

    # ✅ 최근 10일
    cutoff_date = pd.Timestamp(today_date - datetime.timedelta(days=9))
    recent_10_days_df = df[df['날짜'] >= cutoff_date]
    recent_count = len(recent_10_days_df)
    recent_ratio = (recent_count / total_count) * 100 if total_count > 0 else 0

    # ✅ 오늘 / 어제
    today_count = df[df['날짜'] == pd.Timestamp(today_date)].shape[0]
    yesterday_date = today_date - datetime.timedelta(days=1)
    yesterday_count = df[df['날짜'] == pd.Timestamp(yesterday_date)].shape[0]
    diff = today_count - yesterday_count
    if yesterday_count > 0:
        change_ratio = (diff / yesterday_count) * 100
    else:
        change_ratio = None

    # ✅ 이상감지
    anomalies, threshold_today, daily_counts_recent, k, attention_factor, recent_ratio_model = detect_anomaly_dynamic(
        df, date_column='날짜', recent_days=10, window=3
    )

    # ✅ 급락 감지
    drop_ratio, recent_peak = detect_drop_alert(daily_counts_recent)

    # ✅ 이상감지 상태 평가 ← 이 한 줄 추가!
    anomaly_level = get_anomaly_level(today_count, threshold_today, attention_factor)

    # ✅ 결과 출력
    print("\n✅ === 도수치료 현황판 지표 ===")
    print(f"키워드: 도수치료")
    print(f"총 크롤링 건수: {total_count}")
    print(f"최근 10일 이내 건수: {recent_count}")
    print(f"최근 10일 비중: {recent_ratio:.1f}%")
    print(f"오늘 건수: {today_count}")
    print(f"어제 건수: {yesterday_count}")
    print(f"어제 대비 변화량: {diff:+d}")
    if change_ratio is not None:
        print(f"어제 대비 변화율: {change_ratio:+.1f}%")
    else:
        print(f"어제 대비 변화율: 계산 불가 (어제 0건)")

    if drop_ratio is not None:
        print(f"급락 감지: 오늘 피크 대비 {drop_ratio*100:.1f}% 수준 (급락!)")
    else:
        print("급락 감지: 없음")

    print(f"이상감지 상태: {anomaly_level}")
    print("=============================\n")


if __name__ == "__main__":
    main()

