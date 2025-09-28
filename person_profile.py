"""
可复用的人物画像和场景生成系统
结合了灵活的轴架构设计和实用的业务配置
支持多领域、多语言、可扩展的人物画像生成
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol, Dict, Any, Union, Callable
from faker import Faker
import random
import json


class PersonalAxis(Protocol):
    """人物轴接口协议"""
    axis_name: str
    
    def get(self) -> str:
        """获取轴值"""
        ...
    
    def get_weighted(self, weight: float = 1.0) -> str:
        """获取带权重的轴值（用于智能匹配）"""
        ...


@dataclass
class DiscreteAxis:
    """离散选择轴"""
    axis_name: str
    options: List[str]
    weights: Optional[List[float]] = None
    
    def get(self) -> str:
        if self.weights:
            return random.choices(self.options, weights=self.weights)[0]
        return random.choice(self.options)
    
    def get_weighted(self, weight: float = 1.0) -> str:
        # 根据权重调整选择概率
        if weight > 1.0:  # 偏向极端值
            extreme_indices = [0, len(self.options)-1]
            if len(self.options) > 2:
                return random.choice([self.options[i] for i in extreme_indices])
        elif weight < 1.0:  # 偏向中间值
            mid = len(self.options) // 2
            return self.options[mid]
        return self.get()


@dataclass 
class FakerAxis:
    """基于Faker的轴"""
    axis_name: str
    faker_method: str = "name"
    lang: str = "zh_CN"
    format_func: Optional[Callable] = None
    
    def __post_init__(self):
        self.faker = Faker(self.lang)
        if not hasattr(self.faker, self.faker_method):
            raise ValueError(f"Faker does not have method {self.faker_method}")
    
    def get(self) -> str:
        method = getattr(self.faker, self.faker_method)
        result = method()
        if self.format_func:
            result = self.format_func(result)
        return str(result)
    
    def get_weighted(self, weight: float = 1.0) -> str:
        return self.get()


@dataclass
class RangeAxis:
    """数值范围轴"""
    axis_name: str
    min_value: Union[int, float] = 0
    max_value: Union[int, float] = 10
    is_float: bool = False
    
    def get(self) -> str:
        if self.is_float:
            value = random.uniform(self.min_value, self.max_value)
            return f"{value:.1f}"
        else:
            value = random.randint(int(self.min_value), int(self.max_value))
            return str(value)
    
    def get_weighted(self, weight: float = 1.0) -> str:
        # 权重影响数值分布
        if weight > 1.0:  # 偏向极值
            if random.random() < 0.5:
                target = self.min_value
            else:
                target = self.max_value
        else:  # 偏向中值
            target = (self.min_value + self.max_value) / 2
        
        # 添加随机偏移
        if self.is_float:
            offset = (self.max_value - self.min_value) * 0.1 * random.uniform(-1, 1)
            value = max(self.min_value, min(self.max_value, target + offset))
            return f"{value:.1f}"
        else:
            offset = int((self.max_value - self.min_value) * 0.1 * random.uniform(-1, 1))
            value = max(int(self.min_value), min(int(self.max_value), int(target + offset)))
            return str(value)


@dataclass
class ConditionalAxis:
    """条件轴 - 根据其他轴的值动态选择"""
    axis_name: str
    conditions: Dict[str, Dict[str, Any]]  # {condition_axis: {value: options}}
    default_axis: PersonalAxis
    
    def __init__(self, axis_name: str, conditions: Dict, default_axis: PersonalAxis):
        self.axis_name = axis_name
        self.conditions = conditions
        self.default_axis = default_axis
        self._context = {}
    
    def set_context(self, context: Dict[str, str]):
        """设置上下文（其他轴的值）"""
        self._context = context
    
    def get(self) -> str:
        for condition_axis, value_map in self.conditions.items():
            if condition_axis in self._context:
                context_value = self._context[condition_axis]
                for pattern, axis in value_map.items():
                    if pattern in context_value or pattern == context_value:
                        return axis.get()
        return self.default_axis.get()
    
    def get_weighted(self, weight: float = 1.0) -> str:
        return self.get()


class AxisPresets:
    """预设轴配置库"""
    
    # ========== 中文轴定义 ==========
    @staticmethod
    def patience_zh():
        return DiscreteAxis(
            axis_name="耐心程度",
            options=[
                "极度耐心", "非常耐心", "比较耐心", "有耐心", "普通", 
                "有点急躁", "比较急躁", "很急躁", "非常急躁", "极度急躁"
            ]
        )
    
    @staticmethod
    def clarity_zh():
        return DiscreteAxis(
            axis_name="表达清晰度",
            options=[
                "表达清晰", "逻辑清楚", "条理分明", "比较清楚", "普通", 
                "有点模糊", "表达不清", "逻辑混乱", "很难理解", "完全不清楚"
            ]
        )
    
    @staticmethod
    def verbosity_zh():
        return DiscreteAxis(
            axis_name="话语量",
            options=[
                "话很多", "比较健谈", "爱聊天", "话适中", "普通", 
                "话较少", "比较安静", "很少说话", "惜字如金", "几乎不说话"
            ]
        )
    
    @staticmethod
    def politeness_zh():
        return DiscreteAxis(
            axis_name="礼貌程度",
            options=[
                "极其礼貌", "非常客气", "很有礼貌", "比较礼貌", "普通", 
                "有点直接", "比较直率", "不太客气", "有些粗鲁", "很不礼貌"
            ]
        )
    
    @staticmethod
    def expertise_zh():
        return DiscreteAxis(
            axis_name="专业程度",
            options=[
                "专家级别", "非常专业", "很有经验", "比较专业", "普通用户", 
                "新手", "初学者", "不太了解", "完全不懂", "一无所知"
            ]
        )
    
    @staticmethod
    def emotion_zh():
        return DiscreteAxis(
            axis_name="情绪状态",
            options=[
                "非常开心", "开心", "平静", "普通", "有点焦虑", 
                "焦虑", "不安", "生气", "很生气", "愤怒"
            ]
        )
    
    @staticmethod
    def name_zh():
        return FakerAxis(
            axis_name="姓名",
            faker_method="name",
            lang="zh_CN"
        )
    
    @staticmethod
    def age():
        return RangeAxis(
            axis_name="年龄",
            min_value=18,
            max_value=70
        )
    
    @staticmethod
    def occupation_zh():
        return DiscreteAxis(
            axis_name="职业",
            options=[
                "程序员", "教师", "医生", "律师", "销售", "会计", 
                "工程师", "设计师", "学生", "服务员", "司机", "个体户"
            ]
        )
    
    @staticmethod
    def education_zh():
        return DiscreteAxis(
            axis_name="学历",
            options=["小学", "初中", "高中", "大专", "本科", "硕士", "博士"]
        )
    
    @staticmethod
    def income_level_zh():
        return DiscreteAxis(
            axis_name="收入水平",
            options=["低收入", "中等收入", "高收入"]
        )
    
    # ========== 英文轴定义 ==========
    @staticmethod
    def patience_en():
        return DiscreteAxis(
            axis_name="patience",
            options=[
                "Extremely Patient", "Very Patient", "Patient", "Neutral", 
                "Slightly Impatient", "Impatient", "Very Impatient", "Extremely Impatient"
            ]
        )
    
    @staticmethod
    def mbti():
        return DiscreteAxis(
            axis_name="personality_type",
            options=[
                "INTJ (Architect)", "INTP (Thinker)", "ENTJ (Commander)", "ENTP (Debater)",
                "INFJ (Advocate)", "INFP (Mediator)", "ENFJ (Protagonist)", "ENFP (Campaigner)",
                "ISTJ (Logistician)", "ISFJ (Defender)", "ESTJ (Executive)", "ESFJ (Consul)",
                "ISTP (Virtuoso)", "ISFP (Adventurer)", "ESTP (Entrepreneur)", "ESFP (Entertainer)"
            ]
        )


class PersonaProfile:
    """人物画像类"""
    
    def __init__(self, 
                 axes: List[PersonalAxis] = None, 
                 language: str = "简体中文",
                 profile_id: str = None,
                 preset_name: str = None):
        self.axes = axes or []
        self.language = language
        self.profile_id = profile_id or f"profile_{random.randint(1000, 9999)}"
        self.preset_name = preset_name  # 🔥 新增：记录画像预设名称
        self._cache = {}
        self._context = {}
    
    def add_axis(self, axis: PersonalAxis):
        """添加轴"""
        self.axes.append(axis)
    
    def remove_axis(self, axis_name: str):
        """移除轴"""
        self.axes = [axis for axis in self.axes if axis.axis_name != axis_name]
    
    def get_axis_value(self, axis_name: str, use_cache: bool = True) -> Optional[str]:
        """获取特定轴的值"""
        if use_cache and axis_name in self._cache:
            return self._cache[axis_name]
        
        for axis in self.axes:
            if axis.axis_name == axis_name:
                # 为条件轴设置上下文
                if isinstance(axis, ConditionalAxis):
                    axis.set_context(self._context)
                
                value = axis.get()
                if use_cache:
                    self._cache[axis_name] = value
                    self._context[axis_name] = value
                return value
        return None
    
    def generate_profile(self, use_cache: bool = True) -> Dict[str, str]:
        """生成完整画像"""
        profile = {}
        
        # 第一轮：生成基础轴的值
        for axis in self.axes:
            if not isinstance(axis, ConditionalAxis):
                value = self.get_axis_value(axis.axis_name, use_cache)
                if value:
                    profile[axis.axis_name] = value
        
        # 第二轮：生成条件轴的值
        for axis in self.axes:
            if isinstance(axis, ConditionalAxis):
                value = self.get_axis_value(axis.axis_name, use_cache)
                if value:
                    profile[axis.axis_name] = value
        
        return profile
    
    def get_persona_text(self) -> List[str]:
        """获取文本格式的画像"""
        profile = self.generate_profile()
        persona_items = []
        
        for axis_name, value in profile.items():
            persona_items.append(f"{axis_name}: {value}")
        
        if self.language:
            persona_items.append(f"使用语言: {self.language}")
        
        return persona_items
    
    def as_prompt(self, identifier: str = "人物画像") -> str:
        """生成提示词格式"""
        profile_text = "\n".join(self.get_persona_text())
        return f"<{identifier}>\n{profile_text}\n</{identifier}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "profile_id": self.profile_id,
            "language": self.language,
            "preset_name": self.preset_name,  # 🔥 添加预设名称
            "profile": self.generate_profile(),
            "axes_config": [
                {
                    "axis_name": axis.axis_name,
                    "axis_type": type(axis).__name__
                } for axis in self.axes
            ]
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ProfilePresets:
    """预设画像配置"""
    
    @staticmethod
    def basic_chinese_customer():
        """基础中文客户画像"""
        return PersonaProfile(
            axes=[
                AxisPresets.name_zh(),
                AxisPresets.age(),
                AxisPresets.occupation_zh(),
                AxisPresets.education_zh(),
                AxisPresets.patience_zh(),
                AxisPresets.politeness_zh(),
                AxisPresets.emotion_zh()
            ],
            language="简体中文",
            preset_name="basic_chinese_customer" 
        )
    
    @staticmethod
    def business_customer():
        """商业客户画像"""
        return PersonaProfile(
            axes=[
                AxisPresets.name_zh(),
                AxisPresets.age(),
                AxisPresets.occupation_zh(),
                AxisPresets.education_zh(),
                AxisPresets.income_level_zh(),
                AxisPresets.patience_zh(),
                AxisPresets.clarity_zh(),
                AxisPresets.politeness_zh(),
                AxisPresets.expertise_zh(),
                AxisPresets.emotion_zh()
            ],
            language="简体中文",
            preset_name="business_customer"
        )
    
    @staticmethod
    def tech_support_user():
        """技术支持用户画像"""
        tech_skill = DiscreteAxis(
            axis_name="技术水平",
            options=["完全小白", "初学者", "有一定基础", "比较熟练", "技术专家"]
        )
        
        problem_urgency = DiscreteAxis(
            axis_name="问题紧急程度", 
            options=["不急", "一般", "比较急", "很急", "非常紧急"]
        )
        
        return PersonaProfile(
            axes=[
                AxisPresets.name_zh(),
                AxisPresets.age(),
                AxisPresets.occupation_zh(),
                tech_skill,
                problem_urgency,
                AxisPresets.patience_zh(),
                AxisPresets.clarity_zh(),
                AxisPresets.emotion_zh()
            ],
            language="简体中文",
            preset_name="tech_support_user"
        )
    
    @staticmethod
    def international_user():
        """国际用户画像（英文）"""
        return PersonaProfile(
            axes=[
                FakerAxis("name", faker_method="name", lang="en_US"),
                AxisPresets.age(),
                FakerAxis("occupation", faker_method="job", lang="en_US"),
                AxisPresets.patience_en(),
                AxisPresets.mbti()
            ],
            language="English",
            preset_name="international_user" 
        )
        
    @staticmethod
    def diverse_conditional_customer():
        """风格多样、画像维度完整的条件轴客户画像"""
        # 不同职业对应的沟通风格
        tech_style = DiscreteAxis("沟通风格", ["技术术语", "逻辑清晰", "简洁直接"])
        doctor_style = DiscreteAxis("沟通风格", ["专业严谨", "耐心细致", "温和解释"])
        sales_style = DiscreteAxis("沟通风格", ["热情主动", "善于倾听", "引导成交"])
        teacher_style = DiscreteAxis("沟通风格", ["循循善诱", "条理清晰", "亲切随和"])
        default_style = DiscreteAxis("沟通风格", ["普通", "一般", "随意"])

        # 年龄影响情绪表达
        young_emotion = DiscreteAxis("情绪状态", ["活力充沛", "情绪外露", "容易激动", "乐观"])
        middle_emotion = DiscreteAxis("情绪状态", ["稳重", "理性", "偶尔焦虑", "平和"])
        elder_emotion = DiscreteAxis("情绪状态", ["淡定", "宽容", "容易怀旧", "温和"])

        # 条件轴：沟通风格依赖职业
        communication_axis = ConditionalAxis(
            axis_name="沟通风格",
            conditions={
                "职业": {
                    "程序员": tech_style,
                    "工程师": tech_style,
                    "医生": doctor_style,
                    "护士": doctor_style,
                    "销售": sales_style,
                    "教师": teacher_style
                }
            },
            default_axis=default_style
        )

        # 条件轴：情绪状态依赖年龄
        emotion_axis = ConditionalAxis(
            axis_name="情绪状态",
            conditions={
                "年龄": {
                    # 这里用字符串匹配，实际生成时年龄是字符串
                    "18": young_emotion, "19": young_emotion, "20": young_emotion, "21": young_emotion, "22": young_emotion,
                    "23": young_emotion, "24": young_emotion, "25": young_emotion, "26": young_emotion, "27": young_emotion, "28": young_emotion, "29": young_emotion,
                    "30": middle_emotion, "31": middle_emotion, "32": middle_emotion, "33": middle_emotion, "34": middle_emotion, "35": middle_emotion,
                    "36": middle_emotion, "37": middle_emotion, "38": middle_emotion, "39": middle_emotion, "40": middle_emotion, "41": middle_emotion, "42": middle_emotion, "43": middle_emotion, "44": middle_emotion, "45": middle_emotion,
                    "50": elder_emotion, "55": elder_emotion, "60": elder_emotion, "65": elder_emotion, "70": elder_emotion
                }
            },
            default_axis=DiscreteAxis("情绪状态", ["普通", "平静", "偶尔焦虑"])
        )

        return PersonaProfile(
            axes=[
                AxisPresets.name_zh(),
                AxisPresets.age(),
                AxisPresets.occupation_zh(),
                AxisPresets.education_zh(),
                AxisPresets.income_level_zh(),
                AxisPresets.patience_zh(),
                AxisPresets.politeness_zh(),
                communication_axis,  # 条件轴：沟通风格
                emotion_axis         # 条件轴：情绪状态
            ],
            language="简体中文",
            preset_name="diverse_conditional_customer" 
        )


class ScenarioProfile:
    """场景画像类"""
    
    def __init__(self, 
                 scenario_name: str,
                 scenario_type: str,
                 context: str,
                 objective: str,
                 parameters: Dict[str, Any] = None):
        self.scenario_name = scenario_name
        self.scenario_type = scenario_type
        self.context = context
        self.objective = objective
        self.parameters = parameters or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type,
            "context": self.context,
            "objective": self.objective,
            "parameters": self.parameters
        }
    
    def as_prompt(self, identifier: str = "场景设定") -> str:
        """生成提示词格式"""
        content = f"场景名称: {self.scenario_name}\n"
        content += f"场景类型: {self.scenario_type}\n"
        content += f"背景: {self.context}\n"
        content += f"目标: {self.objective}\n"
        
        if self.parameters:
            content += "参数设定:\n"
            for key, value in self.parameters.items():
                content += f"  {key}: {value}\n"
        
        return f"<{identifier}>\n{content}</{identifier}>"


class ProfileGenerator:
    """画像生成器"""
    
    def __init__(self):
        self.scenario_templates = {
            "客服咨询": {
                "contexts": [
                    "客户询问产品使用方法",
                    "客户反馈产品问题", 
                    "客户申请退换货",
                    "客户查询订单状态"
                ],
                "objective": "解决客户问题，提供满意的服务"
            },
            "销售沟通": {
                "contexts": [
                    "客户了解产品功能",
                    "客户咨询价格和优惠", 
                    "客户比较不同产品",
                    "客户考虑购买决策"
                ],
                "objective": "了解客户需求，促成销售"
            },
            "技术支持": {
                "contexts": [
                    "用户遇到技术故障",
                    "用户需要功能指导",
                    "用户询问系统配置",
                    "用户报告软件bug"
                ],
                "objective": "解决技术问题，指导正确使用"
            },
            "贷款咨询": {
                "contexts": [
                    "客户询问贷款利率",
                    "客户了解贷款流程",
                    "客户咨询还款方式",
                    "客户比较不同贷款产品"
                ],
                "objective": "帮助客户了解贷款信息，促成贷款申请"
            },
            "贷款信息核实": {
                "contexts": [
                    "核实客户贷款申请信息",
                ],
                "objective": "确保客户信息准确，防止欺诈"
            }
        }
    
    def generate_persona(self, preset_name: str = "basic_chinese_customer", **kwargs) -> PersonaProfile:
        """生成人物画像"""
        preset_method = getattr(ProfilePresets, preset_name, None)
        if preset_method:
            persona = preset_method()
        else:
            persona = ProfilePresets.basic_chinese_customer()
        
        # 应用自定义参数
        for key, value in kwargs.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        
        return persona
    
    def generate_scenario(self, scenario_type: str = None) -> ScenarioProfile:
        """生成场景画像"""
        if not scenario_type:
            scenario_type = random.choice(list(self.scenario_templates.keys()))
        
        template = self.scenario_templates.get(scenario_type, self.scenario_templates["客服咨询"])
        context = random.choice(template["contexts"])
        
        parameters = {
            "时间压力": random.choice(["低", "中", "高"]),
            "复杂程度": random.choice(["简单", "中等", "复杂"]),
            "情绪强度": random.choice(["平和", "中等", "激烈"])
        }
        
        return ScenarioProfile(
            scenario_name=f"{scenario_type}场景",
            scenario_type=scenario_type,
            context=context,
            objective=template["objective"],
            parameters=parameters
        )
    
    def create_conversation_prompt(self, 
                                   persona: PersonaProfile, 
                                   scenario: ScenarioProfile) -> str:
        """创建对话生成提示词"""
        return f"""请基于以下设定生成自然的对话：

