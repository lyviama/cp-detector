#!/usr/bin/env python3
"""
idol-astro algorithm_v2.py — 15个功能模块完整算法
塔罗5个: daily-tarot, tarot-3, tarot-relationship, tarot-celtic, tarot-hexagram
雷诺曼4个: leno-daily, leno-3, leno-9, leno-grand
泰式5个: thai-profile, thai-match, thai-fortune, thai-fortune-match, thai-color-match
"""

import json, random, os, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pymysql
from opencc import OpenCC
_cc_s2t = OpenCC('s2t')
_cc_t2s = OpenCC('t2s')

# ─── DeepSeek 配置 ─────────────────────────────────────────────
DEEPSEEK_KEY = os.environ.get('AUXILIARY_VISION_API_KEY', '') or os.environ.get('DEEPSEEK_API_KEY', '')
if not DEEPSEEK_KEY:
    # Fallback: 从yijing-site api.py获取的key
    DEEPSEEK_KEY = 'sk-21f6df12c71347b985d89bb48fae68a3'
LLM_BASE = 'https://api.deepseek.com/chat/completions'

def _llm_call(system_msg, user_msg, temperature=0.85, max_tokens=2000):
    """调用DeepSeek生成解读文本"""
    import urllib.request, urllib.error
    if not DEEPSEEK_KEY:
        return ''
    body = json.dumps({
        'model': 'deepseek-v4-flash',
        'messages': [
            {'role': 'system', 'content': system_msg},
            {'role': 'user', 'content': user_msg},
        ],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }).encode()
    req = urllib.request.Request(LLM_BASE, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEEPSEEK_KEY}'
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f"[DeepSeek ERROR] {e}")
        return ''

# ─── 工具函数 ──────────────────────────────────────────────

ZODIAC_DATES = [
    ('Capricorn', '摩羯座', 1, 1, 1, 19), ('Aquarius', '水瓶座', 1, 20, 2, 18),
    ('Pisces', '双鱼座', 2, 19, 3, 20), ('Aries', '白羊座', 3, 21, 4, 19),
    ('Taurus', '金牛座', 4, 20, 5, 20), ('Gemini', '双子座', 5, 21, 6, 21),
    ('Cancer', '巨蟹座', 6, 22, 7, 22), ('Leo', '狮子座', 7, 23, 8, 22),
    ('Virgo', '处女座', 8, 23, 9, 22), ('Libra', '天秤座', 9, 23, 10, 23),
    ('Scorpio', '天蝎座', 10, 24, 11, 22), ('Sagittarius', '射手座', 11, 23, 12, 21),
    ('Capricorn', '摩羯座', 12, 22, 12, 31),
]

ZODIAC_ANIMALS = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']

def get_zodiac_sign(month, day):
    for en, cn, sm, sd, em, ed in ZODIAC_DATES:
        if (month == sm and day >= sd) or (month == em and day <= ed):
            return cn
    return '摩羯座'

def get_chinese_zodiac(year):
    return ZODIAC_ANIMALS[(year - 4) % 12] if year > 1900 else ''

def parse_birth_date(date_str):
    """解析生日字符串 → (year, month, day) 或 None"""
    if not date_str:
        return None
    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%m-%d', '%m/%d', '%m.%d']:
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            return (dt.year, dt.month, dt.day)
        except ValueError:
            continue
    return None

def get_day_of_week(date_str):
    """从日期字符串获取星期几(0=周日)"""
    p = parse_birth_date(date_str)
    if not p:
        return None
    try:
        dt = datetime.date(p[0], p[1], p[2])
        return dt.weekday()  # 0=Mon...6=Sun → 需要转换
    except Exception:
        return None

def python_weekday_to_iso(wd):
    """Python weekday (0=Mon) → ISO (0=Sun)"""
    return (wd + 1) % 7

def get_iso_day_of_week(date_str):
    """获取ISO星期几: 0=Sunday"""
    p = parse_birth_date(date_str)
    if not p:
        return None
    try:
        dt = datetime.date(p[0], p[1], p[2])
        return dt.isoweekday() % 7  # Mon=1→1%7=1, Sun=7→7%7=0
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
# 塔罗牌模块 (78张牌 + 5种牌阵)
# ═══════════════════════════════════════════════════════════

# ── Prompt版本管理 ──
PROMPT_VERSION = "2.0"

# ── 饭圈风格语料库 ──
FANDOM_STYLE = """你是豆卜的追星命理解读师, 不是传统算命先生, 是追星引力分析师。

语言体系:
1. 【专有名词】使用豆卜引力体系术语(引力场/引力波/共振/轨道咬合/能量积聚/能量弥散), 不用传统命理术语(命宫/大运/流年/身旺身弱/五行缺X)
2. 【追星场景】每个解读都绑定具体的追昧行动(抢票/补物料/产粮/淘周边/打榜/磕糖), 不说空话
3. 【句式】永远不用"你今天会...""你应该...", 改用"今天适合...""引力波提示...""窗口打开时..."
4. 【饭圈亲切感】像闺蜜聊天, 不是老师讲课。用"信我""实话说""绝了""本命""蒸煮"等自然表达, 不堆砌缩写
5. 【追星文化】提到偶像用"你推""本命""蒸煮""自家", 不用"明星""艺人"等正式称呼
6. 【十神能量类型】比肩=同频共振型, 劫财=竞速冲浪型, 食神=灵感溢出型, 伤官=表达裂变型, 偏财=淘金直觉型, 正财=理性规划型, 七杀=破壁冲锋型, 正官=轨道稳定型, 偏印=探索雷达型, 正印=沉浸吸收型
7. 【五行引力元素】木=生长引力, 火=燃烧引力, 土=锚定引力, 金=锐利引力, 水=流动引力
8. 【牌面解读】要具体, 结合牌意说人话, 不要列式地一张一张牌来解读, 融入叙述中自然带出
9. 【结尾】给一句让人心暖的话, 如"追星最重要的不是追到什么, 是追的过程让你变成了谁""宇宙不急, 你也不用急, 该来的惊喜自己会敲门"

禁忌:
- 绝不用"贵人相助""桃花朵朵""财运亨通""万事如意"这种模板词
- 绝不用"你需要注意""你应该""你必须"这种教导口吻
- 绝不编造牌面/八字未暗示的内容

风格要求：
1. 口语化、接地气，像对朋友说话不像写报告
2. 可以用饭圈常用语和表达方式（不要太正式），比如"绝了""真的假的""实话说""信我""眉眉""本命"等自然说法，但不要堆砌缩写
3. 提到偶像时用"你家哥哥""你本命""蒸煮""自家"等粉丝称呼，提到其他偶像用"别家""对家"
4. 解读结果要有情感共鸣，让粉丝觉得"对对对，就是这样！""太懂了吧"
5. 不要用"你应该""建议你"这种教导口吻，用"说实话，这个牌说明你……""眉眉，你们两个这个组合真的特别""这个牌告诉你有缘"这种更接地气的方式
6. 分析缘分和关系时，用粉丝熟悉的话："实锤了""这个组合我觉得有那个""你们两个的磁场真的超强""这个牌告诉你有缘"
7. 结尾给一句让人心暖的话，比如"放心，成为更好的自己，给你家哥哥打call""信我，你和本命的故事才刚开始""别内耗啊，追星开心就好，一点内耗都不要有"
8. 牌面解读要具体，结合牌意说人话，不要列式地一张一张牌来解读"第一张牌……第二张牌……"，要融入叙述中自然带出
"""

FORTUNE_MEANINGS = {
    1: '谨慎谦虚，小心行事',
    2: '注意健康财运，防范损失',
    3: '财运中等，安稳生活',
    4: '幸运儿，心想事成',
    5: '先苦后甜，越老越富',
    6: '贵人相助，未来富裕',
    7: '多阻碍，需坚持',
    8: '高贵可成大器，受人信赖',
    9: '有运需努力，白手起家',
    10: '近朱者赤，慎交友',
}

class TarotReader:
    def __init__(self, conn):
        self.conn = conn

    def draw_cards(self, n):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tarot_cards")
            all_cards = cur.fetchall()
        drawn = random.sample(all_cards, min(n, len(all_cards)))
        result = []
        for card in drawn:
            reversed_flag = random.choice([True, False])
            pos = "reversed" if reversed_flag else "upright"
            kws = self._parse_json(card.get('keywords_' + pos, '[]'))
            # 过滤掉纯英文关键词（只保留中文），保证DeepSeek收到纯中文
            kws = [k for k in kws if k and any('\u4e00' <= ch <= '\u9fff' for ch in k)]
            # 如果过滤后为空，保留原始关键词（纯英文的牌作为fallback）
            if not kws:
                kws = self._parse_json(card.get('keywords_' + pos, '[]'))
                kws = kws[:4] if kws else []
            meaning = card.get('meaning_general_' + pos, '') or card.get('meaning_up', '') or card.get('meaning_rev', '') or ''
            result.append({
                'id': card['id'], 'name': card['name'],
                'name_cn': card.get('name_cn', ''),
                'arcana': card['arcana'], 'number': card['number'],
                'suit': card['suit'], 'reversed': reversed_flag,
                'img': card.get('img', ''),
                'keywords': kws, 'keywords_cn': kws,
                'meaning': meaning,
                'meaning_love': card.get('meaning_love_' + pos, ''),
                'meaning_career': card.get('meaning_career_' + pos, ''),
                'element': card.get('element', ''),
                'astrology': card.get('astrology', ''),
            })
        return result

    def _parse_json(self, val):
        if not val:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        return val if isinstance(val, list) else []


    def draw_major_only(self, n):
        import random as _rnd
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tarot_cards WHERE arcana='major'")
            all_cards = cur.fetchall()
        drawn = _rnd.sample(all_cards, min(n, len(all_cards)))
        result = []
        for card in drawn:
            rev = _rnd.choice([True, False])
            pos = 'reversed' if rev else 'upright'
            kws = self._parse_json(card.get('keywords_' + pos, '[]'))
            kws = [k for k in kws if k]
            result.append({
                'name': card.get('name',''), 'name_cn': card.get('name_cn',''),
                'arcana': 'major', 'number': card.get('number',0),
                'reversed': rev, 'element': card.get('element',''),
                'astrology': card.get('astrology',''),
                'meaning': card.get('meaning_'+pos, ''),
                'meaning_upright': card.get('meaning_upright',''),
                'meaning_reversed': card.get('meaning_reversed',''),
                'keywords': kws, 'image_url': card.get('image_url',''),
            })
        return result

    # ── 5种牌阵 ──

    SPREADS = {
        'daily': {
            'name_cn': '每日一牌',
            'count': 1,
            'positions': [{'name': '今日指引', 'meaning': '今天宇宙给你的讯息'}],
            'system': '你是一位和粉丝打成一片的塔罗占卜师，说话像跟闺蜜聊天一样自然亲切。请根据抽到的塔罗牌，为粉丝解读今日运势。回复用纯中文，2-3段，像聊天一样聊运势和建议。',
        },
        'three': {
            'name_cn': '三牌阵',
            'count': 3,
            'positions': [{'name': '过去', 'meaning': '过去的影响'}, {'name': '现在', 'meaning': '当前的状况'}, {'name': '未来', 'meaning': '未来的趋势'}],
            'system': '你是一位跟粉丝关系超好的塔罗占卜师。解读三牌阵像跟朋友分析感情走向一样自然。回复用纯中文，分过去现在未来三部分聊。',
        },
        'relationship': {
            'name_cn': '关系牌阵',
            'count': 7,
            'positions': [
                {'name': '你', 'meaning': '你在关系中的角色'}, {'name': '对方', 'meaning': '对方在关系中的角色'},
                {'name': '关系现状', 'meaning': '关系的当前状态'}, {'name': '联结纽带', 'meaning': '你们的共同点'},
                {'name': '分歧与矛盾', 'meaning': '差异和矛盾'}, {'name': '建议', 'meaning': '改善关系的指引'},
                {'name': '未来走向', 'meaning': '关系的未来走向'},
            ],
            'system': '你是一位超懂CP的塔罗占卜师，解读缘分时像姐妹间讨论实锤和感情一样自然。回复用纯中文，把7个位置融成连贯的故事来讲，最后综合总结。',
        },
        'celtic': {
            'name_cn': '凯尔特十字',
            'count': 10,
            'positions': [
                {'name': '当前状况', 'meaning': '问题的核心和当前状态'}, {'name': '挑战/阻碍', 'meaning': '你面对的挑战'},
                {'name': '过去基础', 'meaning': '远期过去的影响'}, {'name': '近期过去', 'meaning': '近期事件的影响'},
                {'name': '可能结果', 'meaning': '若持续现状的结果'}, {'name': '近期未来', 'meaning': '即将到来的变化'},
                {'name': '自我认知', 'meaning': '你如何看待自己'}, {'name': '外部影响', 'meaning': '外界对你的影响'},
                {'name': '希望与恐惧', 'meaning': '内心深处的期待和担忧'}, {'name': '最终结局', 'meaning': '所有影响的最终走向'},
            ],
            'system': '你是一位深谙饭圈文化的塔罗大师。凯尔特十字解读像资深站姐分析爱豆运势一样专业又接地气。回复用纯中文，把10个位置串成一个完整的故事，最后总结。',
        },
        'hexagram': {
            'name_cn': '六芒星牌阵',
            'count': 5,
            'positions': [
                {'name': '灵性(顶)', 'meaning': '最高指引和精神方向'}, {'name': '风(右上)', 'meaning': '思维、沟通和智慧'},
                {'name': '火(右下)', 'meaning': '热情、行动和创造力'}, {'name': '土(左下)', 'meaning': '现实、稳定和物质'},
                {'name': '水(左上)', 'meaning': '情感、直觉和潜意识'},
            ],
            'system': '你是一位说话超有梗的塔罗占卜师。六芒星解读像朋友聊心事一样娓娓道来。回复用纯中文，五个元素串起来分析，最后给个温暖的总结。',
        },
        'love': {
            'name_cn': '爱情牌阵',
            'count': 4, 'cost': 6,
            'positions': [
                {'name': '你的情感状态', 'meaning': '你当前的情感状态和内心感受'},
                {'name': '对方的情感状态', 'meaning': '对方当前的情感状态和想法'},
                {'name': '关系现状', 'meaning': '你们关系的当前状况和核心动态'},
                {'name': '关系建议', 'meaning': '对这段关系的发展建议'},
            ],
            'system': '你是一位擅长解读爱情的塔罗师，说话温柔又一针见血。请根据4张牌分别解读双方状态、关系现状和建议。回复用纯中文，分四个部分详细解读，最后综合总结。',
        },
        'choice': {
            'name_cn': '抉择牌阵',
            'count': 5, 'cost': 6,
            'positions': [
                {'name': '当前处境', 'meaning': '你目前面临的整体情况'},
                {'name': '选项A的现状', 'meaning': '选择A的当前状态'},
                {'name': '选项A的潜在结果', 'meaning': '如果坚持选A，最终结果如何'},
                {'name': '选项B的现状', 'meaning': '选择B的当前状态'},
                {'name': '选项B的潜在结果', 'meaning': '如果坚持选B，最终结果如何'},
            ],
            'system': '你是一位帮人做决定的塔罗师，逻辑清晰又善解人意。请根据5张牌分析当前处境和两个选项的利弊。回复用纯中文，先分析现状，再分别解读A和B，最后给出综合建议。',
        },
        'yesno': {
            'name_cn': '是否牌阵',
            'count': 1, 'cost': 2,
            'positions': [
                {'name': '宇宙的回答', 'meaning': '对你问题的直接指引'},
            ],
            'system': '你是一位直觉敏锐的塔罗师。用户问了一个是非题，你抽到了一张大阿卡纳。正位的牌倾向于是，逆位的牌倾向于否。请给出明确的倾向性回答，并解释原因。回复用纯中文。',
        },
    }

    def read_spread(self, spread_type):
        """读取指定牌阵 — 返回{spread, cards}"""
        sp = self.SPREADS.get(spread_type)
        if not sp:
            return None
        cards = self.draw_major_only(sp['count']) if spread_type == 'yesno' else self.draw_cards(sp['count'])
        reading = {
            'spread': {'type': spread_type, 'name_cn': sp['name_cn'], 'count': sp['count']},
            'cards': [],
        }
        for card, pos in zip(cards, sp['positions']):
            card['position'] = pos
            reading['cards'].append(card)
        return reading


# ═══════════════════════════════════════════════════════════
# 雷诺曼模块 (36张牌 + 4种牌阵)
# ═══════════════════════════════════════════════════════════

