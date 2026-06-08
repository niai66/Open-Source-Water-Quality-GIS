"""
海口市POI全量采集器 - 多边形搜索 + 动态网格切分版
通过递归切分地图区域，突破API单区域返回限制
"""

import requests
import time
import math
import pandas as pd
from typing import List, Dict, Optional, Tuple, Set
from threading import Lock, Semaphore
from datetime import datetime
import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    # 日志格式：时间 - 日志级别 - 日志内容
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../haikou_polygon_collect.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# 获取一个 logger 对象
logger = logging.getLogger(__name__)


class HaikouPolygonCollector:
    """海口市POI采集器 - 多边形搜索 + 动态网格切分"""

    # 初始化配置、密钥、网格、统计
    def __init__(self, api_keys: List[str]):
        # 海口市行政边界（矩形范围）
        self.city_bounds = {
            "min_lng": 110.10,
            "min_lat": 19.80,
            "max_lng": 110.60,
            "max_lat": 20.10
        }

        self.grid_bounds = [
            {"name": "龙华区核心", "bounds": [110.28, 20.00, 110.38, 20.05]},
            {"name": "秀英区核心", "bounds": [110.20, 19.98, 110.30, 20.03]},
            {"name": "琼山区核心", "bounds": [110.35, 19.98, 110.45, 20.02]},
            {"name": "美兰区核心", "bounds": [110.32, 20.01, 110.42, 20.08]},
        ]

        # API密钥
        # 1. 过滤空值和空白字符串
        self.api_keys = [k for k in api_keys if k and k.strip()]

        # 2. 轮询索引
        self.key_index = 0

        # 3. 线程锁（多线程安全）
        self.key_lock = Lock()

        # 4. 失效密钥集合
        self.disabled_keys = set()

        if not self.api_keys:
            logger.error("没有提供任何API密钥")
            sys.exit(1)

        # API接口
        self.place_polygon_api = "https://restapi.amap.com/v3/place/polygon"
        self.place_text_api = "https://restapi.amap.com/v3/place/text"

        # 验证API密钥
        self._validate_api_keys()

        # POI类型（核心类型，避免过度细分）
        self.poi_types = self._get_core_poi_types()

        # 网格切分配置
        self.max_grid_depth = 6  # 最大切分深度
        self.min_grid_size = 0.01  # 0.01最小网格大小（约1km）
        self.poi_threshold = 200  # 单网格POI数量阈值，超过则继续切分

        # QPS控制
        self.key_qps_tracker = {}  # 追踪每个密钥的请求时间戳
        self.qps_lock = Lock()  # 线程锁，保证并发安全
        self.max_qps_per_key = 8  # 每个密钥最大QPS（每秒8次请求）

        # 既控制总并发，又避免单密钥超限
        self.semaphore = Semaphore(self.max_qps_per_key * len(self.api_keys))  # 全局并发控制，最大并发 = 密钥数 × 单密钥QPS

        # 统计
        self.stats = {
            "total_requests": 0,  # 总请求次数
            "success_requests": 0,  # 成功请求次数
            "failed_requests": 0,  # 失败请求次数
            "grid_splits": 0,  # 网格分裂次数
            "total_grids": 0,  # 总网格数量
            "start_time": datetime.now()  # 任务开始时间
        }
        # 统计锁
        self.stats_lock = Lock()

        # 结果存储
        self.results = []  # 存储采集结果列表
        self.results_lock = Lock()  # 结果列表的线程锁

        # POI去重
        self.seen_poi_ids: Set[str] = set()  # 已处理的POI ID集合
        self.seen_lock = Lock()  # 去重集合的线程锁

        # 网格管理
        self.processed_grids: Set[str] = set()  # 已处理的网格集合
        self.grid_lock = Lock()  # 网格集合的线程锁

        # 检查点
        self.last_saved_count = 0  # 上次保存时的数据量
        self.checkpoint_file = "../haikou_polygon_checkpoint.xlsx"  # 检查点文件路径
        self.load_checkpoint()  # 启动时加载之前的进度

    def _get_core_poi_types(self) -> List[Dict]:
        """获取核心POI类型"""
        return [
            # 住宅相关
            {"name": "住宅小区", "code": "120201"},
            {"name": "商务写字楼", "code": "120100"},
            {"name": "别墅", "code": "120202"},
            # 餐饮
            {"name": "中餐厅", "code": "050100"},
            {"name": "快餐厅", "code": "050300"},
            {"name": "咖啡厅", "code": "050400"},
            # 购物
            {"name": "商场", "code": "060100"},
            {"name": "超市", "code": "060200"},
            {"name": "便利店", "code": "060300"},
            # 生活服务
            {"name": "美容美发", "code": "070100"},
            {"name": "洗衣店", "code": "070800"},
            {"name": "通讯营业厅", "code": "071800"},
            # 医疗
            {"name": "综合医院", "code": "090100"},
            {"name": "诊所", "code": "090300"},
            {"name": "药店", "code": "090400"},
            # 教育
            {"name": "幼儿园", "code": "141201"},
            {"name": "小学", "code": "141202"},
            {"name": "中学", "code": "141203"},
            {"name": "大学", "code": "141204"},
            # 交通
            {"name": "公交车站", "code": "150400"},
            {"name": "停车场", "code": "150600"},
            {"name": "加油站", "code": "150200"},
            # 金融
            {"name": "银行", "code": "160100"},
            {"name": "ATM", "code": "160101"},
        ]

    # 验证 API 密钥有效性
    def _validate_api_keys(self):
        """验证API密钥"""
        logger.info(f"正在验证 {len(self.api_keys)} 个API密钥...")
        # 有效的key
        valid_keys = []

        for i, key in enumerate(self.api_keys):
            logger.info(f"验证密钥 {i + 1}/{len(self.api_keys)}: {key[:8]}...")
            if self._test_api_key(key):
                valid_keys.append(key)
                logger.info(f" API密钥 {key[:8]}... 有效")
            else:
                logger.warning(f" API密钥 {key[:8]}... 无效")
            time.sleep(0.5)

        self.api_keys = valid_keys
        logger.info(f"有效API密钥数量: {len(self.api_keys)}")

    def _test_api_key(self, api_key: str) -> bool:
        """测试API密钥有没有效"""
        try:
            params = {
                "key": api_key,
                "keywords": "测试",
                "city": "海口",
                "offset": 1,
                "page": 1,
                "output": "json"
            }
            response = requests.get(self.place_text_api, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = str(data.get("status", ""))
                if status == "1":
                    return True
        except:
            pass
        return False

    def get_next_key(self) -> Optional[str]:
        """获取下一个可用的API密钥"""
        with self.key_lock:
            if not self.api_keys:
                return None
            for _ in range(len(self.api_keys)):
                key = self.api_keys[self.key_index]
                self.key_index = (self.key_index + 1) % len(self.api_keys)
                if key not in self.disabled_keys:
                    return key
            logger.warning("所有API密钥暂时不可用，等待60秒...")
            time.sleep(60)
            self.disabled_keys.clear()
            return self.get_next_key()

    def wait_for_qps(self, api_key: str):
        """QPS控制"""
        with self.qps_lock:
            now = time.time()
            last_request = self.key_qps_tracker.get(api_key, 0)
            elapsed = now - last_request

            # 如果距离上次请求时间过短，则等待
            if elapsed < (1.0 / self.max_qps_per_key):
                time.sleep((1.0 / self.max_qps_per_key) - elapsed)

            # 更新最后请求时间
            self.key_qps_tracker[api_key] = time.time()

    def search_by_polygon(self, types: str, bounds: List[float],
                          page: int = 1, retry: int = 3) -> Tuple[List[Dict], int]:
        """
        按多边形区域搜索POI
        bounds: [min_lng, min_lat, max_lng, max_lat]
        """
        polygon = f"{bounds[0]},{bounds[1]}|{bounds[2]},{bounds[1]}|{bounds[2]},{bounds[3]}|{bounds[0]},{bounds[3]}|{bounds[0]},{bounds[1]}"

        for attempt in range(retry):
            try:
                api_key = self.get_next_key()
                if not api_key:
                    return [], 0
                # 控制单个key 时间   1/8
                self.wait_for_qps(api_key)

                params = {
                    "key": api_key,
                    "polygon": polygon,
                    "types": types,
                    "offset": 25,
                    "page": page,
                    "extensions": "all",
                    "output": "json"
                }
                # http get 请求
                response = requests.get(self.place_polygon_api, params=params, timeout=15)

                with self.stats_lock:
                    self.stats["total_requests"] += 1

                if response.status_code != 200:
                    logger.warning(f"HTTP错误 {response.status_code}")
                    time.sleep(1)
                    continue

                data = response.json()
                status = str(data.get("status", ""))
                info = data.get("info", "")

                if status != "1":
                    if "DAILY_QUERY_OVER_LIMIT" in info:
                        logger.warning(f"API密钥 {api_key[:8]}... 配额用尽")
                        with self.key_lock:
                            self.disabled_keys.add(api_key)
                        time.sleep(2)
                        continue
                    else:
                        logger.debug(f"API错误: {info}")
                        time.sleep(1)
                        continue

                with self.stats_lock:
                    self.stats["success_requests"] += 1

                pois = data.get("pois", [])
                total = int(data.get("count", 0))

                return pois, total

            except Exception as e:
                logger.error(f"搜索异常: {e}")
                if attempt < retry - 1:
                    time.sleep(2)

        return [], 0

    def get_poi_count_in_grid(self, types: str, bounds: List[float]) -> int:
        """获取网格内的POI数量（仅第一页估算）"""
        _, total = self.search_by_polygon(types, bounds, page=1)
        return total

    def process_poi(self, poi: Dict, type_name: str, grid_name: str) -> Optional[Dict]:
        """处理POI数据"""
        try:
            poi_id = poi.get("id", "")

            with self.seen_lock:
                if poi_id in self.seen_poi_ids:
                    return None
                self.seen_poi_ids.add(poi_id)

            location = poi.get("location", "").split(",")
            if len(location) < 2:
                return None

            result = {
                "POI_ID": poi_id,
                "名称": poi.get("name", ""),
                "地址": poi.get("address", ""),
                "经度": float(location[0]),
                "纬度": float(location[1]),
                "省份": poi.get("pname", ""),
                "城市": poi.get("cityname", ""),
                "行政区": poi.get("adname", ""),
                "类型": poi.get("type", ""),
                "子类型": type_name,
                "电话": poi.get("tel", ""),
                "来源网格": grid_name,
                "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return result

        except Exception as e:
            logger.debug(f"处理POI失败: {e}")
            return None

    def collect_in_grid(self, type_info: Dict, bounds: List[float],
                        grid_name: str, depth: int = 0) -> int:
        """
        在单个网格内采集POI（递归切分）
        """
        type_name = type_info["name"]
        type_code = type_info["code"]

        # 检查是否已处理过该网格
        grid_key = f"{type_code}_{bounds[0]:.4f}_{bounds[1]:.4f}_{bounds[2]:.4f}_{bounds[3]:.4f}"
        with self.grid_lock:
            if grid_key in self.processed_grids:
                return 0
            self.processed_grids.add(grid_key)

        # 获取网格内POI数量
        total_count = self.get_poi_count_in_grid(type_code, bounds)

        # 判断是否需要继续切分   中心点
        grid_width = bounds[2] - bounds[0]
        grid_height = bounds[3] - bounds[1]

        should_split = (
                depth < self.max_grid_depth and  # 未达到最大深度
                total_count > self.poi_threshold and  # POI数量超过阈值
                grid_width > self.min_grid_size and  # 网格宽度足够大
                grid_height > self.min_grid_size  # 网格高度足够大
        )

        if should_split:
            # 四等分网格
            with self.stats_lock:
                self.stats["grid_splits"] += 1
            # 计算中心点
            mid_lng = (bounds[0] + bounds[2]) / 2
            mid_lat = (bounds[1] + bounds[3]) / 2
            # 创建4个子网格
            sub_grids = [
                {"bounds": [bounds[0], bounds[1], mid_lng, mid_lat], "name": f"{grid_name}_SW"},
                {"bounds": [mid_lng, bounds[1], bounds[2], mid_lat], "name": f"{grid_name}_SE"},
                {"bounds": [bounds[0], mid_lat, mid_lng, bounds[3]], "name": f"{grid_name}_NW"},
                {"bounds": [mid_lng, mid_lat, bounds[2], bounds[3]], "name": f"{grid_name}_NE"},
            ]

            # 递归采集子网格
            total_collected = 0
            for sub_grid in sub_grids:
                collected = self.collect_in_grid(
                    type_info, sub_grid["bounds"], sub_grid["name"], depth + 1
                )
                total_collected += collected
                time.sleep(0.1)  # 避免请求过快

            return total_collected

        # 不切分，直接采集
        logger.info(f"采集网格 [{grid_name}] - {type_name} (深度:{depth}, 预估:{total_count}条)")

        collected = 0
        page = 1
        max_pages = min(50, math.ceil(total_count / 25) + 5) if total_count > 0 else 50

        while page <= max_pages:
            pois, total = self.search_by_polygon(type_code, bounds, page)

            if not pois:
                if page == 1:
                    logger.info(f"  网格无数据: {grid_name} - {type_name}")
                break

            for poi in pois:
                result = self.process_poi(poi, type_name, grid_name)
                if result:
                    with self.results_lock:
                        self.results.append(result)
                        collected += 1

            logger.info(f"  {grid_name} [{type_name}] 第{page}页: 获取{len(pois)}条, 累计{collected}条")

            if len(pois) < 25:
                break

            page += 1
            time.sleep(0.1)

        if collected > 0:
            logger.info(f"   {grid_name} [{type_name}] 完成: 采集{collected}条")

        with self.stats_lock:
            self.stats["total_grids"] += 1

        return collected

    def collect_by_grid_system(self, type_info: Dict) -> int:
        """使用网格系统采集指定类型的POI"""
        type_name = type_info["name"]
        logger.info(f"\n{'=' * 60}")
        logger.info(f"开始采集类型: {type_name}")
        logger.info(f"{'=' * 60}")

        total_collected = 0

        # 使用优化的网格边界    按区采如果结果小于100就全市采
        for grid in self.grid_bounds:
            grid_name = grid["name"]
            bounds = grid["bounds"]

            collected = self.collect_in_grid(type_info, bounds, grid_name, depth=0)
            total_collected += collected

            logger.info(f"  {grid_name} 类型[{type_name}] 采集: {collected}条")

            # 定期保存
            if len(self.results) % 2000 == 0:
                self.save_checkpoint()

        # 如果优化网格采集不足，使用全市矩形网格
        if total_collected < 100:  # 阈值可调整
            logger.info(f"  优化网格采集较少，使用全市矩形网格补充")
            collected = self.collect_in_grid(
                type_info,
                [self.city_bounds["min_lng"], self.city_bounds["min_lat"],
                 self.city_bounds["max_lng"], self.city_bounds["max_lat"]],
                "全市矩形",
                depth=0
            )
            total_collected += collected

        logger.info(f" 类型 {type_name} 采集完成: 总计{total_collected}条")
        return total_collected

    def load_checkpoint(self):
        """加载检查点"""
        if os.path.exists(self.checkpoint_file):
            try:
                df = pd.read_excel(self.checkpoint_file, engine='openpyxl')
                if len(df) > 0:
                    for _, row in df.iterrows():
                        poi_id = row.get('POI_ID', '')
                        if poi_id:
                            with self.seen_lock:
                                self.seen_poi_ids.add(poi_id)
                    self.results = df.to_dict('records')
                    self.last_saved_count = len(self.results)
                    logger.info(f"从检查点恢复 {len(self.results)} 条数据")
            except Exception as e:
                logger.warning(f"加载检查点失败: {e}")

    def save_checkpoint(self):
        """保存检查点"""
        with self.results_lock:
            if len(self.results) > self.last_saved_count + 100:
                df = pd.DataFrame(self.results)
                with pd.ExcelWriter(self.checkpoint_file, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='海口POI数据', index=False)
                self.last_saved_count = len(self.results)
                logger.info(f"检查点已保存: {len(self.results)} 条")

    def run_full_collection(self):
        """运行全量采集"""
        start_time = time.time()
        logger.info("=" * 70)
        logger.info("海口市POI采集器 - 多边形搜索+动态网格切分版")
        logger.info(f"可用API密钥: {len(self.api_keys)} 个")
        logger.info(f"POI类型数量: {len(self.poi_types)} 个")
        logger.info(f"初始网格数量: {len(self.grid_bounds)} 个")
        logger.info("=" * 70)

        total_collected = len(self.results)
        logger.info(f"已恢复数据: {total_collected} 条")

        for idx, type_info in enumerate(self.poi_types):
            if total_collected > 0 and total_collected % 5000 == 0:
                self.save_checkpoint()

            count = self.collect_by_grid_system(type_info)
            total_collected += count

            elapsed = time.time() - start_time
            rate = total_collected / elapsed if elapsed > 0 else 0
            logger.info(f"\n 全局进度: {idx + 1}/{len(self.poi_types)} 类型")
            logger.info(f" 累计采集: {total_collected:,} 条")
            logger.info(f" 平均速率: {rate:.1f} 条/秒")
            logger.info(f" 网格切分数: {self.stats['grid_splits']}")
            logger.info(f" 处理网格数: {self.stats['total_grids']}")

            self.save_checkpoint()

        # 最终统计
        self.print_stats(start_time)
        return self.results

    def print_stats(self, start_time):
        """打印统计"""
        elapsed = time.time() - start_time

        logger.info("\n" + "=" * 70)
        logger.info(" 采集完成！")
        logger.info(f"总耗时: {elapsed:.1f} 秒 ({elapsed / 3600:.2f} 小时)")
        logger.info(f"总请求数: {self.stats['total_requests']:,}")
        logger.info(f"成功请求: {self.stats['success_requests']:,}")
        logger.info(f"失败请求: {self.stats['failed_requests']:,}")
        logger.info(f"网格切分次数: {self.stats['grid_splits']:,}")
        logger.info(f"处理网格总数: {self.stats['total_grids']:,}")
        logger.info(f"唯一POI总数: {len(self.seen_poi_ids):,}")
        logger.info(f"采集数据量: {len(self.results):,} 条")

        if len(self.results) > 0:
            df = pd.DataFrame(self.results)

            # 行政区分布
            logger.info("\n 各区分布:")
            district_counts = df['行政区'].value_counts()
            for district, count in district_counts.items():
                logger.info(f"  {district}: {count:,} 条 ({count / len(df) * 100:.1f}%)")

            # 类型分布
            logger.info("\n 类型分布TOP10:")
            type_counts = df['子类型'].value_counts().head(10)  # 类型分布TOP10
            for type_name, count in type_counts.items():
                logger.info(f"  {type_name}: {count:,} 条")

            self.save_final_results()

    def save_final_results(self):
        """保存最终结果"""
        df = pd.DataFrame(self.results)

        # 经纬度去重
        original_count = len(df)
        df = df.drop_duplicates(subset=['经度', '纬度'])  # subset：指定用于判断重复的列（子集）
        if original_count > len(df):
            logger.info(f"经过去重: {original_count} -> {len(df)} 条")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"haikou_poi_polygon_{len(df)}条_{timestamp}.xlsx"

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='全部POI', index=False)  # index=False：不写入 DataFrame 的索引列

            if '子类型' in df.columns:
                # value_counts()：统计每个子类型的数量
                # reset_index()：将索引（类型）转换为列
                type_stats = df['子类型'].value_counts().reset_index()
                type_stats.columns = ['类型', '数量']
                type_stats.to_excel(writer, sheet_name='类型统计', index=False)

            district_stats = df['行政区'].value_counts().reset_index()
            district_stats.columns = ['行政区', '数量']
            district_stats.to_excel(writer, sheet_name='行政区统计', index=False)

            # 网格来源统计
            if '来源网格' in df.columns:
                grid_stats = df['来源网格'].value_counts().head(20).reset_index()
                grid_stats.columns = ['网格', '数量']
                grid_stats.to_excel(writer, sheet_name='网格统计', index=False)

        logger.info(f"\n 数据已保存: {filename}")


def main():
    """主函数"""
    API_KEYS = [
        "替换为自己的KEY"
    ]

    logger.info("=" * 70)
    logger.info("海口市POI采集器 v4.0 - 多边形搜索+网格切分版")
    logger.info("=" * 70)

    collector = HaikouPolygonCollector(API_KEYS)

    logger.info(f"\n 采集策略:")
    logger.info(f"  - 采集方式: 多边形搜索 + 动态网格切分")
    logger.info(f"  - POI类型: {len(collector.poi_types)} 个核心类型")
    logger.info(f"  - 初始网格: {len(collector.grid_bounds)} 个优化网格")
    logger.info(f"  - 最大切分深度: {collector.max_grid_depth}")
    logger.info(f"  - 单网格POI阈值: {collector.poi_threshold} 条")
    logger.info(f"  - 最小网格精度: {collector.min_grid_size} 度 (~{collector.min_grid_size * 111:.1f}km)")

    try:
        results = collector.run_full_collection()
        logger.info(f"\n 采集成功！共获取 {len(results)} 条数据")
    except KeyboardInterrupt:
        logger.info("\n 用户中断")
        collector.save_checkpoint()
    except Exception as e:
        logger.error(f" 程序异常: {e}", exc_info=True)
        collector.save_checkpoint()


if __name__ == "__main__":
    main()
