import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

class InventoryRecord(BaseModel):
    """
    滞留在庫データの1レコードを表すデータモデル。
    経理提出用のExcelファイルの構造を想定しています。
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    item_code: str = Field(..., alias='品目コード')
    item_text: Optional[str] = Field(None, alias='品目テキスト')
    storage_location: Optional[str] = Field(None, alias='保管場所')
    inventory_date: datetime.date = Field(..., alias='在庫日付')
    days_stagnant: Optional[int] = Field(None, alias='滞留日数')
    quantity: float = Field(..., alias='数量')
    unit: Optional[str] = Field(None, alias='単位')
    amount_jpy: float = Field(..., alias='金額(JPY)')
    currency: Optional[str] = Field(None, alias='通貨')

    @field_validator('inventory_date', mode='before')
    @classmethod
    def to_python_date(cls, value):
        """PandasのTimestampやdatetimeをPythonのdateに変換する。"""
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        if hasattr(value, 'to_pydatetime'): # for pandas Timestamps
            return value.to_pydatetime().date()
        try:
            # 'YYYY-MM-DD' or other common string formats
            return datetime.datetime.fromisoformat(str(value)).date()
        except (ValueError, TypeError):
            raise ValueError(f"Date format for '{value}' is incorrect.")

    @field_validator('item_text', 'storage_location', 'unit', 'currency', mode='before')
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value.strip() == '':
            return None
        return value