class LenormandReader:
    def __init__(self, conn):
        self.conn = conn

    def draw_cards(self, n):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM lenormand_cards ORDER BY id")
            all_cards = cur.fetchall()
        drawn = random.sample(all_cards, min(n, len(all_cards)))
        result = []
        for c in drawn:
            card = dict(c)
            card['keywords'] = self._parse_json(card.get('keywords', '[]'))
            card['keywords_cn'] = self._parse_json(card.get('keywords_cn', '[]'))
            # 补充含义
            card['meaning_general'] = card.get('meaning_general_cn', '') or card.get('meaning_general', '')
            card['meaning_love'] = card.get('meaning_love_cn', '') or card.get('meaning_love', '')
            card['meaning_career'] = card.get('meaning_career_cn', '') or card.get('meaning_career', '')
            card['img'] = '/idol/lenormand-img/' + str(card.get('id',0)) + '_' + card.get('name','Card') + '.jpg'
            result.append(card)
        return result

    def _parse_json(self, val):
        if not val:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        return val if isinstance(val, list) else []

    SPREADS = {
        'daily': {
            'name_cn': '雷诺曼每日一牌',
            'count': 1,
            'positions': [{'name': '今日指引', 'meaning': '今天给你的关键提示'}],
            'system': '你是一位说话超直又超准的雷诺曼占卜师，粉丝叫你最懂她的占卜师。回复纯中文，用自然标题分段解读，包括：牌面解读、感情运势、事业运势、幸运指南、行动建议。每个部分用“【标题】”格式，每部分2-3句，解读丰富有深度。',
        },
        'three': {
            'name_cn': '三牌阵',
            'count': 3,
            'positions': [{'name': '过去', 'meaning': '过去的影响'}, {'name': '现在', 'meaning': '当前状况'}, {'name': '未来', 'meaning': '未来走向'}],
            'system': '你是一位超懂粉丝的雷诺曼占卜师。回复纯中文，用自然标题分段解读，包括：过去影响、现状分析、未来趋势、感情运势、事业运势、幸运建议、行动指南。每部分用“【标题】”格式，2-3句，内容丰富。',
        },
        'nine': {
            'name_cn': '九宫格',
            'count': 9,
            'positions': [
                {'name': '过去(1,1)', 'meaning': '左上—过去经历'}, {'name': '现状(1,2)', 'meaning': '中上—当前状态'},
                {'name': '未来(1,3)', 'meaning': '右上—未来发展'}, {'name': '内在(2,1)', 'meaning': '左中—内心世界'},
                {'name': '核心(2,2)', 'meaning': '中心—问题核心'}, {'name': '外在(2,3)', 'meaning': '右中—外部环境'},
                {'name': '阻碍(3,1)', 'meaning': '左下—困难障碍'}, {'name': '行动(3,2)', 'meaning': '中下—行动指引'},
                {'name': '结果(3,3)', 'meaning': '右下—最终结果'},
            ],
            'system': '你是一位精通雷诺曼九宫格的大师。九宫格是雷诺曼最经典的牌阵，3x3布局呈现人生的完整画面。读法规则：①逐行读（每行3张=一句话）②逐列读③对角线读④中心牌=问题核心。请按行+列+对角线结构解读。回复纯中文，用自然标题分段解读，包括：逐行解读、逐列解读、对角线解读、核心牌分析、整体运势、感情运势、事业运势、幸运指南、行动建议。每部分用“【标题】”格式，每格至少1-2句，总结至少3-4句。必须基于牌面含义解读。',
        },
        'grand': {
            'name_cn': '大蓝图牌阵',
            'count': 36,
            'positions': [
                {'name': '1骑手', 'meaning': '消息/通讯'},
                {'name': '2三叶草', 'meaning': '小幸运'},
                {'name': '3船', 'meaning': '旅行/远方'},
                {'name': '4房子', 'meaning': '家庭/安全感'},
                {'name': '5树', 'meaning': '健康/成长'},
                {'name': '6云', 'meaning': '困扰/不确定'},
                {'name': '7蛇', 'meaning': '复杂/背叛'},
                {'name': '8棺材', 'meaning': '结束/转变'},
                {'name': '9花束', 'meaning': '喜悦/礼物'},
                {'name': '10镰刀', 'meaning': '突然断裂'},
                {'name': '11鞭子', 'meaning': '冲突/争论'},
                {'name': '12鸟', 'meaning': '沟通/社交'},
                {'name': '13孩子', 'meaning': '新开始/纯真'},
                {'name': '14狐狸', 'meaning': '谨慎/自我保护'},
                {'name': '15熊', 'meaning': '力量/权威'},
                {'name': '16星星', 'meaning': '希望/灵感'},
                {'name': '17鹳', 'meaning': '变化/迁移'},
                {'name': '18狗', 'meaning': '忠诚/友谊'},
                {'name': '19高塔', 'meaning': '孤立/权威'},
                {'name': '20花园', 'meaning': '社交/公众'},
                {'name': '21山', 'meaning': '阻碍/延迟'},
                {'name': '22十字路口', 'meaning': '选择/决定'},
                {'name': '23老鼠', 'meaning': '损失/焦虑'},
                {'name': '24心', 'meaning': '爱情/感情'},
                {'name': '25戒指', 'meaning': '承诺/合同'},
                {'name': '26书', 'meaning': '知识/学习'},
                {'name': '27信件', 'meaning': '消息/通知'},
                {'name': '28男人', 'meaning': '问卜者(男)'},
                {'name': '29女人', 'meaning': '问卜者(女)'},
                {'name': '30百合', 'meaning': '成熟/耐心'},
                {'name': '31太阳', 'meaning': '成功/快乐'},
                {'name': '32月亮', 'meaning': '情感/认可'},
                {'name': '33钥匙', 'meaning': '关键/解答'},
                {'name': '34鱼', 'meaning': '财富/商业'},
                {'name': '35锚', 'meaning': '稳定/根基'},
                {'name': '36十字架', 'meaning': '命运/考验'},
            ],
            'system': '你是一位精通雷诺曼大蓝图的大师。36张牌全部展开在4×9格子中，每张牌落在对应的"House"位置上（House的主题由该位置编号对应的标准含义决定）。读法规则：①找到问卜者牌（男人/女人）②看问卜者周围的牌（邻居关系）③看关键House（心=爱情、戒指=承诺、鱼=财富、太阳=成功、棺材=结束等）④注意牌与牌的组合含义。回复纯中文，每个关键位置单独一段，用“【位置名】”格式做标题。最后分5大领域（【感情运势】、【事业运势】、【财运分析】、【健康提示】、【人际关系】）总结，每个领域2-3句。',
        },
    }

    def read_spread(self, spread_type):
        sp = self.SPREADS.get(spread_type)
        if not sp:
            return None
        cards = self.draw_cards(sp['count'])
        reading = {
            'spread': {'type': spread_type, 'name_cn': sp['name_cn'], 'count': sp['count']},
            'cards': [],
        }
        for card, pos in zip(cards, sp['positions']):
            card['position'] = pos
            reading['cards'].append(card)
        return reading

    def daily_card(self):
        cards = self.draw_cards(1)
        return cards[0] if cards else None


# ═══════════════════════════════════════════════════════════
# 泰式星期命理模块
# ═══════════════════════════════════════════════════════════


# P2-5: Thai element compatibility matrix
THAI_ELEMENT_COMPAT = {
    ('火', '火'): {'score': 95, 'level': 'strong', 'desc': '同为火元素，能量强烈共振，热情洋溢'},
    ('水', '水'): {'score': 95, 'level': 'strong', 'desc': '同为水元素，情感深度共鸣，心灵相通'},
    ('风', '风'): {'score': 95, 'level': 'strong', 'desc': '同为风元素，思维方式同步，交流默契'},
    ('火', '风'): {'score': 80, 'level': 'harmony', 'desc': '火借风势，风助火威，创造力和行动力互补'},
    ('风', '火'): {'score': 80, 'level': 'harmony', 'desc': '风借火光，灵感碰撞，思维与行动完美搭配'},
    ('水', '风'): {'score': 55, 'level': 'neutral', 'desc': '水与风各走其道，需要理解彼此的差异'},
    ('风', '水'): {'score': 55, 'level': 'neutral', 'desc': '风与水节奏不同，但可以互相启发'},
    ('火', '水'): {'score': 35, 'level': 'clash', 'desc': '水火不容，需要空间和耐心磨合'},
    ('水', '火'): {'score': 35, 'level': 'clash', 'desc': '火热水冷，热情与理性需要找到平衡'},
}

def thai_element_compat(elem_a, elem_b):
    key = (elem_a or '', elem_b or '')
    return THAI_ELEMENT_COMPAT.get(key, {'score': 50, 'level': 'unknown', 'desc': '未知元素组合'})

class ThaiBirthDay:
    def __init__(self, conn):
        self.conn = conn

    def get_day_profile(self, date_str):
        """根据出生日期获取泰国星期命理完整档案 — 8个维度"""
        dow = get_iso_day_of_week(date_str)
        if dow is None:
            return None

        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM thai_birth_days WHERE day_of_week=%s", (dow,))
            row = cur.fetchone()
        if not row:
            return None

        profile = {
            'day_of_week': dow,
            'day_name_cn': row.get('day_name_cn', ''),
            'planet': {'cn': row.get('planet_cn', ''), 'en': row.get('planet_en', ''), 'thai': row.get('planet_thai', '')},
            'color': {'cn': row.get('color_cn', ''), 'en': row.get('color_en', ''), 'thai': row.get('color_thai', ''), 'hex': row.get('color_hex', '')},
            'element': {'cn': row.get('element', ''), 'en': row.get('element', '')},
            'direction': {'cn': row.get('direction_cn', ''), 'en': row.get('lucky_direction_en', ''), 'thai': row.get('lucky_direction_thai', '')},
            'deity': {'cn': row.get('deity_thai', row.get('deity_en', '')), 'en': row.get('deity_en', ''), 'thai': row.get('deity_thai', '')},
            'title': {'cn': row.get('day_name_cn', ''), 'en': row.get('title_en', ''), 'thai': row.get('title_thai', '')},
            'description': row.get('description', ''),
        }
        return profile

    def compatibility(self, date_a, date_b):
        """两人缘分匹配 — 6个维度"""
        dow_a = get_iso_day_of_week(date_a)
        dow_b = get_iso_day_of_week(date_b)
        if dow_a is None or dow_b is None:
            return None

        # 匹配评分
        diff = abs(dow_a - dow_b)
        diff = min(diff, 7 - diff)

        if diff == 0:
            score = 100
            level = '完美匹配'
        elif diff == 1:
            score = 85
            level = '高度契合'
        elif diff == 2:
            score = 70
            level = '良好互补'
        elif diff == 3:
            score = 50
            level = '中性平衡'
        else:
            score = 30
            level = '差异互补'

        prof_a = self.get_day_profile(date_a)
        prof_b = self.get_day_profile(date_b)

        # 6个维度分析
        dimensions = []
        # 1. 行星和谐度
        elem_a = prof_a['element']['cn'] if prof_a else ''
        elem_b = prof_b['element']['cn'] if prof_b else ''
        ec = thai_element_compat(elem_a, elem_b)
        dimensions.append({
            'name': '行星和谐度',
            'a': prof_a['planet']['cn'] if prof_a else '',
            'b': prof_b['planet']['cn'] if prof_b else '',
            'match': ec['score'] >= 70,
            'score': ec['score'],
            'level': ec['level'],
            'desc': ec['desc'],
        })
        # 2. 色彩协调
        color_match = ec['score'] >= 70
        color_desc = '幸运色同元素系，色彩能量高度协调' if ec['level'] == 'strong' else ('幸运色互补元素，色彩搭配有张力' if ec['level'] == 'harmony' else ('幸运色中性搭配，各自发光' if ec['level'] == 'neutral' else '幸运色差异较大，但差异即魅力'))
        dimensions.append({
            'name': '色彩协调度',
            'a': prof_a['color']['cn'] if prof_a else '',
            'b': prof_b['color']['cn'] if prof_b else '',
            'match': color_match,
            'desc': color_desc,
        })
        # 3. 性格互补
        # 互补规则：不同元素的行星性格互补，同元素则相似
        personality_compat = ec['level'] in ('harmony', 'neutral')
        pers_desc = ('不同元素但能量和谐，性格互补成长' if ec['level'] == 'harmony' else ('元素差异适中，带来新鲜视角' if ec['level'] == 'neutral' else ('同元素性格相似，默契十足' if ec['level'] == 'strong' else '元素有张力，需要更多包容')))
        dimensions.append({
            'name': '性格互补度',
            'desc_a': prof_a['description'][:50] if prof_a else '',
            'desc_b': prof_b['description'][:50] if prof_b else '',
            'match': personality_compat,
            'desc': pers_desc,
        })
        # 4. 方位磁场
        # 方位互补规则：相对方位(北↔南、东↔西)互补，相邻方位协调，相同方位共振
        dir_compat_map = {'北': '南', '南': '北', '东': '西', '西': '东', '东北': '西南', '西南': '东北', '东南': '西北', '西北': '东南'}
        dir_a = prof_a['direction']['cn'] if prof_a else ''
        dir_b = prof_b['direction']['cn'] if prof_b else ''
        dir_match = bool(dir_a and dir_b and dir_compat_map.get(dir_a) == dir_b)
        dir_harmony = bool(dir_a and dir_b and dir_a == dir_b)
        dimensions.append({
            'name': '方位磁场',
            'a': dir_a,
            'b': dir_b,
            'match': dir_match or dir_harmony,
            'desc': '方位互补(相对)，阴阳调和' if dir_match else ('方位相同，磁场共振' if dir_harmony else '方位不同，各有磁场'),
        })
        # 5. 守护神共鸣
        # 守护神互补规则：同日守护神=强共鸣，不同日=各有守护
        deity_match = bool(prof_a and prof_b and prof_a['title']['cn'] == prof_b['title']['cn'])
        dimensions.append({
            'name': '守护神共鸣',
            'a': prof_a['deity']['cn'] if prof_a else '',
            'b': prof_b['deity']['cn'] if prof_b else '',
            'match': deity_match,
            'desc': '同一守护神庇佑，共鸣强烈' if deity_match else '不同守护神，各有庇佑方式',
        })
        # 6. 整体评分
        dimensions.append({
            'name': '整体缘分评分',
            'score': score,
            'level': level,
            'desc': level,
        })

        return {
            'day_a': dow_a, 'day_b': dow_b,
            'profile_a': prof_a, 'profile_b': prof_b,
            'score': score, 'level': level,
            'dimensions': dimensions,
        }


    def fortune_number(self, date_str):
        """根据出生日期计算运命数字(1-10) — 拉玛四世公式"""
        p = parse_birth_date(date_str)
        if not p:
            return None, None
        year, month, day = p
        
        # 生肖年数映射
        animal = get_chinese_zodiac(year)
        animal_map = {'鼠':1,'牛':2,'虎':3,'兔':4,'龙':5,'蛇':6,'马':7,'羊':8,'猴':9,'鸡':10,'狗':11,'猪':12}
        animal_num = animal_map.get(animal, 1)
        
        # 泰国历月份映射: 1月=2, 2月=3 ... 12月=1
        month_map = {1:2, 2:3, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9, 9:10, 10:11, 11:12, 12:1}
        month_num = month_map.get(month, month)
        
        # 星期数: 周日=1 周一=2 ... 周六=7
        dow = get_iso_day_of_week(date_str)
        week_num = dow + 1 if dow is not None else None
        
        if week_num is None:
            return None, None
        
        # 运命数 = (生肖年数 + 月份 + 星期数) % 10, 0则=10
        fortune = (animal_num + month_num + week_num) % 10
        if fortune == 0:
            fortune = 10
        
        return fortune, {
            'fortune_number': fortune,
            'chinese_zodiac': animal,
            'chinese_zodiac_num': animal_num,
            'month_num': month_num,
            'week_num': week_num,
        }

    def color_fortune_match(self, date_a, date_b):
        """守护色缘分匹配"""
        prof_a = self.get_day_profile(date_a)
        prof_b = self.get_day_profile(date_b)
        if not prof_a or not prof_b:
            return None
        
        color_a = prof_a.get('color', {}).get('cn', '')
        color_b = prof_b.get('color', {}).get('cn', '')
        color_a_en = prof_a.get('color', {}).get('en', '')
        color_b_en = prof_b.get('color', {}).get('en', '')
        
        # 暖色/冷色分类
        warm = {'红','黄','橙','粉'}
        cool = {'绿','蓝','紫','青'}
        color_type_a = 'warm' if color_a in warm else ('cool' if color_a in cool else 'other')
        color_type_b = 'warm' if color_b in warm else ('cool' if color_b in cool else 'other')
        
        # 匹配规则
        color_pair = tuple(sorted([color_a, color_b]))
        match_rules = {
            ('红', '黄'): {'score': 90, 'desc': '暖色系天生暧昧'},
            ('红', '粉'): {'score': 88, 'desc': '热情撞热情'},
            ('黄', '绿'): {'score': 65, 'desc': '春意盎然'},
            ('黄', '橙'): {'score': 85, 'desc': '阳光组合'},
            ('绿', '蓝'): {'score': 75, 'desc': '清新自然'},
            ('蓝', '紫'): {'score': 80, 'desc': '梦幻组合'},
            ('红', '绿'): {'score': 55, 'desc': '圣诞冲突'},
            ('粉', '紫'): {'score': 70, 'desc': '梦幻浪漫'},
        }
        
        if color_a == color_b:
            score = 95
            desc = '灵魂同色'
        elif color_pair in match_rules:
            rule = match_rules[color_pair]
            score = rule['score']
            desc = rule['desc']
        else:
            score = 60
            desc = '各有特色'
        
        return {
            'color_a': color_a,
            'color_b': color_b,
            'color_a_en': color_a_en,
            'color_b_en': color_b_en,
            'color_type_a': color_type_a,
            'color_type_b': color_type_b,
            'score': score,
            'desc': desc,
            'profile_a': prof_a,
            'profile_b': prof_b,
        }


# ═══════════════════════════════════════════════════════════
# 偶像搜索
# ═══════════════════════════════════════════════════════════

class IdolSearch:
    def __init__(self, conn):
        self.conn = conn

    def search(self, name, region=None):
        with self.conn.cursor() as cur:
            variants = list(set([name, _cc_s2t.convert(name), _cc_t2s.convert(name)]))
            conditions = []
            params = []
            for v in variants:
                conditions.append("(name LIKE %s OR name_local LIKE %s OR real_name LIKE %s OR group_name LIKE %s)")
                params.extend([f'%{v}%'] * 4)
            sql = "SELECT * FROM idols WHERE (" + " OR ".join(conditions) + ")"
            if region:
                sql += " AND region=%s"
                params.append(region)
            sql += " LIMIT 20"
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def random_idol(self, region=None):
        with self.conn.cursor() as cur:
            sql = "SELECT * FROM idols"
            params = []
            if region:
                sql += " WHERE region=%s"
                params.append(region)
            sql += " ORDER BY RAND() LIMIT 1"
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


# ═══════════════════════════════════════════════════════════
# DeepSeek解读生成函数（11个功能模块各自的system prompt）
# ═══════════════════════════════════════════════════════════

# ── 通用: 塔罗牌关键词解释 ──

