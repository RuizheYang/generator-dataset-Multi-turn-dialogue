import json
import glob
from pathlib import Path


# ========== 合并数据 ==========
def merge_and_group_conversations(output_dir):
    """合并所有jsonl文件并按场景分组"""
    jsonl_files = list(output_dir.glob('*.jsonl'))
    print(f"找到 {len(jsonl_files)} 个JSONL文件:")
    all_data = []
    for file in jsonl_files:
        with open(file, 'r', encoding='utf-8') as f:
            file_data = [json.loads(line.strip()) for line in f]
            all_data.extend(file_data)
        print(f"  - {file.name}: {len(file_data)} 条")
    grouped = {}
    for item in all_data:
        scenario = item.get('scenario', {}).get('scenario_type', 'unknown')
        grouped.setdefault(scenario, []).append(item.get('conversation', []))
    print("按场景类型分组统计:")
    for k, v in grouped.items():
        print(f"  {k}: {len(v)} 条对话")
    print(f"总场景类型数: {len(grouped)}")
    return grouped
    
    
# ========== 标注数据 ==========
import random

def extract_conversation_context(conversation, end_idx, context_turns=2):
    """提取对话上下文"""
    start_idx = max(0, end_idx - context_turns + 1)
    context = conversation[start_idx:end_idx + 1]
    
    # 格式化对话历史
    formatted_context = []
    for turn in context:
        role = "user" if turn['role'] == 'user' else "assistant"
        formatted_context.append(f"{role}: {turn['content']}")
    
    return "\n".join(formatted_context)

def generate_end_of_turn_samples(grouped_conversations, total_samples=100):
    """
    生成 <end-of-turn> 标签的训练样本
    用户轮次已结束（话已说完）
    
    Args:
        grouped_conversations: 按场景分组的对话数据
        total_samples: 总样本数量
    
    Returns:
        list: 训练样本列表，包含用户轮次和机器人轮次各50%
    """
    samples = []
    scenarios = list(grouped_conversations.keys())
    
    # 确保有对话数据的场景
    valid_scenarios = [s for s in scenarios if grouped_conversations[s]]
    if not valid_scenarios:
        return []
    
    # 每个场景应该生成的样本数
    samples_per_scenario = total_samples // len(valid_scenarios)
    
    # 用户轮次和机器人轮次各占50%
    user_samples_per_scenario = samples_per_scenario // 2
    assistant_samples_per_scenario = samples_per_scenario - user_samples_per_scenario
    
    for scenario_type in valid_scenarios:
        conversations = grouped_conversations[scenario_type]
        scenario_samples = []
        
        # 生成用户轮次样本
        user_count = 0
        attempts = 0
        max_attempts = len(conversations) * 3
        
        while user_count < user_samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            if len(conversation) < 2:
                continue
                
            # 找到用户的完整轮次
            user_turns = [i for i, turn in enumerate(conversation) if turn['role'] == 'user']
            if not user_turns:
                continue
                
            turn_idx = random.choice(user_turns)
            context = extract_conversation_context(conversation, turn_idx)
            
            sample = {
                "instruction": "分析以下对话中用户的最后一句话。如果用户的说话轮次已经结束（话已说完），则输出 <end-of-turn>。如果用户明显还没说完（例如，只是一个停顿），则输出 <continue-turn>。不要解释原因。",
                "input": context,
                "output": "<end-of-turn>",
                "scenario": scenario_type,
                "type": "user_turn"
            }
            
            scenario_samples.append(sample)
            user_count += 1
        
        # 生成机器人轮次样本（模拟机器人说完话的情况）
        assistant_count = 0
        attempts = 0
        
        while assistant_count < assistant_samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            if len(conversation) < 2:
                continue
                
            # 找到助手的完整轮次
            assistant_turns = [i for i, turn in enumerate(conversation) if turn['role'] == 'assistant']
            if not assistant_turns:
                continue
                
            turn_idx = random.choice(assistant_turns)
            context = extract_conversation_context(conversation, turn_idx)
            
            # 修改instruction为机器人轮次场景
            sample = {
                "instruction": "分析以下对话中助手的最后一句话。如果助手的说话轮次已经结束（话已说完），则输出 <end-of-turn>。如果助手明显还没说完（例如，只是一个停顿），则输出 <continue-turn>。不要解释原因。",
                "input": context,
                "output": "<end-of-turn>",
                "scenario": scenario_type,
                "type": "assistant_turn"
            }
            
            scenario_samples.append(sample)
            assistant_count += 1
        
        samples.extend(scenario_samples)
        print(f"场景 '{scenario_type}': 生成了 {len(scenario_samples)} 个 end-of-turn 样本 (用户:{user_count}, 助手:{assistant_count})")
    
    return samples

