# 开源水质与地理信息系统

---

## 目录

1. 项目概述
2. 技术栈
3. 系统架构
4. 后台模块详解
5. 前端功能展示
6. 数据采集工具
7. 核心亮点
8. 总结与展望

---

## 一、项目概述

| 项目 | 说明 |
|------|------|
| **项目名称** | 开源水质与地理信息系统 |
| **英文名** | HttpAPITest |
| **项目定位** | 面向水务/地名管理的 Web 全栈系统，集**数据管理、地理信息、数据采集**于一体 |
| **核心功能** | 地名信息管理、存量地名处理、地名信息统计、高德 POI 数据采集 |

### 业务背景

- 水务/地名管理部门需要一套轻量级工具来管理地名数据
- 需要支持从 Excel 批量导入/导出地名数据
- 需要对存量地名进行规范化处理（原始地址 → 规范化地址）
- 需要从高德地图采集 POI（兴趣点）数据用于地理信息分析

---

## 二、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **Python 3** | 开发语言 |
| **FastAPI** | Web 框架（异步、高性能、自动生成 OpenAPI 文档） |
| **MySQL** | 关系型数据库（存储地名数据） |
| **mysql-connector-python** | MySQL 驱动 |
| **SQLAlchemy + Pandas** | ORM 及数据分析（用于 Excel 导入导出） |
| **Uvicorn** | ASGI 服务器 |
| **Pydantic** | 数据验证（请求参数模型） |

### 前端

| 技术 | 用途 |
|------|------|
| **Vue 3** | 前端框架（Composition API） |
| **Vite** | 构建工具 |
| **Element Plus** | UI 组件库 |
| **Axios** | HTTP 请求库 |
| **Vue Router** | 前端路由 |

### 数据采集

| 技术 | 用途 |
|------|------|
| **高德地图 API** | POI 搜索接口（多边形搜索 / 文本搜索） |
| **Requests** | HTTP 客户端 |
| **多线程 + 信号量** | 并发控制与 QPS 限流 |
| **OpenPyXL** | Excel 读写 |

---

## 三、系统架构

```
┌─────────────────────────────────────────────┐
│              前端 (Vue 3 + Vite)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │地名信息管理│ │存量地名处理│ │地名信息统计│    │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘    │
│        └─────────────┼─────────────┘         │
│                     │ Axios                  │
└─────────────────────┼───────────────────────┘
                      │ HTTP (127.0.0.1:8000)
┌─────────────────────┼───────────────────────┐
│            后端 (FastAPI + Uvicorn)           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ places   │ │stock_pl-│ │  stats   │    │
│  │ 路由     │ │aces 路由 │ │ 路由     │    │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘    │
│        └─────────────┼─────────────┘         │
│                     │                       │
│              ┌──────┴──────┐               │
│              │  数据库操作   │               │
│              │ (dbmysql.py) │               │
│              └──────┬──────┘               │
└─────────────────────┼───────────────────────┘
                      │
              ┌───────┴───────┐
              │    MySQL DB   │
              │  (HTTP_FAST)  │
              └───────────────┘

另附独立模块：
┌───────────────────────────────────────┐
│    高德 POI 采集器 (Gaode_crawler.py)  │
│    → 多边形搜索 + 动态网格切分          │
│    → 输出 Excel 文件                   │
└───────────────────────────────────────┘
```

---

## 四、后台模块详解

### 4.1 入口文件 `main.py`

```python
app = FastAPI(title="地名信息管理系统", version="1.0.0")
app.add_middleware(CORSMiddleware, ...)   # 允许前端跨域
app.mount("/static", ...)                # 挂载静态文件
app.include_router(places_router)        # 地名管理路由
app.include_router(stock_places_router)  # 存量地名路由
app.include_router(stats_router)         # 统计路由
```

- **CORS**：允许 localhost:5173（Vite 开发服务器）跨域访问
- **静态文件**：提供 Swagger UI、Redoc、upload.html 等
- **三个路由模块**：职责分离，各管一块业务

### 4.2 地名信息管理 `routers/places.py`

**数据表：** `water_place_management`

| 接口 | 方法 | 说明 |
|------|------|------|
| `/place/list` | GET | 分页查询（可按区域筛选） |
| `/place/info/{id}` | GET | 获取单条详情 |
| `/place/add` | POST | 新增地名 |
| `/place/update/{id}` | PUT | 修改地名 |
| `/place/delete/{id}` | DELETE | 删除地名 |
| `/place/export` | GET | 导出全部数据到 Excel |
| `/place/import` | POST | 从 Excel 批量导入 |

