"""
AI 解卦模块 — AI-Powered I Ching Interpretation

使用大语言模型对占卜结果进行综合解读，结合卦辞、爻辞、
变卦、互卦、错卦、综卦等信息，给出个性化的自然语言解读。
"""
import json
from app.debug import log

_SYSTEM_PROMPT = """你是一位精通《易经》的占卜解读大师。你的解读风格应该像傅佩荣、曾仕强——先引用经典原文建立权威，再用现代语言解释，最后映射到问卦者身上。你不是"原创者"，你是"经典的翻译者和应用者"。

## 核心法则：经文锚定

**每一个解读段落必须先引用至少一句经文原文，再展开现代解读。** 让经典自己先说话。权威来自经文，不来自你的意见。

引用格式：「卦辞云：'……'」「xx爻辞曰：'……'」「《彖》曰：'……'」「《象》曰：'……'」

## 解读框架（内部使用，输出不出现编号）

你需要在心里按以下结构组织解读，但在输出文字中用自然语言串联，**禁止出现"第一步""第二步"等步骤编号**：

1. 共情开场：识别问卦者的情绪，用1-2句话回应。语气根据问题类型调整——职场事业沉稳有力，感情人际温和含蓄，抉择方向清晰果断。

2. 经文锚定 + 卦象释义：引用本卦卦辞和动爻爻辞原文，然后逐层解释——先说字面意思，再说核心意象（"这里'狐'象征隐藏的隐患""这里'乘马班如'形容进退两难"），最后将意象映射到问卦者的具体处境。

3. 变卦 + 关联卦象推演：交代本卦到变卦的逻辑链条（代表了什么态势变化），用互卦看内在因素，错卦和综卦提供反面视角。

4. 体用生克：分析体卦（占者）和用卦（环境）的五行关系。在五行基础上细分阴阳属性。

5. 行动建议 + 逆向预警：建议分两个层次——短期可执行动作（具体到行为）和长期评估框架（判断标准或时间窗口）。**必须在末尾说明"什么情况下应该重新考虑当前判断"**。

## 说服力修辞原则

**以经文说狠话**：需要给出批评性意见时，让经文原文承担负面信息。例如：「不是我说你，而是爻辞'负且乘，致寇至'说的正是你现在的状态——所得配不上位置。」

**为不确定性留退路**：使用"以目前之势来看""卦象显示的趋势是""如果……则应重新审视"等缓冲句式，不把话说死。

**口诀提炼**：每次解读结尾用一句话总结核心启示，增强记忆锚点。

**委婉转折**：先肯定卦象中的吉利因素，再指出警示——"卦象在此处确有转机，但某爻的警示同样不可忽视……"

## 处世原则

**双面论证**：涉及选择时，同时分析每个方向在卦象中的依据和局限性，不偏向单一方向。

**方向对比框架**：多选项时，用体用生克对各选项做对比评估。

**破执原则**：如果卦象暗示问卦者已有答案却不敢面对，先引用一句与"执念/自欺"相关的经文（如益卦九五"勿问元吉"、蒙卦初六"发蒙"等），然后用经文原文说出那句不中听的话，再用现代语言温和解释。

## 输出规范

- 用现代汉语，语言简洁有力、有画面感
- **禁止使用"第一步""第二步"等步骤编号**，用自然段落过渡
- 每条分析必须落到具体问题上
- 长度控制在 800 字以内
- 不空谈哲理，每句话有经典文本作为锚点"""