{persona.as_prompt()}

{scenario.as_prompt()}

要求：
1. 对话要体现人物的性格特征和沟通风格
2. 内容要符合场景设定和目标
3. 语言自然流畅，符合{persona.language}的表达习惯
4. 包含适当的情感表达
5. 明确区分user和assistant角色

输出格式：
{{
    "conversation": [
        {{"role": "user", "content": "用户说话内容"}},
        {{"role": "assistant", "content": "客服回复内容"}},
        ...
    ]
}}"""

    def batch_generate(self, 
                      count: int = 10, 
                      preset_name: str = "basic_chinese_customer",
                      scenario_type: str = None) -> List[Dict[str, Any]]:
        """批量生成画像和对话提示"""
        results = []
        
        for i in range(count):
            persona = self.generate_persona(preset_name)
            scenario = self.generate_scenario(scenario_type)
            prompt = self.create_conversation_prompt(persona, scenario)
            
            results.append({
                "id": i + 1,
                "persona": persona.to_dict(),
                "scenario": scenario.to_dict(),
                "conversation_prompt": prompt
            })
        
        return results


# 使用示例
if __name__ == "__main__":
    # 创建生成器
    generator = ProfileGenerator()
    
    print("=== 基础中文客户画像示例 ===")
    persona1 = generator.generate_persona("basic_chinese_customer")
    print(persona1.as_prompt())
    print()
    
    print("=== 商业客户画像示例 ===")
    persona2 = generator.generate_persona("business_customer")
    print(persona2.as_prompt())
    print()
    
    print("=== 技术支持用户画像示例 ===")
    persona3 = generator.generate_persona("tech_support_user")
    print(persona3.as_prompt())
    print()
    
    print("=== 国际用户画像示例 ===")
    persona4 = generator.generate_persona("international_user")
    print(persona4.as_prompt())
    print()
    
    print("=== 场景画像示例 ===")
    scenario = generator.generate_scenario("客服咨询")
    print(scenario.as_prompt())
    print()
    
    print("=== 对话生成提示词示例 ===")
    prompt = generator.create_conversation_prompt(persona1, scenario)
    print(prompt)
    print()
    
    print("=== 自定义画像示例 ===")
    # 创建自定义画像
    custom_persona = PersonaProfile(
        axes=[
            AxisPresets.name_zh(),
            AxisPresets.age(),
            DiscreteAxis("专业领域", ["人工智能", "数据科学", "软件开发"]),
            AxisPresets.patience_zh(),
            AxisPresets.expertise_zh()
        ],
        language="简体中文"
    )
    print(custom_persona.as_prompt("自定义专家画像"))
    print()
    
    print("=== JSON导出示例 ===")
    print(persona1.to_json())