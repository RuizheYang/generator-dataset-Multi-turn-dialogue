"""
数据集生成器核心实现
封装所有复杂的生成逻辑，提供简洁的对外接口
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import time
import random
from collections import Counter

from openai_client import create_azure_openai_client
from person_profile import ProfileGenerator, PersonaProfile, ScenarioProfile


# ==================== 配置类 ====================

@dataclass
class GenerationConfig:
    """生成配置"""
    # 必需参数
    api_key: str
    endpoint: str
    
    # LLM配置
    engine: str = "gpt-4.1"
    model: str = "gpt-4.1"
    temperature: float = 0.7
    api_version: str = "2025-03-01-preview"
    
    # 生成配置
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    
    # 人物画像配置 - 支持多种画像随机选择
    persona_presets: List[str] = field(default_factory=lambda: [
        "basic_chinese_customer", 
        "business_customer", 
        "tech_support_user"
    ])
    scenario_types: List[str] = field(default_factory=lambda: ["客服咨询", "销售沟通", "技术支持", "贷款咨询", "贷款信息核实"])
    
    # 输出配置
    output_dir: str = "./output"
    output_format: str = "jsonl"  # json, jsonl
    include_metadata: bool = True
    
    # 日志配置
    log_level: str = "INFO"


# ==================== 核心生成器 ====================

class ConversationGenerator:
    """对话生成器 - 核心实现类"""
    
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.profile_generator = ProfileGenerator()
        self.llm = self._create_llm_client()
        self._setup_logging()
    
    def _create_llm_client(self):
        """创建LLM客户端"""
        return create_azure_openai_client(
            api_key=self.config.api_key,
            endpoint=self.config.endpoint,
            engine=self.config.engine,
            model=self.config.model,
            temperature=self.config.temperature,
            api_version=self.config.api_version
        )
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def generate_single_conversation(self, persona: PersonaProfile = None, scenario: ScenarioProfile = None) -> Dict[str, Any]:
        """生成单条对话"""
        # 如果没有提供画像，则随机选择一种画像类型生成
        if not persona:
            # 🔥 从多种画像中随机选择
            persona_preset = random.choice(self.config.persona_presets)
            persona = self.profile_generator.generate_persona(persona_preset)
            self.logger.debug(f"🎭 随机选择画像类型: {persona_preset}")
        
        if not scenario:
            scenario_type = random.choice(self.config.scenario_types)
            scenario = self.profile_generator.generate_scenario(scenario_type)
        
        # 创建提示词
        prompt = self.profile_generator.create_conversation_prompt(persona, scenario)
        
        # 调用LLM生成
        start_time = time.time()
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(self.llm.complete, prompt),
                timeout=self.config.timeout
            )
            generation_time = time.time() - start_time
            
            # 解析对话
            conversation = self._parse_response(str(response))
            
            # 构建结果
            result = {
                "conversation": conversation,
                "persona": persona.to_dict(),
                "scenario": scenario.to_dict()
            }
            
            # 添加元数据
            if self.config.include_metadata:
                result["metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "generation_time": generation_time,
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "persona_preset": getattr(persona, 'preset_name', 'unknown'),  # 🔥 记录画像类型
                    "scenario_type": scenario.scenario_type
                }
            
            self.logger.info(f"✅ 对话生成成功，耗时 {generation_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 对话生成失败: {str(e)}")
            raise
    
    def _parse_response(self, response_text: str) -> List[Dict[str, str]]:
        """解析LLM响应为对话格式"""
        try:
            # 提取JSON部分
            if "```json" in response_text:
                json_part = response_text.split("```json")[1].split("```")[0].strip()
            elif "{" in response_text and "}" in response_text:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                json_part = response_text[start_idx:end_idx]
            else:
                json_part = response_text.strip()
            
            parsed = json.loads(json_part)
            
            # 确保返回对话格式
            if "conversation" in parsed:
                return parsed["conversation"]
            elif isinstance(parsed, list):
                return parsed
            else:
                return [{"role": "assistant", "content": str(parsed)}]
                
        except json.JSONDecodeError:
            self.logger.warning(f"JSON解析失败，返回原始文本")
            return [{"role": "assistant", "content": response_text}]
    
    async def generate_batch_conversations(self, count: int) -> List[Dict[str, Any]]:
        """批量生成对话"""
        self.logger.info(f"🚀 开始批量生成 {count} 条对话")
        
        results = []
        
        for i in range(count):
            try:
                # 带重试的生成
                result = await self._generate_with_retry()
                if result:
                    results.append(result)
                    self.logger.info(f"📈 进度: {len(results)}/{count}")
                
                # 批次间延迟
                if i < count - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    
            except Exception as e:
                self.logger.error(f"第 {i+1} 条生成失败: {str(e)}")
                continue
        
        self.logger.info(f"✨ 批量生成完成: {len(results)}/{count} 成功")
        return results
    
    async def _generate_with_retry(self) -> Optional[Dict[str, Any]]:
        """带重试的单条生成"""
        for attempt in range(self.config.max_retries):
            try:
                return await self.generate_single_conversation()
            except Exception as e:
                self.logger.warning(f"第 {attempt + 1} 次尝试失败: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    self.logger.error(f"重试 {self.config.max_retries} 次后仍失败")
        return None
    
    async def save_conversations(self, conversations: List[Dict[str, Any]], filename: str = None) -> str:
        """保存对话数据"""
        # 生成文件名
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dataset_{timestamp}.{self.config.output_format}"
        
        # 确保输出目录存在
        output_path = Path(self.config.output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 根据格式保存
        if self.config.output_format == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for conv in conversations:
                    f.write(json.dumps(conv, ensure_ascii=False) + '\n')
        else:  # json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        # 生成统计报告
        await self._generate_report(conversations, output_path)
        
        self.logger.info(f"💾 数据已保存到: {output_path}")
        return str(output_path)
    
    async def _generate_report(self, conversations: List[Dict[str, Any]], output_path: Path):
        """生成统计报告"""
        # 计算统计信息
        stats = self._calculate_stats(conversations)
        
        report = {
            "summary": {
                "total_conversations": len(conversations),
                "generated_at": datetime.now().isoformat(),
                "config": {
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "persona_presets": self.config.persona_presets,  # 🔥 使用新的字段名
                    "scenario_types": self.config.scenario_types
                }
            },
            "statistics": stats
        }
        
        # 保存报告
        report_path = output_path.with_suffix('.report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def _calculate_stats(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计信息"""
        if not conversations:
            return {}
        
        conversation_lengths = []
        occupations = []
        scenarios = []
        persona_presets = []  # 🔥 新增：画像类型统计
        
        for conv in conversations:
            # 对话长度统计
            if "conversation" in conv:
                conversation_lengths.append(len(conv["conversation"]))
            
            # 职业统计
            if "persona" in conv and "profile" in conv["persona"]:
                occupation = conv["persona"]["profile"].get("职业")
                if occupation:
                    occupations.append(occupation)
            
            # 场景统计
            if "scenario" in conv:
                scenario_type = conv["scenario"].get("scenario_type")
                if scenario_type:
                    scenarios.append(scenario_type)
            
            # 🔥 画像类型统计
            if "metadata" in conv and "persona_preset" in conv["metadata"]:
                persona_preset = conv["metadata"]["persona_preset"]
                if persona_preset:
                    persona_presets.append(persona_preset)
        
        return {
            "conversation_length": {
                "average": sum(conversation_lengths) / len(conversation_lengths) if conversation_lengths else 0,
                "min": min(conversation_lengths) if conversation_lengths else 0,
                "max": max(conversation_lengths) if conversation_lengths else 0
            },
            "occupation_distribution": dict(Counter(occupations)),
            "scenario_distribution": dict(Counter(scenarios)),
            "persona_preset_distribution": dict(Counter(persona_presets))  # 🔥 新增统计
        }