def build_prompt(result: dict) -> str:
    """根据占卜结果构建 AI 提示词。
    兼容两种格式：嵌套格式（result页面）和扁平格式（API）。
    """
    # 统一转换为嵌套格式
    if "original_hexagram" not in result and "original_name_cn" in result:
        result = _api_result_to_nested(result)

    question = result.get("question", "")
    original = result.get("original_hexagram", {})
    changed = result.get("changed_hexagram")
    interp = result.get("interpretation", {})
    body_use = result.get("body_use", {})
    lines = result.get("lines", [])

    parts = []

    # 占者所问放在最前面，权重最高
    if question:
        parts.append(f"## 占者所问 [这是解读的核心，所有分析必须围绕此问题展开]\n{question}")
    else:
        parts.append("## 占者所问\n（未写明具体问题，请根据卦象给出通用性解读）")

    # 本卦
    parts.append(f"## 本卦\n第{original.get('number','?')}卦 {original.get('name',{}).get('cn','')}（{original.get('name',{}).get('pinyin','')}）")
    parts.append(f"卦辞：{original.get('judgment',{}).get('cn','')}")
    parts.append(f"彖传：{original.get('tuan',{}).get('cn','')}")
    parts.append(f"大象传：{original.get('xiang',{}).get('cn','')}")
    parts.append(f"上卦{original.get('upper_name','')}（{original.get('upper_trigram','')}）下卦{original.get('lower_name','')}（{original.get('lower_trigram','')}）")

    # 变爻
    positions = result.get("changing_positions", [])
    if positions:
        parts.append(f"## 变爻\n共{len(positions)}个变爻，位置：{positions}")
        for line in lines:
            if line.get("changing"):
                parts.append(f"- {line.get('name','')}：{line.get('text','')}")

    # 变卦
    if changed:
        parts.append(f"## 变卦\n第{changed.get('number','?')}卦 {changed.get('name',{}).get('cn','')}（{changed.get('name',{}).get('pinyin','')}）")
        parts.append(f"卦辞：{changed.get('judgment',{}).get('cn','')}")

    # 解卦规则
    parts.append(f"## 解卦规则\n{interp.get('primary_description','')}")

    # 相关卦象
    mutual = result.get("mutual_hexagram")
    opposite = result.get("opposite_hexagram")
    reverse = result.get("reverse_hexagram")
    if mutual:
        parts.append(f"## 互卦\n第{mutual.get('number','?')}卦 {mutual.get('name',{}).get('cn','')} — 揭示内在因素")
    if opposite:
        parts.append(f"## 错卦\n第{opposite.get('number','?')}卦 {opposite.get('name',{}).get('cn','')} — 对立面视角")
    if reverse:
        parts.append(f"## 综卦\n第{reverse.get('number','?')}卦 {reverse.get('name',{}).get('cn','')} — 换个角度看")

    # 体用分析
    if body_use:
        parts.append(f"## 体用分析\n体卦：{body_use.get('body_trigram','')}（{body_use.get('body_element','')}，代表占者）")
        parts.append(f"用卦：{body_use.get('use_trigram','')}（{body_use.get('use_element','')}，代表环境）")
        parts.append(f"生克关系：{body_use.get('relation','')} — {'吉' if body_use.get('auspicious') else '凶'}")

    # 所有爻
    parts.append("## 六爻详情")
    for line in lines:
        marker = " 【变爻】" if line.get("changing") else ""
        parts.append(f"- {line.get('name','')}：{line.get('text','')}{marker}")

    return "\n\n".join(parts)


