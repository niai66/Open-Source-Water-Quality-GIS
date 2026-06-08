from pydantic import BaseModel

class StockPlaceParam(BaseModel):
    """存量地名处理 - 新增/修改参数模型"""
    BATCHNO: str = ""
    ORIGINAL_ADDRESS: str = ""
    STANDARDIZEDADDRESS: str = ""
    LONGITUDE: float = 0
    LATITUDE: float = 0
    STATE: str = "0"
    REMARK: str = ""
