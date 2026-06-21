"""
AI 解卦模块 — AI-Powered I Ching Interpretation

使用大语言模型对占卜结果进行综合解读，结合卦辞、爻辞、
变卦、互卦、错卦、综卦等信息，给出个性化的自然语言解读。
"""
import json
from app.debug import log

_SYSTEM_PROMPT = """你是一位精通《易经》的占卜解读大师。你会收到一次占卜的完整信息，
包括本卦、变卦、互卦、错卦、综卦，以及朱熹变爻解卦规则和体用生克分析。

请根据以下原则进行解读：

1. **第一步：理解卦象** — 解释本卦的核心含义（结合卦辞和彖传），分析上下卦的关系。
2. **第二步：分析变爻** — 根据变爻的位置和爻辞，指出正在发生的变化和关键转折点。
3. **第三步：综合判断** — 结合变卦分析发展趋势，参考互卦看内在因素，错卦提供反面视角。
4. **第四步：体用生克** — 分析体卦（占者自身）和用卦（外部环境）的五行关系。
5. **第五步：给出建议** — 基于以上分析，给占者具体的行动建议和注意事项。

回复要求：
- 语言简洁有力，用现代汉语
- 不要重复原文，而是解释其实际含义
- 结合占者所问的问题进行针对性解读
- 长度控制在 500 字以内
- 结构清晰，分段呈现"""


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

    if question:
        parts.append(f"## 占者所问\n{question}")
    else:
        parts.append("## 占者所问\n（未写明具体问题）")

    # 本卦
    parts.append(f"## 本卦\n第{original.get('number','?')}卦 {original.get('name',{}).get('cn','')}（{original.get('name',{}).get('pinyin','')}）")
    parts.append(f"卦辞：{original.get('judgment',{}).get('cn','')}")
    parts.append(f"彖传：{original.get('tuan',{}).get('cn','')}")
    parts.append(f"大象传：{original.get('xiang',{}).get('cn','')}")

    # 上卦下卦
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
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            thinking={"type": "disabled"},
        )

        # DeepSeek 在 thinking 模式下会返回 ThinkingBlock，
        # 需要遍历 content 找到 TextBlock 取 text
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