def generate_continue_turn_samples(grouped_conversations, total_samples=100):
    """
    生成 <continue-turn> 标签的训练样本
    通过随机截断来模拟话没说完的情况
    """
    samples = []
    scenarios = list(grouped_conversations.keys())
    valid_scenarios = [s for s in scenarios if grouped_conversations[s]]
    
    if not valid_scenarios:
        return []
    
    samples_per_scenario = total_samples // len(valid_scenarios)
    user_samples_per_scenario = samples_per_scenario // 2
    assistant_samples_per_scenario = samples_per_scenario - user_samples_per_scenario
    
    for scenario_type in valid_scenarios:
        conversations = grouped_conversations[scenario_type]
        scenario_samples = []
        
        # 生成用户轮次样本（截断用户话语）
        user_count = 0
        attempts = 0
        max_attempts = len(conversations) * 3
        
        while user_count < user_samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            
            # 找到较长的用户轮次
            long_user_turns = [
                i for i, turn in enumerate(conversation) 
                if turn['role'] == 'user' and len(turn['content']) > 30
            ]
            
            if not long_user_turns:
                continue
                
            turn_idx = random.choice(long_user_turns)
            original_content = conversation[turn_idx]['content']
            
            # 随机截断（保留30%-80%的内容）
            truncate_ratio = random.uniform(0.3, 0.8)
            truncate_pos = int(len(original_content) * truncate_ratio)
            
            # 寻找合适的截断点
            truncate_chars = ['，', '。', '！', '？', '、', ' ', '；']
            best_pos = truncate_pos
            for i in range(max(0, truncate_pos-10), min(len(original_content), truncate_pos+10)):
                if original_content[i] in truncate_chars:
                    best_pos = i
                    break
            
            truncated_content = original_content[:best_pos].strip()
            if len(truncated_content) < 10:
                continue
                
            # 创建截断后的对话
            modified_conversation = conversation[:turn_idx] + [
                {"role": "user", "content": truncated_content}
            ]
            
            context = extract_conversation_context(modified_conversation, len(modified_conversation)-1)
            
            sample = {
                "instruction": "分析以下对话中用户的最后一句话。如果用户的说话轮次已经结束（话已说完），则输出 <end-of-turn>。如果用户明显还没说完（例如，只是一个停顿），则输出 <continue-turn>。不要解释原因。",
                "input": context,
                "output": "<continue-turn>",
                "scenario": scenario_type,
                "type": "user_turn"
            }
            
            scenario_samples.append(sample)
            user_count += 1
        
        # 生成助手轮次样本（截断助手话语）
        assistant_count = 0
        attempts = 0
        
        while assistant_count < assistant_samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            
            # 找到较长的助手轮次
            long_assistant_turns = [
                i for i, turn in enumerate(conversation) 
                if turn['role'] == 'assistant' and len(turn['content']) > 30
            ]
            
            if not long_assistant_turns:
                continue
                
            turn_idx = random.choice(long_assistant_turns)
            original_content = conversation[turn_idx]['content']
            
            # 随机截断
            truncate_ratio = random.uniform(0.3, 0.8)
            truncate_pos = int(len(original_content) * truncate_ratio)
            
            truncate_chars = ['，', '。', '！', '？', '、', ' ', '；']
            best_pos = truncate_pos
            for i in range(max(0, truncate_pos-10), min(len(original_content), truncate_pos+10)):
                if original_content[i] in truncate_chars:
                    best_pos = i
                    break
            
            truncated_content = original_content[:best_pos].strip()
            if len(truncated_content) < 10:
                continue
                
            modified_conversation = conversation[:turn_idx] + [
                {"role": "assistant", "content": truncated_content}
            ]
            
            context = extract_conversation_context(modified_conversation, len(modified_conversation)-1)
            
            sample = {
                "instruction": "分析以下对话中助手的最后一句话。如果助手的说话轮次已经结束（话已说完），则输出 <end-of-turn>。如果助手明显还没说完（例如，只是一个停顿），则输出 <continue-turn>。不要解释原因。",
                "input": context,
                "output": "<continue-turn>",
                "scenario": scenario_type,
                "type": "assistant_turn"
            }
            
            scenario_samples.append(sample)
            assistant_count += 1
        
        samples.extend(scenario_samples)
        print(f"场景 '{scenario_type}': 生成了 {len(scenario_samples)} 个 continue-turn 样本 (用户:{user_count}, 助手:{assistant_count})")
    
    return samples

