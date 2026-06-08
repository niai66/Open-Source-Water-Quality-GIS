from fastapi import APIRouter, HTTPException, Query, Path, UploadFile, File
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from utils.dbmysql import cursor, db, row_to_dict, rows_to_list
from models.StockPlace import StockPlaceParam
import pandas as pd
import uuid
import io
import datetime

from sqlalchemy import create_engine
engine = create_engine("mysql+mysqlconnector://root:123456@127.0.0.1:3306/HTTP_FAST")

router = APIRouter(prefix="/stock_place", tags=["存量地名处理"])


@router.get("/list", summary="分页查询存量地名")
def list_stock_places(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    address: str = Query(None)
):
    params = []
    where = ""
    if address:
        where = " AND ORIGINAL_ADDRESS LIKE %s"
        params.append(f"%{address}%")

    cursor.execute(f"SELECT COUNT(*) AS total FROM water_existing_placenames WHERE 1=1{where}", params)
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT * FROM water_existing_placenames WHERE 1=1{where} ORDER BY CREATE_TIME DESC LIMIT %s OFFSET %s",
        params + [size, (page - 1) * size]
    )
    rows = rows_to_list(cursor, cursor.fetchall())
    return {"code": 200, "data": {"list": rows, "total": total, "page": page, "size": size}}


@router.get("/export", summary="导出全部存量地名到 Excel")
def export_stock_excel():
    df = pd.read_sql(
        "SELECT BATCHNO, ORIGINAL_ADDRESS, STANDARDIZEDADDRESS, LONGITUDE, LATITUDE, STATE, REMARK "
        "FROM water_existing_placenames ORDER BY CREATE_TIME DESC", engine)
    df.columns = ['批次号', '原始地址', '规范化地址', '经度', '纬度', '状态', '备注']
    if '状态' in df.columns:
        df['状态'] = df['状态'].apply(lambda x: '已使用' if str(x) == '1' else '未使用')
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name='存量地名')
    buf.seek(0)
    filename = f"存量地名处理_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )


@router.get("/info/{place_id}", summary="获取存量地名详情")
def get_stock_place(place_id: str = Path(...)):
    cursor.execute("SELECT * FROM water_existing_placenames WHERE ID = %s", (place_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(404, "未找到该记录")
    return {"code": 200, "data": row_to_dict(cursor, row)}


@router.post("/add", summary="新增存量地名")
def add_stock_place(place: StockPlaceParam):
    new_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO water_existing_placenames (ID, BATCHNO, ORIGINAL_ADDRESS, STANDARDIZEDADDRESS, LONGITUDE, LATITUDE, STATE, REMARK) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (new_id, place.BATCHNO, place.ORIGINAL_ADDRESS,
         place.STANDARDIZEDADDRESS, place.LONGITUDE, place.LATITUDE,
         place.STATE, place.REMARK))
    db.commit()
    return {"code": 200, "msg": "添加成功", "id": new_id}


@router.put("/update/{place_id}", summary="修改存量地名")
def update_stock_place(place_id: str, place: StockPlaceParam):
    cursor.execute(
        "UPDATE water_existing_placenames SET BATCHNO=%s, ORIGINAL_ADDRESS=%s, "
        "STANDARDIZEDADDRESS=%s, LONGITUDE=%s, LATITUDE=%s, STATE=%s, REMARK=%s WHERE ID=%s",
        (place.BATCHNO, place.ORIGINAL_ADDRESS,
         place.STANDARDIZEDADDRESS, place.LONGITUDE, place.LATITUDE,
         place.STATE, place.REMARK, place_id))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "更新失败，记录不存在")
    return {"code": 200, "msg": "更新成功"}


@router.delete("/delete/{place_id}", summary="删除存量地名")
def delete_stock_place(place_id: str):
    cursor.execute("DELETE FROM water_existing_placenames WHERE ID = %s", (place_id,))
    db.commit()
    return {"code": 200, "msg": "删除成功"}