**字段模型：**
- `PROVINCE`（省份）、`COUNTY`（市县）、`DISTRICT`（区域）
- `VILLAGE`（地址/村庄）、`LONGITUDE`（经度）、`LATITUDE`（纬度）
- `REMARK`（备注）

**关键代码亮点：**

```python
# Excel 导出 - 使用 pandas 读取数据库并输出
df = pd.read_sql("SELECT ... FROM water_place_management ...", engine)
df.to_excel(buf, index=False, sheet_name='地名数据')

# Excel 导入 - 智能列名映射
col_map = {
    '省份': 'PROVINCE', '市县': 'COUNTY', '区域': 'DISTRICT',
    '地址/村庄': 'VILLAGE', '经度': 'LONGITUDE', '纬度': 'LATITUDE', ...
}
df = df.rename(columns=col_map)
df.to_sql('water_place_management', engine, if_exists='append', index=False)
```

### 4.3 存量地名处理 `routers/stock_places.py`

**数据表：** `water_existing_placenames`

**特有功能：**
- 原始地址 → 规范化地址的转换
- **应用/取消应用** 状态切换（STATE: 0=未使用, 1=已使用）
- 支持多种 Excel 列名映射（兼容不同数据来源）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/stock_place/list` | GET | 分页查询（可按地址搜索） |
| `/stock_place/add` | POST | 新增存量地名 |
| `/stock_place/update/{id}` | PUT | 修改 |
| `/stock_place/delete/{id}` | DELETE | 删除 |
| `/stock_place/apply/{id}` | PUT | **应用**（标记为已使用） |
| `/stock_place/cancel/{id}` | PUT | **取消应用** |
| `/stock_place/export` | GET | 导出 Excel |
| `/stock_place/import` | POST | 批量导入 |

**智能导入逻辑：**
```python
# 自动构建规范化地址
if all(c in df.columns for c in ['ADDR_PROVINCE', 'ADDR_CITY', 'ADDR_DISTRICT']):
    df['STANDARDIZEDADDRESS'] = (df['ADDR_PROVINCE'] + df['ADDR_CITY'] 
                                 + df['ADDR_DISTRICT'] + df['ORIGINAL_ADDRESS'])
# 合并备注字段
for c in remark_cols:
    df.loc[mask, 'REMARK'] = df.loc[mask, 'REMARK'].str.cat(...)
```

### 4.4 数据统计 `routers/stats.py`

**概览统计：**
```python
/places/stats → {
    "province_count": N,   # 覆盖省份数
    "city_count": N,       # 覆盖城市数
    "district_count": N,   # 覆盖区县数
    "town_count": N        # 覆盖乡镇数
}
```

**明细统计：**
```python
/places/stats/detail → 按省/市/区/乡/村分组统计地名数量
```

### 4.5 数据库连接 `utils/dbmysql.py`

```python
config = {
    "user": "root", "password": "123456",
    "host": "127.0.0.1", "port": 3306,
    "database": "HTTP_FAST"
}
db = mysql.connector.connect(**config)
```

- 提供 `row_to_dict()` 和 `rows_to_list()` 两个辅助函数
- 将数据库元组转换为字典格式，便于 JSON 序列化

---

## 五、前端功能展示

### 5.1 技术选型

- **Vue 3 Composition API** + `<script setup>` 语法
- **Element Plus** 组件库（表格、分页、表单、弹窗、消息提示）
- **Axios** 统一 HTTP 请求
- **Vite** 极速开发体验
- **暗色主题**（深蓝基调，护眼美观）

### 5.2 路由结构

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向 | → `/place-management` |
| `/place-management` | 地名信息管理 | CRUD + 导入导出 |
| `/existing-placenames` | 存量地名处理 | CRUD + 应用/取消 + 导入导出 |
| `/place-stats` | 地名信息统计 | 统计卡片 + 明细表格 |

### 5.3 核心封装：`usePlaceApi` Composable

```javascript
export function usePlaceApi(module, defaultForm) {
  // 封装了所有 CRUD 操作：
  // fetchData()     → 分页查询
  // handleSearch()  → 搜索
  // openAddDialog() → 新增弹窗
  // openEditDialog()→ 编辑弹窗
  // handleSubmit()  → 提交（新增/修改）
  // handleDelete()  → 删除
  // handleExport()  → 导出 Excel
  // handleImport()  → 导入 Excel
}
```

> 通过传入不同的 `module`（如 `'place'` / `'stock_place'`），同一套代码即可适配不同路由，实现 **DRY（Don't Repeat Yourself）**。

### 5.4 页面截图描述

| 页面 | 功能描述 |
|------|----------|
| **地名信息管理** | 顶部搜索栏 + 操作按钮（导入/导出/新增），数据表格显示省/市/区/村庄/经纬度，支持编辑和删除，分页控件，新增/编辑弹窗 |
| **存量地名处理** | 类似布局，额外显示"应用"和"取消应用"按钮，状态标签（已使用/未使用） |
| **地名信息统计** | 四张统计卡片（省/市/区/乡镇数量），下方分组统计明细表格 |

---

## 六、数据采集工具

### 6.1 高德 POI 采集器 `Gaode_crawler.py`

**用途：** 从高德地图 API 批量采集海口市 POI 数据

### 核心策略：多边形搜索 + 动态网格切分

```
                   ┌──────────────────┐
                   │  城市矩形边界     │
                   │  (110.10~110.60, │
                   │   19.80~20.10)   │
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         ┌────┴────┐  ┌────┴────┐  ┌────┴────┐
         │龙华区核心│  │秀英区核心│  │琼山区核心│ ...
         └─────────┘  └─────────┘  └─────────┘
              │             │             │
         ┌────┴────┐  递归切分（四等分）   │
         │ SW  NW  │  ← 直到 POI < 200   │
         │ SE  NE  │    或达到最大深度 6   │
         └─────────┘                      │
