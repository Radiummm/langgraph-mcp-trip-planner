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
from ..models.schemas import TripRequest, TripPlan
from ..config import get_settings
from .travel_skills import build_skill_context

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
    planner_context: str
    trip_plan: Optional[dict]
    validation_errors: list[str]
    repair_attempted: bool
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
        workflow.add_node("build_planner_context", self._context_builder_node)
        workflow.add_node("plan_itinerary", self._planner_node)
        workflow.add_node("validate_itinerary", self._validator_node)
        workflow.add_node("repair_itinerary", self._repair_node)

        workflow.add_edge(START, "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "search_attractions")
        workflow.add_edge("search_attractions", "query_weather")
        workflow.add_edge("query_weather", "search_hotels")
        workflow.add_edge("search_hotels", "build_planner_context")
        workflow.add_edge("build_planner_context", "plan_itinerary")
        workflow.add_edge("plan_itinerary", "validate_itinerary")
        workflow.add_conditional_edges(
            "validate_itinerary",
            self._route_after_validation,
            {"repair": "repair_itinerary", "end": END},
        )
        workflow.add_edge("repair_itinerary", "validate_itinerary")

        return workflow.compile()

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        result = await self.graph.ainvoke(
            {
                "request": request,
                "rag_context": "",
                "attraction_results": "",
                "weather_results": "",
                "hotel_results": "",
                "planner_context": "",
                "trip_plan": None,
                "validation_errors": [],
                "repair_attempted": False,
                "error": None,
            }
        )
        trip_plan = result.get("trip_plan")
        if not trip_plan:
            raise ValueError("旅行计划生成失败：模型未返回可解析的行程JSON")
        if result.get("validation_errors"):
            raise ValueError(f"旅行计划校验失败：{'; '.join(result['validation_errors'])}")
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
        keywords=" ".join(request.preferences) if request.preferences else "景点"
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

    async def _context_builder_node(self, state: TripPlannerState) -> dict:
        """节点4: 裁剪并组装给Planner的上下文。"""
        print("🧩 节点4-构建Planner上下文")
        skill_context = build_skill_context(state["request"])
        # ponytail: 字符数裁剪足够面试demo；如果真实流量上来，再换token级裁剪和结构化POI列表。
        context = f"""**RAG摘要:**
{self._trim(state["rag_context"], 1200) or "无"}

**旅行Skills:**
{skill_context}

**景点候选摘要:**
{self._trim(state["attraction_results"], 2000) or "无"}

**天气摘要:**
{self._trim(state["weather_results"], 800) or "无"}

**酒店候选摘要:**
{self._trim(state["hotel_results"], 1200) or "无"}
"""
        return {"planner_context": context}

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

**可用上下文:**
{state["planner_context"]}

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
        
        print(f"🗺️  节点5-规划行程: {query[:200]}...")

        response=await self._planner_chain.ainvoke({
            "query": query
        })

        response_text=response.content
        try:
            trip_plan=self._parse_response(response_text)
            return {"trip_plan": trip_plan.model_dump()}
        except Exception as e:
            print(f"⚠️  规划解析失败: {e}")
            return {"trip_plan": None, "validation_errors": [f"规划JSON解析失败: {e}"]}

    async def _validator_node(self, state: TripPlannerState) -> dict:
        """节点6: 用schema和业务规则校验Planner输出。"""
        errors = self._validate_plan(state.get("trip_plan"), state["request"])
        if errors:
            print(f"🔎 节点6-行程校验未通过: {errors}")
        else:
            print("🔎 节点6-行程校验通过")
        return {"validation_errors": errors}

    async def _repair_node(self, state: TripPlannerState) -> dict:
        """节点7: 只修复一次结构和缺失字段。"""
        request = state["request"]
        print("🛠️  节点7-修复行程JSON")
        query = f"""下面的旅行计划没有通过校验，请只修复JSON，不要输出解释。

**校验错误:**
{json.dumps(state["validation_errors"], ensure_ascii=False)}

**原旅行计划:**
{json.dumps(state["trip_plan"], ensure_ascii=False)}

**可用上下文:**
{state["planner_context"]}

请返回符合要求的{request.city}{request.travel_days}天旅行计划JSON。"""
        response = await self._planner_chain.ainvoke({"query": query})
        trip_plan = self._parse_response(response.content)
        return {"trip_plan": trip_plan.model_dump(), "repair_attempted": True}

    def _route_after_validation(self, state: TripPlannerState) -> str:
        if state.get("validation_errors") and not state.get("repair_attempted"):
            return "repair"
        return "end"
    # ============ 辅助方法(沿用原有逻辑) ============

    def _trim(self, text: str, limit: int) -> str:
        text = (text or "").strip()
        return text if len(text) <= limit else text[:limit] + "\n...(已裁剪)"

    def _validate_plan(self, plan: Optional[dict], request: TripRequest) -> list[str]:
        if not plan:
            return ["未生成trip_plan"]

        try:
            trip_plan = TripPlan(**plan)
        except Exception as e:
            return [f"TripPlan schema不合法: {e}"]

        errors: list[str] = []
        if trip_plan.city != request.city:
            errors.append("城市与用户请求不一致")
        if len(trip_plan.days) != request.travel_days:
            errors.append("行程天数与用户请求不一致")

        for day in trip_plan.days:
            if not 2 <= len(day.attractions) <= 3:
                errors.append(f"第{day.day_index + 1}天景点数量应为2-3个")
            meal_types = {meal.type for meal in day.meals}
            if not {"breakfast", "lunch", "dinner"}.issubset(meal_types):
                errors.append(f"第{day.day_index + 1}天缺少早中晚三餐")
            for attraction in day.attractions:
                location = attraction.location
                if location.longitude == 0 or location.latitude == 0:
                    errors.append(f"{attraction.name}缺少有效坐标")

        if trip_plan.budget:
            budget = trip_plan.budget
            subtotal = (
                budget.total_attractions
                + budget.total_hotels
                + budget.total_meals
                + budget.total_transportation
            )
            if budget.total != subtotal:
                errors.append("预算总额与分项加总不一致")

        return errors

    def _parse_response(self, response: str) -> TripPlan:
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

async def get_trip_planner_agent() -> LangGraphTripPlanner:
    global _planner_instance

    if not _planner_instance:
        instance = LangGraphTripPlanner()
        await instance.initialize_tools()
        _planner_instance = instance

    return _planner_instance