# ==================== 对外接口 ====================

class DatasetExpander:
    """数据集扩展器 - 对外接口类"""
    
    def __init__(self, api_key: str, endpoint: str, **kwargs):
        """初始化扩展器"""
        # 🔥 向后兼容：处理旧的 persona_preset 参数
        if 'persona_preset' in kwargs and 'persona_presets' not in kwargs:
            # 如果只提供了旧的 persona_preset，转换为新的 persona_presets
            kwargs['persona_presets'] = [kwargs['persona_preset']]
            del kwargs['persona_preset']  # 移除旧参数
        
        self.config = GenerationConfig(
            api_key=api_key,
            endpoint=endpoint,
            **kwargs
        )
        self.generator = ConversationGenerator(self.config)
    
    async def expand(self, count: int, output_filename: str = None) -> str:
        """扩展数据集 - 主要对外接口"""
        # 批量生成对话
        conversations = await self.generator.generate_batch_conversations(count)
        
        # 保存结果
        output_path = await self.generator.save_conversations(conversations, output_filename)
        
        return output_path
    
    async def generate_single(self) -> Dict[str, Any]:
        """生成单条对话"""
        return await self.generator.generate_single_conversation()
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)


# ==================== 便捷函数 ====================

async def expand_dataset(
    count: int,
    api_key: str,
    endpoint: str,
    output_dir: str = "./output",
    output_filename: str = None,
    **kwargs
) -> str:
    """
    便捷的数据集扩展函数
    
    Args:
        count: 生成对话数量
        api_key: OpenAI API Key
        endpoint: OpenAI Endpoint
        output_dir: 输出目录
        output_filename: 输出文件名
        **kwargs: 其他配置参数
    
    Returns:
        输出文件路径
    """
    expander = DatasetExpander(
        api_key=api_key,
        endpoint=endpoint,
        output_dir=output_dir,
        **kwargs
    )
    
    return await expander.expand(count, output_filename)