def _llm_keywords_explain(card_name, keywords, is_reversed, meaning=''):
    """为每张牌的关键词生成中文解释 + meaning翻译"""
    if not keywords:
        return [], ''
    kw_text = ', '.join(keywords[:6])
    position = '逆位' if is_reversed else '正位'
    sys_msg = f'你是塔罗牌解读专家。为塔罗牌"{card_name}"({position})的关键词生成简短解释。回复JSON格式:{{"keywords":[{{"word":"词","explain":"一句话解释"}}]}}。纯JSON不要markdown。'
    user_msg = f'关键词: {kw_text}\n原义: {meaning[:200]}'
    text = _llm_call(sys_msg, user_msg, max_tokens=800)
    kw_details = []
    try:
        if text:
            # 去掉可能的markdown包裹
            text = text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            data = json.loads(text)
            kw_details = data.get('keywords', [])[:6]
    except:
        kw_details = [{'word': kw, 'explain': kw} for kw in keywords[:6]]

    # meaning翻译
    meaning_cn = ''
    if meaning:
        m_text = _llm_call(
            '你是塔罗牌翻译专家。将以下英文塔罗牌含义翻译为优美的中文。只输出翻译结果，不要其他内容。',
            meaning[:300],
            max_tokens=500,
        )
        meaning_cn = m_text.strip() if m_text else ''

    return kw_details, meaning_cn


# ── 5个塔罗功能的解读 ──

def _parse_structured_from_llm(text):
    import re as _re
    m = _re.search(r'```json\s*\n?(.*?)\n?```', text, _re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    for i in range(len(text)-1, -1, -1):
        if text[i] == '{':
            try: return json.loads(text[i:])
            except: continue
    return None


def generate_tarot_reading(spread_type, cards, idol_name, user_zodiac, question=''):
    """生成塔罗牌阵解读文本"""
    sp = TarotReader.SPREADS.get(spread_type, TarotReader.SPREADS['daily'])
    card_text = '\n'.join([
        f"- 位置: {c.get('position', {}).get('name', '?')} | 牌: {c.get('name_cn', c.get('name', '?'))} | {'逆位' if c.get('reversed') else '正位'} | 元素: {c.get('element', '')} | 对应星座: {c.get('astrology', '')} | 关键词: {', '.join(c.get('keywords', []))} | 含义: {c.get('meaning', '')[:150]}"
        for c in cards
    ])
    idol_info = f"偶像: {idol_name}" if idol_name else ""
    zodiac_info = f"粉丝星座: {user_zodiac}" if user_zodiac else ""
    q_info = f"粉丝的问题: {question}" if question else ""
    user_msg = f"{card_text}\n{idol_info}\n{zodiac_info}\n{q_info}"
    # 质量约束追加到system prompt后
    quality_constraint = ("\n重要：解读必须严格基于牌面关键词和位置含义，不得编造牌面未暗示的内容。\n" + FANDOM_STYLE
    + chr(10) + "解读完成后，用代码块输出结构化数据："
    + chr(10) + '{"summary": "一句话总结", "cards": [{"position": "位置名", "card": "牌名", "interpretation": "解读要点"}], "advice": "综合建议", "keywords": ["关键词"]}'
    + "\n\n反巴纳姆约束(必须遵守):\n"
    + "1.每张牌解读必须引用该牌具体关键词,禁止泛泛而谈\n"
    + "2.行动建议必须具体可执行,如本周三前完成XX,不能说保持积极心态\n"
    + "3.时间预测限定范围(3天内/本周/7月中旬),不能说不久的将来\n"
    + "4.禁止万能话术:你是有魅力的人/你最近经历不少/命运会给你答案\n"
    + "5.牌面信息不足时直接说建议补充问题后重新占卜,不要编造\n"
    )
    return _llm_call(sp['system'] + quality_constraint, user_msg, max_tokens=2500)


def generate_tarot_daily(cards, idol_name, question=''):
    return generate_tarot_reading('daily', cards, idol_name, '', question)

def generate_tarot_three(cards, idol_name, user_zodiac, question=''):
    return generate_tarot_reading('three', cards, idol_name, user_zodiac, question)

def generate_tarot_relationship(cards, idol_name, user_zodiac, question=''):
    return generate_tarot_reading('relationship', cards, idol_name, user_zodiac, question)

def generate_tarot_celtic(cards, idol_name, user_zodiac, question=''):
    return generate_tarot_reading('celtic', cards, idol_name, user_zodiac, question)

def generate_tarot_hexagram(cards, idol_name, user_zodiac, question=''):
    return generate_tarot_reading('hexagram', cards, idol_name, user_zodiac, question)


# ── 4个雷诺曼功能的解读 ──

def generate_lenormand_reading(spread_type, cards, idol_name, question='', conn=None):
    sp = LenormandReader.SPREADS.get(spread_type, LenormandReader.SPREADS['daily'])
    # 雷诺曼牌组合词典（高频组合→含义，给DeepSeek参考）
    # P2-4: DB combo lookup
    db_combos = dict()
    if conn:
        try:
            with conn.cursor() as cur:
                card_names = [c.get('name', '') for c in cards]
                if len(card_names) >= 2:
                    ph = ','.join(['%s'] * len(card_names))
                    cur.execute(f"SELECT card1_name, card2_name, meaning_cn FROM lenormand_combinations WHERE card1_name IN ({ph}) AND card2_name IN ({ph})", card_names + card_names)
                    for row in cur.fetchall():
                        n1, n2 = row['card1_name'], row['card2_name']
                        if n1 in card_names and n2 in card_names:
                            db_combos[(n1, n2)] = row['meaning_cn']
        except Exception:
            pass
    COMBINATIONS = {
        '骑手+心': '爱情消息到来', '心+戒指': '订婚/婚姻承诺', '心+百合': '长久的爱情',
        '骑手+信件': '好消息送达', '信件+心': '情书/表白消息', '鸟+信件': '电话/通讯',
        '蛇+戒指': '复杂的关系/合同纠纷', '棺材+信件': '坏消息/通知结束',
        '镰刀+心': '突然的心碎/关系断裂', '太阳+心': '幸福的爱情', '月亮+心': '浪漫的情感',
        '鱼+太阳': '商业成功', '钥匙+鱼': '财富的关键机会', '船+鱼': '海外财富',
        '树+太阳': '健康恢复/活力', '树+棺材': '健康问题', '狗+心': '忠诚的友谊/爱情',
        '熊+鱼': '大笔财富', '星星+太阳': '巨大的成功', '鹳+孩子': '新生命的到来',
        '钥匙+太阳': '突破性成功', '高塔+云': '权威受损', '十字架+心': '命运的爱情考验',
        '男人+心': '男性对爱情的看法', '女人+心': '女性对爱情的看法',
        '男人+女人': '问卜者的关系状态', '戒指+男人': '男性的承诺',
        '花束+女人': '女性收到礼物', '花束+心': '浪漫惊喜',
        '孩子+船': '远行的新开始', '十字路口+船': '旅行中的选择',
        '山+镰刀': '突然的阻碍解除', '锚+太阳': '稳定且成功',
    }
    name_map = {c.get('name', ''): c.get('name_cn', c.get('name', '')) for c in cards}
    if db_combos:
        for (n1, n2), meaning in db_combos.items():
            cn1 = name_map.get(n1, n1)
            cn2 = name_map.get(n2, n2)
            COMBINATIONS[cn1 + '+' + cn2] = meaning
    combo_text = '牌组合参考:\n' + '\n'.join(f'  {k} → {v}' for k, v in COMBINATIONS.items())
    card_text = '\n'.join([
        f"- 位置: {c.get('position', {}).get('name', '?')}({c.get('position', {}).get('meaning', '')}) | 牌: {c.get('name_cn', c.get('name', '?'))}{c.get('emoji', '')}\n  通用: {c.get('meaning_general_cn', c.get('meaning_general', ''))}\n  感情: {c.get('meaning_love_cn', c.get('meaning_love', ''))}\n  事业: {c.get('meaning_career_cn', c.get('meaning_career', ''))}\n  关键词: {', '.join(c.get('keywords_cn', c.get('keywords', [])))}"
        for c in cards  # 传全部36张牌
    ])
    idol_info = f"偶像: {idol_name}" if idol_name else ""
    q_info = f"粉丝的问题: {question}" if question else ""
    return _llm_call(sp['system'], f"{card_text}\n\n{combo_text}\n\n{idol_info}\n{q_info}", max_tokens=4000)


# ── 2个泰式功能的解读 ──

def generate_thai_profile(profile, idol_name=''):
    """泰国命理个人档案解读"""
    if not profile:
        return ''
    gender_text = f"问卜者性别: {'女' if getattr(self, '_user_gender', None) == 0 else '男' if getattr(self, '_user_gender', None) == 1 else '未知'}"
    sys_msg = '你是一位既懂泰国命理又深谙追星文化的解读师，像知心姐姐给粉丝分析缘分一样温暖。回复纯中文，分4个方面解读。注意使用正确的性别称呼(她/他)。'
    text = f"""{gender_text}
命理档案:
- 出生日: {profile.get('day_name_cn', '')}
- 守护行星: {profile.get('planet', {}).get('cn', '')}
- 幸运色: {profile.get('color', {}).get('cn', '')}
- 元素: {profile.get('element', {}).get('cn', '')}
- 幸运方位: {profile.get('direction', {}).get('cn', '')}
- 守护神: {profile.get('deity', {}).get('cn', '')}
- 性格描述: {profile.get('description', '')}"""
    if idol_name:
        text += f"\n- 偶像: {idol_name}"
    return _llm_call(sys_msg, text, max_tokens=1500)

def generate_thai_match(compat, idol_name=''):
    """泰国命理缘分匹配解读"""
    if not compat:
        return ''
    gender_text = f"问卜者性别: {'女' if getattr(self, '_user_gender', None) == 0 else '男' if getattr(self, '_user_gender', None) == 1 else '未知'}"
    sys_msg = '你是一位超会看CP的泰国命理大师，缘分匹配解读像闺蜜讨论配不配一样自然。回复纯中文，分6个维度分析，最后总结。注意使用正确的性别称呼(她/他)。'
    prof_a = compat.get('profile_a', {})
    prof_b = compat.get('profile_b', {})
    dim_text = '\n'.join([f"- {d['name']}: {d.get('desc', '')}" for d in compat.get('dimensions', [])])
    text = f"""{gender_text}
匹配评分: {compat.get('score', 0)}/100 ({compat.get('level', '')})

你的命理:
- 星期: {prof_a.get('day_name_cn', '')} | 守护行星: {prof_a.get('planet', {}).get('cn', '')} | 元素: {prof_a.get('element', {}).get('cn', '')}

偶像命理:
- 星期: {prof_b.get('day_name_cn', '')} | 守护行星: {prof_b.get('planet', {}).get('cn', '')} | 元素: {prof_b.get('element', {}).get('cn', '')}

维度分析:
{dim_text}"""
    if idol_name:
        text += f"\n偶像: {idol_name}"
    return _llm_call(sys_msg, text, max_tokens=2000)


def generate_thai_fortune(fortune_data, idol_name=''):
    """运命数字解读"""
    if not fortune_data:
        return ''
    sys_msg = FANDOM_STYLE + '你是一位精通道家数字命理和泰国运命数字的解读师。根据运命数字分析命运特质，像闺蜜聊天一样自然亲切。回复纯中文，2-3段。'
    num = fortune_data.get('fortune_number', 0)
    meaning = FORTUNE_MEANINGS.get(num, '')
    text = f"""运命数字: {num}
数字含义: {meaning}
生肖: {fortune_data.get('chinese_zodiac', '')}(第{fortune_data.get('chinese_zodiac_num', '')}数)
月份参数: {fortune_data.get('month_num', '')}
星期参数: {fortune_data.get('week_num', '')}"""
    if idol_name:
        text += f"\n偶像: {idol_name}"
    return _llm_call(sys_msg, text, max_tokens=1500)

def generate_thai_fortune_match(match_data, idol_name=''):
    """运命数字交叉匹配解读"""
    if not match_data:
        return ''
    sys_msg = FANDOM_STYLE + '你是一位精通数字命理匹配的大师。根据两人运命数字的交叉关系分析缘分，像闺蜜讨论CP一样自然。回复纯中文，分3段分析。'
    fa = match_data.get('fortune_a', {})
    fb = match_data.get('fortune_b', {})
    text = f"""运数匹配分析:
你({match_data.get('name_a', '你')}):
- 运命数字: {fa.get('fortune_number', '')}
- 含义: {fa.get('meaning', '')}
- 生肖: {fa.get('chinese_zodiac', '')}

偶像({match_data.get('name_b', '偶像')}):
- 运命数字: {fb.get('fortune_number', '')}
- 含义: {fb.get('meaning', '')}
- 生肖: {fb.get('chinese_zodiac', '')}

交叉评分: {match_data.get('score', 0)}/100
匹配关系: {match_data.get('match_desc', '')}"""
    if idol_name:
        text += f"\n偶像: {idol_name}"
    return _llm_call(sys_msg, text, max_tokens=2000)

def generate_thai_color_match(match_data, idol_name=''):
    """守护色缘分解读"""
    if not match_data:
        return ''
    sys_msg = FANDOM_STYLE + '你是一位精通色彩命理和泰国守护色的解读师。根据两人守护色的缘分关系分析，像闺蜜讨论配不配一样自然亲切。回复纯中文，分3段分析。'
    text = f"""守护色缘分分析:
你({match_data.get('name_a', '你')}):
- 守护色: {match_data.get('color_a', '')}({match_data.get('color_a_en', '')})
- 色系: {'暖色系' if match_data.get('color_type_a')=='warm' else '冷色系'}

偶像({match_data.get('name_b', '偶像')}):
- 守护色: {match_data.get('color_b', '')}({match_data.get('color_b_en', '')})
- 色系: {'暖色系' if match_data.get('color_type_b')=='warm' else '冷色系'}

缘分评分: {match_data.get('score', 0)}/100
色彩关系: {match_data.get('desc', '')}"""
    if idol_name:
        text += f"\n偶像: {idol_name}"
    return _llm_call(sys_msg, text, max_tokens=2000)


# ═══════════════════════════════════════════════════════════
# 统一入口: 11个功能模块
# ═══════════════════════════════════════════════════════════

# 功能定义: func → {spread_type, reader, group, reader_class}
FUNC_MAP = {
    # 塔罗组
    'daily-tarot':       {'group': 'tarot', 'spread': 'daily',       'cost': 2,  'trial': True,  'name_cn': '每日一牌'},
    'tarot-3':           {'group': 'tarot', 'spread': 'three',        'cost': 4,  'trial': True,  'name_cn': '三牌阵'},
    'tarot-relationship':{'group': 'tarot', 'spread': 'relationship', 'cost': 6,  'trial': False, 'name_cn': '关系牌阵'},
    'tarot-celtic':      {'group': 'tarot', 'spread': 'celtic',       'cost': 8,  'trial': False, 'name_cn': '凯尔特十字'},
    'tarot-hexagram':    {'group': 'tarot', 'spread': 'hexagram',     'cost': 8,  'trial': False, 'name_cn': '六芒星牌阵'},
    'tarot-love':     {'group': 'tarot', 'spread': 'love',   'cost': 6,  'trial': False, 'name_cn': '爱情牌阵'},
    'tarot-choice':   {'group': 'tarot', 'spread': 'choice', 'cost': 6,  'trial': False, 'name_cn': '抉择牌阵'},
    'tarot-yesno':    {'group': 'tarot', 'spread': 'yesno',  'cost': 2,  'trial': True,  'name_cn': '是否牌阵'},

    # 雷诺曼组
    'leno-daily':         {'group': 'lenormand', 'spread': 'daily',   'cost': 2,  'trial': True,  'name_cn': '雷诺曼每日'},
    'leno-3':             {'group': 'lenormand', 'spread': 'three',    'cost': 4,  'trial': True,  'name_cn': '雷诺曼三牌'},
    'leno-9':             {'group': 'lenormand', 'spread': 'nine',     'cost': 6,  'trial': False, 'name_cn': '九宫格'},
    'leno-grand':         {'group': 'lenormand', 'spread': 'grand',   'cost': 12, 'trial': False, 'name_cn': '大蓝图'},
    # 泰式组
    'thai-profile':       {'group': 'thai', 'spread': 'profile',      'cost': 4,  'trial': True,  'name_cn': '个人命盘'},
    'thai-match':         {'group': 'thai', 'spread': 'match',        'cost': 4,  'trial': True,  'name_cn': '缘分匹配'},
    'thai-fortune':       {'group': 'thai', 'spread': 'fortune',        'cost': 4,  'trial': True,  'name_cn': '运命数字'},
    'thai-fortune-match': {'group': 'thai', 'spread': 'fortune-match',  'cost': 6,  'trial': True,  'name_cn': '运数匹配'},
    'thai-color-match':   {'group': 'thai', 'spread': 'color-match',    'cost': 4,  'trial': True,  'name_cn': '守护色缘分'},
    # 中式组
    'zodiac-match':       {'group': 'chinese',      'spread': 'zodiac-match',      'cost': 4,  'trial': True,  'name_cn': '属相匹配'},
    'dream':              {'group': 'chinese',      'spread': 'dream',             'cost': 2,  'trial': True,  'name_cn': '周公解梦'},
    'meihua-love':        {'group': 'chinese',      'spread': 'meihua-love',       'cost': 6,  'trial': False, 'name_cn': '梅花感情占卦'},
    'love-match':         {'group': 'chinese',      'spread': 'love-match',        'cost': 4,  'trial': True,  'name_cn': '八字感情匹配'},
    # 星座组
    'constellation-profile':{'group': 'constellation','spread': 'constellation_profile','cost': 1,'trial': True,'name_cn': '个人星盘'},    'constellation-daily':{'group': 'constellation','spread': 'constellation_daily','cost': 1,'trial': True,'name_cn': '今日运势'},    'constellation_match':{'group': 'constellation','spread': 'constellation_match','cost': 2,'trial': True,'name_cn': '星座匹配'},
}


class DivinationEngine:
    """11个功能模块的统一引擎"""

    def __init__(self, conn):
        self.conn = conn
        self.tarot = TarotReader(conn)
        self.lenormand = LenormandReader(conn)
        self.thai = ThaiBirthDay(conn)
        self.idols = IdolSearch(conn)

    def execute(self, func, idol_name=None, user_birth=None, target_birth=None, user_gender=None, question='', lang=None):
        """
        执行占卜功能
        func: 功能代码 (daily-tarot, tarot-3, etc.)
        idol_name: 偶像名称
        user_birth: 用户生日
        question: 用户问题
        """
        info = FUNC_MAP.get(func)
        if not info:
            return {'error': f'未知功能: {func}'}

        self._user_gender = user_gender
        result = {
            'func': func,
            'func_name': info['name_cn'],
            'group': info['group'],
            'cost': info['cost'],
        }

        # 查偶像
        idol = None
        idol_zodiac = ''
        if idol_name:
            idols = self.idols.search(idol_name)
            if idols:
                idol = idols[0]
                result['idol'] = {
                    'name': idol.get('name', ''),
                    'region': idol.get('region', ''),
                    'birth_date': idol.get('birth_date', ''),
                    'zodiac_sign': idol.get('zodiac_sign', ''),
                    'chinese_zodiac': idol.get('chinese_zodiac', ''),
                    'group_name': idol.get('group_name', ''),
                }
                if idol.get('birth_date'):
                    p = parse_birth_date(idol['birth_date'])
                    if p:
                        idol_zodiac = get_zodiac_sign(p[1], p[2])

        # 用户星座
        user_zodiac = ''
        if user_birth:
            p = parse_birth_date(user_birth)
            if p:
                user_zodiac = get_zodiac_sign(p[1], p[2])
                result['user'] = {
                    'birth_date': user_birth,
                    'zodiac_sign': user_zodiac,
                    'chinese_zodiac': get_chinese_zodiac(p[0]),
                }

        group = info['group']
        spread = info['spread']

        # ── 塔罗组 ──
        if group == 'tarot':
            reading = self.tarot.read_spread(spread)
            if not reading:
                return {'error': '牌阵数据异常'}
            result['tarot'] = reading

            # DeepSeek并行: 解读 + 关键词解释
            cards = reading.get('cards', [])
            # 大牌阵(>=7)串行跑避免DeepSeek并发超限，小牌阵并行
            big_spread = len(cards) >= 7
            if big_spread:
                # 大牌阵：只跑主解读，关键词解释跳过（牌太多串行太慢）
                try:
                    raw_interp = generate_tarot_reading(spread, cards, idol_name or '', user_zodiac, question)
                    result['tarot']['interpretation'] = raw_interp
                    structured = _parse_structured_from_llm(raw_interp)
                    if structured:
                        result['tarot']['structured'] = structured
                except Exception:
                    pass
            else:
                # 小牌阵：并行跑
                futures = {}
                kw_futures = []
                with ThreadPoolExecutor(max_workers=len(cards)+1) as pool:
                    f = pool.submit(generate_tarot_reading, spread, cards, idol_name or '', user_zodiac, question)
                    futures[f] = 'interpretation'
                    for ci, card in enumerate(cards):
                        kws = card.get('keywords', [])[:6]
                        if kws:
                            kf = pool.submit(_llm_keywords_explain,
                                card.get('name_cn', card.get('name', '')),
                                kws, card.get('reversed', False), card.get('meaning', ''))
                            kw_futures.append((ci, kf))

                    # 收解读
                    try:
                        _first = list(futures.keys())[0]
                        _interp_raw = _first.result(timeout=60)
                        result['tarot']['interpretation'] = _interp_raw
                        _struct = _parse_structured_from_llm(_interp_raw)
                        if _struct:
                            result['tarot']['structured'] = _struct
                    except Exception:
                        pass

                    # 收关键词
                    for ci, kf in kw_futures:
                        try:
                            kw_details, meaning_cn = kf.result(timeout=15)
                            if ci < len(cards):
                                if kw_details:
                                    cards[ci]['keywords_detail'] = kw_details
                                if meaning_cn:
                                    cards[ci]['meaning'] = meaning_cn
                        except Exception:
                            pass

        # ── 雷诺曼组 ──
        elif group == 'lenormand':
            reading = self.lenormand.read_spread(spread)
            if not reading:
                return {'error': '牌阵数据异常'}
            result['lenormand'] = reading

            # DeepSeek解读
            cards = reading.get('cards', [])
            try:
                interp = generate_lenormand_reading(spread, cards, idol_name or '', question, conn=self.conn)
                if interp:
                    result['lenormand']['interpretation'] = interp
            except Exception:
                pass

        # ── 泰式组 ──
        elif group == 'thai':
            if spread == 'profile':
                # 个人命盘 — 用偶像或用户生日
                target_date = user_birth
                target_name = ''
                if idol and idol.get('birth_date'):
                    target_date = idol['birth_date']
                    target_name = idol.get('name', '')

                # 如果两个都有，都算
                profiles = {}
                if idol and idol.get('birth_date'):
                    prof = self.thai.get_day_profile(idol['birth_date'])
                    if prof:
                        profiles['idol'] = prof
                if user_birth:
                    prof = self.thai.get_day_profile(user_birth)
                    if prof:
                        profiles['user'] = prof

                result['thai'] = {'profiles': profiles}

                # DeepSeek解读
                with ThreadPoolExecutor(max_workers=len(profiles)) as pool:
                    futures = {}
                    if 'idol' in profiles:
                        f = pool.submit(generate_thai_profile, profiles['idol'], idol_name or '')
                        futures[f] = 'idol_interp'
                    if 'user' in profiles:
                        f = pool.submit(generate_thai_profile, profiles['user'], '')
                        futures[f] = 'user_interp'
                    for f in as_completed(futures, timeout=45):
                        try:
                            text = f.result()
                            key = futures[f]
                            if text and 'thai' in result:
                                if key == 'idol_interp':
                                    result['thai']['idol_interpretation'] = text
                                elif key == 'user_interp':
                                    result['thai']['user_interpretation'] = text
                        except Exception:
                            pass

            elif spread == 'match':
                # 缘分匹配 — 需要偶像和用户生日
                if not idol or not idol.get('birth_date') or not user_birth:
                    return {'error': '缘分匹配需要偶像和你的生日信息'}
                compat = self.thai.compatibility(user_birth, idol['birth_date'])
                if not compat:
                    return {'error': '无法计算缘分匹配'}
                result['thai'] = compat

                # DeepSeek解读
                try:
                    interp = generate_thai_match(compat, idol_name or '')
                    if interp:
                        result['thai']['interpretation'] = interp
                except Exception:
                    pass

            elif spread == 'fortune':
                # 运命数字
                fortunes = {}
                if user_birth:
                    fn, fd = self.thai.fortune_number(user_birth)
                    if fd:
                        fd['meaning'] = FORTUNE_MEANINGS.get(fn, '')
                        fortunes['user'] = fd
                if idol and idol.get('birth_date'):
                    fn, fd = self.thai.fortune_number(idol['birth_date'])
                    if fd:
                        fd['meaning'] = FORTUNE_MEANINGS.get(fn, '')
                        fortunes['idol'] = fd

                if not fortunes:
                    return {'error': '无法计算运命数字，请提供生日信息'}

                result['thai'] = {'fortunes': fortunes}

                # DeepSeek解读
                with ThreadPoolExecutor(max_workers=len(fortunes)) as pool:
                    futures = {}
                    if 'idol' in fortunes:
                        f = pool.submit(generate_thai_fortune, fortunes['idol'], idol_name or '')
                        futures[f] = 'idol_interp'
                    if 'user' in fortunes:
                        f = pool.submit(generate_thai_fortune, fortunes['user'], '')
                        futures[f] = 'user_interp'
                    for f in as_completed(futures, timeout=45):
                        try:
                            text = f.result()
                            key = futures[f]
                            if text and 'thai' in result:
                                if key == 'idol_interp':
                                    result['thai']['idol_interpretation'] = text
                                elif key == 'user_interp':
                                    result['thai']['user_interpretation'] = text
                        except Exception:
                            pass

            elif spread == 'fortune-match':
                # 运命数字匹配 — 需要偶像和用户生日
                if not idol or not idol.get('birth_date') or not user_birth:
                    return {'error': '运数匹配需要偶像和你的生日信息'}
                fn_a, fd_a = self.thai.fortune_number(user_birth)
                fn_b, fd_b = self.thai.fortune_number(idol['birth_date'])
                if fn_a is None or fn_b is None:
                    return {'error': '无法计算运命数字'}
                fd_a['meaning'] = FORTUNE_MEANINGS.get(fn_a, '')
                fd_b['meaning'] = FORTUNE_MEANINGS.get(fn_b, '')

                # 交叉匹配评分
                a, b = fn_a, fn_b
                if a == b:
                    score, match_desc = 100, '同频共振'
                elif a + b == 10:
                    score, match_desc = 90, '互补圆满'
                elif a + b == 5 or a + b == 15:
                    score, match_desc = 85, '和谐搭配'
                elif (a % 2) == (b % 2):
                    score, match_desc = 70, '频率相近'
                else:
                    score, match_desc = 55, '互补学习'

                match_data = {
                    'name_a': '你',
                    'name_b': idol.get('name', '偶像'),
                    'fortune_a': fd_a,
                    'fortune_b': fd_b,
                    'score': score,
                    'match_desc': match_desc,
                }
                result['thai'] = match_data

                # DeepSeek解读
                try:
                    interp = generate_thai_fortune_match(match_data, idol_name or '')
                    if interp:
                        result['thai']['interpretation'] = interp
                except Exception:
                    pass

            elif spread == 'color-match':
                # 守护色缘分 — 需要偶像和用户生日
                if not idol or not idol.get('birth_date') or not user_birth:
                    return {'error': '守护色缘分需要偶像和你的生日信息'}
                color_match = self.thai.color_fortune_match(user_birth, idol['birth_date'])
                if not color_match:
                    return {'error': '无法计算守护色缘分'}
                color_match['name_a'] = '你'
                color_match['name_b'] = idol.get('name', '偶像')
                result['thai'] = color_match

                # DeepSeek解读
                try:
                    interp = generate_thai_color_match(color_match, idol_name or '')
                    if interp:
                        result['thai']['interpretation'] = interp
                except Exception:
                    pass

        # ── 中式组 ──
        elif group == 'chinese':
            func_id = func
            birth_info = {}
            if user_birth:
                parts = user_birth.split('-')
                if len(parts) == 3:
                    birth_info = {'birth_year': int(parts[0]), 'birth_month': int(parts[1]), 'birth_day': int(parts[2])}
            if func_id == 'zodiac-match':
                target_info = {}
                if target_birth:
                    tp = target_birth.split('-')
                    if len(tp) == 3:
                        target_info = {'birth_year': int(tp[0]), 'birth_month': int(tp[1]), 'birth_day': int(tp[2])}
                result['chinese'] = divine_shengxiao(birth_info, question, target_info)
            elif func_id == 'dream':
                result['chinese'] = divine_dream(question)
            elif func_id == 'meihua-love':
                target_info = {}
                if target_birth:
                    tp = target_birth.split('-')
                    if len(tp) == 3:
                        target_info = {'birth_year': int(tp[0]), 'birth_month': int(tp[1]), 'birth_day': int(tp[2])}
                result['chinese'] = divine_meihua_love(birth_info, question, target_info)
            elif func_id == 'love-match':
                target_info = {}
                if target_birth:
                    tp = target_birth.split('-')
                    if len(tp) == 3:
                        target_info = {'birth_year': int(tp[0]), 'birth_month': int(tp[1]), 'birth_day': int(tp[2])}
                result['chinese'] = divine_love_match(birth_info, question, target_info)
        # ── 星座组 ──
        elif group == 'constellation':
            func_id = func
            birth_info = {}
            if user_birth:
                parts = user_birth.split('-')
                if len(parts) == 3:
                    birth_info = {'birth_year': int(parts[0]), 'birth_month': int(parts[1]), 'birth_day': int(parts[2])}
            if func_id == 'constellation-profile':
                result['chinese'] = divine_constellation_profile(birth_info, question)
            elif func_id == 'constellation-daily':
                result['chinese'] = divine_constellation_daily(birth_info, question)
            elif func_id == 'constellation_match':
                result['chinese'] = divine_constellation_match(birth_info, question)
        return result

    def func_list(self):
        """返回所有功能模块列表"""
        result = []
        for func, info in FUNC_MAP.items():
            sp = None
            if info['group'] == 'tarot':
                sp = self.tarot.SPREADS.get(info['spread'])
            elif info['group'] == 'lenormand':
                sp = self.lenormand.SPREADS.get(info['spread'])
            result.append({
                'func': func,
                'name_cn': info['name_cn'],
                'group': info['group'],
                'cost': info['cost'],
                'trial': info['trial'],
                'card_count': sp['count'] if sp else 0,
            })
        return result

# ═══════════════════════════════════════════════════════════
# 八字/中式常量与辅助函数
# ═══════════════════════════════════════════════════════════
TG = list('甲乙丙丁戊己庚辛壬癸')
DZ = list('子丑寅卯辰巳午未申酉戌亥')
WX = list('木木火火土土金金水水')

def wx_relation(a, b):
    rels = {'木木':'比和','火火':'比和','土土':'比和','金金':'比和','水水':'比和',
        '木火':'我生','火土':'我生','土金':'我生','金水':'我生','水木':'我生',
        '木水':'生我','火木':'生我','土火':'生我','金土':'生我','水金':'生我',
        '木土':'我克','火金':'我克','土水':'我克','金木':'我克','水火':'我克',
        '木金':'克我','火水':'克我','土木':'克我','金火':'克我','水土':'克我'}
    return rels.get(a+b, '比和')

# ───────────────────────────────────────────────────────────
# 地理五行（以中原洛阳为原点的方位五行，与经纬度无关）
# 东方木 / 南方火 / 中央土 / 西方金 / 北方水
# ───────────────────────────────────────────────────────────
PROVINCE_WX = {
    # 东方·木
    '山东': '木', '江苏': '木', '上海': '木', '浙江': '木', '安徽': '木',
    '福建': '木', '台湾': '木',
    # 南方·火
    '广东': '火', '广西': '火', '海南': '火', '云南': '火', '贵州': '火',
    '湖南': '火', '江西': '火', '香港': '火', '澳门': '火',
    # 中央·土
    '河南': '土', '湖北': '土',
    # 西方·金
    '四川': '金', '重庆': '金', '陕西': '金', '甘肃': '金', '青海': '金',
    '宁夏': '金', '新疆': '金', '西藏': '金',
    # 北方·水
    '河北': '水', '山西': '水', '北京': '水', '天津': '水', '辽宁': '水',
    '吉林': '水', '黑龙江': '水', '内蒙古': '水',
}

COUNTRY_WX = {
    # 东方·木
    '日本': '木', '韩国': '木', '朝鲜': '木',
    # 南方·火
    '泰国': '火', '越南': '火', '菲律宾': '火', '印尼': '火', '印度尼西亚': '火',
    '马来西亚': '火', '新加坡': '火', '印度': '火', '缅甸': '火', '柬埔寨': '火',
    '老挝': '火', '文莱': '火', '东帝汶': '火',
    # 西方·金
    '美国': '金', '英国': '金', '法国': '金', '德国': '金', '意大利': '金',
    '西班牙': '金', '葡萄牙': '金', '荷兰': '金', '比利时': '金', '瑞士': '金',
    '奥地利': '金', '瑞典': '金', '挪威': '金', '丹麦': '金', '芬兰': '金',
    '波兰': '金', '乌克兰': '金', '俄罗斯': '金', '土耳其': '金', '希腊': '金',
    '爱尔兰': '金', '冰岛': '金', '加拿大': '金', '墨西哥': '金', '巴西': '金',
    '阿根廷': '金', '智利': '金', '哥伦比亚': '金', '秘鲁': '金', '澳大利亚': '金',
    '新西兰': '金', '南非': '金', '埃及': '金', '摩洛哥': '金', '以色列': '金',
    '沙特': '金', '阿联酋': '金', '伊朗': '金', '伊拉克': '金',
    # 北方·水
    '蒙古': '水', '哈萨克斯坦': '水', '乌兹别克斯坦': '水',
}

def geo_to_wx(place):
    """从出生地/所在地字符串解析方位五行。
    输入示例：'广东省深圳市' / '广东深圳' / '日本东京' / '泰国曼谷' / '北京'
    返回：('木'|'火'|'土'|'金'|'水'|None, 匹配到的键)
    """
    if not place:
        return None, None
    s = str(place).strip().replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '')
    # 先精确前缀匹配（避免"内蒙古"误匹配到"蒙古"）
    for table in (PROVINCE_WX, COUNTRY_WX):
        for k, v in table.items():
            if s.startswith(k):
                return v, k
    # 再做 substring 匹配（同样省份优先）
    for table in (PROVINCE_WX, COUNTRY_WX):
        for k, v in table.items():
            if k in s:
                return v, k
    return None, None

