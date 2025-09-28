# 数据集扩充系统使用指南

## 🎯 设计理念

本系统采用**"接口与实现分离"**的设计原则：
- `generator.py`: 封装所有复杂实现逻辑
- `main.py`: 提供简洁的使用示例
- 使用者只需关心简单的调用接口，无需了解内部实现

## 🚀 快速开始

### 1. 最简单的使用方式

```python
from generator import expand_dataset

# 一行代码生成数据集
output_path = await expand_dataset(
    count=10,
    api_key="your_api_key",
    endpoint="your_endpoint"
)
```

### 2. 自定义配置

```python
from generator import DatasetExpander

# 创建自定义扩展器
expander = DatasetExpander(
    api_key="your_key",
    endpoint="your_endpoint",
    persona_preset="business_customer",  # 商业客户画像
    scenario_types=["销售沟通"],          # 销售场景
    temperature=0.8,                    # LLM创造性
    output_format="json"                # 输出格式
)

# 生成数据集
output_path = await expander.expand(count=50)
```

### 3. 预设配置

```python
from generator import PresetConfigs

# 使用预设的客服配置
customer_service = PresetConfigs.customer_service(api_key, endpoint)
await customer_service.expand(count=100)

# 使用预设的销售配置
sales = PresetConfigs.sales_conversation(api_key, endpoint)
await sales.expand(count=50)

# 使用预设的技术支持配置
tech = PresetConfigs.tech_support(api_key, endpoint)
await tech.expand(count=30)

# 使用预设的贷款咨询配置
loan_consultation = PresetConfigs.loan_consultation(api_key, endpoint)
await loan_consultation.expand(count=20)

# 使用预设的贷款信息核实配置
loan_verification = PresetConfigs.loan_verification(api_key, endpoint)
await loan_verification.expand(count=20)

# 使用综合服务配置（包含所有场景类型）
comprehensive = PresetConfigs.comprehensive_service(api_key, endpoint)
await comprehensive.expand(count=100)
```

## 📋 支持的配置选项

### 画像类型 (persona_preset)
- `basic_chinese_customer`: 基础中文客户
- `business_customer`: 商业客户
- `tech_support_user`: 技术支持用户
- `international_user`: 国际用户

### 场景类型 (scenario_types)
- `客服咨询`: 客户服务场景
- `销售沟通`: 销售对话场景
- `技术支持`: 技术支持场景
- `贷款咨询`: 贷款相关咨询场景
- `贷款信息核实`: 贷款信息验证场景

### 输出格式 (output_format)
- `jsonl`: 每行一个JSON对象
- `json`: 标准JSON数组格式

## 🔧 高级用法

### 生成单条对话
```python
expander = DatasetExpander(api_key, endpoint)
conversation = await expander.generate_single()
```

### 批量生成不同类型
```python
tasks = [
    expand_dataset(count=100, scenario_types=["客服咨询"]),
    expand_dataset(count=50, scenario_types=["销售沟通"]),
    expand_dataset(count=30, scenario_types=["技术支持"]),
    expand_dataset(count=40, scenario_types=["贷款咨询"]),
    expand_dataset(count=40, scenario_types=["贷款信息核实"])
]

results = await asyncio.gather(*tasks)
```

### 动态更新配置
```python
expander = DatasetExpander(api_key, endpoint)

# 更新配置
expander.update_config(
    temperature=0.9,
    persona_preset="business_customer"
)

# 生成新的数据集
await expander.expand(count=20)
```

## 📊 输出文件结构

### JSONL 格式示例
```json
{"conversation": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "persona": {...}, "scenario": {...}, "metadata": {...}}
{"conversation": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "persona": {...}, "scenario": {...}, "metadata": {...}}
```

### 自动生成的报告文件
- `dataset_20241225_143022.jsonl`: 主数据文件
- `dataset_20241225_143022.report.json`: 统计报告文件

报告内容包括：
- 生成总数和成功率
- 对话长度统计
- 人物职业分布
- 场景类型分布

## 🎉 运行示例

直接运行 `main.py` 查看各种使用示例：

```bash
python main.py
```

输出将包括：
- 快速生成示例
- 自定义配置示例  
- 预设配置示例
- 单条对话生成示例

## 💡 最佳实践

1. **开发阶段**: 使用小数量(5-10条)快速测试
2. **生产环境**: 根据需要调整 `temperature` 和 `max_retries`
3. **大批量生成**: 使用异步并发，但注意API限速
4. **错误处理**: 系统自动重试，无需手动处理

## 🔄 扩展指南

如需添加新的画像类型或场景类型，只需修改 `person_profile.py` 中的预设配置，系统会自动支持。

```python
# 添加新的画像预设
class ProfilePresets:
    @staticmethod
    def new_customer_type():
        return PersonaProfile(...)

# 在生成器中使用
expander = DatasetExpander(
    api_key=api_key,
    endpoint=endpoint,
    persona_preset="new_customer_type"
)
```

这样的设计让使用变得极其简单，同时保持了系统的强大功能！