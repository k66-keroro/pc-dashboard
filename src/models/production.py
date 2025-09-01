import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

class ProductionRecord(BaseModel):
    """
    生産実績データの1レコードを表すデータモデル。
    夜間バッチファイル（KANSEI_JISSEKI.txt）の構造に基づいています。
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    plant: str = Field(..., alias='プラント')
    storage_location: Optional[str] = Field(None, alias='保管場所')
    item_code: str = Field(..., alias='品目コード')
    item_text: str = Field(..., alias='品目テキスト')
    order_number: str = Field(..., alias='指図番号')
    order_type: str = Field(..., alias='指図タイプ')
    mrp_controller: str = Field(..., alias='MRP管理者')
    order_quantity: int = Field(..., alias='指図数量')
    actual_quantity: int = Field(..., alias='実績数量')
    cumulative_quantity: int = Field(..., alias='累計数量')
    remaining_quantity: int = Field(..., alias='残数量')
    input_datetime: datetime.datetime = Field(..., alias='入力日時')
    planned_completion_date: Optional[datetime.date] = Field(None, alias='計画完了日')
    wbs_element: Optional[str] = Field(None, alias='WBS要素')
    sales_order_number: Optional[str] = Field(None, alias='受注伝票番号')
    sales_order_item_number: Optional[str] = Field(None, alias='受注明細番号')

    # 金額 (amount) はデータソースにはなく、処理中に計算される
    amount: Optional[float] = Field(None, alias='amount')

    @field_validator('input_datetime', mode='before')
    @classmethod
    def to_python_datetime(cls, value):
        """PandasのTimestampをPythonのdatetimeに変換する。"""
        if hasattr(value, 'to_pydatetime'):
            return value.to_pydatetime()
        return value

    @field_validator('planned_completion_date', mode='before')
    @classmethod
    def parse_planned_completion_date(cls, value):
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None

        date_str = str(value)
        if '.' in date_str: # Handle potential float conversion like '20250728.0'
            date_str = date_str.split('.')[0]

        try:
            # Handles 'YYYYMMDD' format
            return datetime.datetime.strptime(date_str, '%Y%m%d').date()
        except (ValueError, TypeError):
            # A value was provided but it's not in the correct format.
            raise ValueError(f"Date format for '{value}' is incorrect, expected YYYYMMDD.")

    @field_validator('storage_location', 'wbs_element', mode='before')
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value.strip() == '':
            return None
        return value

    @field_validator('sales_order_number', 'sales_order_item_number', mode='before')
    @classmethod
    def clean_sap_numbers(cls, value):
        """空文字列をNoneに変換し、先頭のゼロを削除する。"""
        if not isinstance(value, str):
            return value

        # Trim whitespace first
        stripped_val = value.strip()

        if stripped_val == '':
            return None

        # If it's a numeric string, strip leading zeros
        if stripped_val.isdigit():
            return stripped_val.lstrip('0') or '0'

        # Return original stripped value if not purely numeric (e.g., 'I-0310937-20')
        return stripped_val