def get_bazi(year, month, day, hour=12):
    import sxtwl
    try:
        d = sxtwl.fromSolar(year, month, day)
        ygz, mgz, dgz = d.getYearGZ(), d.getMonthGZ(), d.getDayGZ()
        hgz = d.getHourGZ(hour)
        return TG[ygz.tg], DZ[ygz.dz], TG[mgz.tg], DZ[mgz.dz], TG[dgz.tg], DZ[dgz.dz], TG[hgz.tg], DZ[hgz.dz]
    except Exception:
        tg_y = TG[(year-4) % 10]
        dz_y = DZ[(year-4) % 12]
        tg_m = TG[(year*1 + month) % 10]
        dz_m = DZ[(month + 1) % 12]
        tg_d = TG[(year + month + day) % 10]
        dz_d = DZ[(day + 1) % 12]
        return tg_y, dz_y, tg_m, dz_m, tg_d

def get_today_bazi():
    import datetime
    t = datetime.datetime.now()
    return get_bazi(t.year, t.month, t.day, t.hour)

# ═══════════════════════════════════════════════════════════
# 属相匹配
# ═══════════════════════════════════════════════════════════
ZODIAC_ANIMALS = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
ZODIAC_LIU_HE = {0:1,1:0,2:11,11:2,3:10,10:3,4:9,9:4,5:8,8:5,6:7,7:6}
ZODIAC_SANHE = [[0,4,8],[3,7,11],[6,10,2],[9,1,5]]
ZODIAC_LIU_CHONG = {0:6,6:0,1:7,7:1,2:8,8:2,3:9,9:3,4:10,10:4,5:11,11:5}
ZODIAC_LIU_HAI = {0:11,11:0,1:10,10:1,2:9,9:2,3:8,8:3,4:7,7:4,5:6,6:5}
ZODIAC_SANXING = {'寅巳申':[2,5,8],'丑戌未':[1,4,7],'子卯午':[0,3,6],'辰午酉亥':[]}
ZODIAC_ZIXING = {0,3,6,9}

