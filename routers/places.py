from fastapi import APIRouter, HTTPException, Query, Path, UploadFile, File
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from utils.dbmysql import cursor, db, row_to_dict, rows_to_list
from models.Place import PlaceParam
import pandas as pd
import uuid
import io
import datetime

# ── pandas 用引擎 ──
from sqlalchemy import create_engine
engine = create_engine("mysql+mysqlconnector://root:123456@127.0.0.1:3306/HTTP_FAST")

router = APIRouter(prefix="/place", tags=["地名管理"])


@router.get("/list", summary="分页查询地名列表")
def list_places(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    district: str = Query(None)
):
    params = []
    where = ""
    if district:
        where = " AND DISTRICT LIKE %s"
        params.append(f"%{district}%")

    cursor.execute(f"SELECT COUNT(*) AS total FROM water_place_management WHERE 1=1{where}", params)
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT * FROM water_place_management WHERE 1=1{where} ORDER BY CREATE_TIME DESC LIMIT %s OFFSET %s",
        params + [size, (page - 1) * size]
    )
    rows = rows_to_list(cursor, cursor.fetchall())
    return {"code": 200, "data": {"list": rows, "total": total, "page": page, "size": size}}


@router.get("/export", summary="导出全部地名到 Excel")
def export_excel():
    df = pd.read_sql(
        "SELECT BATCH_NO, PROVINCE, COUNTY, DISTRICT, VILLAGE, LONGITUDE, LATITUDE, REMARK "
        "FROM water_place_management ORDER BY CREATE_TIME DESC", engine)
    df.columns = ['批次号', '省份', '市县', '区域', '地址/村庄', '经度', '纬度', '备注']
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name='地名数据')
    buf.seek(0)
    filename = f"地名数据_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )


@router.get("/info/{place_id}", summary="获取地名详情")
def get_place(place_id: str = Path(...)):
    cursor.execute("SELECT * FROM water_place_management WHERE ID = %s", (place_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(404, "未找到该记录")
    return {"code": 200, "data": row_to_dict(cursor, row)}


@router.post("/add", summary="新增地名信息")
def add_place(place: PlaceParam):
    new_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO water_place_management (ID, PROVINCE, COUNTY, DISTRICT, VILLAGE, LONGITUDE, LATITUDE, REMARK) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (new_id, place.PROVINCE, place.COUNTY, place.DISTRICT,
         place.VILLAGE, place.LONGITUDE, place.LATITUDE, place.REMARK))
    db.commit()
    return {"code": 200, "msg": "添加成功", "id": new_id}


@router.put("/update/{place_id}", summary="修改地名信息")
def update_place(place_id: str, place: PlaceParam):
    cursor.execute(
        "UPDATE water_place_management SET PROVINCE=%s, COUNTY=%s, DISTRICT=%s, "
        "VILLAGE=%s, LONGITUDE=%s, LATITUDE=%s, REMARK=%s WHERE ID=%s",
        (place.PROVINCE, place.COUNTY, place.DISTRICT,
         place.VILLAGE, place.LONGITUDE, place.LATITUDE, place.REMARK, place_id))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "更新失败，记录不存在")
    return {"code": 200, "msg": "更新成功"}


@router.delete("/delete/{place_id}", summary="删除地名信息")
def delete_place(place_id: str):
    cursor.execute("DELETE FROM water_place_management WHERE ID = %s", (place_id,))
    db.commit()
    return {"code": 200, "msg": "删除成功"}


@router.post("/import", summary="从 Excel 导入地名数据")
def import_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "仅支持 .xlsx / .xls 文件")

    df = pd.read_excel(io.BytesIO(file.file.read()))
    col_map = {
        '省份': 'PROVINCE', '市县': 'COUNTY', '区域': 'DISTRICT',
        '城市': 'COUNTY', '行政区': 'DISTRICT',
        '地址/村庄': 'VILLAGE', '地址': 'VILLAGE',
        '经度': 'LONGITUDE', '纬度': 'LATITUDE', '备注': 'REMARK',
        'POI_ID': 'BATCH_NO',
    }
    df = df.rename(columns=col_map).loc[:, ~df.columns.duplicated()]

    for col in ['PROVINCE', 'COUNTY', 'DISTRICT', 'VILLAGE']:
        if col not in df.columns:
            raise HTTPException(400, f"Excel 缺少必要列: {col}")

    for col in ['PROVINCE', 'COUNTY', 'DISTRICT', 'VILLAGE', 'BATCH_NO', 'REMARK']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
    for col in ['LONGITUDE', 'LATITUDE']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    cols = ['ID', 'BATCH_NO', 'PROVINCE', 'COUNTY', 'DISTRICT', 'VILLAGE', 'LONGITUDE', 'LATITUDE', 'REMARK']
    df = df[[c for c in cols if c in df.columns]]
    count = len(df)
    df.to_sql('water_place_management', engine, if_exists='append', index=False)
    return {"code": 200, "msg": f"成功导入 {count} 条数据"}