async def generate_single_conversation(
    api_key: str,
    endpoint: str,
    **kwargs
) -> Dict[str, Any]:
    """
    生成单条对话的便捷函数
    """
    expander = DatasetExpander(
        api_key=api_key,
        endpoint=endpoint,
        **kwargs
    )
    
    return await expander.generate_single()


# ==================== 预设配置 ====================

class PresetConfigs:
    """预设配置类"""
    
    @staticmethod
    def customer_service(api_key: str, endpoint: str) -> DatasetExpander:
        """客服对话配置 - 使用多种客户画像"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=["basic_chinese_customer", "business_customer"],  # 🔥 多种画像
            scenario_types=["客服咨询"],
            temperature=0.7,
            output_format="jsonl"
        )
    
    @staticmethod
    def sales_conversation(api_key: str, endpoint: str) -> DatasetExpander:
        """销售对话配置 - 专注商业客户"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=["business_customer"],  # 🔥 适合销售的画像
            scenario_types=["销售沟通"],
            temperature=0.8,
            output_format="json"
        )
    
    @staticmethod
    def tech_support(api_key: str, endpoint: str) -> DatasetExpander:
        """技术支持配置 - 多种用户类型"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=["tech_support_user", "basic_chinese_customer"],  # 🔥 技术用户和普通用户
            scenario_types=["技术支持"],
            temperature=0.6,
            output_format="jsonl"
        )
    
    @staticmethod
    def loan_consultation(api_key: str, endpoint: str) -> DatasetExpander:
        """贷款咨询配置 - 商业和普通客户"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=["business_customer", "basic_chinese_customer"],  # 🔥 多种客户类型
            scenario_types=["贷款咨询"],
            temperature=0.7,
            output_format="jsonl"
        )
    
    @staticmethod
    def loan_verification(api_key: str, endpoint: str) -> DatasetExpander:
        """贷款信息核实配置 - 商业和普通客户"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=["business_customer", "basic_chinese_customer"],  # 🔥 多种客户类型
            scenario_types=["贷款信息核实"],
            temperature=0.6,
            output_format="jsonl"
        )
    
    @staticmethod
    def comprehensive_service(api_key: str, endpoint: str) -> DatasetExpander:
        """综合服务配置 - 平衡的画像分布"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=[  # 🔥 精选的画像组合
                "basic_chinese_customer",
                "business_customer",
                "tech_support_user"
            ],
            scenario_types=["客服咨询", "销售沟通", "技术支持", "贷款咨询", "贷款信息核实"],
            temperature=0.7,
            output_format="jsonl"
        )
    
    @staticmethod
    def diverse_scenarios(api_key: str, endpoint: str) -> DatasetExpander:
        """多样化场景配置 - 所有画像类型"""
        return DatasetExpander(
            api_key=api_key,
            endpoint=endpoint,
            persona_presets=[  # 🔥 使用所有可用的画像类型
                "basic_chinese_customer",
                "business_customer", 
                "tech_support_user",
                "international_user",  # 如果你有这个画像的话
                "diverse_conditional_customer"  # 包含条件轴的复杂画像
            ],
            scenario_types=["客服咨询", "销售沟通", "技术支持", "贷款咨询", "贷款信息核实"],
            temperature=0.7,
            output_format="jsonl"
        )