def divine_shengxiao(birth_info, question='', target_info=None):
    _y = birth_info.get('birth_year', 0)
    if not _y or _y < 1900: return {'score':0, 'summary':'请先在个人资料中填写您的出生日期，才能进行属相匹配～'}
    my_idx = (_y - 4) % 12
    if my_idx < 0 or my_idx > 11: return {'score':0, 'summary':'需要您的出生年份'}
    my_animal = ZODIAC_ANIMALS[my_idx]
    t_idx = None
    if target_info and target_info.get('birth_year'):
        t_idx = (target_info['birth_year'] - 4) % 12
    if t_idx is None:
        q = (question or '').strip()
        for i, a in enumerate(ZODIAC_ANIMALS):
            if a in q: t_idx = i; break
    if t_idx is None:
        return {'score':0, 'summary':'您的属相是%s。请告诉我对方的属相或出生日期。' % my_animal, 'sections':[{'title':'您的属相','content':'属%s' % my_animal}]}
    t_animal = ZODIAC_ANIMALS[t_idx]

    # ── 五行属性 ──
    WX_MAP = {0:'水',1:'土',2:'木',3:'木',4:'土',5:'火',6:'火',7:'土',8:'金',9:'金',10:'土',11:'水'}
    my_wx = WX_MAP[my_idx]
    t_wx = WX_MAP[t_idx]

    # ── 基础评分 ──
    score = 50
    relations = []

    # 六合
    if ZODIAC_LIU_HE.get(my_idx) == t_idx:
        score += 20; relations.append(('六合','吉',
            '子丑合土、寅亥合木、卯戌合火、辰酉合金、巳申合水、午未合火。'
            '六合为最高亲和力，两属相天生互补，相处自然融洽，彼此默契度高。'))
    # 三合
    sanhe_name = None
    for g in ZODIAC_SANHE:
        if my_idx in g and t_idx in g:
            sanhe_name = '、'.join(ZODIAC_ANIMALS[i] for i in g)
            score += 15; relations.append(('三合(%s)' % sanhe_name,'吉',
                '三合为三局合力，气场共振。属%s、%s、%s三合为一局，你们同属此局，志趣相投，合作运强。' % tuple(ZODIAC_ANIMALS[i] for i in g)))
            break
    # 六冲
    if ZODIAC_LIU_CHONG.get(my_idx) == t_idx:
        score -= 15; relations.append(('六冲','凶',
            '子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲。'
            '六冲为正面碰撞，性格上容易产生分歧，需要更多包容和理解。'))
    # 六害
    if ZODIAC_LIU_HAI.get(my_idx) == t_idx:
        score -= 10; relations.append(('六害','凶',
            '子未害、丑午害、寅巳害、卯辰害、申亥害、酉戌害。'
            '六害为暗中损耗，相处时需注意沟通方式，避免误会积累。'))
    # 三刑
    for name, members in ZODIAC_SANXING.items():
        if my_idx in members and t_idx in members:
            score -= 10; relations.append(('三刑(%s)' % name,'凶',
                '%s相刑，性格上可能存在固执碰撞，但若能互相迁就则可化解。' % name))
            break
    # 自刑
    if my_idx in ZODIAC_ZIXING and t_idx == my_idx:
        score -= 8; relations.append(('自刑','凶',
            '同类自刑，两人属相相同且为自刑属相，容易钻牛角尖，需学会换位思考。'))
    # 同属相但非自刑
    if my_idx == t_idx and my_idx not in ZODIAC_ZIXING:
        score += 5; relations.append(('同属相','平',
            '属相相同，性格底色相近，容易理解对方，但也可能缺少互补的火花。'))

    score = max(0, min(100, score))
    if score >= 75: lv = '大吉'
    elif score >= 60: lv = '中吉'
    elif score >= 45: lv = '一般'
    elif score >= 30: lv = '小凶'
    else: lv = '凶'

    # ── 五行关系 ──
    def _wx_desc(a, a_wx, b, b_wx):
        """Generate five-element relationship description."""
        T = {
            ('水','水'):'比和：双方五行同为水，气场对称共鸣，容易理解彼此的内心世界，但需避免过于相似导致的乏味。',
            ('木','木'):'比和：双方同为木性，积极向上，共同成长，关系稳定有活力。',
            ('火','火'):'比和：双方同为火性，热情似火，感情浓烈有激情，注意控制情绪节奏。',
            ('土','土'):'比和：双方同为土性，踏实稳重，感情根基牢固，适合长相厮守。',
            ('金','金'):'比和：双方同为金性，理性果断，做事高效，感情中需多展现柔软面。',
        }
        P = {
            ('水','木'):'水生木：属%s(水)滋养属%s(木)，属%s的灵感滋润着属%s，是互相成就的组合。',
            ('木','火'):'木生火：属%s(木)点燃属%s(火)，热情洋溢的互动中，属%s与属%s的感情不断升温。',
            ('火','土'):'火生土：属%s(火)温暖属%s(土)，属%s的热情给属%s带来安全感，是可靠的伴侣组合。',
            ('土','金'):'土生金：属%s(土)孕育属%s(金)，属%s有耐心包容，属%s务实可靠，互补性极强。',
            ('金','水'):'金生水：属%s(金)生属%s(水)，智慧交融中，属%s的果断配上属%s的灵动柔美。',
            ('木','水'):'水生木：属%s(水)滋养属%s(木)，属%s能激发属%s的灵感，互相成就的组合。',
            ('火','木'):'木生火：属%s(木)点燃属%s(火)，属%s能点燃属%s的热情，让关系充满活力。',
            ('土','火'):'火生土：属%s(火)温暖属%s(土)，属%s的热情让属%s感到安心与稳定。',
            ('金','土'):'土生金：属%s(土)孕育属%s(金)，属%s稳重包容，属%s在关键时刻展现果断。',
            ('水','金'):'金生水：属%s(金)生属%s(水)，属%s理性果断，属%s以智慧与柔软回应。',
            ('水','火'):'水克火：属%s(水)克制属%s(火)，属%s需给属%s足够的空间与自由，避免控制欲过强。',
            ('火','金'):'火克金：属%s(火)克制属%s(金)，属%s的热情与属%s的理性需找到平衡点。',
            ('木','土'):'木克土：属%s(木)克制属%s(土)，属%s的灵活与属%s的稳重需互相尊重。',
            ('土','水'):'土克水：属%s(土)克制属%s(水)，属%s需避免过度约束属%s的自由与灵性。',
            ('金','木'):'金克木：属%s(金)克制属%s(木)，属%s的果断与属%s的温柔交织，需互相包容。',
        }
        if (a_wx, b_wx) in T: return T[(a_wx, b_wx)]
        if (a_wx, b_wx) in P: return P[(a_wx, b_wx)] % (a, b, a, b)
        return '属%s(%s)与属%s(%s)五行关系平和，相处自然互补。' % (a, a_wx, b, b_wx)


    wx_desc = _wx_desc(my_animal, my_wx, t_animal, t_wx)



    # ── 幸运元素 ──
    LUCKY_COLORS = {
        '水':'蓝色、黑色',
        '木':'绿色、青色',
        '火':'红色、紫色',
        '土':'黄色、棕色',
        '金':'白色、金色',
    }
    # 组合幸运色：取双方五行对应的颜色
    combo_colors = set()
    for wx in [my_wx, t_wx]:
        if wx in LUCKY_COLORS:
            for c in LUCKY_COLORS[wx].split('、'):
                combo_colors.add(c)
    lucky_color = '、'.join(sorted(combo_colors)[:4])
    # 相生五行色最旺
    WX_COLORS = {'水':'蓝色','木':'绿色','火':'红色','土':'黄色','金':'白色'}
    LUCKY_DIRS = {'水':'北方','木':'东方','火':'南方','土':'中央','金':'西方'}
    LUCKY_NUMS = {'水':'1、6','木':'3、8','火':'2、7','土':'5、0','金':'4、9'}
    lucky_dir = LUCKY_DIRS.get(my_wx, '东方')
    lucky_num = LUCKY_NUMS.get(my_wx, '3、8')

    # ── 多维度分析 ──
    # 感情运
    love_score = min(100, max(0, score + (10 if '六合' in str(relations) else 0) + (5 if sanhe_name else 0)))
    if love_score >= 75: love_desc = '属%s与属%s在感情方面天然契合，容易产生心动的感觉，恋爱运旺盛。' % (my_animal, t_animal)
    elif love_score >= 55: love_desc = '感情基础良好，需要双方主动经营，多制造浪漫惊喜可以加深感情。'
    elif love_score >= 40: love_desc = '感情路上可能遇到一些波折，但只要彼此真心，困难都是成长的养分。'
    else: love_desc = '感情方面挑战较大，需要更多耐心和包容，建议多沟通、少冲动。'

    # 事业合作
    biz_score = min(100, max(0, score + (5 if my_wx == t_wx else 0)))
    if biz_score >= 70: biz_desc = '合作运极佳！两人搭档可以发挥1+1>2的效果，适合合伙做事。'
    elif biz_score >= 50: biz_desc = '工作中可以互补，各自发挥所长是最佳模式，避免争抢主导权。'
    else: biz_desc = '工作中容易产生分歧，建议明确分工、各司其职，减少交叉决策。'

    # 健康提醒
    wx_health = {
        '水':'注意肾脏、泌尿系统，多喝温水，避免熬夜。',
        '木':'注意肝胆、眼睛，保持充足睡眠，多亲近自然。',
        '火':'注意心脏、血液循环，控制情绪起伏，适当运动。',
        '土':'注意脾胃消化，饮食规律，少食生冷。',
        '金':'注意呼吸系统、皮肤，保持空气流通，多深呼吸。',
    }
    health_desc = '属%s体质偏%s，属%s体质偏%s。两人在一起时' % (my_animal, my_wx, t_animal, t_wx)
    health_desc += wx_health.get(my_wx, '保持健康作息。')

    # ── 相处建议 ──
    if score >= 70:
        advice = '你们是天生一对的好组合！珍惜这份默契，继续保持良好互动。偶尔制造小惊喜，会让关系更加甜蜜。'
    elif score >= 50:
        advice = '你们的组合有潜力，关键在于互相理解和包容。多关注对方的需求，遇到分歧时先冷静再沟通，避免冷战。'
    else:
        advice = '属相差异较大不代表无法相处，关键是心态。学会欣赏对方的不同之处，用沟通代替指责，用心经营就能化解矛盾。'

    # ── 构建sections ──
    sections = [
        {'title':'属相匹配总评', 'content':
            '属%s × 属%s\n'
            '综合评分：%d分（%s）\n'
            '你的五行属性：%s ｜ 对方五行属性：%s\n'
            '五行关系：%s' % (my_animal, t_animal, score, lv, my_wx, t_wx, wx_desc)},
        {'title':'六爻关系', 'content': '\n'.join(
            '【%s】%s\n%s' % (r[0], r[1], r[2]) for r in relations) if relations else '无特殊冲合关系，属相相处平和。'},
        {'title':'感情运', 'content': '感情契合度：%d分\n%s' % (love_score, love_desc)},
        {'title':'事业合作', 'content': '合作默契度：%d分\n%s' % (biz_score, biz_desc)},
        {'title':'健康提醒', 'content': health_desc},
        {'title':'幸运指南', 'content':
            '幸运颜色：%s\n幸运方位：%s\n幸运数字：%s' % (lucky_color, lucky_dir, lucky_num)},
        {'title':'相处建议', 'content': advice},
    ]

    tags = ['#%s' % my_animal, '#%s' % t_animal]
    return {'score':score, 'summary':'属%s×属%s %d分（%s）' % (my_animal, t_animal, score, lv), 'sections':sections, 'tags':tags}

def divine_dream(question=''):
    dream = (question or '').strip()
    if not dream: return {'score':0, 'summary':'请描述梦境', 'sections':[], 'tags':[]}
    DWX = {'水':['水','河','海','雨','游泳','船','鱼','湖','泉','冰','雪','泪','井','泉'],
           '火':['火','烧','太阳','红','烟','焰','灯','蜡烛','爆炸','燃烧','烤箱'],
           '木':['树','花','草','林','竹','森林','叶','果','根','藤','柳','松'],
           '金':['刀','剑','钱','金','银','铁','针','锤','车','枪','武器','珠宝'],
           '土':['山','地','石','墙','房','洞穴','坟墓','泥土','砖','沙漠','桥']}
    AWX = {'龙':'土','蛇':'火','马':'火','羊':'土','猴':'金','鸡':'金','狗':'土','猪':'水','鼠':'水','牛':'土','虎':'木','兔':'木'}
    dwxn = '土'
    detected_wx = []
    for wx, kws in DWX.items():
        for kw in kws:
            if kw in dream:
                dwxn = wx
                detected_wx.append(wx)
                break
    for a, aw in AWX.items():
        if a in dream:
            dwxn = aw
            if aw not in detected_wx:
                detected_wx.append(aw)
    bazi = get_today_bazi()
    my_wx = WX[TG.index(bazi[4])]
    rel = wx_relation(my_wx, dwxn)
    dj_map = {
        '比和':('好运之兆','气场同类相合，梦境反映内心平衡'),
        '生我':('好运之兆','有贵人相助之象'),
        '我克':('主动掌控','能驾驭当前局面'),
        '我生':('消耗精力','注意劳逸结合，避免过度付出'),
        '克我':('压力提醒','近期可能面临挑战，需提前准备')}
    dj, dm = dj_map.get(rel, ('平静之兆','一切平稳'))
    WXDM = {
        '水':'水主智，梦水多为潜意识流动。水代表智慧、财富的流动，也象征情感的深沉变化。梦见水，暗示你的内在正在经历某种转化。',
        '火':'火主礼，梦火多为激情或焦虑。火代表热情、力量和变革，也象征紧张或冲突。梦见火，说明你内心有强烈的情感需要表达。',
        '木':'木主仁，梦木多为成长和生机。木代表生长、发展和希望，也象征人际关系。梦见木，预示新的开始或关系的成长。',
        '金':'金主义，梦金多为决断和收获。金代表收获、权力和正义，也象征果断的抉择。梦见金，提示你需要在某个问题上做出决定。',
        '土':'土主信，梦土多为稳定和根基。土代表安全、务实和耐心，也象征固执或停滞。梦见土，提醒你关注生活的基础建设。'}
    WX_HEALTH = {
        '水':'注意肾脏、泌尿系统健康，多饮温水，避免熬夜伤阴。',
        '木':'注意肝胆和眼睛，保持充足睡眠，多亲近自然舒缓压力。',
        '火':'注意心血管系统，控制情绪起伏，适当运动释放压力。',
        '土':'注意脾胃消化系统，饮食规律少食生冷，细嚼慢咽。',
        '金':'注意呼吸系统和皮肤健康，保持空气流通，多做深呼吸练习。'}
    WX_LUCK = {
        '水':{'color':'蓝色、黑色','dir':'北方','num':'1、6','season':'冬季'},
        '木':{'color':'绿色、青色','dir':'东方','num':'3、8','season':'春季'},
        '火':{'color':'红色、紫色','dir':'南方','num':'2、7','season':'夏季'},
        '土':{'color':'黄色、棕色','dir':'中央','num':'5、0','season':'四季交替'},
        '金':{'color':'白色、金色','dir':'西方','num':'4、9','season':'秋季'}}
    summary = '梦境「%s」\n五行属性：%s | 今日五行：%s | 吉凶：%s' % (dream[:20], dwxn, my_wx, dj)
    secs = [
        {'title':'梦境总评',
         'content':'**吉凶**：%s\n%s\n**梦境五行**：%s\n**你今日五行**：%s\n**五行关系**：%s → %s' % (dj, dm, dwxn, my_wx, my_wx, rel)},
        {'title':'五行解梦',
         'content':'**五行%s之梦**：\n%s\n\n梦中出现的%s元素，与今日五行%s形成「%s」关系。%s' % (dwxn, WXDM.get(dwxn, ''), dwxn, my_wx, rel, dm)},
        {'title':'身心提示',
         'content':WX_HEALTH.get(dwxn, '保持健康作息，注意身心平衡。')},
        {'title':'幸运指南',
         'content':'**幸运颜色**：%s\n**幸运方位**：%s\n**幸运数字**：%s\n**旺盛季节**：%s' % (WX_LUCK[dwxn]['color'], WX_LUCK[dwxn]['dir'], WX_LUCK[dwxn]['num'], WX_LUCK[dwxn]['season'])},
        {'title':'行动建议',
         'content':'%s\n\n梦境是潜意识的反映，不必过分紧张。保持平常心，顺势而为即可。' % ('吉兆已至，积极把握机遇。' if '好运' in dj or '掌控' in dj else '注意调节情绪，适当放松身心。' if '压力' in dj or '消耗' in dj else '保持平常心，顺其自然。')},
    ]
    return {'score':0, 'summary':summary, 'sections':secs, 'tags':[dwxn, dj]}

XIANTIAN_GUA = {0:'干坦',1:'干兑',2:'干离',3:'干震',4:'干巷',5:'干坎',6:'干艦',7:'干坦',
    8:'兑干',9:'兑兑',10:'兑离',11:'兑震',12:'兑巷',13:'兑坎',14:'兑艦',15:'兑坦',
    16:'离干',17:'离兑',18:'离离',19:'离震',20:'离巷',21:'离坎',22:'离艦',23:'离坦',
    24:'震干',25:'震兑',26:'震离',27:'震震',28:'震巷',29:'震坎',30:'震艦',31:'震坦',
    32:'巷干',33:'巷兑',34:'巷离',35:'巷震',36:'巷巷',37:'巷坎',38:'巷艦',39:'巷坦',
    40:'坎干',41:'坎兑',42:'坎离',43:'坎震',44:'坎巷',45:'坎坎',46:'坎艦',47:'坎坦',
    48:'艦干',49:'艦兑',50:'艦离',51:'艦震',52:'艦巷',53:'艦坎',54:'艦艦',55:'艦坦',
    56:'坦干',57:'坦兑',58:'坦离',59:'坦震',60:'坦巷',61:'坦坎',62:'坦艦',63:'坦坦'}