@router.put("/apply/{place_id}", summary="应用存量地名")
def apply_stock_place(place_id: str):
    cursor.execute("UPDATE water_existing_placenames SET STATE='1' WHERE ID=%s", (place_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "记录不存在")
    return {"code": 200, "msg": "应用成功"}


@router.put("/cancel/{place_id}", summary="取消应用存量地名")
def cancel_stock_place(place_id: str):
    cursor.execute("UPDATE water_existing_placenames SET STATE='0' WHERE ID=%s", (place_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "记录不存在")
    return {"code": 200, "msg": "取消应用成功"}


@router.post("/import", summary="从 Excel 导入存量地名")
def import_stock_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "仅支持 .xlsx / .xls 文件")

    df = pd.read_excel(io.BytesIO(file.file.read()))
    col_map = {
        '批次号': 'BATCHNO', '原始地址': 'ORIGINAL_ADDRESS',
        '规范化地址': 'STANDARDIZEDADDRESS', '经度': 'LONGITUDE',
        '纬度': 'LATITUDE', '状态': 'STATE', '备注': 'REMARK',
        'POI_ID': 'BATCHNO', '地址': 'ORIGINAL_ADDRESS',
        '省份': 'ADDR_PROVINCE', '城市': 'ADDR_CITY',
        '行政区': 'ADDR_DISTRICT', '名称': 'ADDR_NAME',
        '类型': 'REMARK_TYPE', '子类型': 'REMARK_SUBTYPE',
        '电话': 'REMARK_TEL', '来源网格': 'REMARK_GRID',
        '采集时间': 'REMARK_TIME',
    }
    df = df.rename(columns=col_map).loc[:, ~df.columns.duplicated()]

    if 'ORIGINAL_ADDRESS' not in df.columns:
        raise HTTPException(400, "Excel 缺少地址列")

    # 构建规范化地址
    if all(c in df.columns for c in ['ADDR_PROVINCE', 'ADDR_CITY', 'ADDR_DISTRICT']):
        for c in ['ADDR_PROVINCE', 'ADDR_CITY', 'ADDR_DISTRICT']:
            df[c] = df[c].fillna('').astype(str)
        df['STANDARDIZEDADDRESS'] = (df['ADDR_PROVINCE'].str.strip() + df['ADDR_CITY'].str.strip()
                                     + df['ADDR_DISTRICT'].str.strip() + df['ORIGINAL_ADDRESS'].str.strip())
    elif 'STANDARDIZEDADDRESS' not in df.columns:
        df['STANDARDIZEDADDRESS'] = df['ORIGINAL_ADDRESS']

    # 合并备注
    remark_cols = [c for c in df.columns if c.startswith('ADDR_') or c.startswith('REMARK_')]
    if 'REMARK' not in df.columns:
        df['REMARK'] = ''
    for c in remark_cols:
        df[c] = df[c].fillna('').astype(str)
        mask = df[c].str.len() > 0
        label = c.replace('ADDR_', '').replace('REMARK_', '')
        df.loc[mask, 'REMARK'] = df.loc[mask, 'REMARK'].str.cat(
            df.loc[mask, c].apply(lambda x: f"{label}:{x}"), sep='; ', na_rep='')

    for col in ['BATCHNO', 'ORIGINAL_ADDRESS', 'STANDARDIZEDADDRESS', 'REMARK']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
    for col in ['LONGITUDE', 'LATITUDE']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    if 'STATE' in df.columns:
        df['STATE'] = df['STATE'].apply(lambda x: '1' if str(x) in ['1', '已使用'] else '0')
    else:
        df['STATE'] = '0'

    df['ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    cols = ['ID', 'BATCHNO', 'ORIGINAL_ADDRESS', 'STANDARDIZEDADDRESS',
            'LONGITUDE', 'LATITUDE', 'STATE', 'REMARK']
    df = df[[c for c in cols if c in df.columns]]
    count = len(df)
    df.to_sql('water_existing_placenames', engine, if_exists='append', index=False)
    return {"code": 200, "msg": f"成功导入 {count} 条数据"}