async def interpret_with_ai(result: dict) -> str:
    """使用 AI 解读占卜结果。

    Args:
        result: 完整的占卜结果字典

    Returns:
        AI 生成的解读文本
    """
    log(900, f"ai_interpret: start hexagram={result.get('original_hexagram',{}).get('name',{}).get('cn','?')}")

    user_prompt = build_prompt(result)

    try:
        import anthropic
        from app.config import settings

        api_key = getattr(settings, 'anthropic_api_key', None)
        if not api_key:
            log(901, "ai_interpret: no API key configured", level="WARN")
            return _fallback_interpretation(result)

        client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=getattr(settings, 'anthropic_base_url', 'https://api.deepseek.com/anthropic'),
        )
        model = getattr(settings, 'anthropic_model', 'deepseek-v4-pro')

        log(902, f"ai_interpret: calling model={model} base_url={client.base_url}")

        # 构建请求参数，根据供应商适配
        create_kwargs = {
            "model": model,
            "max_tokens": 1200,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        # DeepSeek 需要显式禁用 thinking 避免消耗输出 token
        base_url = str(client.base_url)
        if "deepseek" in base_url:
            create_kwargs["thinking"] = {"type": "disabled"}

        message = await client.messages.create(**create_kwargs)

        # 遍历 content 找到 TextBlock 取 text（兼容 DeepSeek ThinkingBlock）
        text = ""
        for block in message.content:
            if hasattr(block, 'text'):
                text += block.text
        if not text:
            log(908, "ai_interpret: no text in response", level="WARN")
            return _fallback_interpretation(result)
        log(903, f"ai_interpret: OK len={len(text)}")
        return text

    except ImportError:
        log(904, "ai_interpret: anthropic SDK not installed", level="WARN")
        return _fallback_interpretation(result)
    except Exception as e:
        log(905, "ai_interpret: API call FAILED", level="ERROR", error=e)
        return _fallback_interpretation(result)


def _fallback_interpretation(result: dict) -> str:
    """当 AI API 不可用时的规则化解读回退方案。"""
    original = result.get("original_hexagram", {})
    changed = result.get("changed_hexagram")
    interp_data = result.get("interpretation", {})
    lines = result.get("lines", [])
    body_use = result.get("body_use", {})

    parts = []
    parts.append("【AI 服务暂不可用，以下为基于规则的综合解读】\n")

    # 本卦概览
    original_name = original.get("name", {}).get("cn", "")
    original_judgment = original.get("judgment", {}).get("cn", "")
    parts.append(f"本卦为**{original_name}**，卦辞曰：{original_judgment}")

    upper = original.get("upper_name", "")
    lower = original.get("lower_name", "")
    parts.append(f"上{lower}下{upper}，代表了事情的内外结构。")

    # 变爻分析
    changing = [l for l in lines if l.get("changing")]
    if changing:
        parts.append(f"\n本卦有 **{len(changing)} 个变爻**：")
        for l in changing:
            parts.append(f"- {l.get('name','')}（{l.get('text','')}）")
    else:
        parts.append("\n本卦无变爻，局势稳定，以卦辞为主进行判断。")

    # 变卦
    if changed:
        changed_name = changed.get("name", {}).get("cn", "")
        changed_judgment = changed.get("judgment", {}).get("cn", "")
        parts.append(f"\n变卦为**{changed_name}**，代表事情发展的趋势：{changed_judgment}")

    # 解卦规则
    parts.append(f"\n解卦方法：{interp_data.get('primary_description','')}")

    # 体用
    if body_use:
        rel = body_use.get("relation", "")
        auspicious = "吉" if body_use.get("auspicious") else "凶"
        rel_desc = {
            "比和": "体卦与用卦五行相同，内外和谐，行事顺遂。",
            "生我": "用卦生体卦，外部环境对占者有利，时机恰当。",
            "我生": "体卦生用卦，占者需付出较多，宜谨慎行事。",
            "我克": "体卦克用卦，占者占据主动，但耗费精力。",
            "克我": "用卦克体卦，外部环境不利，需等待时机。",
        }
        parts.append(f"\n体用分析：{rel}（{auspicious}）— {rel_desc.get(rel, '')}")

    # 行动建议
    parts.append("\n## 行动建议")
    if body_use.get("auspicious"):
        parts.append("- 当前时机相对有利，可以主动推进。")
    else:
        parts.append("- 当前时机不太有利，建议谨慎行事，等待更好的时机。")
    parts.append("- 参考变卦的方向，把握关键转折点。")
    parts.append("- 保持内心的中正平和，顺应变化之势。")

    return "\n".join(parts)


def _api_result_to_nested(flat: dict) -> dict:
    """将扁平 API 格式转为嵌套页面格式。"""
    return {
        "question": flat.get("question", ""),
        "original_hexagram": {
            "number": flat.get("original_number"),
            "name": {"cn": flat.get("original_name_cn", ""), "pinyin": flat.get("original_name_pinyin", "")},
            "judgment": {"cn": flat.get("original_judgment", "")},
            "upper_name": flat.get("upper_trigram_name", ""),
            "lower_name": flat.get("lower_trigram_name", ""),
            "tuan": {"cn": flat.get("interpretation", {}).get("_texts", {}).get("original_tuan", "") if isinstance(flat.get("interpretation"), dict) else ""},
            "xiang": {"cn": flat.get("interpretation", {}).get("_texts", {}).get("original_xiang", "") if isinstance(flat.get("interpretation"), dict) else ""},
        },
        "changed_hexagram": {
            "number": flat.get("changed_number"),
            "name": {"cn": flat.get("changed_name_cn", ""), "pinyin": flat.get("changed_name_pinyin", "")},
            "judgment": {"cn": flat.get("changed_judgment", "")},
        } if flat.get("changed_name_cn") else None,
        "changing_positions": flat.get("changing_positions", []),
        "interpretation": flat.get("interpretation", {}),
        "mutual_hexagram": flat.get("mutual_hexagram"),
        "opposite_hexagram": flat.get("opposite_hexagram"),
        "reverse_hexagram": flat.get("reverse_hexagram"),
        "body_use": flat.get("body_use"),
        "lines": flat.get("lines", []),
    }