GUA_WX = ['金','金','火','木','木','水','土','土']

def divine_meihua_love(birth_info, question='', target_info=None):
    # 梅花易数起卦：用年月日时数字起卦
    import random
    now = datetime.datetime.now()
    try:
        y = int(birth_info.get('birth_year', now.year))
        m = int(birth_info.get('birth_month', now.month))
        d = int(birth_info.get('birth_day', now.day))
        h = int(birth_info.get('birth_hour', now.hour))
    except:
        y, m, d, h = now.year, now.month, now.day, now.hour
    
    # 起卦算法：上卦=(年+月+日)%8, 下卦=(年+月+日+时)%8, 动爻=(年+月+日+时)%6
    upper_idx = (y + m + d) % 8
    lower_idx = (y + m + d + h) % 8
    dong_idx = (y + m + d + h) % 6
    # 如果有target_info，用target的生日影响下卦
    if target_info and target_info.get('birth_year'):
        ty = int(target_info['birth_year'])
        tm = int(target_info.get('birth_month', 1))
        td = int(target_info.get('birth_day', 1))
        lower_idx = (ty + tm + td + h) % 8
        dong_idx = (y + m + d + ty + tm + td) % 6
    
    BAGUA = ['坎水','坤土','震木','巽木','乾金','兑金','艮土','离火']
    BAGUA_CN = {'坎':'水','坤':'土','震':'木','巽':'木','乾':'金','兑':'金','艮':'土','离':'火'}
    BAGUA_MEAN = {
        '坎':'代表智慧与变化，感情中有深厚的感性力量，如水般深沉。',
        '坤':'代表包容与厚德，感情中稳重踏实，是可靠的港湾。',
        '震':'代表行动与突破，感情中有强烈的冲动和热情，主动追求。',
        '巽':'代表柔和与渗透，感情中细腻温婉，善于经营感情细节。',
        '乾':'代表刚健与领导，感情中果断坚定，但需学会柔软表达。',
        '兑':'代表喜悦与交流，感情中善于表达爱意，是快乐的伙伴。',
        '艮':'代表静止与守成，感情中忠诚专一，但需避免过于固执。',
        '离':'代表光明与热情，感情中灿烂热烈，是浪漫的追逐者。'}
    GUAMEAN = {
        '坎坎':'双重水象，感情深沉如海，默契极高但也需注入新鲜感。',
        '坎坤':'水润大地，滋养深厚，对方能给你带来安全感与稳定。',
        '坎震':'水雷屯卦，感情初期有波折，但坚持之后会有好结果。',
        '坎巽':'水风井卦，感情如井水般源远流长，细水长流最长久。',
        '坎乾':'水天需卦，感情需要耐心等待时机，不可急于求成。',
        '坎兑':'水泽节卦，感情需要适度节制，享受甜蜜的同时保持独立。',
        '坎艮':'水山蹇卦，感情路上有阻碍，但两人同心可克服困难。',
        '坎离':'水火既济卦，水火相济，阴阳调和，是非常好的感情组合。',
        '坤坎':'地水师卦，包容与智慧并存，你们能在理解中共同成长。',
        '坤坤':'双重土象，感情根基牢固如山，适合长久稳定的伴侣关系。',
        '坤震':'地雷复卦，在困难中重新开始，对方给你重新出发的勇气。',
        '坤巽':'地风升卦，感情稳步上升，每一天都在变得更好。',
        '坤乾':'地天泰卦，天地交泰，阴阳和合，是上上等的感情组合！',
        '坤兑':'地泽临卦，感情亲密和谐，善于享受二人世界的甜蜜。',
        '坤艮':'地山谦卦，感情中谦逊互让，不争不抢，是幸福的模样。',
        '坤离':'地火明夷卦，感情有光明也有暗面，需要共同面对内心阴影。',
        '震坎':'雷水解卦，行动化解困境，你们能在困难中找到出路。',
        '震坤':'雷地豫卦，感情充满喜悦和期待，是令人羡慕的组合。',
        '震震':'双重雷象，感情充满激情和活力，但需避免过于冲动。',
        '震巽':'雷风恒卦，雷风相随，感情持久不变，是最稳定的组合之一。',
        '震乾':'雷天大壮卦，感情力量强大，两人都是行动派。',
        '震兑':'雷泽归妹卦，感情中有归宿感，但需确认时机成熟再行动。',
        '震艮':'雷山小过卦，感情中小事需注意细节，细节决定成败。',
        '震离':'雷火丰卦，感情丰盛饱满，是充满激情和创造力的组合。',
        '巽坎':'风涣卦，柔风散水，感情中善于化解矛盾，沟通能力强。',
        '巽坤':'风地观卦，感情中有洞察力，善于理解对方的深层需求。',
        '巽震':'风雷益卦，彼此增益，互相成就，感情越来越好。',
        '巽巽':'双重风象，感情灵活多变，善于适应不同环境。',
        '巽乾':'风天小畜卦，感情需要积累和耐心，厚积薄发。',
        '巽兑':'风泽中孚卦，感情中以诚信为本，互相信任是基石。',
        '巽艮':'风山渐卦，感情循序渐进，不急不躁，自然水到渠成。',
        '巽离':'风火家人卦，家庭观念强，适合组建家庭的感情组合。',
        '乾坎':'天水讼卦，刚柔碰撞，需学会退让和妥协。',
        '乾坤':'天地否卦，需要努力沟通打破隔阂，化否为泰。',
        '乾震':'天雷无妄卦，感情中需保持真诚，不可有欺骗。',
        '乾巽':'天风姤卦，缘分天注定，珍惜这份相遇。',
        '乾乾':'双重金象，感情果断坚毅，但也需柔软表达。',
        '乾兑':'天泽履卦，感情中需小心谨慎，尊重彼此的底线。',
        '乾艮':'天山遁卦，感情中有退缩倾向，需主动面对问题。',
        '乾离':'天火同人卦，志同道合，是理想的灵魂伴侣组合。',
        '兑坎':'泽水困卦，感情中有困境但可以突破，坚持就是胜利。',
        '兑坤':'泽地萃卦，感情聚集美好，善于创造浪漫和惊喜。',
        '兑震':'泽雷随卦，随缘而动，不刻意不强求，自然最好。',
        '兑巽':'泽风大过卦，感情浓烈但需适度，过犹不及。',
        '兑兑':'双重泽象，感情充满喜悦和交流，是快乐的组合。',
        '兑艮':'泽山咸卦，山泽通气，感情感应灵敏，心灵相通。',
        '兑离':'泽火革卦，感情中勇于变革，不断进化让关系更新。',
        '艮坎':'山水蒙卦，感情中有迷茫需启蒙，多沟通消除误解。',
        '艮坤':'山地剥卦，感情需防患于未然，注意维护根基。',
        '艮震':'山雷颐卦，感情需要滋养和呵护，用心经营。',
        '艮巽':'山风蛊卦，感情需要修正和调整，发现问题及时解决。',
        '艮乾':'山天大畜卦，感情积蓄力量，厚积薄发后有大成就。',
        '艮兑':'山泽损卦，感情中需适当牺牲，有舍才有得。',
        '艮艮':'双重山象，感情忠贞不渝，但也需学会灵活变通。',
        '艮离':'山火贲卦，感情中有装饰和美化，善于营造氛围。',
        '离坎':'火水未济卦，感情尚未圆满，需继续努力经营。',
        '离坤':'火地晋卦，感情光明上升，前途美好。',
        '离震':'火雷噬嗑卦，感情中需果断决策，不拖泥带水。',
        '离巽':'火风鼎卦，感情中有升华和蜕变，越来越好。',
        '离乾':'火天大有卦，感情丰盛圆满，拥有很多美好的事物。',
        '离兑':'火泽睽卦，感情中有分歧需理解，求同存异。',
        '离艮':'火山旅卦，感情中有漂泊感，需找到归属感。',
        '离离':'双重火象，感情热烈灿烂，光芒四射但也需适度降温。'}
    
    upper_gua = BAGUA[upper_idx % 8]
    lower_gua = BAGUA[lower_idx % 8]
    upper_name = upper_gua[0]
    lower_name = lower_gua[0]
    gua_key = upper_name + lower_name
    
    upper_wx = BAGUA_CN[upper_name]
    lower_wx = BAGUA_CN[lower_name]
    rel = wx_relation(upper_wx, lower_wx)
    rel_map = {'比和':'体用比和，气场和谐', '生我':'用生体，对方滋养你', '我生':'体生用，你付出较多', '克我':'用克体，需注意压力', '我克':'体克用，你能掌控关系'}
    
    # 评分
    score = 50
    if rel in ('比和','生我'): score += 20
    elif rel == '我生': score += 5
    elif rel == '我克': score += 10
    elif rel == '克我': score -= 10
    # 泰卦加分
    if gua_key in ('坤乾','巽震','兑艮','乾离','坎离','震巽'): score += 15
    # 否卦减分
    if gua_key in ('乾坤','离坎','兑离','巽乾'): score -= 10
    score = max(0, min(100, score))
    if score >= 75: lv = '大吉'
    elif score >= 60: lv = '中吉'
    elif score >= 45: lv = '一般'
    elif score >= 30: lv = '小凶'
    else: lv = '凶'
    
    WX_LUCK = {'水':{'color':'蓝色','dir':'北方','num':'1、6'},
               '木':{'color':'绿色','dir':'东方','num':'3、8'},
               '火':{'color':'红色','dir':'南方','num':'2、7'},
               '土':{'color':'黄色','dir':'中央','num':'5、0'},
               '金':{'color':'白色','dir':'西方','num':'4、9'}}
    
    gua_mean = GUAMEAN.get(gua_key, '此卦象提示感情需要用心经营，顺其自然。')
    upper_mean = BAGUA_MEAN.get(upper_name, '')
    lower_mean = BAGUA_MEAN.get(lower_name, '')
    
    if score >= 60:
        advice = '卦象显示你们的感情缘分深厚，珍惜这份缘分，保持真诚的沟通。在关系中保持自我，同时用心经营，幸福就在身边。'
    elif score >= 40:
        advice = '卦象提示感情有潜力但也有挑战。关键在于双方的理解与包容，遇到分歧时先冷静再沟通。用心经营，定能开花结果。'
    else:
        advice = '卦象显示感情路上有些波折，但波折不等于无望。学会欣赏对方的优点，用沟通代替猜测，用行动代替等待。'
    
    sections = [
        {'title':'梅花卦象', 'content':
            '**上卦**：%s（%s）\n**下卦**：%s（%s）\n**动爻**：第%d爻\n'
            '**体用关系**：%s\n**综合评分**：%d分（%s）' % (upper_gua, upper_mean[:15], lower_gua, lower_mean[:15], dong_idx+1, rel_map.get(rel,rel), score, lv)},
        {'title':'卦象解读', 'content':
            '**%s卦**：\n%s\n\n'
            '**上卦%s**：%s\n**下卦%s**：%s' % (gua_key, gua_mean, upper_name, upper_mean, lower_name, lower_mean)},
        {'title':'感情分析', 'content':
            '**感情契合度**：%d分\n'
            '%s' % (score, '你们的组合卦象吉利，感情基础扎实，是值得珍惜的缘分。' if score >= 60 else '你们的组合有一定挑战，但挑战也是成长的契机，用心经营可以化解。')},
        {'title':'幸运指南', 'content':
            '**幸运颜色**：%s\n**幸运方位**：%s\n**幸运数字**：%s' % (WX_LUCK.get(upper_wx,{}).get('color','白色'), WX_LUCK.get(upper_wx,{}).get('dir','东方'), WX_LUCK.get(upper_wx,{}).get('num','3、8'))},
        {'title':'相处建议', 'content': advice},
    ]
    return {'score':score, 'summary':'梅花卦象 %s卦 %d分（%s）' % (gua_key, score, lv), 'sections':sections, 'tags':[gua_key, lv]}

def divine_love_match(birth_info, question='', target_info=None):
    import datetime
    now = datetime.datetime.now()
    try:
        uy = int(birth_info.get('birth_year', 0))
        um = int(birth_info.get('birth_month', now.month))
        ud = int(birth_info.get('birth_day', now.day))
        uh = int(birth_info.get('birth_hour', now.hour))
    except:
        return {'score':0, 'summary':'需要您的出生日期', 'sections':[{'title':'提示','content':'请提供您的出生年月日时'}], 'tags':[]}
    if uy < 1900 or uy > 2100:
        return {'score':0, 'summary':'出生年份不正确', 'sections':[], 'tags':[]}
    my_bazi = get_bazi(uy, um, ud, uh)
    my_day_wx = WX[TG.index(my_bazi[4])]
    ty = tm = td = th = 0
    if target_info and target_info.get('birth_year'):
        ty = int(target_info['birth_year'])
        tm = int(target_info.get('birth_month', 1))
        td = int(target_info.get('birth_day', 1))
        th = int(target_info.get('birth_hour', 12))
    if not ty or ty < 1900:
        return {'score':0, 'summary':'需要对方出生日期', 'sections':[{'title':'提示','content':'请提供对方的出生年月日'}], 'tags':[]}
    t_bazi = get_bazi(ty, tm, td, th)
    t_day_wx = WX[TG.index(t_bazi[4])]
    def _shishen(day_wx, other_wx):
        rel = wx_relation(day_wx, other_wx)
        ss_map = {'比和':'比肩/劫财','生我':'正印/偏印','我生':'食神/伤官','克我':'正官/七杀','我克':'正财/偏财'}
        return ss_map.get(rel, '比肩')
    my_to_target = _shishen(my_day_wx, t_day_wx)
    target_to_me = _shishen(t_day_wx, my_day_wx)
    score = 50
    wx_rel = wx_relation(my_day_wx, t_day_wx)
    if wx_rel == '比和': score += 15
    elif wx_rel == '生我': score += 20
    elif wx_rel == '我生': score += 5
    elif wx_rel == '我克': score += 10
    elif wx_rel == '克我': score -= 5
    my_zodiac = (uy - 4) % 12
    t_zodiac = (ty - 4) % 12
    ZODIAC_SANHE = [[0,4,8],[3,7,11],[6,10,2],[9,1,5]]
    ZODIAC_LIU_HE = {0:1,1:0,2:11,11:2,3:10,10:3,4:9,9:4,5:8,8:5,6:7,7:6}
    for g in ZODIAC_SANHE:
        if my_zodiac in g and t_zodiac in g:
            score += 10
            break
    if ZODIAC_LIU_HE.get(my_zodiac) == t_zodiac:
        score += 10
    score = max(0, min(100, score))
    if score >= 80: lv = '天作之合'
    elif score >= 65: lv = '情投意合'
    elif score >= 50: lv = '有缘有分'
    elif score >= 35: lv = '需要经营'
    else: lv = '考验较多'
    SS_MEAN = {
        '比肩/劫财': {'desc':'你们像知心朋友，有很强的共鸣感，但需避免过于相似导致的乏味。','love':'80', 'biz':'70', 'tip':'保持各自独立性，给对方空间。'},
        '正印/偏印': {'desc':'对方给你带来安全感和庇护，是温暖的依靠，感情基础深厚。','love':'90', 'biz':'65', 'tip':'珍惜对方的包容，适时回馈关爱。'},
        '食神/伤官': {'desc':'你们之间有强烈的吸引力和表达欲，但需注意言辞不要太尖锐。','love':'75', 'biz':'80', 'tip':'用赞美代替批评，欣赏对方的光芒。'},
        '正官/七杀': {'desc':'对方对你有天然的约束力和影响力，可能是你欣赏的类型。','love':'70', 'biz':'85', 'tip':'在尊重中找到平衡，不必完全顺从。'},
        '正财/偏财': {'desc':'对方是你想要守护的人，有很强的占有欲和责任感。','love':'85', 'biz':'75', 'tip':'在守护和自由之间找到平衡。'},
    }
    my_ss = SS_MEAN.get(my_to_target, SS_MEAN['比肩/劫财'])
    t_ss = SS_MEAN.get(target_to_me, SS_MEAN['比肩/劫财'])
    WX_LUCK = {'水':{'color':'蓝色、黑色','dir':'北方'}, '木':{'color':'绿色','dir':'东方'},
               '火':{'color':'红色','dir':'南方'}, '土':{'color':'黄色','dir':'中央'},
               '金':{'color':'白色','dir':'西方'}}
    sections = [
        {'title':'八字总评', 'content':
            '**综合匹配度**：%d分（%s）\n\n'
            '**你的八字**：%s年 %s月 %s日 %s时\n日主：%s（%s）\n'
            '**对方八字**：%s年 %s月 %s日 %s时\n日主：%s（%s）\n'
            '**五行关系**：%s' % (
                score, lv,
                my_bazi[0], my_bazi[1], my_bazi[2], my_bazi[3], my_bazi[4], my_bazi[5],
                my_day_wx, my_bazi[4],
                t_bazi[0], t_bazi[1], t_bazi[2], t_bazi[3], t_bazi[4], t_bazi[5],
                t_day_wx, t_bazi[4],
                wx_rel)},
        {'title':'十神分析', 'content':
            '**你看对方**：%s\n%s\n\n'
            '**对方看你**：%s\n%s' % (
                my_to_target, my_ss['desc'],
                target_to_me, t_ss['desc'])},
        {'title':'感情运', 'content':
            '**感情契合度**：%s分\n'
            '%s' % (
                my_ss['love'],
                '双方容易产生深厚的情感共鸣。' if score >= 65 else '需要双方主动经营，多创造美好回忆。')},
        {'title':'事业合作', 'content':
            '**合作默契度**：%s分\n'
            '%s' % (my_ss['biz'],
                   '事业上的配合度高，适合共同创业或合作项目。' if score >= 65 else '各自发挥所长是最佳模式，避免争抢主导权。')},
        {'title':'相处建议', 'content':
            '**给你的建议**：%s\n**给对方的建议**：%s' % (my_ss['tip'], t_ss['tip'])},
        {'title':'幸运指南', 'content':
            '**幸运颜色**：%s\n**幸运方位**：%s' % (
                WX_LUCK.get(my_day_wx, {}).get('color', '白色'),
                WX_LUCK.get(my_day_wx, {}).get('dir', '东方'))},
    ]
    return {'score':score, 'summary':'八字匹配 %d分（%s）' % (score, lv), 'sections':sections, 'tags':['%s' % my_day_wx, '%s' % t_day_wx]}

