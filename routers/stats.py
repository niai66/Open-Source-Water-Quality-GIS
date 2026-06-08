from fastapi import APIRouter, Query
from utils.dbmysql import cursor
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("mysql+mysqlconnector://root:123456@127.0.0.1:3306/HTTP_FAST")

router = APIRouter(prefix="/places", tags=["数据统计"])


@router.get("/stats", summary="获取地名统计概览")
def get_places_stats():
    cursor.execute(
        "SELECT COUNT(DISTINCT PROVINCE) AS province_count, "
        "COUNT(DISTINCT COUNTY) AS city_count, "
        "COUNT(DISTINCT DISTRICT) AS district_count, "
        "COUNT(DISTINCT SUBDISTRICT) AS town_count "
        "FROM water_place_management"
    )
    row = cursor.fetchone()
    return {
        "province_count": row[0],
        "city_count": row[1],
        "district_count": row[2],
        "town_count": row[3]
    }


@router.get("/stats/detail", summary="获取地名统计明细")
def get_places_stats_detail(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    sql = """SELECT PROVINCE, COUNTY, DISTRICT, SUBDISTRICT, VILLAGE, COUNT(*) AS cnt
             FROM water_place_management
             GROUP BY PROVINCE, COUNTY, DISTRICT, SUBDISTRICT, VILLAGE
             ORDER BY cnt DESC, PROVINCE, COUNTY, DISTRICT, SUBDISTRICT, VILLAGE"""
    df = pd.read_sql(sql, engine)
    total = len(df)
    df_page = df.iloc[(page - 1) * size: page * size]
    items = []
    for _, r in df_page.iterrows():
        items.append({
            "province": str(r["PROVINCE"] or ""),
            "city": str(r["COUNTY"] or ""),
            "district": str(r["DISTRICT"] or ""),
            "town": str(r["SUBDISTRICT"] or ""),
            "village": str(r["VILLAGE"] or ""),
            "count": int(r["cnt"])
        })
    return {"total": total, "items": items, "page": page, "size": size}