def generate_interrupt_samples(grouped_conversations, total_samples=100):
    """
    生成 <interrupt> 标签的训练样本
    用户打断助手说话
    """
    samples = []
    scenarios = list(grouped_conversations.keys())
    valid_scenarios = [s for s in scenarios if grouped_conversations[s]]
    
    if not valid_scenarios:
        return []
    
    samples_per_scenario = total_samples // len(valid_scenarios)
    
    for scenario_type in valid_scenarios:
        conversations = grouped_conversations[scenario_type]
        scenario_samples = []
        
        count = 0
        attempts = 0
        max_attempts = len(conversations) * 3
        
        while count < samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            
            # 找到助手的轮次
            assistant_turns = [
                i for i, turn in enumerate(conversation) 
                if turn['role'] == 'assistant' and len(turn['content']) > 30
            ]
            
            if not assistant_turns:
                continue
                
            turn_idx = random.choice(assistant_turns)
            assistant_turn = conversation[turn_idx]
            
            # 截断助手的话（模拟被打断）
            content = assistant_turn['content']
            truncate_ratio = random.uniform(0.2, 0.7)
            truncate_pos = int(len(content) * truncate_ratio)
            
            truncate_chars = ['，', '。', '！', '？', '、', ' ', '；']
            best_pos = truncate_pos
            for i in range(max(0, truncate_pos-10), min(len(content), truncate_pos+10)):
                if content[i] in truncate_chars:
                    best_pos = i
                    break
            
            truncated_assistant = content[:best_pos].strip()
            if len(truncated_assistant) < 10:
                continue
            
            # 生成用户的打断话语
            interrupt_phrases = [
                # === 基础打断表达 ===
                "等等，我想问一下", "不对，我的情况不是这样", "慢着，我还有个问题",
                "你先等一下", "不行，这个方案不合适", "打断一下，我想说",
                "等一下，你刚才说的", "我觉得不对", "这个我不同意", "你误解了我的意思",
                "不是这样的", "等等，我需要澄清", "停一下，我有异议",
                
                # === 疑问和困惑 ===
                "等等，我没听懂", "慢着，什么意思？", "不对不对，我搞混了",
                "等一下，你说的是哪个？", "我有点糊涂了", "这里我不明白",
                "等等，能重复一遍吗？", "不好意思，我没跟上", "这个地方我疑惑",
                
                # === 纠正和澄清 ===
                "不是的，实际情况是", "错了，应该是这样", "不对，我要说明一下",
                "等等，我纠正一下", "这里有误解", "我补充一点信息",
                "不是这么回事", "实际上不是这样", "让我澄清一下",
                
                # === 急迫和焦虑 ===
                "等等等等！", "不行不行！", "慢点慢点！", "等一下！",
                "我着急了", "这个很重要！", "先等等！", "别说了！",
                "我必须打断你", "这个问题很紧急", "不能这样！",
                
                # === 反对和异议 ===
                "我反对这个说法", "这个不对", "我不认同", "这里有问题",
                "我有不同看法", "这个我不接受", "我觉得有误", "这样不行",
                "我要提出异议", "这个方案不可行", "我有保留意见",
                
                # === 请求解释 ===
                "等等，能详细说说吗？", "这个怎么理解？", "为什么这样？",
                "能解释一下吗？", "这是什么意思？", "我需要更多信息",
                "这个逻辑我不懂", "能举个例子吗？", "具体是怎样的？",
                
                # === 情感表达 ===
                "我很担心这个", "我有点紧张", "这让我很困扰",
                "我不太舒服", "这样我不安心", "我有些顾虑",
                "这让我很意外", "我感到困惑", "这出乎我意料",
                
                # === 时间紧迫 ===
                "等等，时间不够了", "我赶时间", "能快点吗？",
                "我还有事", "时间来不及", "我得马上知道",
                "这个很紧急", "不能耽误了", "时间有限",
                
                # === 专业场景：金融贷款 ===
                "等等，利率是多少？", "慢着，还款方式呢？", "不对，我的征信没问题",
                "等一下，手续费多少？", "我的收入证明呢？", "这个条件不符合",
                "等等，审批要多久？", "我的额度是多少？", "担保人的事情",
                
                # === 专业场景：客服咨询 ===
                "等等，我的订单号是", "不对，我的问题是", "慢着，我要投诉",
                "等一下，我要退货", "我的账户有问题", "这个费用不对",
                "等等，我没收到", "不是这个产品", "我要换个客服",
                
                # === 专业场景：技术支持 ===
                "等等，我的系统是", "不对，这个步骤有问题", "慢着，操作失败了",
                "等一下，我看不到", "这个按钮在哪？", "我的版本不一样",
                "等等，报错了", "不行，还是不行", "我重启了还是不行",
                
                # === 专业场景：销售沟通 ===
                "等等，价格能便宜点吗？", "慢着，有优惠活动吗？", "不对，这个配置不够",
                "等一下，竞品比较呢？", "我考虑考虑", "这个太贵了",
                "等等，售后服务呢？", "我需要看看样品", "能试用吗？",
                
                # === 口语化表达 ===
                "哎等等", "诶慢着", "哎哎哎", "等会儿等会儿",
                "别急别急", "慢点说", "你等等", "让我说句话",
                "打住打住", "停停停", "先别说", "等我一下",
                
                # === 礼貌打断 ===
                "不好意思，我打断一下", "抱歉，我插一句", "对不起，我想说",
                "请允许我插话", "麻烦等等", "能让我说一下吗？",
                "不好意思打断", "借我说一句", "请稍等片刻",
                
                # === 网络用语风格 ===
                "等等，我懵了", "慢着，我晕了", "不对，我蒙圈了",
                "等一下，我卡住了", "这个我get不到", "我有点方了",
                "等等，这啥意思？", "我有点懵逼", "这个我不太懂",
                
                # === 地方方言色彩 ===
                "等等咧", "慢点哈", "不对滴", "等一哈",
                "慢慢来嘛", "莫急嘛", "等等先", "慢着点",
                "不是这样滴", "我说一哈", "等等撒",
                
                # === 情境化表达 ===
                "等等，我老婆说不是这样", "慢着，我得问问家里", "不对，我妈说不是这样",
                "等一下，我朋友建议不这样", "我同事说不是这样", "我之前听说",
                "等等，网上说", "我看攻略说", "别人告诉我",
                
                # === 强调重要性 ===
                "等等！这很重要", "慢着！关键问题", "不对！重点是",
                "等一下！核心是", "这个很关键", "重要的来了",
                "这是关键点", "核心问题是", "最重要的是",
                
                # === 表达怀疑 ===
                "等等，真的吗？", "慢着，确定吗？", "不对，可能吗？",
                "等一下，靠谱吗？", "这个可信吗？", "真的假的？",
                "确实这样？", "不会吧？", "有这事？"
            ]
            
            user_interrupt = random.choice(interrupt_phrases)
            
            # 构建对话上下文
            context_conversation = conversation[:turn_idx] + [
                {"role": "assistant", "content": truncated_assistant},
                {"role": "user", "content": user_interrupt}
            ]
            
            context = extract_conversation_context(context_conversation, len(context_conversation)-1)
            
            sample = {
                "instruction": "在助手说话时，用户插话了。判断用户的插话是否构成打断。如果用户意图抢占话语权并提出新话题或指令，则输出 <interrupt>。如果用户只是在附和（例如说\"嗯\"、\"好的\"），则输出 <continue-speak>。不要解释原因。",
                "input": context,
                "output": "<interrupt>",
                "scenario": scenario_type,
                "type": "assistant_speaking"
            }
            
            scenario_samples.append(sample)
            count += 1
        
        samples.extend(scenario_samples)
        print(f"场景 '{scenario_type}': 生成了 {len(scenario_samples)} 个 interrupt 样本")
    
    return samples