# ═══════════════════════════════════════════════════════════
# 星座匹配
# ═══════════════════════════════════════════════════════════
SIGN_DATA = [
    ('Aries','白羊座','♈','Fire','Cardinal',(3,21),(4,19)),
    ('Taurus','金牛座','♉','Earth','Fixed',(4,20),(5,20)),
    ('Gemini','双子座','♊','Air','Mutable',(5,21),(6,21)),
    ('Cancer','巨蟹座','♋','Water','Cardinal',(6,22),(7,22)),
    ('Leo','狮子座','♌','Fire','Fixed',(7,23),(8,22)),
    ('Virgo','处女座','♍','Earth','Mutable',(8,23),(9,22)),
    ('Libra','天秤座','♎','Air','Cardinal',(9,23),(10,23)),
    ('Scorpio','天蝎座','♏','Water','Fixed',(10,24),(11,22)),
    ('Sagittarius','射手座','♐','Fire','Mutable',(11,23),(12,21)),
    ('Capricorn','摩羯座','♑','Earth','Cardinal',(12,22),(1,19)),
    ('Aquarius','水瓶座','♒','Air','Fixed',(1,20),(2,18)),
    ('Pisces','双鱼座','♓','Water','Mutable',(2,19),(3,20)),
]
ELEM_CN = {'Fire':'火象','Earth':'土象','Air':'风象','Water':'水象'}
QUAL_CN = {'Cardinal':'开创','Fixed':'固定','Mutable':'变动'}
SIGN_LIST = [s[0] for s in SIGN_DATA]
SIGN_CN_MAP = {s[0]: s[1] for s in SIGN_DATA}
SIGN_EMOJI_MAP = {s[0]: s[2] for s in SIGN_DATA}

def _get_sun_sign(month, day):
    for name, cn, emoji, elem, qual, (sm, sd), (em, ed) in SIGN_DATA:
        if sm > em:
            if (month == sm and day >= sd) or (month == em and day <= ed) or month > sm or month < em:
                return (name, cn, emoji, elem, qual)
        else:
            if (sm < month < em) or (month == sm and day >= sd) or (month == em and day <= ed):
                return (name, cn, emoji, elem, qual)
    return ('Pisces', SIGN_CN_MAP['Pisces'], SIGN_EMOJI_MAP['Pisces'], 'Water', 'Mutable')

def _parse_target_birth(question):
    import re
    q = (question or '').strip()
    for s in SIGN_DATA:
        if s[1] in q: return {'type': 'sign', 'sign': s[0], 'sign_cn': s[1]}
    m = re.search(r'(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})', q)
    if m: return {'type': 'birth', 'year': int(m.group(1)), 'month': int(m.group(2)), 'day': int(m.group(3))}
    m2 = re.search(r'(\d{1,2})[月/\-.](\d{1,2})', q)
    if m2: return {'type': 'month_day', 'month': int(m2.group(1)), 'day': int(m2.group(2))}
    return None

def _calc_sign_score(s1, s2):
    score = 50
    info1 = [x for x in SIGN_DATA if x[0]==s1][0]
    info2 = [x for x in SIGN_DATA if x[0]==s2][0]
    e1, e2, q1, q2 = info1[3], info2[3], info1[4], info2[4]
    if e1 == e2: score += 20
    comp = {'Fire':'Air','Air':'Fire','Earth':'Water','Water':'Earth'}
    if comp.get(e1) == e2: score += 15
    if q1 == q2: score += 10
    idx1, idx2 = SIGN_LIST.index(s1), SIGN_LIST.index(s2)
    diff = abs(idx1 - idx2)
    if diff > 6: diff = 12 - diff
    if diff <= 2: score += 15
    elif diff >= 5: score -= 5
    return min(score, 100)

def divine_constellation_match(birth_info, question=''):
    year = birth_info.get('birth_year', 0)
    month = birth_info.get('birth_month', 0)
    day = birth_info.get('birth_day', 0)
    if not year or not month or not day:
        return {'score':0, 'summary':'需要您的出生日期', 'sections':[], 'tags':[]}
    my_sign, my_cn, my_emoji, my_elem, my_qual = _get_sun_sign(month, day)
    target = _parse_target_birth(question)
    if not target:
        info_text = '**%s** %s\n**元素**：%s\n**守护星**：%s\n**特质**：%s' % (my_cn, my_emoji, ELEM_CN[my_elem], _get_ruler(my_sign), QUAL_CN[my_qual])
        return {'score':0, 'summary':'您的太阳星座是%s%s。请告诉我对方的星座或出生日期。' % (my_cn, my_emoji), 'sections':[{'title':'您的星座','content':info_text}],'tags':[my_cn]}
    if target['type'] == 'sign':
        t_sign, t_cn = target['sign'], target['sign_cn']
        t_emoji = SIGN_EMOJI_MAP.get(t_sign, '')
        t_info = [x for x in SIGN_DATA if x[0]==t_sign][0]
        t_elem, t_qual = t_info[3], t_info[4]
    elif target['type'] in ('birth', 'month_day'):
        t_sign, t_cn, t_emoji, t_elem, t_qual = _get_sun_sign(target.get('month',1), target.get('day',1))
    else:
        return {'score':0, 'summary':'无法识别对方信息', 'sections':[], 'tags':[]}
    score = _calc_sign_score(my_sign, t_sign)
    if score >= 80: lv = '天生一对'
    elif score >= 65: lv = '高度契合'
    elif score >= 50: lv = '互相吸引'
    elif score >= 35: lv = '需要磨合'
    else: lv = '挑战成长'
    
    # 元素关系
    ELEM_REL = {
        ('Fire','Fire'):'同为火象星座，热情似火，感情浓烈，但需注意控制节奏避免灼伤。你们都充满活力和激情。',
        ('Earth','Earth'):'同为土象星座，踏实稳重，感情根基牢固，是适合长相厮守的组合。务实可靠。',
        ('Air','Air'):'同为风象星座，思维活跃，沟通无碍，是精神层面的知己。但需避免过于理性缺乏感性。',
        ('Water','Water'):'同为水象星座，情感深沉，默契极高，心灵相通。但需注意不要过于敏感多疑。',
        ('Fire','Air'):'火与风是天然搭档！火需要风的助燃，风因火而生动。你们互相激发灵感与激情。',
        ('Air','Fire'):'风助火势，你们的组合充满创造力和活力。思想碰撞产生火花，是令人羡慕的组合。',
        ('Earth','Water'):'土与水是最佳拍档！水滋润大地，大地承载水流。你们互相滋养，感情深厚稳定。',
        ('Water','Earth'):'水润大地，大地包容水流。你们之间有天然的互补性，是安全感和深情的完美结合。',
        ('Fire','Water'):'火与水相互挑战。火的热情遇上水的深沉，需要互相理解和调整。水能调和火的急躁，火能温暖水的冷静。',
        ('Water','Fire'):'水与火的碰撞充满张力。你们之间有强烈的吸引力，但也需注意平衡感性与理性。',
        ('Fire','Earth'):'火与土的组合需要耐心。火的冲动遇上土的稳重，需要互相包容差异。火的热度能温暖土的沉静。',
        ('Earth','Fire'):'土能承载火的能量。你们需要找到节奏上的平衡，土的耐心配合火的热忱，可以成就非凡。',
        ('Air','Earth'):'风与土的组合差异较大。风的自由遇上土的踏实，需要互相尊重对方的生活方式。',
        ('Earth','Air'):'土的务实与风的灵活形成互补。如果能在稳定中注入变化，在变化中保持根基，会越来越好。',
        ('Air','Water'):'风与水的组合富有诗意。风的轻盈遇上水的深沉，如果风能读懂水的情感，水能欣赏风的自由，会很美。',
        ('Water','Air'):'水的感性与风的理性相互补充。你们可以成为彼此的良师益友，在理解中共同成长。',
    }
    elem_desc = ELEM_REL.get((my_elem, t_elem), ELEM_REL.get((t_elem, my_elem), '你们的元素关系独特，互相学习共同成长。'))
    
    # 品质分析
    QUAL_PAIR = {
        '基本/基本':'同为基本宫，都是天生的领导者和行动派，做事果断有力。',
        '固定/固定':'同为固定宫，都是忠诚坚定的人，感情中持久不变，但也需避免固执。',
        '变动/变动':'同为变动宫，都是灵活多变的人，善于适应环境，但需注意保持稳定。',
        '基本/固定':'行动力与坚持力结合，一个发起一个执行，互补性很强。',
        '固定/基本':'坚持与行动的搭配，你们能在计划与执行间找到默契。',
        '基本/变动':'行动与适应的结合，一个定方向一个找方法，效率很高。',
        '变动/基本':'灵活与果断的搭配，你帮助对方调整方向，对方帮你坚定决策。',
        '固定/变动':'稳定与变化的碰撞，对方给你安全感，你给对方新鲜感。',
        '变动/固定':'你带来变化和活力，对方提供稳定和依靠，互补性极强。',
    }
    qual_key = '%s/%s' % (my_qual, t_qual)
    qual_desc = QUAL_PAIR.get(qual_key, QUAL_PAIR.get('%s/%s' % (t_qual, my_qual), '你们各有独特的性格特质，在相处中互相学习。'))
    
    # 守护星
    def _get_ruler(sign):
        rulers = {'Aries':'火星','Taurus':'金星','Gemini':'水星','Cancer':'月亮',
                  'Leo':'太阳','Virgo':'水星','Libra':'金星','Scorpio':'冥王星',
                  'Sagittarius':'木星','Capricorn':'土星','Aquarius':'天王星','Pisces':'海王星'}
        return rulers.get(sign, '未知')
    
    my_ruler = _get_ruler(my_sign)
    t_ruler = _get_ruler(t_sign)
    
    if score >= 65:
        advice = '你们的星座组合非常匹配！保持真诚的沟通，在欣赏彼此差异的同时，发挥各自的优点。这段关系有成为灵魂伴侣的潜力。'
    elif score >= 45:
        advice = '你们的组合有吸引力也有挑战。关键是学会欣赏对方不同的视角和方式，在理解中找到共同点。用心经营，定能让感情升温。'
    else:
        advice = '星座差异较大不代表无法相处，恰恰相反，差异是成长的契机。学会换位思考，用包容代替评判，你们可以在挑战中建立更深层次的连接。'
    
    SIGN_COLORS = {
        'Aries':'红色、橙色','Taurus':'绿色、粉色','Gemini':'黄色、浅蓝','Cancer':'银色、白色',
        'Leo':'金色、橙色','Virgo':'米色、墨绿','Libra':'粉色、浅蓝','Scorpio':'深红、黑色',
        'Sagittarius':'紫色、蓝色','Capricorn':'棕色、黑色','Aquarius':'天蓝、银色','Pisces':'海蓝、薰衣草'}
    
    sections = [
        {'title':'匹配总评', 'content':
            '**综合匹配度**：%d/100（%s）**\n\n'
            '%s %s × %s %s\n'
            '**你的守护星**：%s | **对方守护星**：%s\n'
            '%s' % (score, lv, my_cn, my_emoji, t_cn, t_emoji, my_ruler, t_ruler, elem_desc[:80] + '...')},
        {'title':'元素互动', 'content':
            '**%s（%s）** × **%s（%s）**\n\n%s' % (my_cn, ELEM_CN[my_elem], t_cn, ELEM_CN[t_elem], elem_desc)},
        {'title':'品质分析', 'content':
            '**%s**是%s型，**%s**是%s型。\n\n%s' % (my_cn, QUAL_CN[my_qual], t_cn, QUAL_CN[t_qual], qual_desc)},
        {'title':'感情默契', 'content':
            '**感情契合度**：%d分\n'
            '%s' % (min(100, score + 5),
                   '你们在情感上有天然的默契，容易产生心动的感觉。保持浪漫和惊喜，让感情持续升温。' if score >= 60 else
                   '感情需要双方主动经营，多表达爱意，多创造共同回忆，你们的感情会越来越深厚。')},
        {'title':'最佳相处模式', 'content':
            '你们作为%s和%s的组合，最佳的相处之道是：%s' % (
                my_cn, t_cn,
                '保持各自的独立空间，同时在关键时刻给予对方全力支持。' if score >= 60 else
                '在沟通中寻找共识，在差异中互相学习，用理解和耐心化解分歧。')},
        {'title':'幸运指南', 'content':
            '**你的幸运色**：%s\n**对方幸运色**：%s\n'
            '约会时可选择与双方幸运色相关的场所或穿搭，增进缘分。' % (
                SIGN_COLORS.get(my_sign, '白色'), SIGN_COLORS.get(t_sign, '白色'))},
        {'title':'相处建议', 'content': advice},
    ]
    return {'score':score, 'summary':'%s×%s 匹配度%d分' % (my_cn, t_cn, score), 'sections':sections, 'tags':[my_cn, t_cn], 'extra':{'my_sign':my_sign, 'target_sign':t_sign}}

# ═══════════════════════════════════════════════════════════
# 星座个人性格分析
# ═══════════════════════════════════════════════════════════