```

### 关键技术点

| 技术 | 说明 |
|------|------|
| **多边形搜索 API** | `restapi.amap.com/v3/place/polygon` |
| **动态网格切分** | POI 数量 > 200 时自动四等分递归 |
| **多 API Key 轮询** | 4 个 Key 轮流使用，单 Key 失效自动跳过 |
| **QPS 控制** | 每 Key 最多 8 QPS，信号量控制总并发 |
| **检查点恢复** | 每 2000 条自动保存，支持断点续采 |
| **POI 去重** | 基于 POI_ID 的 Set 去重 |
| **最终去重** | 按经纬度去重，输出统计报表 |

### 采集结果

```
采集完成！
总耗时: X.X 小时
总请求数: N
成功请求: N
唯一POI总数: N
采集数据量: N 条

各区分布:
  龙华区: N 条 (XX.X%)
  秀英区: N 条 (XX.X%)
  ...

类型分布TOP10:
  住宅小区: N 条
  中餐厅: N 条
  ...
```

### 输出文件

- `haikou_poi_polygon_{数量}条_{时间戳}.xlsx` — 最终数据
- `haikou_polygon_checkpoint.xlsx` — 检查点
- `haikou_polygon_collect.log` — 运行日志

---

## 七、核心亮点

### ✨ 1. 全栈一体化
- 后端 FastAPI 自动生成 Swagger/Redoc API 文档
- 前端 Vue 3 + Element Plus 暗色主题，界面专业
- 前后端分离，清晰分层

### ✨ 2. 完整的 CRUD + 导入导出
- 支持 Excel 批量导入/导出
- 智能列名映射（兼容多种 Excel 格式）
- 存量地名规范化处理

### ✨ 3. 高德 POI 智能采集
- 动态网格切分算法，突破 API 单次返回限制
- 多 Key 轮询 + QPS 控制，高效稳定
- 检查点断点续采，防止意外中断数据丢失

### ✨ 4. 数据统计与可视化
- 四维度统计卡片（省/市/区/乡镇）
- 分组明细统计，方便分析数据分布

### ✨ 5. 代码质量
- 前后端均采用现代框架最佳实践
- 前端 Composable 封装，高度复用
- 后端路由职责清晰，参数校验严谨

---

## 八、总结与展望

### 已完成功能 ✅

- [x] 地名信息 CRUD（增删改查）
- [x] 存量地名处理（应用/取消应用）
- [x] Excel 批量导入/导出
- [x] 地名数据统计分析
- [x] 高德 POI 数据采集工具

### 可扩展方向 🚀

| 方向 | 说明 |
|------|------|
| **地图可视化** | 接入 Leaflet/Mapbox 在地图上展示地名点位 |
| **用户权限系统** | 增加登录认证与角色权限管理 |
| **更多数据源** | 接入百度地图、天地图等更多数据源 |
| **定时采集** | 定时任务自动采集 POI 增量数据 |
| **数据大屏** | 地名数据可视化大屏展示 |

---

> **技术栈：** Python FastAPI + Vue 3 + MySQL
> **开发工具：** VS Code / PyCharm
