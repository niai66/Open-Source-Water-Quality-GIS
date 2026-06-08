from pydantic import BaseModel

class PlaceParam(BaseModel):
    """地名信息管理 - 新增/修改参数模型"""
    PROVINCE: str = ""
    COUNTY: str = ""
    DISTRICT: str = ""
    VILLAGE: str = ""
    LONGITUDE: float = 0
    LATITUDE: float = 0
    REMARK: str = ""
