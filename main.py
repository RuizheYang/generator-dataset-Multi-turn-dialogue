"""
数据集扩充系统 - 简洁的主入口
使用者只需要关心简单的调用接口，无需了解内部实现
"""

import asyncio
from generator import expand_dataset, DatasetExpander, PresetConfigs


# ==================== 配置参数 ====================

# Azure OpenAI 配置
API_KEY = "<YOUR_API_KEY>"
ENDPOINT = "<YOUR_ENDPOINT>"


# ==================== 使用示例 ====================

async def example_quick_generate():
    """示例1: 快速生成数据集"""
    print("🚀 示例1: 快速生成 5 条客服对话")
    
    output_path = await expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        output_dir="./output",
        persona_preset="basic_chinese_customer",
        scenario_types=["客服咨询"]
    )
    
    print(f"✅ 数据集已生成: {output_path}")


async def example_custom_config():
    """示例2: 使用自定义配置"""
    print("\n🎯 示例2: 自定义配置生成商业对话")
    
    # 创建自定义扩展器
    expander = DatasetExpander(
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="business_customer",
        scenario_types=["销售沟通"],
        temperature=0.8,
        output_format="json",
        output_dir="./custom_output"
    )
    
    # 生成数据集
    output_path = await expander.expand(
        count=3,
        output_filename="business_sales.json"
    )
    
    print(f"✅ 商业对话数据集已生成: {output_path}")


async def example_preset_configs():
    """示例3: 使用预设配置"""
    print("\n⚙️ 示例3: 使用预设配置生成技术支持对话")
    
    # 使用技术支持预设
    tech_expander = PresetConfigs.tech_support(API_KEY, ENDPOINT)
    
    output_path = await tech_expander.expand(
        count=3,
        output_filename="tech_support_conversations.jsonl"
    )
    
    print(f"✅ 技术支持对话已生成: {output_path}")


async def example_loan_scenarios():
    """示例4: 生成贷款相关场景对话"""
    print("\n💰 示例4: 生成贷款相关场景对话")
    
    # 贷款咨询配置
    loan_consultation = PresetConfigs.loan_consultation(API_KEY, ENDPOINT)
    output_path1 = await loan_consultation.expand(
        count=3,
        output_filename="loan_consultation_demo.jsonl"
    )
    print(f"✅ 贷款咨询对话已生成: {output_path1}")
    
    # 贷款信息核实配置
    loan_verification = PresetConfigs.loan_verification(API_KEY, ENDPOINT)
    output_path2 = await loan_verification.expand(
        count=3,
        output_filename="loan_verification_demo.jsonl"
    )
    print(f"✅ 贷款信息核实对话已生成: {output_path2}")


async def example_single_conversation():
    """示例5: 生成单条对话"""
    print("\n🎈 示例5: 生成单条对话测试")
    
    expander = DatasetExpander(
        api_key=API_KEY,
        endpoint=ENDPOINT,
        temperature=0.6
    )
    
    try:
        conversation = await expander.generate_single()
        
        print("生成的对话:")
        for i, turn in enumerate(conversation["conversation"][:4], 1):
            role = "👤 用户" if turn["role"] == "user" else "🤖 助手"
            content = turn["content"]
            print(f"{i}. {role}: {content}")
            
        if len(conversation["conversation"]) > 4:
            print(f"... (共 {len(conversation['conversation'])} 轮对话)")
            
    except Exception as e:
        print(f"❌ 单条生成失败: {e}")


async def example_comprehensive_service():
    """示例6: 使用综合服务配置生成多种场景对话"""
    print("\n🌟 示例6: 生成包含所有场景的综合对话数据")
    
    comprehensive = PresetConfigs.comprehensive_service(API_KEY, ENDPOINT)
    output_path = await comprehensive.expand(
        count=10,
        output_filename="comprehensive_conversations.jsonl"
    )
    
    print(f"✅ 综合场景对话已生成: {output_path}")
    print("包含场景: 客服咨询、销售沟通、技术支持、贷款咨询、贷款信息核实")


# ==================== 批量生成不同类型数据 ====================

async def batch_generate_all_types():
    """批量生成所有类型的对话数据"""
    print("\n🔄 批量生成所有类型的对话数据")
    
    tasks = []
    
    # 客服对话
    tasks.append(expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="basic_chinese_customer",
        scenario_types=["客服咨询"],
        output_filename="customer_service.jsonl"
    ))
    
    # 销售对话
    tasks.append(expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="business_customer",
        scenario_types=["销售沟通"],
        temperature=0.8,
        output_filename="sales.jsonl"
    ))
    
    # 技术支持对话
    tasks.append(expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="tech_support_user",
        scenario_types=["技术支持"],
        temperature=0.6,
        output_filename="tech_support.jsonl"
    ))
    
    # 贷款咨询对话
    tasks.append(expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="business_customer",
        scenario_types=["贷款咨询"],
        temperature=0.7,
        output_filename="loan_consultation.jsonl"
    ))
    
    # 贷款信息核实对话
    tasks.append(expand_dataset(
        count=5,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        persona_preset="business_customer",
        scenario_types=["贷款信息核实"],
        temperature=0.6,
        output_filename="loan_verification.jsonl"
    ))
    
    # 并行执行
    results = await asyncio.gather(*tasks)
    
    print("📊 批量生成完成:")
    for i, path in enumerate(results, 1):
        print(f"  {i}. {path}")


# ==================== 主函数 ====================

async def main():
    """主函数 - 演示各种使用方式"""
    print("=" * 60)
    print("🎉 数据集扩充系统 - 使用示例")
    print("=" * 60)
    
    try:
        # 运行示例
        await example_quick_generate()
        await example_custom_config()
        await example_preset_configs()
        await example_loan_scenarios()
        await example_single_conversation()
        await example_comprehensive_service()
        
        # 如果需要批量生成，取消注释下面这行
        # await batch_generate_all_types()
        
    except Exception as e:
        print(f"\n❌ 运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✨ 所有示例运行完成!")
    print("=" * 60)


# ==================== 命令行快速接口 ====================

def quick_start():
    """快速启动接口"""
    print("🚀 快速启动数据集生成...")
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(example_single_conversation())