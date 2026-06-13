"""高德地图MCP服务封装"""

import json
import re
from typing import Any, Dict, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

_mcp_client: Optional[MultiServerMCPClient] = None
_amap_tools: Optional[List[Any]] = None
_tool_map: Optional[Dict[str, Any]] = None
_amap_service: Optional["AmapService"] = None


async def get_amap_tools() -> List[Any]:
    """初始化并返回高德 MCP 工具列表。"""
    global _mcp_client, _amap_tools, _tool_map

    if _amap_tools is None:
        settings = get_settings()
        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")

        _mcp_client = MultiServerMCPClient(
            {
                "amap": {
                    "transport": "stdio",
                    "command": "uvx",
                    "args": ["amap-mcp-server"],
                    "env": {"AMAP_MAPS_API_KEY": settings.amap_api_key},
                }
            }
        )
        _amap_tools = await _mcp_client.get_tools()
        _tool_map = {tool.name: tool for tool in _amap_tools}

        print("✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_tools)}")
        for tool in _amap_tools[:5]:
            print(f"     - {tool.name}")
        if len(_amap_tools) > 5:
            print(f"     ... 还有 {len(_amap_tools) - 5} 个工具")

    return _amap_tools


def get_tool_map_sync() -> Dict[str, Any]:
    """同步读取已初始化的工具映射。"""
    if _tool_map is None:
        raise RuntimeError("高德MCP工具尚未初始化")
    return _tool_map


def _format_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


class AmapService:
    """高德地图服务封装类。"""

    async def _ensure_tools(self) -> Dict[str, Any]:
        await get_amap_tools()
        return get_tool_map_sync()

    async def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        try:
            tool_map = await self._ensure_tools()
            tool = tool_map.get("maps_text_search")
            if tool is None:
                raise RuntimeError("MCP工具 maps_text_search 不存在")

            result = await tool.ainvoke(
                {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower(),
                }
            )
            print(f"POI搜索结果: {_format_tool_result(result)[:200]}...")

            data = _extract_json_object(_format_tool_result(result))
            pois = data.get("pois", []) if data else []
            parsed: List[POIInfo] = []
            for poi in pois:
                location_text = poi.get("location", "")
                longitude, latitude = 0.0, 0.0
                if isinstance(location_text, str) and "," in location_text:
                    longitude_text, latitude_text = location_text.split(",", 1)
                    longitude = float(longitude_text)
                    latitude = float(latitude_text)
                parsed.append(
                    POIInfo(
                        id=str(poi.get("id", "")),
                        name=str(poi.get("name", "")),
                        type=str(poi.get("type", "")),
                        address=str(poi.get("address", "")),
                        location=Location(longitude=longitude, latitude=latitude),
                        tel=poi.get("tel"),
                    )
                )
            return parsed
        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    async def get_weather(self, city: str) -> List[WeatherInfo]:
        try:
            tool_map = await self._ensure_tools()
            tool = tool_map.get("maps_weather")
            if tool is None:
                raise RuntimeError("MCP工具 maps_weather 不存在")

            result = await tool.ainvoke({"city": city})
            print(f"天气查询结果: {_format_tool_result(result)[:200]}...")
            return []
        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    async def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking",
    ) -> Optional[Dict[str, Any]]:
        try:
            tool_map = await self._ensure_tools()
            route_tools = {
                "walking": "maps_direction_walking_by_address",
                "driving": "maps_direction_driving_by_address",
                "transit": "maps_direction_transit_integrated_by_address",
            }
            tool_name = route_tools.get(route_type, "maps_direction_walking_by_address")
            tool = tool_map.get(tool_name)
            if tool is None:
                raise RuntimeError(f"MCP工具 {tool_name} 不存在")

            arguments = {
                "origin_address": origin_address,
                "destination_address": destination_address,
            }
            if origin_city:
                arguments["origin_city"] = origin_city
            if destination_city:
                arguments["destination_city"] = destination_city

            result = await tool.ainvoke(arguments)
            print(f"路线规划结果: {_format_tool_result(result)[:200]}...")
            return None
        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return None

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        try:
            tool_map = await self._ensure_tools()
            tool = tool_map.get("maps_geo")
            if tool is None:
                raise RuntimeError("MCP工具 maps_geo 不存在")

            arguments = {"address": address}
            if city:
                arguments["city"] = city
            result = await tool.ainvoke(arguments)
            print(f"地理编码结果: {_format_tool_result(result)[:200]}...")
            return None
        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    async def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        try:
            tool_map = await self._ensure_tools()
            tool = tool_map.get("maps_search_detail")
            if tool is None:
                raise RuntimeError("MCP工具 maps_search_detail 不存在")

            result = await tool.ainvoke({"id": poi_id})
            result_text = _format_tool_result(result)
            print(f"POI详情结果: {result_text[:200]}...")

            data = _extract_json_object(result_text)
            return data if data else {"raw": result_text}
        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}


async def get_amap_service() -> AmapService:
    """获取高德地图服务实例。"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service
