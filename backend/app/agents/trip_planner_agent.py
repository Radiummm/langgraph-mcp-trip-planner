"""多智能体旅行规划系统"""

import asyncio
import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_tools, get_tool_map_sync
from ..services.rag_service import get_rag_service
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, Location
from ..config import get_settings

_planner_instance: Optional["LangGraphTripPlanner"] = None

# ============ Agent提示词 (去掉[TOOL_CALL:...]格式指令) ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

重要提示:
你必须使用提供的工具来搜索真实的景点信息，不要编造数据。

当搜索景点时:
- 使用 maps_text_search 工具
- keywords 设为用户偏好或"景点"
- city 设为目标城市
- 如果搜索结果不够，尝试不同的关键词组合
- 返回你搜索到的所有景点信息(名称、地址、描述等)
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

重要提示:
你必须使用提供的工具来查询真实天气，不要编造数据。

当查询天气时:
- 使用 maps_weather 工具
- city 设为目标城市
- 返回完整的天气信息
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市搜索合适的酒店。

重要提示:
你必须使用提供的工具来搜索真实的酒店信息，不要编造数据。

当搜索酒店时:
- 使用 maps_text_search 工具
- keywords 设为"酒店"或"宾馆"
- city 设为目标城市
- 返回你搜索到的所有酒店信息(名称、地址、价格等)
"""

PLANNER_SYSTEM_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

重要提示:
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. 必须包含预算信息:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""

class TripPlannerState(TypedDict):
    request: TripRequest
    rag_context: str
    attraction_results:str
    weather_results:str
    hotel_results:str
    trip_plan: Optional[dict]
    error:Optional[str]

class LangGraphTripPlanner:
    def __init__(self):
        try:
            self.settings=get_settings()
            self.llm = get_llm()
            self.graph=self._build_graph()

        except Exception as e:
            print(f"❌ LangGraph系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def initialize_tools(self):
        await  get_amap_tools()  # 初始化高德工具

        print("高德工具初始化完成")
        tools = list(get_tool_map_sync().values())

        self._attraction_agent=create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=ATTRACTION_AGENT_PROMPT,
        )

        print("  - 创建天气查询Agent...")
        self._weather_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=WEATHER_AGENT_PROMPT,
        )

        print("  - 创建酒店推荐Agent...")
        self._hotel_agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=HOTEL_AGENT_PROMPT,
        )

        print("  - 创建行程规划链...")
        planner_system_prompt = PLANNER_SYSTEM_PROMPT.replace("{", "{{").replace("}", "}}")
        planner_prompt = ChatPromptTemplate.from_messages([
            ("system", planner_system_prompt),
            ("human", "{query}"),
        ])
        self._planner_chain = planner_prompt | self.llm

        print("  ✅ 所有子agent和工具初始化完成")


    def _build_graph(self):
        workflow=StateGraph(TripPlannerState)

        workflow.add_node("retrieve_knowledge", self._rag_node)
        workflow.add_node("search_attractions", self._attraction_node)
        workflow.add_node("query_weather", self._weather_node)
        workflow.add_node("search_hotels", self._hotel_node)
        workflow.add_node("plan_itinerary", self._planner_node)

        workflow.add_edge(START, "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "search_attractions")
        workflow.add_edge("search_attractions", "query_weather")
        workflow.add_edge("query_weather", "search_hotels")
        workflow.add_edge("search_hotels", "plan_itinerary")
        workflow.add_edge("plan_itinerary", END)

        return workflow.compile()

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        result = await self.graph.ainvoke(
            {
                "request": request,
                "rag_context": "",
                "attraction_results": "",
                "weather_results": "",
                "hotel_results": "",
                "trip_plan": None,
                "error": None,
            }
        )
        trip_plan = result.get("trip_plan")
        if not trip_plan:
            return self._create_fallback_plan(request)
        return TripPlan(**trip_plan)

    async def _rag_node(self, state: TripPlannerState) -> dict:
        request = state["request"]
        print(f"📚 节点0-RAG检索: {request.city} / {request.preferences}")

        try:
            rag_service = get_rag_service()
            chunks = await asyncio.to_thread(
                rag_service.retrieve,
                city=request.city,
                preferences=request.preferences,
                free_text_input=request.free_text_input or "",
            )
            rag_context = rag_service.format_context(chunks)
            if rag_context:
                print(f"   召回知识片段: {len(chunks)} 个")
            else:
                print("   RAG未配置或未召回相关知识片段")
            return {"rag_context": rag_context}
        except Exception as e:
            print(f"⚠️  RAG检索失败，跳过知识增强: {e}")
            return {"rag_context": ""}
    
    async def _attraction_node(self, state: TripPlannerState) -> dict:
        request=state["request"]
        keywords=request.preferences[0] if request.preferences else "景点"
        query = f"请搜索{request.city}的{keywords}相关景点，返回详细的景点信息。"
        print(f"📍 节点1-搜索景点: {query}")
        result = await self._attraction_agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        response = result["messages"][-1].content
        print(f"   结果: {response[:200]}...")
        return {"attraction_results": response}

    async def _weather_node(self, state: TripPlannerState) -> dict:
        request = state["request"]
        query = f"请查询{request.city}的天气信息"
        print(f"🌤️  节点2-查询天气: {query}")

        result=await self._weather_agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        
        response=result["messages"][-1].content
        print(f"   结果: {response[:200]}...")
        return {"weather_results": response}


    async def _hotel_node(self, state: TripPlannerState) -> dict:
        """节点3: 搜索酒店"""
        request = state["request"]
        query = f"请搜索{request.city}的{request.accommodation}酒店"
        print(f"🏨 节点3-搜索酒店: {query}")

        result = await self._hotel_agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        response = result["messages"][-1].content
        print(f"   结果: {response[:200]}...")
        return {"hotel_results": response}

    async def _planner_node(self, state: TripPlannerState) -> dict:
        request = state["request"]

        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**RAG知识库召回内容:**
{state["rag_context"] or "未召回相关知识片段，请主要参考工具结果。"}

**景点信息:**
{state["attraction_results"]}

**天气信息:**
{state["weather_results"]}

**酒店信息:**
{state["hotel_results"]}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
6. 景点的经纬度坐标要真实准确
"""
        
        if request.free_text_input:
            query += f"\n\n**用户补充信息:** {request.free_text_input}"
        
        print(f"🗺️  节点4-规划行程: {query[:200]}...")

        response=await self._planner_chain.ainvoke({
            "query": query
        })

        response_text=response.content
        try:
            trip_plan=self._parse_response(response_text,request)
            return {"trip_plan": trip_plan.model_dump()}
        except Exception as e:
            print(f"⚠️  规划解析失败: {e}，使用fallback")
            fallback = self._create_fallback_plan(request)
            return {"trip_plan": fallback.model_dump()}
    # ============ 辅助方法(沿用原有逻辑) ============

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")

            data = json.loads(json_str)
            return TripPlan(**data)

        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        from datetime import datetime, timedelta

        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)

            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )

async def get_trip_planner_agent() -> LangGraphTripPlanner:
    global _planner_instance

    if not _planner_instance:
        instance = LangGraphTripPlanner()
        await instance.initialize_tools()
        _planner_instance = instance

    return _planner_instance