# 详细的星座性格数据库
SIGN_PERSONALITY = {
    'Aries': {
        'traits': ['热情冲动', '勇敢果断', '天生领袖', '争强好胜'],
        'personality': '白羊座是十二星座的第一个，象征着新的开始。你天生就是开拓者，充满活力和冒险精神。做事果断，不喜欢拖泥带水，一旦决定就全力以赴。你的热情具有感染力，总能带动身边的人一起前进。',
        'strengths': '行动力强、勇于挑战、热情大方、坦诚直率',
        'weaknesses': '容易冲动、缺乏耐心、好胜心强、有时过于自我',
        'love': '感情中热情如火，喜欢主动出击，追求刺激和新鲜感。对喜欢的人会毫不保留地表达爱意，是热烈而真诚的恋人。',
        'career': '适合需要领导力和行动力的工作。创业、销售、体育、军事等领域是你的主场。不喜欢被束缚，需要充分发挥自主性。',
        'lucky_number': '9', 'lucky_color': '红色、橙色',
        'best_match': '狮子座、射手座、双子座', 'advice': '学会放慢脚步，三思而后行。在追求目标的同时，不要忽视身边人的感受。'
    },
    'Taurus': {
        'traits': ['踏实稳重', '忠诚可靠', '审美独到', '享受生活'],
        'personality': '金牛座是最让人安心的存在。你稳重踏实，做事有条不紊，一旦承诺就会坚守到底。你有着极高的审美品味，热爱美食、音乐和一切美好的事物。对物质和情感都很重视，追求品质生活。',
        'strengths': '可靠忠诚、耐心坚韧、审美敏锐、脚踏实地',
        'weaknesses': '固执己见、变化较慢、有时过于保守、占有欲强',
        'love': '感情中忠诚专一，一旦爱上就全心全意。喜欢用行动表达爱意，为你爱的人创造稳定温暖的生活环境。',
        'career': '适合需要稳定性和专业性的工作。金融、房地产、艺术、烹饪、园艺等领域都能发挥你的优势。你天生善于管理资源和创造价值。',
        'lucky_number': '6', 'lucky_color': '绿色、粉色',
        'best_match': '处女座、摩羯座、巨蟹座', 'advice': '保持开放心态，勇于接受变化。有时候放手一搏，反而能获得更好的结果。'
    },
    'Gemini': {
        'traits': ['聪明灵活', '善于沟通', '好奇多才', '社交达人'],
        'personality': '双子座是天生的沟通大师和信息收集者。你的思维敏捷，口才出众，能轻松适应各种社交场合。对世界充满好奇心，喜欢学习新事物，兴趣广泛。你的双重性格让你既有理性分析的一面，也有感性表达的一面。',
        'strengths': '思维敏捷、口才出众、适应力强、知识面广',
        'weaknesses': '注意力分散、难以深入、有时善变、缺乏持久',
        'love': '感情中需要精神层面的交流，喜欢有趣幽默的伴侣。重视对话和思想的碰撞，理想的爱情是灵魂层面的共鸣。',
        'career': '适合需要沟通和创造力的工作。媒体、写作、翻译、教育、市场营销等领域是你的强项。你的多才多艺让你在任何领域都能游刃有余。',
        'lucky_number': '5', 'lucky_color': '黄色、浅蓝',
        'best_match': '天秤座、水瓶座、白羊座', 'advice': '学会专注，深耕一个领域。在追求新鲜感的同时，也要珍惜已经拥有的。'
    },
    'Cancer': {
        'traits': ['温柔体贴', '重视家庭', '直觉敏锐', '情感丰富'],
        'personality': '巨蟹座是最具母性光辉的星座。你温柔体贴，善于照顾他人，是朋友圈中的暖心存在。家庭对你来说非常重要，你愿意为所爱之人付出一切。你的直觉异常敏锐，能察觉到别人忽略的情感变化。',
        'strengths': '善解人意、忠诚顾家、直觉敏锐、情感丰富',
        'weaknesses': '过于敏感、情绪化、缺乏安全感、有时过于保护',
        'love': '感情中深情专一，渴望稳定的安全感。一旦认定一个人，会用尽全力去守护和经营这段感情。你是最好的伴侣和最温暖的家。',
        'career': '适合需要关怀和创造力的工作。护理、教育、心理咨询、餐饮、房地产等领域都能让你发挥所长。你的同理心是最大的优势。',
        'lucky_number': '2', 'lucky_color': '银色、白色',
        'best_match': '天蝎座、双鱼座、金牛座', 'advice': '学会放手，不要过度保护。给自己更多的独立空间，你会变得更强大。'
    },
    'Leo': {
        'traits': ['自信大方', '慷慨豪爽', '天生王者', '热爱舞台'],
        'personality': '狮子座天生自带王者光环。你自信大方，在任何场合都能成为焦点。你慷慨豪爽，对朋友忠诚义气，是值得信赖的伙伴。你有着强烈的创造力和表现欲，喜欢在舞台上发光发热。',
        'strengths': '领导力强、自信大方、慷慨忠诚、创造力丰富',
        'weaknesses': '过于骄傲、需要关注、有时霸道、不够细腻',
        'love': '感情中热情而浪漫，喜欢制造惊喜和仪式感。对伴侣慷慨大方，会尽全力让对方感到幸福和被爱。忠诚度极高。',
        'career': '适合需要领导力和创造力的工作。演艺、管理、政治、时尚、娱乐等领域都是你的舞台。你天生就是被人仰望的存在。',
        'lucky_number': '1', 'lucky_color': '金色、橙色',
        'best_match': '白羊座、射手座、天秤座', 'advice': '学会倾听，不要总是占据中心位置。真正的王者不需要时刻证明自己。'
    },
    'Virgo': {
        'traits': ['细致认真', '追求完美', '善于分析', '脚踏实地'],
        'personality': '处女座是最值得信赖的星座。你做事细致认真，注重细节，追求完美。你有极强的分析能力和组织能力，能把复杂的事情理出头绪。你务实低调，用实际行动证明自己的价值。',
        'strengths': '细心负责、分析能力强、务实低调、追求卓越',
        'weaknesses': '过于挑剔、容易焦虑、完美主义、有时过于拘谨',
        'love': '感情中细腻而周到，喜欢用细心和行动来表达爱意。虽然不太会甜言蜜语，但每一个细节都透露着你的深情。',
        'career': '适合需要精细和专业性的工作。医疗、会计、编辑、科研、质量管理等领域都能让你大放异彩。你的严谨和专业是无价之宝。',
        'lucky_number': '7', 'lucky_color': '米色、墨绿',
        'best_match': '金牛座、摩羯座、天蝎座', 'advice': '对自己和他人都多一些宽容。完美是追求的方向，不是评判的标准。'
    },
    'Libra': {
        'traits': ['优雅迷人', '追求和谐', '公正客观', '审美出众'],
        'personality': '天秤座是最优雅迷人的星座。你追求平衡与和谐，有着天生的外交天赋和审美品味。你重视公平正义，总能从客观的角度看问题。你的社交能力出众，能在不同的人群中游刃有余。',
        'strengths': '社交能力强、审美出众、公正客观、善于调解',
        'weaknesses': '优柔寡断、过于讨好、逃避冲突、有时虚荣',
        'love': '感情中浪漫而优雅，追求灵魂伴侣般的完美爱情。你重视伴侣的外在条件和内在品质，希望两个人在一起是最佳拍档。',
        'career': '适合需要审美和社交能力的工作。法律、外交、设计、艺术、公共关系等领域都能发挥你的优势。你天生就是关系的艺术家。',
        'lucky_number': '8', 'lucky_color': '粉色、浅蓝',
        'best_match': '双子座、水瓶座、狮子座', 'advice': '学会做决定，不要害怕冲突。有时候不完美的选择也比犹豫不决要好。'
    },
    'Scorpio': {
        'traits': ['神秘深邃', '意志坚定', '洞察力强', '感情强烈'],
        'personality': '天蝎座是最具神秘感的星座。你意志坚定，一旦确定目标就不会轻易放弃。你有惊人的洞察力，能看透事物的本质。你的感情深沉而强烈，爱恨分明，是最忠诚也最可怕的对手。',
        'strengths': '意志力强、洞察力敏锐、忠诚专一、感情深沉',
        'weaknesses': '占有欲强、容易嫉妒、记仇、控制欲强',
        'love': '感情中炽热而深沉，要么不爱，要爱就爱到骨子里。你对伴侣的忠诚度极高，但也要求同样的回馈。你的爱是致命的。',
        'career': '适合需要深度和洞察力的工作。侦探、心理研究、金融分析、外科医生、调查记者等领域都是你的主场。',
        'lucky_number': '4', 'lucky_color': '深红、黑色',
        'best_match': '巨蟹座、双鱼座、处女座', 'advice': '学会信任和放手。不是所有事情都需要掌控，有时候信任本身就是最大的力量。'
    },
    'Sagittarius': {
        'traits': ['自由奔放', '乐观开朗', '热爱冒险', '哲学思考'],
        'personality': '射手座是最自由奔放的星座。你乐观开朗，热爱自由，不喜欢被任何事物束缚。你对世界充满好奇，喜欢探索未知领域，追求人生的意义和真理。你有着哲学家般的思考深度。',
        'strengths': '乐观开朗、视野开阔、诚实坦率、热爱学习',
        'weaknesses': '过于自由、缺乏责任、有时粗心、说话直接',
        'love': '感情中需要自由和空间，不喜欢被束缚。你希望伴侣能和你一起探索世界，共同成长。你的乐观和幽默是最好的感情催化剂。',
        'career': '适合需要创新和探索的工作。旅行、教育、出版、哲学研究、国际贸易等领域都能让你大展身手。',
        'lucky_number': '3', 'lucky_color': '紫色、蓝色',
        'best_match': '白羊座、狮子座、天秤座', 'advice': '在追求自由的同时，也要学会承担责任。承诺不是枷锁，而是另一种飞翔的方式。'
    },
    'Capricorn': {
        'traits': ['坚韧不拔', '野心勃勃', '沉稳内敛', '责任心强'],
        'personality': '摩羯座是最坚韧不拔的星座。你目标明确，意志坚定，有着超越常人的毅力和耐力。你沉稳内敛，用实际行动证明自己。事业心强，不怕吃苦，为了目标可以付出比任何人更多的努力。',
        'strengths': '坚韧毅力强、目标明确、责任心强、务实可靠',
        'weaknesses': '过于严肃、不善表达、有时过于功利、压力大',
        'love': '感情中慢热但忠诚，一旦认定就绝不回头。你用行动和时间证明爱的深度，是值得托付一生的伴侣。虽然不太浪漫，但胜在稳定可靠。',
        'career': '适合需要长远规划和管理能力的工作。企业管理、政府、建筑、金融、工程等领域都能让你逐步登上巅峰。',
        'lucky_number': '10', 'lucky_color': '棕色、黑色',
        'best_match': '金牛座、处女座、双鱼座', 'advice': '工作之余别忘了享受生活。成功的定义不止一个，健康和快乐同样重要。'
    },
    'Aquarius': {
        'traits': ['独立创新', '人道主义', '思维超前', '特立独行'],
        'personality': '水瓶座是最具创新精神的星座。你独立思考，不走寻常路，总是走在时代的前沿。你有着强烈的人道主义精神，关心社会公平和人类未来。你的思维方式独特，常常能提出令人耳目一新的见解。',
        'strengths': '思维创新、独立自主、关心他人、胸怀广阔',
        'weaknesses': '过于理想化、情感疏离、有时叛逆、难以捉摸',
        'love': '感情中需要精神上的独立和自由。你希望伴侣是灵魂层面的伙伴，能和你一起讨论人生、社会和未来。你的爱是理性和感性的完美结合。',
        'career': '适合需要创新和独立思考的工作。科技、发明、社会活动、航天、网络、心理学等领域都能让你发挥天赋。',
        'lucky_number': '11', 'lucky_color': '天蓝、银色',
        'best_match': '双子座、天秤座、射手座', 'advice': '在追求理想的同时，也要关注身边人的感受。改变世界从改变自己开始。'
    },
    'Pisces': {
        'traits': ['浪漫多情', '善解人意', '艺术天赋', '直觉超群'],
        'personality': '双鱼座是最具艺术气质的星座。你浪漫多情，想象力丰富，有着超凡的艺术天赋。你善解人意，总能感受到他人的情绪。你的直觉超群，仿佛与另一个维度的世界有着神秘的联系。',
        'strengths': '善解人意、艺术天赋、直觉敏锐、想象力丰富',
        'weaknesses': '过于感性、容易逃避、缺乏主见、有时过于软弱',
        'love': '感情中浪漫而深情，全身心地投入爱情。你是十二星座中最懂得爱的星座，能给予伴侣最温柔最深情的陪伴。',
        'career': '适合需要创造力和同理心的工作。艺术、音乐、写作、心理咨询、慈善、灵性导师等领域都能让你发光。',
        'lucky_number': '12', 'lucky_color': '海蓝、薰衣草',
        'best_match': '天蝎座、巨蟹座、金牛座', 'advice': '学会建立界限，不要为了取悦他人而迷失自己。你的善良需要配上坚定的力量。'
    }
}

def divine_constellation_profile(birth_info, question=''):
    """星座个人性格分析"""
    month = birth_info.get('birth_month', 0)
    day = birth_info.get('birth_day', 0)
    if not month or not day:
        return {'score': 0, 'summary': '需要您的出生日期', 'sections': []}
    
    sign, cn, emoji, elem, qual = _get_sun_sign(month, day)
    p = SIGN_PERSONALITY.get(sign, {})
    
    sections = [
        {'title': '核心性格', 'content':
            '你是%s %s，属于%s%s。\\n\\n%s' % (cn, emoji, ELEM_CN[elem], QUAL_CN[qual] + '宫', p.get('personality', ''))},
        {'title': '性格特质', 'content':
            '【关键词】%s\\n\\n'
            '**优势**：%s\\n**短板**：%s' % (
            '、'.join(p.get('traits', [])), p.get('strengths', ''), p.get('weaknesses', ''))},
        {'title': '爱情观', 'content': p.get('love', '')},
        {'title': '事业方向', 'content': p.get('career', '')},
        {'title': '幸运指南', 'content':
            '**幸运数字**：%s\\n**幸运色**：%s\\n**最佳星座拍档**：%s' % (
            p.get('lucky_number', ''), p.get('lucky_color', ''), p.get('best_match', ''))},
        {'title': '人生建议', 'content': p.get('advice', '')},
    ]
    return {'score': 0, 'summary': '%s %s 的星座性格分析' % (cn, emoji), 'sections': sections, 'tags': [cn]}


# ═══════════════════════════════════════════════════════════
# 星座今日运势
# ═══════════════════════════════════════════════════════════

DAILY_DIMS = ['综合运势', '爱情运势', '事业运势', '财运运势']

# 运势内容池 - 每个维度每种级别都有多条，按日期+星座hash选一条
FORTUNE_POOL = {
    'high': {
        '综合运势': [
            '今天整体运势非常好，适合做出重要决定。你的直觉和判断力都处于高水平，把握住今天的好时机。',
            '今天是个充满机遇的日子，贵人运旺盛，会遇到意想不到的好消息。保持积极心态，好运自然来。',
            '星象对你格外友好，今天无论做什么都有事半功倍的效果。适合推进重要项目或做出长期规划。',
            '今天能量满满，信心十足。你的魅力和影响力达到巅峰，是展现自己、争取机会的最佳时机。',
        ],
        '爱情运势': [
            '桃花运旺盛的一天！单身的你可能会遇到令你心动的人。有伴侣的你感情甜蜜度飙升，适合制造浪漫惊喜。',
            '今天感情运势极佳，你散发出迷人的魅力。适合表白或推进感情关系，对方会被你的真诚打动。',
            '爱情的甜蜜能量环绕着你。适合和伴侣共度美好时光，一次深入的对话可能让感情更进一步。',
            '今天你的温柔和体贴格外动人，对方会被你深深吸引。感情的火花随时可能绽放。',
        ],
        '事业运势': [
            '事业运大旺！今天在工作中会获得认可和赞赏。适合提出新方案或争取重要项目。',
            '今天工作效率极高，思维清晰，灵感不断。你的能力和表现会被上级注意到，升职加薪指日可待。',
            '职场贵人运强，可能会得到前辈或领导的关键指导。把握住今天的每个机会。',
            '今天适合做重要的汇报或展示。你的表达能力和说服力处于巅峰状态。',
        ],
        '财运运势': [
            '财运亨通的一天！可能会有意外收入或好的投资机会。但也要注意理性消费，不要冲动购物。',
            '今天偏财运不错，可能会收到红包或奖金。适合制定理财计划，为未来做好财务规划。',
            '金钱运势良好，之前的投资可能开始有回报。适合关注稳健的理财机会。',
            '今天消费时可能有优惠或折扣，适合做重要的购买决定。但切忌贪小便宜吃大亏。',
        ],
    },
    'mid': {
        '综合运势': [
            '今天运势平稳，没有大起大落。适合处理日常事务，保持良好的心态比什么都重要。',
            '今天整体还不错，但需要主动出击。好运不会自己找上门来，把握住身边的每个机会。',
            '星象显示今天适合稳步推进计划。不需要急于求成，按部就班就能取得不错的效果。',
            '今天状态中等偏上，关键在于心态。保持积极乐观，小确幸也会给你带来好心情。',
        ],
        '爱情运势': [
            '感情运势平稳，没有大的波动。适合和伴侣进行日常的沟通和交流，维持感情的稳定。',
            '今天感情方面没有特别的亮点，但也不差。可以主动关心对方，小小的举动就能温暖人心。',
            '桃花运一般，不急不躁。与其刻意寻找，不如先做好自己，吸引力自然会提升。',
            '感情需要一点小惊喜来调味。今天的你可以尝试用不同的方式表达爱意。',
        ],
        '事业运势': [
            '工作运势平稳，今天适合处理常规任务。不急于求新求变，把基础打扎实更重要。',
            '今天工作效率一般，可能会遇到一些小阻碍。保持耐心，逐一解决即可。',
            '职场今天没有大的变化，适合做好手头的事。下班后可以考虑学习新技能提升自己。',
            '工作状态中规中矩，但你的稳定输出本身就是一种优势。坚持就是胜利。',
        ],
        '财运运势': [
            '财运平稳，适合做日常的收支管理。不建议今天做大的投资决定，先观望为妙。',
            '今天收入支出基本持平。适合审视近期的消费习惯，合理规划接下来的开支。',
            '金钱方面没有大的波动，适合制定长期的理财目标。积少成多是今天的主题。',
            '今天不太适合冲动消费，看到想买的东西可以先加入购物清单冷静一下。',
        ],
    },
    'low': {
        '综合运势': [
            '今天可能会遇到一些小挑战，保持冷静是关键。逆境中往往隐藏着转机，换个角度看问题。',
            '今天运势偏低，建议低调行事。避免与人争论，多听少说，减少不必要的冲突。',
            '今天可能感到精力不足或状态不佳。给自己一些休息和恢复的时间，不要勉强自己。',
            '星象提醒你今天放慢节奏。退一步海阔天空，有些事情等一等反而有更好的结果。',
        ],
        '爱情运势': [
            '感情运势偏弱，今天容易产生误会。沟通时多注意措辞，避免说出让自己后悔的话。',
            '今天不适合讨论重要的感情话题。双方情绪都不太稳定，等到气消了再谈会更有效。',
            '桃花运低迷的一天。与其强求感情，不如先照顾好自己的情绪和状态。',
            '感情中可能出现小摩擦，关键是要学会换位思考。多一份理解，少一份抱怨。',
        ],
        '事业运势': [
            '工作中可能遇到阻碍或被误解。保持专业态度，用实力说话比解释更有效。',
            '今天工作效率偏低，注意力不集中。建议优先处理重要紧急的事务，其他的事情可以延后。',
            '职场中今天尽量少说话多做事。避免卷入办公室的是非纷争，专注自己的工作。',
            '今天可能面临一些工作压力，适当休息很重要。不要硬撑，合理分配精力。',
        ],
        '财运运势': [
            '今天财运欠佳，需要控制消费欲望。看到促销打折也不要冲动购买，买回来可能后悔。',
            '金钱方面需要谨慎。避免借钱给他人或做冒险投资，稳妥为先。',
            '今天不适合做重要的财务决定。先观察市场走向，等运势回升时再行动。',
            '可能会有意料之外的开销，建议提前做好预算。量入为出是今天的财务准则。',
        ],
    }
}

def divine_constellation_daily(birth_info, question=''):
    """星座今日运势"""
    month = birth_info.get('birth_month', 0)
    day = birth_info.get('birth_day', 0)
    if not month or not day:
        return {'score': 0, 'summary': '需要您的出生日期', 'sections': []}
    
    sign, cn, emoji, elem, qual = _get_sun_sign(month, day)
    
    # 用日期+星座作为伪随机种子，确保同一天同一星座结果一致
    import datetime, hashlib
    today = datetime.date.today()
    seed_str = '%s-%s-%d-%02d-%02d' % (sign, today.year, today.month, today.day, today.timetuple().tm_yday)
    seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    
    import random
    rng = random.Random(seed)
    
    sections = []
    dim_scores = {}
    for dim in DAILY_DIMS:
        # 随机选运势级别
        r = rng.random()
        if r < 0.25:
            level, score, stars = 'high', rng.randint(80, 98), rng.randint(4, 5)
        elif r < 0.65:
            level, score, stars = 'mid', rng.randint(50, 79), rng.randint(3, 4)
        else:
            level, score, stars = 'low', rng.randint(20, 49), rng.randint(1, 2)
        
        dim_scores[dim] = score
        
        pool = FORTUNE_POOL[level][dim]
        content = pool[rng.randint(0, len(pool) - 1)]
        sections.append({'title': dim, 'content': '**运势指数**：%d/100 %s\\n\\n%s' % (score, '★' * stars + '☆' * (5 - stars), content)})
    
    avg_score = sum(dim_scores.values()) // 4
    if avg_score >= 75:
        advice = '今天整体运势很不错，抓住机会积极行动！适合处理重要事务和推进关键计划。'
    elif avg_score >= 50:
        advice = '今天运势中规中矩，保持平常心稳步推进。适合处理日常事务和学习充电。'
    else:
        advice = '今天运势偏低，建议低调行事，给自己一些休息时间。遇到困难不要硬扛，寻求帮助是明智的选择。'
    
    sections.append({'title': '今日建议', 'content': advice})
    
    return {'score': avg_score, 'summary': '%s %s 今日运势指数%d分' % (cn, emoji, avg_score), 'sections': sections, 'tags': [cn]}
