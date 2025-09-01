import datetime

def get_week_of_month(target_date: datetime.date) -> int:
    """
    指定された日付がその月の第何週かを計算する。
    週の定義：
    - 週は日曜日に始まる。
    - 月の第1週は、その月の1日を含む週。
      - 1日が日曜日の場合、第1週は1日～7日。
      - 1日が日曜日でない場合、第1週は1日から最初の土曜日まで。
    - 第2週以降は、日曜日から土曜日までの7日間。
    """
    if not isinstance(target_date, datetime.date):
        raise TypeError("target_date must be a datetime.date object")

    first_day_of_month = target_date.replace(day=1)

    # 月の初日が何曜日か (Monday=0, Sunday=6)
    first_day_weekday = first_day_of_month.weekday()

    # 日曜始まりに変換 (Sunday=0, Saturday=6)
    first_day_weekday_sun_start = (first_day_weekday + 1) % 7

    # 第1週の最終日（最初の土曜日）の日付を計算
    # 1日が日曜(0)なら、最初の土曜は6日後 -> day=7
    # 1日が月曜(1)なら、最初の土曜は5日後 -> day=6
    # 1日が土曜(6)なら、最初の土曜は0日後 -> day=1
    end_of_first_week_day = 1 + (6 - first_day_weekday_sun_start)

    end_of_first_week = first_day_of_month.replace(day=end_of_first_week_day)

    if target_date <= end_of_first_week:
        return 1
    else:
        # 第1週以降の日数を計算
        days_after_first_week = (target_date - end_of_first_week).days
        # 週数を計算し、第1週分を足す
        return (days_after_first_week - 1) // 7 + 2

def get_mrp_type(mrp_controller: str) -> str:
    """
    MRP管理者の文字列から「内製」か「外注」かを判定する。
    """
    if isinstance(mrp_controller, str):
        if mrp_controller.startswith('PC'):
            try:
                num = int(mrp_controller[2:])
                if 1 <= num <= 3:
                    return '内製'
                elif 4 <= num <= 6:
                    return '外注'
            except (ValueError, IndexError):
                pass # 数値でない or PCの後に文字がない場合は 'その他' にフォールバック

    return 'その他'
