import pandas as pd
import datetime
import os

# ✅ 이상감지 함수
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

# ✅ 급락 감지
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

# ✅ 상태 평가
def get_anomaly_level(today_count, threshold_today, attention_factor):
    if threshold_today is None:
        return "데이터없음"
    if today_count <= threshold_today:
        return "✅ 양호"
    elif today_count <= threshold_today * attention_factor:
        return "⚠️ 주의"
    else:
        return "❗ 경고"

# ✅ 메인 분석 함수
def run_analysis():
    EXCEL_PATH = os.path.join(os.getcwd(), "trend_data.xlsx")
    today_date = datetime.date.today()

    # ✅ 엑셀 읽기
    df = pd.read_excel(EXCEL_PATH)
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])

    result_list = []

    # ✅ 키워드별 그룹 처리
    for keyword_name, df_group in df.groupby('키워드'):
        total_count = len(df_group)

        # ✅ 최근 10일
        cutoff_date = pd.Timestamp(today_date - datetime.timedelta(days=9))
        recent_10_days_df = df_group[df_group['날짜'] >= cutoff_date]
        recent_count = len(recent_10_days_df)
        recent_ratio = (recent_count / total_count) * 100 if total_count > 0 else 0

        # ✅ 오늘 / 어제
        today_count = df_group[df_group['날짜'] == pd.Timestamp(today_date)].shape[0]
        yesterday_date = today_date - datetime.timedelta(days=1)
        yesterday_count = df_group[df_group['날짜'] == pd.Timestamp(yesterday_date)].shape[0]
        diff = today_count - yesterday_count
        if yesterday_count > 0:
            change_ratio = (diff / yesterday_count) * 100
        else:
            change_ratio = None

        # ✅ 이상감지
        anomalies, threshold_today, daily_counts_recent, k, attention_factor, recent_ratio_model = detect_anomaly_dynamic(
            df_group, date_column='날짜', recent_days=10, window=3
        )

        # ✅ 급락 감지
        drop_ratio, recent_peak = detect_drop_alert(daily_counts_recent)

        # ✅ 상태 평가
        anomaly_level = get_anomaly_level(today_count, threshold_today, attention_factor)

        # ✅ 상위 3개 연관검색어 (콤마 포함 셀 분해)
        all_search_terms = df_group['연관검색어'].dropna().str.split(",")
        all_search_terms_flat = all_search_terms.explode().str.strip()
        top_related_search_terms = (
            all_search_terms_flat.value_counts().head(3).index.tolist()
        )
        top_related_search_terms_str = ", ".join(top_related_search_terms)

        # ✅ 상위 3개 연관키워드 (콤마 포함 셀 분해)
        all_related_keywords = df_group['연관키워드'].dropna().str.split(",")
        all_related_keywords_flat = all_related_keywords.explode().str.strip()
        top_related_keywords = (
            all_related_keywords_flat.value_counts().head(3).index.tolist()
        )
        top_related_keywords_str = ", ".join(top_related_keywords)

        # ✅ 결과 딕셔너리
        result_row = {
            "키워드": keyword_name,
            "총 크롤링 건수": total_count,
            "최근 10일 건수(비중)": f"{recent_count} ({recent_ratio:.1f}%)",
            "오늘 건수": f"{today_count} (어제 {yesterday_count} 대비 {diff:+d} / {change_ratio:+.1f}%)" if change_ratio is not None else f"{today_count} (어제 {yesterday_count} 대비 {diff:+d} / 계산 불가)",
            "급락 감지": "급락!" if drop_ratio is not None else "없음",
            "이상감지 상태": anomaly_level,
            #"이상감지 모델 민감도(k)": f"{k:.2f}" if k is not None else "N/A",
            #"오늘 기준 임계치": f"{threshold_today:.2f}" if threshold_today is not None else "N/A",
            #"attention_factor": f"{attention_factor:.2f}" if attention_factor is not None else "N/A",
            "상위 연관검색어": top_related_search_terms_str,
            "상위 연관키워드": top_related_keywords_str
        }

        result_list.append(result_row)

    # ✅ 컬럼 추출
    columns = list(result_list[0].keys()) if result_list else []

    return columns, result_list