def generate_continue_speak_samples(grouped_conversations, total_samples=100):
    """
    生成 <continue-speak> 标签的训练样本
    用户只是附和，助手应该继续说话
    """
    samples = []
    scenarios = list(grouped_conversations.keys())
    valid_scenarios = [s for s in scenarios if grouped_conversations[s]]
    
    if not valid_scenarios:
        return []
    
    samples_per_scenario = total_samples // len(valid_scenarios)
    
    for scenario_type in valid_scenarios:
        conversations = grouped_conversations[scenario_type]
        scenario_samples = []
        
        count = 0
        attempts = 0
        max_attempts = len(conversations) * 3
        
        while count < samples_per_scenario and attempts < max_attempts:
            attempts += 1
            conversation = random.choice(conversations)
            
            # 找到助手的轮次
            assistant_turns = [
                i for i, turn in enumerate(conversation) 
                if turn['role'] == 'assistant' and len(turn['content']) > 20
            ]
            
            if not assistant_turns:
                continue
                
            turn_idx = random.choice(assistant_turns)
            assistant_turn = conversation[turn_idx]
            
            # 在助手说话中间插入用户附和
            content = assistant_turn['content']
            split_pos = random.randint(len(content)//4, len(content)*3//4)
            
            # 生成用户附和话语
            agreement_phrases = [
                # 基础附和
                "嗯", "好的", "是的", "对", "明白了", "好", "嗯嗯", 
                "知道了", "行", "可以", "嗯，对", "好的好的", "是",
                "嗯好", "明白", "了解", "好吧", "嗯是的",
                
                # 情感附和
                "哦", "啊", "哦哦", "啊是的", "嗯哼", "嗯呢", "嗯嗯呢",
                "嗯对对", "对对对", "是是是", "好好好", "行行行",
                
                # 确认理解
                "我懂了", "我明白", "我知道", "我了解", "我理解",
                "明白的", "懂了", "理解了", "清楚了", "知道的",
                
                # 鼓励继续
                "你继续说", "接着说", "然后呢", "嗯然后", "继续",
                "还有呢", "往下说", "你说", "嗯你说", "我在听",
                
                # 赞同表达
                "没错", "对的", "就是这样", "说得对", "正是",
                "确实", "有道理", "对啊", "是这样", "没毛病",
                
                # 疑问附和
                "是吗", "真的吗", "这样啊", "哦是吗", "原来如此",
                "这样的", "哦这样", "嗯是这样", "原来是这样",
                
                # 情绪附和
                "嗯呐", "嗯嗯嗯", "好嘞", "得嘞", "成", "中",
                "ok", "OK", "okok", "好咧", "得", "嘞",
                
                # 思考附和
                "嗯...是的", "对...没错", "嗯...好的", "是...我懂",
                "哦...明白", "啊...对对", "嗯...继续", "对...然后呢",
                
                # 地方方言风格
                "嗯咧", "好滴", "晓得了", "知道滴", "明白滴",
                "好嘞嘞", "成咧", "中滴", "行嘞", "得咧",
                
                # 网络用语风格
                "ok的", "get到了", "收到", "明白哒", "懂哒",
                "好滴呀", "嗯呐呐", "对鸭", "是滴", "没问题哒",
                
                # 职场风格
                "好的，您继续", "明白，请继续", "了解，您说",
                "收到，继续", "知道了，然后呢", "理解，往下说",
                
                # 混合表达
                "嗯好的", "对明白", "是知道", "好懂了", "嗯理解",
                "对清楚", "是明白", "好知道", "嗯懂的", "对了解",
                
                # 语气词组合
                "嗯呢对", "啊是好", "哦对的", "嗯嗯是", "好呢对",
                "对呢嗯", "是呢好", "嗯呀对", "好呀是", "对呀嗯",
                
                # 重复强调
                "对对", "好好", "是是", "嗯嗯", "行行", "可可",
                "懂懂", "知知", "明明", "了了", "清清", "理理"
            ]
            
            user_agreement = random.choice(agreement_phrases)
            
            # 构建对话上下文（助手说到一半，用户附和）
            partial_assistant = content[:split_pos].strip()
            if len(partial_assistant) < 10:
                continue
            
            context_conversation = conversation[:turn_idx] + [
                {"role": "assistant", "content": partial_assistant},
                {"role": "user", "content": user_agreement}
            ]
            
            context = extract_conversation_context(context_conversation, len(context_conversation)-1)
            
            sample = {
                "instruction": "在助手说话时，用户插话了。判断用户的插话是否构成打断。如果用户意图抢占话语权并提出新话题或指令，则输出 <interrupt>。如果用户只是在附和（例如说\"嗯\"、\"好的\"），则输出 <continue-speak>。不要解释原因。",
                "input": context,
                "output": "<continue-speak>",
                "scenario": scenario_type,
                "type": "assistant_speaking"
            }
            
            scenario_samples.append(sample)
            count += 1
        
        samples.extend(scenario_samples)
        print(f"场景 '{scenario_type}': 生成了 {len(scenario_samples)} 个 continue-speak 样本")
    
    return samples

# 生成所有标签的训练数据
def generate_all_training_data(grouped_conversations, samples_per_label=100):
    """
    生成所有四种标签的训练数据
    
    Args:
        grouped_conversations: 按场景分组的对话数据
        samples_per_label: 每种标签的样本数量
    
    Returns:
        list: 包含所有训练样本的列表
    """
    print("开始生成训练数据...")
    
    # 设置随机种子以确保可重复性
    random.seed(42)
    
    all_samples = []
    
    # 生成各种标签的样本
    print("\n=== 生成 end-of-turn 样本 ===")
    end_of_turn_samples = generate_end_of_turn_samples(grouped_conversations, samples_per_label)
    all_samples.extend(end_of_turn_samples)
    
    print("\n=== 生成 continue-turn 样本 ===")
    continue_turn_samples = generate_continue_turn_samples(grouped_conversations, samples_per_label)
    all_samples.extend(continue_turn_samples)
    
    print("\n=== 生成 interrupt 样本 ===")
    interrupt_samples = generate_interrupt_samples(grouped_conversations, samples_per_label)
    all_samples.extend(interrupt_samples)
    
    print("\n=== 生成 continue-speak 样本 ===")
    continue_speak_samples = generate_continue_speak_samples(grouped_conversations, samples_per_label)
    all_samples.extend(continue_speak_samples)
    
    # 打乱数据顺序
    random.shuffle(all_samples)
    
    # 清理样本数据（移除辅助字段）
    clean_samples = []
    for sample in all_samples:
        clean_sample = {
            "instruction": sample["instruction"],
            "input": sample["input"],
            "output": sample["output"]
        }
        clean_samples.append(clean_sample)
    
    return clean_samples

# 主执行部分
if __name__ == "__main__":
    output_dir = Path('../output')
    scenario_grouped_conversations = merge_and_group_conversations(output_dir)
    output_file = output_dir / 'grouped_conversations_by_scenario.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(scenario_grouped_conversations, f, ensure_ascii=False, indent=2)
    print(f"分组数据已保存到: {output_file}")
    print(f"可以直接使用变量 'scenario_grouped_conversations' 访问数据")
    
    # 生成训练数据
    training_data = generate_all_training_data(scenario_grouped_conversations, samples_per_label=100)
    
    print(f"\n=== 数据生成完成 ===")
    print(f"总样本数: {len(training_data)}")
    
    # 统计输出标签分布
    from collections import Counter
    output_distribution = Counter(item['output'] for item in training_data)
    print(f"\n输出标签分布:")
    for label, count in output_distribution.items():
        print(f"  {label}: {count}")
    
    # 保存训练数据
    train_data_path = Path('data/generated_train_data.json')
    train_data_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(train_data_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n训练数据已保存到: {train_data_path}")
    print(f"数据格式: 标准 Alpaca 格式")
    
    # 展示几个样例
    print(f"\n=== 数据样例 ===")
    sample_by_output = {}
    for item in training_data:
        output_label = item['output']
        if output_label not in sample_by_output:
            sample_by_output[output_label] = item
    
    for label, sample in sample_by_output.items():
        print(f"\n【{label}】样例:")
        print(f"Input: {sample['input'][:100]}...")
        print(f"Output: {sample['output']}")
        print("-" * 50)

