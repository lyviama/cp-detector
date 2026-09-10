"""
六爻起卦排盘模块（idolship 追星专用）
=====================================
- 起卦法：三数起卦（用户输入 a, b, c 三个数字）
- 上卦 = a % 8（取先天八卦数 1-8，0 坤）
- 下卦 = b % 8
- 动爻 = (c % 6) + 1（1-6 爻）
- 用神：根据事件类型自动选取（妻财/父母/官鬼/兄弟/子孙）
- 旺衰：按月令（春夏秋冬四季月）定旺相休囚死
- 评分：用神旺衰 + 动爻生克 → 1-5 星
"""
import datetime

# ─────────────────────────────────────────────────────────
# 先天八卦（数、五行、爻象从下到上）
# ─────────────────────────────────────────────────────────
BAGUA = {
    1: {'name': '乾', 'wx': '金', 'lines': [1, 1, 1], 'symbol': '☰', 'nature': '天'},
    2: {'name': '兑', 'wx': '金', 'lines': [1, 1, 0], 'symbol': '☱', 'nature': '泽'},
    3: {'name': '离', 'wx': '火', 'lines': [1, 0, 1], 'symbol': '☲', 'nature': '火'},
    4: {'name': '震', 'wx': '木', 'lines': [1, 0, 0], 'symbol': '☳', 'nature': '雷'},
    5: {'name': '巽', 'wx': '木', 'lines': [0, 1, 1], 'symbol': '☴', 'nature': '风'},
    6: {'name': '坎', 'wx': '水', 'lines': [0, 1, 0], 'symbol': '☵', 'nature': '水'},
    7: {'name': '艮', 'wx': '土', 'lines': [0, 0, 1], 'symbol': '☶', 'nature': '山'},
    8: {'name': '坤', 'wx': '土', 'lines': [0, 0, 0], 'symbol': '☷', 'nature': '地'},
}

# ─────────────────────────────────────────────────────────
# 64 卦表：key=(上卦数, 下卦数) → 卦名
# ─────────────────────────────────────────────────────────
HEXAGRAM_NAMES = {
    (1,1): '乾为天', (1,2): '天泽履', (1,3): '天火同人', (1,4): '天雷无妄',
    (1,5): '天风姤', (1,6): '天水讼', (1,7): '天山遁', (1,8): '天地否',
    (2,1): '泽天夬', (2,2): '兑为泽', (2,3): '泽火革', (2,4): '泽雷随',
    (2,5): '泽风大过', (2,6): '泽水困', (2,7): '泽山咸', (2,8): '泽地萃',
    (3,1): '火天大有', (3,2): '火泽睽', (3,3): '离为火', (3,4): '火雷噬嗑',
    (3,5): '火风鼎', (3,6): '火水未济', (3,7): '火山旅', (3,8): '火地晋',
    (4,1): '雷天大壮', (4,2): '雷泽归妹', (4,3): '雷火丰', (4,4): '震为雷',
    (4,5): '雷风恒', (4,6): '雷水解', (4,7): '雷山小过', (4,8): '雷地豫',
    (5,1): '风天小畜', (5,2): '风泽中孚', (5,3): '风火家人', (5,4): '风雷益',
    (5,5): '巽为风', (5,6): '风水涣', (5,7): '风山渐', (5,8): '风地观',
    (6,1): '水天需', (6,2): '水泽节', (6,3): '水火既济', (6,4): '水雷屯',
    (6,5): '水风井', (6,6): '坎为水', (6,7): '水山蹇', (6,8): '水地比',
    (7,1): '山天大畜', (7,2): '山泽损', (7,3): '山火贲', (7,4): '山雷颐',
    (7,5): '山风蛊', (7,6): '山水蒙', (7,7): '艮为山', (7,8): '山地剥',
    (8,1): '地天泰', (8,2): '地泽临', (8,3): '地火明夷', (8,4): '地雷复',
    (8,5): '地风升', (8,6): '地水师', (8,7): '地山谦', (8,8): '坤为地',
}

# 京房八宫归属（每卦属于哪个宫 → 决定六亲"我"五行）
PALACE_WX = {
    # 乾宫（金）
    (1,1):'金',(1,5):'金',(1,7):'金',(1,8):'金',(5,8):'金',(7,8):'金',(3,8):'金',(3,1):'金',
    # 兑宫（金）
    (2,2):'金',(2,6):'金',(2,8):'金',(2,7):'金',(6,7):'金',(8,7):'金',(4,7):'金',(4,2):'金',
    # 离宫（火）
    (3,3):'火',(3,7):'火',(3,5):'火',(3,6):'火',(7,6):'火',(5,6):'火',(1,6):'火',(1,3):'火',
    # 震宫（木）
    (4,4):'木',(4,8):'木',(4,6):'木',(4,5):'木',(8,5):'木',(6,5):'木',(2,5):'木',(2,4):'木',
    # 巽宫（木）
    (5,5):'木',(5,1):'木',(5,3):'木',(5,4):'木',(1,4):'木',(3,4):'木',(7,4):'木',(7,5):'木',
    # 坎宫（水）
    (6,6):'水',(6,2):'水',(6,4):'水',(6,3):'水',(2,3):'水',(4,3):'水',(8,3):'水',(8,6):'水',
    # 艮宫（土）
    (7,7):'土',(7,3):'土',(7,1):'土',(7,2):'土',(3,2):'土',(1,2):'土',(5,2):'土',(5,7):'土',
    # 坤宫（土）
    (8,8):'土',(8,4):'土',(8,2):'土',(8,1):'土',(4,1):'土',(2,1):'土',(6,1):'土',(6,8):'土',
}

# 卦辞（简短），每个事件类型可读出"总运势"基调
HEXAGRAM_TEXT = {
    '乾为天': '元亨利贞，刚健中正，大吉之卦',
    '坤为地': '厚德载物，柔顺包容，宜静守',
    '水雷屯': '初难后解，需耐心待时',
    '山水蒙': '蒙昧求明，宜请教学习',
    '水天需': '等待时机，密云不雨',
    '天水讼': '争讼是非，宜和解',
    '地水师': '统率有方，谋略可行',
    '水地比': '亲附团结，人际和谐',
    '风天小畜': '小有积蓄，力量初聚',
    '天泽履': '踩虎尾不咥人，慎行无害',
    '地天泰': '天地交泰，万事通达，大吉',
    '天地否': '天地不交，闭塞不顺',
    '天火同人': '同心同德，人际和谐，吉',
    '火天大有': '大有所获，盛大有成，吉',
    '地山谦': '谦逊低调，可保长久',
    '雷地豫': '欢乐愉悦，利于行动',
    '泽雷随': '随顺时机，变通为宜',
    '山风蛊': '积弊需治，整饬革新',
    '地泽临': '居高临下，势有所成',
    '风地观': '观察体悟，宜静观',
    '火雷噬嗑': '咬合障碍，需努力突破',
    '山火贲': '修饰文采，表面光鲜',
    '山地剥': '剥落衰败，宜守不宜进',
    '地雷复': '一阳来复，转机初现，吉',
    '天雷无妄': '守正勿妄，无往不利',
    '山天大畜': '大有所蓄，积聚力量，吉',
    '山雷颐': '养身养德，正道养育',
    '泽风大过': '负担过重，量力而行',
    '坎为水': '重险重叠，宜谨慎',
    '离为火': '光明附丽，宜有所为',
    '泽山咸': '感应相合，情意相通，吉',
    '雷风恒': '持之以恒，长久不变',
    '天山遁': '退避隐遁，宜暂时抽身',
    '雷天大壮': '声势浩大，刚强有力',
    '火地晋': '晋升上进，光明前行，吉',
    '地火明夷': '光明受伤，宜韬光养晦',
    '风火家人': '家人同心，内务和睦，吉',
    '火泽睽': '乖违背离，事有违逆',
    '水山蹇': '行路艰难，进退两难',
    '雷水解': '险难消解，困局得舒，吉',
    '山泽损': '减损奉献，先难后易',
    '风雷益': '有所增益，利有攸往，吉',
    '泽天夬': '果决断除，需果断行事',
    '天风姤': '不期而遇，防小人',
    '泽地萃': '人才聚集，汇萃一堂，吉',
    '地风升': '顺势上升，步步高升，吉',
    '泽水困': '困境受围，宜守拙待时',
    '水风井': '井养不穷，源源不绝',
    '泽火革': '变革革新，去故取新',
    '火风鼎': '鼎新树立，稳固成器，吉',
    '震为雷': '震动惊醒，处变不惊',
    '艮为山': '适时停止，宜静守',
    '风山渐': '循序渐进，稳步推进，吉',
    '雷泽归妹': '位置不正，宜守本分',
    '雷火丰': '丰盛圆满，盛极需慎',
    '火山旅': '行旅在外，宜随遇而安',
    '巽为风': '柔顺渗透，顺风进退',
    '兑为泽': '喜悦相随，和悦相处，吉',
    '风水涣': '涣散消解，宜重新凝聚',
    '水泽节': '节制有度，适可而止',
    '风泽中孚': '诚信中肯，感人肺腑，吉',
    '雷山小过': '小有过越，宜小不宜大',
    '水火既济': '已成定局，宜防患未然',
    '火水未济': '尚未完成，需继续推进',
}

# ─────────────────────────────────────────────────────────
# 事件类型 → 用神（六亲）
# ─────────────────────────────────────────────────────────
EVENT_YONGSHEN = {
    'sign_lottery': '妻财',   # 抽签/抽票：求物求财
    'ticket':       '妻财',   # 抢票：财物
    'offline':      '父母',   # 线下接送机：行程文书
    'fansign':      '官鬼',   # 签售见面会：偶像（上位者）
    'overseas':     '父母',   # 海外：行程
    'health':      '官鬼',   # 健康：官鬼为病症（子孙为医药），20260824b
    'idol_joy':    '子孙',   # 追星·快乐源泉(娱乐/辱追)：福神主快乐解压，20260825cc
    'idol_friend': '兄弟',   # 追星·像朋友：平辈同担，20260825cc
}

# 六亲映射（"我"五行 → 该五行对应哪个六亲）
def _liuqin_of(other_wx, me_wx):
    """返回 other_wx 对 me_wx 的六亲关系"""
    if other_wx == me_wx:
        return '兄弟'
    # 我生
    sheng = {'木':'火','火':'土','土':'金','金':'水','水':'木'}
    if sheng.get(me_wx) == other_wx:
        return '子孙'
    # 生我
    if sheng.get(other_wx) == me_wx:
        return '父母'
    # 我克
    ke = {'木':'土','火':'金','土':'水','金':'木','水':'火'}
    if ke.get(me_wx) == other_wx:
        return '妻财'
    # 克我
    if ke.get(other_wx) == me_wx:
        return '官鬼'
    return '兄弟'

# 月令旺衰（春木、夏火、秋金、冬水、四季月土）
SEASON_WANG = {
    '春': {'旺':'木','相':'火','休':'水','囚':'金','死':'土'},
    '夏': {'旺':'火','相':'土','休':'木','囚':'水','死':'金'},
    '秋': {'旺':'金','相':'水','休':'土','囚':'火','死':'木'},
    '冬': {'旺':'水','相':'木','休':'金','囚':'土','死':'火'},
    '季月': {'旺':'土','相':'金','休':'火','囚':'木','死':'水'},
}

SEASON_LABEL = {'春':'春季','夏':'夏季','秋':'秋季','冬':'冬季','季月':'四季月'}

def _season_of(date):
    """按节气定月支→季节（正统：辰戌丑未月=四季月/土旺，非公历月份）。
    节气取近似日(误差1-2天)：立春2/4 清明4/4 立夏5/5 小暑7/6 立秋8/7 寒露10/8 立冬11/7 小寒1/5
    """
    m, d = date.month, date.day
    if (m == 2 and d >= 4) or m == 3 or (m == 4 and d < 4): return '春'    # 寅卯月 木旺
    if (m == 4 and d >= 4) or (m == 5 and d < 5): return '季月'            # 辰月 土旺
    if (m == 5 and d >= 5) or m == 6 or (m == 7 and d < 6): return '夏'    # 巳午月 火旺
    if (m == 7 and d >= 6) or (m == 8 and d < 7): return '季月'            # 未月 土旺
    if (m == 8 and d >= 7) or m == 9 or (m == 10 and d < 8): return '秋'   # 申酉月 金旺
    if (m == 10 and d >= 8) or (m == 11 and d < 7): return '季月'          # 戌月 土旺
    if (m == 11 and d >= 7) or m == 12 or (m == 1 and d < 5): return '冬'  # 亥子月 水旺
    return '季月'  # 丑月(1/5~2/4) 土旺

WANG_SCORE = {'旺': 2, '相': 1, '休': 0, '囚': -1, '死': -2}

# ── 20260825ff: 日辰干支 + 旬空/月破/日冲/日合（纯历法推算；只加附加键, 不改旧键不改评分）──
GAN = '甲乙丙丁戊己庚辛壬癸'
ZHI_ALL = '子丑寅卯辰巳午未申酉戌亥'
CHONG = {'子':'午','午':'子','丑':'未','未':'丑','寅':'申','申':'寅','卯':'酉','酉':'卯','辰':'戌','戌':'辰','巳':'亥','亥':'巳'}
LIUHE = {'子':'丑','丑':'子','寅':'亥','亥':'寅','卯':'戌','戌':'卯','辰':'酉','酉':'辰','巳':'申','申':'巳','午':'未','未':'午'}
# 20260827kk: 相刑(三刑两两相见+子卯互刑+辰午酉亥自刑) / 六害 / 支五行(断日月生克)
XING_PAIRS = {('寅','巳'),('巳','寅'),('巳','申'),('申','巳'),('申','寅'),('寅','申'),
              ('丑','戌'),('戌','丑'),('戌','未'),('未','戌'),('未','丑'),('丑','未'),
              ('子','卯'),('卯','子'),('辰','辰'),('午','午'),('酉','酉'),('亥','亥')}
HAI = {'子':'未','未':'子','丑':'午','午':'丑','寅':'巳','巳':'寅','卯':'辰','辰':'卯','申':'亥','亥':'申','酉':'戌','戌':'酉'}
ZHI_WX = {'子':'水','丑':'土','寅':'木','卯':'木','辰':'土','巳':'火','午':'火','未':'土','申':'金','酉':'金','戌':'土','亥':'水'}
WX_SHENG = {'金':'水','水':'木','木':'火','火':'土','土':'金'}
WX_KE = {'金':'木','木':'土','土':'水','水':'火','火':'金'}
# 日干支锚点: 1949-10-01=甲子日（历法公认；与 2000-01-01=戊午日互证一致）
_DAY_ANCHOR = datetime.date(1949, 10, 1)
# 月支近似节气日（与 _season_of 同源精度, 交界±1-2天误差）
_JIE_EDGES = [(1,5,'丑'),(2,4,'寅'),(3,6,'卯'),(4,4,'辰'),(5,5,'巳'),(6,6,'午'),(7,6,'未'),(8,7,'申'),(9,7,'酉'),(10,8,'戌'),(11,7,'亥'),(12,7,'子')]

def _yuezhi_of(date):
    m, d = date.month, date.day
    z = '子'  # 12/7 大雪后 ~ 次年 1/5 小寒前 = 子月
    for em, ed, ez in _JIE_EDGES:
        if m == em and d >= ed:
            return ez
        if m > em:
            z = ez
    return z

def _apply_day_info(cast):
    x = {'day_gz': '', 'day_zhi': '', 'xunkong': '', 'yuezhi': '', 'lines_marks': [''] * 6}
    try:
        ds = str(cast.get('event_date') or datetime.date.today().strftime('%Y-%m-%d'))[:10]
        d = datetime.datetime.strptime(ds, '%Y-%m-%d').date()
        idx = (d.toordinal() - _DAY_ANCHOR.toordinal()) % 60
        day_zhi = ZHI_ALL[idx % 12]
        day_gz = GAN[idx % 10] + day_zhi
        shou_zhi = (idx - idx % 10) % 12                     # 旬首地支
        xunkong = ZHI_ALL[(shou_zhi - 2) % 12] + ZHI_ALL[(shou_zhi - 1) % 12]
        yuezhi = _yuezhi_of(d)
        po = CHONG[yuezhi]                                    # 月破支
        rc = CHONG[day_zhi]                                   # 日冲支
        rh = LIUHE[day_zhi]                                   # 日合支
        marks = []
        mwx0 = ZHI_WX[yuezhi]                                    # 20260827kk: 月建五行
        dwx0 = ZHI_WX[day_zhi]                                   # 日辰(支)五行
        for dz in (cast.get('lines_dz') or []):
            t = ''
            if dz and dz in xunkong: t += '空'
            if dz and dz == po: t += '破'
            if dz and dz == rc: t += '冲'
            if dz and dz == rh: t += '合'
            if dz and (dz, day_zhi) in XING_PAIRS: t += '刑'
            if dz and HAI.get(day_zhi) == dz: t += '害'
            if dz:
                ywx = ZHI_WX[dz]
                if WX_KE[dwx0] == ywx: t += '日克'
                if WX_KE[mwx0] == ywx: t += '月克'
                if WX_SHENG[dwx0] == ywx: t += '日生'
                if WX_SHENG[mwx0] == ywx: t += '月生'
            if len(t) > 4:                                       # 截断保排版: 优先级空>破>冲>合>刑>害>克>生
                _order = ['空','破','冲','合','刑','害','日克','月克','日生','月生']
                _toks, _rest, _i = [], t, 0
                while _i < len(_rest):
                    for _tk in _order:
                        if _rest.startswith(_tk, _i):
                            _toks.append(_tk); _i += len(_tk); break
                    else:
                        _i += 1
                t = ''.join(_toks[:4])
            marks.append(t)
        while len(marks) < 6:
            marks.append('')
        x = {'day_gz': day_gz, 'day_zhi': day_zhi, 'xunkong': xunkong, 'yuezhi': yuezhi, 'lines_marks': marks}
    except Exception:
        pass
    cast.update(x)
    return cast

# 六爻地支配法（每爻一个地支，决定该爻五行）
YANG_DZ = ['子', '寅', '辰', '午', '申', '戌']  # 阳爻（从初到上）
YIN_DZ = ['未', '巳', '卯', '丑', '亥', '酉']   # 阴爻（从初到上）
DZ_TO_WX = {'子':'水','丑':'土','寅':'木','卯':'木','辰':'土','巳':'火',
            '午':'火','未':'土','申':'金','酉':'金','戌':'土','亥':'水'}

# ─────────────────────────────────────────────────────────
# 起卦核心
# ─────────────────────────────────────────────────────────
def cast_hexagram(a, b, c, event_date=None):
    """三数起卦，返回完整卦盘 dict
    a, b, c: 用户输入的三个数字
    event_date: datetime.date（用于月令旺衰）
    """
    if event_date is None:
        event_date = datetime.date.today()

    # 0 → 8（坤），其它 1-7 → 乾~艮
    upper_idx = a % 8 or 8
    lower_idx = b % 8 or 8
    moving = (c % 6) + 1  # 1-6

    upper = BAGUA[upper_idx]
    lower = BAGUA[lower_idx]

    # 6 爻（从下到上）：下卦初二三 + 上卦四五上
    lines = list(lower['lines']) + list(upper['lines'])  # [初, 二, 三, 四, 五, 上]

    name = HEXAGRAM_NAMES.get((upper_idx, lower_idx), '未知卦')
    palace_wx = PALACE_WX.get((upper_idx, lower_idx), '土')

    # 每爻地支 + 五行（按阴阳配支）
    lines_dz = []
    lines_wx = []
    for i, line in enumerate(lines):
        dz = YANG_DZ[i] if line == 1 else YIN_DZ[i]
        lines_dz.append(dz)
        lines_wx.append(DZ_TO_WX[dz])

    # 每爻六亲（按地支五行 vs 宫五行）
    liuqin_lines = [_liuqin_of(wx, palace_wx) for wx in lines_wx]

    # 变卦：动爻阴阳互换
    changed_lines = list(lines)
    changed_lines[moving - 1] = 0 if changed_lines[moving - 1] == 1 else 1

    # 变卦的上下卦
    new_lower_lines = changed_lines[:3]
    new_upper_lines = changed_lines[3:]
    new_upper_idx = _idx_from_lines(new_upper_lines)
    new_lower_idx = _idx_from_lines(new_lower_lines)
    changed_name = HEXAGRAM_NAMES.get((new_upper_idx, new_lower_idx), '未知卦')

    # 月令旺衰
    season = _season_of(event_date)
    season_map = SEASON_WANG[season]

    # 用神
    event_type_default = 'sign_lottery'
    yongshen = EVENT_YONGSHEN.get(event_type_default, '妻财')

    # 用神在哪几爻
    yongshen_positions = [i + 1 for i, lq in enumerate(liuqin_lines) if lq == yongshen]

    # 用神五行 = "我"的五行的对应（用神是哪个五行）
    yongshen_wx = _wx_of_liuqin(yongshen, palace_wx)

    # 用神旺衰（season_map 的键是状态名，值是五行 → 反查）
    yongshen_state = '休'
    for state_name, wx_val in season_map.items():
        if wx_val == yongshen_wx:
            yongshen_state = state_name
            break
    yongshen_score = WANG_SCORE.get(yongshen_state, 0)

    # 动爻发动情况
    moving_liuqin = liuqin_lines[moving - 1]
    moving_wx = lines_wx[moving - 1]
    moving_dz = lines_dz[moving - 1]

    # 动爻与用神的生克
    moving_relation = _rel_to(moving_wx, yongshen_wx)
    if moving_relation == '生':
        relation_score = 1
    elif moving_relation == '克':
        relation_score = -1
    else:
        relation_score = 0

    # 动爻本身就是用神
    is_yongshen_moving = (moving_liuqin == yongshen)
    self_score = 1 if is_yongshen_moving else 0

    # 总分
    total = yongshen_score + relation_score + self_score

    # 星级
    if total >= 3:
        star = 5
    elif total >= 1:
        star = 4
    elif total >= 0:
        star = 3
    elif total >= -2:
        star = 2
    else:
        star = 1

    return {
        'event_date': event_date.strftime('%Y-%m-%d'),
        'season': season,
        'season_label': SEASON_LABEL.get(season, ''),
        'numbers': [int(a), int(b), int(c)],
        'upper_gua': upper['name'] + upper['nature'],
        'lower_gua': lower['name'] + lower['nature'],
        'upper_symbol': upper['symbol'],
        'lower_symbol': lower['symbol'],
        'palace_wx': palace_wx,
        'ben_gua': name,
        'ben_text': HEXAGRAM_TEXT.get(name, ''),
        'bian_gua': changed_name,
        'bian_text': HEXAGRAM_TEXT.get(changed_name, ''),
        'lines': lines,                # 从初到上
        'changed_lines': changed_lines,
        'lines_dz': lines_dz,          # 每爻地支
        'lines_wx': lines_wx,          # 每爻五行
        'moving': moving,
        'moving_dz': moving_dz,
        'moving_liuqin': moving_liuqin,
        'moving_wx': moving_wx,
        'moving_relation': moving_relation,
        'liuqin': liuqin_lines,        # 每爻六亲
        'yongshen': yongshen,
        'yongshen_wx': yongshen_wx,
        'yongshen_state': yongshen_state,
        'yongshen_positions': yongshen_positions,
        'is_yongshen_moving': is_yongshen_moving,
        'score': total,
        'star': star,
    }


def _idx_from_lines(lines):
    """根据三爻（下到上）反查八卦先天数"""
    for idx, info in BAGUA.items():
        if info['lines'] == lines:
            return idx
    return 8


def cast_hexagram_from_lines(lines, moving, event_date=None):
    """手动起卦：直接给 6 爻(0阴/1阳,从初到上) + 动爻(1-6)。复用 cast_hexagram 的断卦逻辑。"""
    if event_date is None:
        event_date = datetime.date.today()
    lines = [int(x) for x in lines]
    if len(lines) != 6:
        raise ValueError('lines 必须 6 个')
    moving = int(moving)
    if moving < 1 or moving > 6:
        raise ValueError('moving 必须 1-6')
    upper_idx = _idx_from_lines(lines[3:])
    lower_idx = _idx_from_lines(lines[:3])
    upper = BAGUA[upper_idx]
    lower = BAGUA[lower_idx]
    name = HEXAGRAM_NAMES.get((upper_idx, lower_idx), '未知卦')
    palace_wx = PALACE_WX.get((upper_idx, lower_idx), '土')
    lines_dz = []; lines_wx = []
    for i, line in enumerate(lines):
        dz = YANG_DZ[i] if line == 1 else YIN_DZ[i]
        lines_dz.append(dz); lines_wx.append(DZ_TO_WX[dz])
    liuqin_lines = [_liuqin_of(wx, palace_wx) for wx in lines_wx]
    changed_lines = list(lines)
    changed_lines[moving - 1] = 0 if changed_lines[moving - 1] == 1 else 1
    new_upper_idx = _idx_from_lines(changed_lines[3:])
    new_lower_idx = _idx_from_lines(changed_lines[:3])
    changed_name = HEXAGRAM_NAMES.get((new_upper_idx, new_lower_idx), '未知卦')
    season = _season_of(event_date)
    season_map = SEASON_WANG[season]
    yongshen = EVENT_YONGSHEN.get('sign_lottery', '妻财')
    yongshen_positions = [i + 1 for i, lq in enumerate(liuqin_lines) if lq == yongshen]
    yongshen_wx = _wx_of_liuqin(yongshen, palace_wx)
    yongshen_state = '休'
    for state_name, wx_val in season_map.items():
        if wx_val == yongshen_wx:
            yongshen_state = state_name
            break
    yongshen_score = WANG_SCORE.get(yongshen_state, 0)
    moving_liuqin = liuqin_lines[moving - 1]
    moving_wx = lines_wx[moving - 1]
    moving_dz = lines_dz[moving - 1]
    moving_relation = _rel_to(moving_wx, yongshen_wx)
    relation_score = 1 if moving_relation == '生' else (-1 if moving_relation == '克' else 0)
    is_yongshen_moving = (moving_liuqin == yongshen)
    self_score = 1 if is_yongshen_moving else 0
    total = yongshen_score + relation_score + self_score
    star = 5 if total >= 3 else (4 if total >= 1 else (3 if total >= 0 else (2 if total >= -2 else 1)))
    return {
        'event_date': event_date.strftime('%Y-%m-%d'),
        'season': season, 'season_label': SEASON_LABEL.get(season, ''),
        'numbers': [],
        'upper_gua': upper['name'] + upper['nature'],
        'lower_gua': lower['name'] + lower['nature'],
        'upper_symbol': upper['symbol'], 'lower_symbol': lower['symbol'],
        'palace_wx': palace_wx,
        'ben_gua': name, 'ben_text': HEXAGRAM_TEXT.get(name, ''),
        'bian_gua': changed_name, 'bian_text': HEXAGRAM_TEXT.get(changed_name, ''),
        'lines': lines, 'changed_lines': changed_lines,
        'lines_dz': lines_dz, 'lines_wx': lines_wx,
        'moving': moving, 'moving_dz': moving_dz, 'moving_liuqin': moving_liuqin,
        'moving_wx': moving_wx, 'moving_relation': moving_relation,
        'liuqin': liuqin_lines,
        'yongshen': yongshen, 'yongshen_wx': yongshen_wx, 'yongshen_state': yongshen_state,
        'yongshen_positions': yongshen_positions, 'is_yongshen_moving': is_yongshen_moving,
        'score': total, 'star': star,
    }


def _wx_of_liuqin(liuqin, me_wx):
    """根据六亲名 + 我五行，反推该六亲对应的五行"""
    sheng = {'木':'火','火':'土','土':'金','金':'水','水':'木'}
    ke = {'木':'土','火':'金','土':'水','金':'木','水':'火'}
    if liuqin == '兄弟':
        return me_wx
    if liuqin == '子孙':
        return sheng.get(me_wx, me_wx)
    if liuqin == '父母':
        # 生我者
        for k, v in sheng.items():
            if v == me_wx:
                return k
        return me_wx
    if liuqin == '妻财':
        return ke.get(me_wx, me_wx)
    if liuqin == '官鬼':
        # 克我者
        for k, v in ke.items():
            if v == me_wx:
                return k
        return me_wx
    return me_wx


def _rel_to(a, b):
    """a 对 b 的生克关系（同/生/克）"""
    if a == b:
        return '同'
    sheng = {'木':'火','火':'土','土':'金','金':'水','水':'木'}
    if sheng.get(a) == b:
        return '生'
    ke = {'木':'土','火':'金','土':'水','金':'木','水':'火'}
    if ke.get(a) == b:
        return '克'
    return '无关'


# ─────────────────────────────────────────────────────────
# 解卦文本生成（追星场景话术）
# ─────────────────────────────────────────────────────────
def divine_for_event(a=0, b=0, c=0, event_type='sign_lottery', event_name='', event_date=None, concern='', lines=None, moving=None):
    """事件六爻起卦（idolship 用）。传 lines(6)+moving 走手动起卦，否则用 a/b/c 三数。
    event_type: sign_lottery | ticket | offline | fansign | overseas
    """
    if lines is not None and moving is not None:
        cast = cast_hexagram_from_lines(lines, moving, event_date)
    else:
        cast = cast_hexagram(a, b, c, event_date)
    cast = _apply_day_info(cast)  # 20260825ff: 日辰干支+旬空/月破/日冲/日合

    # 用 event_type 覆盖用神
    yongshen = EVENT_YONGSHEN.get(event_type, '妻财')
    cast['yongshen'] = yongshen
    palace_wx = cast['palace_wx']
    yongshen_wx = _wx_of_liuqin(yongshen, palace_wx)
    cast['yongshen_wx'] = yongshen_wx

    # 重新算用神旺衰
    season_map = SEASON_WANG[cast['season']]
    yongshen_state = '休'
    for state_name, wx_val in season_map.items():
        if wx_val == yongshen_wx:
            yongshen_state = state_name
            break
    cast['yongshen_state'] = yongshen_state
    cast['yongshen_positions'] = [i + 1 for i, lq in enumerate(cast['liuqin']) if lq == yongshen]

    # 重新算星
    yongshen_score = WANG_SCORE.get(yongshen_state, 0)
    moving_relation = cast['moving_relation']
    relation_score = 1 if moving_relation == '生' else (-1 if moving_relation == '克' else 0)
    is_ys_moving = (cast['moving_liuqin'] == yongshen)
    cast['is_yongshen_moving'] = is_ys_moving
    self_score = 1 if is_ys_moving else 0
    total = yongshen_score + relation_score + self_score
    cast['score'] = total
    cast['star'] = 5 if total >= 3 else (4 if total >= 1 else (3 if total >= 0 else (2 if total >= -2 else 1)))

    # 解析文本
    cast['analysis'] = _gen_event_analysis(cast, event_type, event_name)
    if concern:
        cast['concern_answer'] = _gen_concern_answer(cast, event_type, event_name, concern)
    cast['event_type'] = event_type
    cast['event_name'] = event_name

    return cast


EVENT_LABELS = {
    'sign_lottery': '抽签抽票',
    'ticket':       '抢票',
    'offline':      '线下接送机',
    'fansign':      '签售见面会',
    'overseas':     '海外追星',
    'idol_joy':     '追星',   # 20260825cc
    'idol_friend':  '追星',   # 20260825cc
}

STATE_LABELS = {'旺': '极旺', '相': '次旺', '休': '平淡', '囚': '受困', '死': '极弱'}


def _gen_concern_answer(cast, event_type, event_name, concern):
    """根据用户关心的问题，结合六爻凶吉分数，给出紧扣问题领域的针对性建议（不依赖LLM）"""
    star = cast.get('star', 3)
    ys_state = cast.get('yongshen_state', '休')
    moving_rel = cast.get('moving_relation', '')
    event_lbl = {'sign_lottery':'抽签抽票','ticket':'抢票','offline':'线下活动','fansign':'签售见面会','overseas':'海外追星'}.get(event_type, '活动')
    SL = {'旺':'极旺','相':'次旺','休':'平淡','囚':'受困','死':'极弱'}
    ys_label = SL.get(ys_state, '平淡')

    if star >= 4:
        mood = '卦象不错，用神' + ys_label + '，整体磁场对你有利'
    elif star == 3:
        mood = '运势中规中矩，没什么大起大落'
    else:
        mood = '卦象提示阻力不小，用神' + ys_label + '，需要多做准备'

    if moving_rel == '生':
        mh = '而且动爻生助用神，有暗中的助力，顺其自然就好。'
    elif moving_rel == '克':
        mh = '动爻克用神，过程中可能遇到小波折，心态放平。'
    elif moving_rel == '同气':
        mh = '动爻与用神同气，主动出击效果更佳。'
    else:
        mh = ''

    q = concern.lower()
    out = ['关于「' + concern + '」：']

    def pick(g, m, b):
        out.append(g if star >= 4 else (m if star == 3 else b))

    # 1. 活动能否正常进行/顺利/如期（线下流程类）
    if any(k in q for k in ['正常','顺利','如期','取消','延','改期','还办','晕','能不能去成','成行']):
        pick(mood + '，「' + event_name + '」能正常进行的概率比较高。持续关注官方动态和场地公告，遇临时调整也有缓冲。' + mh,
             mood + '，活动正常进行的可能性较大，但留意官方最后一刻的通知。交通/住宿尽量选可退改的，留 Plan B。',
             mood + '，活动可能有变数（流程调整/天气/临时通知）。保持灵活，重要环节多确认，别把行程卡得太死。')

    # 2. 中签/抽中/抢到（抽选抢票类）
    elif any(k in q for k in ['抽中','中签','中选','抢到','抢票','买到','能中吗','命中率','抽选','概率','能不能抽','能不能抢']):
        pick(mood + '，' + event_lbl + '成功的概率比较大。设备网络手速都备好，果断出手。' + mh,
             mood + '，成败看个人操作和运气各半。提前测试好设备和网络，多平台同蹲，关键时刻别犹豫。',
             mood + '，直接硬拼阻力大。找朋友同步帮忙，或关注其他场次/补位机会。')

    # 3. 值不值/亏不亏/性价比
    elif any(k in q for k in ['值不值','值得','亏','划算','性价比','贵','值吗','要不要买','花得值']):
        pick(mood + '，从卦象看这趟「' + event_name + '」给你的情绪回报会很足，值得投入。预算内果断就好。',
             mood + '，值不值取决于你在乎的是过程还是结果。图开心就值，奔着特定目的建议降低预期。',
             mood + '，性价比偏低或变数较多。量力而行，别为它透支更重要的安排。')

    # 4. 被注意到/互动/回应
    elif any(k in q for k in ['注意到','互动','看到我','被点名','打招呼','回应','能不能被','看到']):
        pick(mood + '，被注意到或互动的机会挺高。穿有辨识度的应援色、站前排主动位置，大胆但不失礼貌。' + mh,
             mood + '，概率五五开，取决于位置和时机。选好位置、准备好话题，自然流露比刻意更有效。',
             mood + '，别太执着于被注意到。享受氛围和音乐，不经意的瞬间反而最珍贵。')

    # 5. 拍到/拍照/物料/视频
    elif any(k in q for k in ['拍到','拍照','照片','物料','视频','直拍','录像','清晰','角度','能不能拍']):
        pick(mood + '，出片率会很高。设备提前清内存、充满电，选好拍摄位置。' + mh,
             mood + '，能拍到但质量看位置和运气。别全程透过屏幕看，留几段记忆用眼睛看。',
             mood + '，拍摄条件可能受限（位置/光线/遮挡）。放平心态，官方物料或同好分享是补充。')

    # 6. 见到/遇到/同框/合影
    elif any(k in q for k in ['见到','遇到','同框','合影','合照','近距离','见到本人','能不能见']):
        pick(mood + '，见到/近距离的机会挺大。留意签售/接送机/散场等节点，注意安全和秩序。' + mh,
             mood + '，见到本人的概率中等，看缘分和时机。别强求，顺其自然遇到更舒服。',
             mood + '，直接见到的概率较低。别为这个孤注一掷安排行程，避免失望。')

    # 7. 签售/聊天/说上话
    elif any(k in q for k in ['签售','签名','聊','说上话','说几句','话题','聊什么','能聊','签名pos']):
        pick(mood + '，互动质量会不错。提前准备1-2句想说的（别太长），真诚比华丽更打动人。' + mh,
             mood + '，能简短互动。准备好签名 pos 和一句话，时间紧别贪多。',
             mood + '，互动时间可能很有限或流程快。心意传达到就行，不强求深度交流。')

    # 8. 人数/规模/阵容
    elif any(k in q for k in ['几个艺人','多少人','人数','规模','多大','多少明星','嘉宾','阵容']):
        pick(event_lbl + '的规模通常活动前1-2天官方会公布。' + mood + '，关注官方公告和站内通知，信息来得及时。',
             '阵容信息一般不会太晚公布。' + mood + '，留意同场粉丝群体的讨论，消息往往比官方快。',
             '阵容可能有变动或延迟公布。' + mood + '，做好心理准备，关注多渠道信息。')

    # 9. 时间/最佳时机
    elif any(k in q for k in ['什么时候','几点','时间','最佳时机','提前多久','什么时候去']):
        pick(mood + '，建议比常规时间再提前30分钟到场，抢占有利位置。',
             mood + '，按官方建议时间到场即可，不用刻意卡太紧。',
             mood + '，建议尽量提前到场留缓冲。路上可能有小状况，别因赶时间影响心态。')

    # 10. 位置/座位
    elif any(k in q for k in ['位置','座位','站哪','哪里','区域','排队']):
        pick(mood + '，选位置可以大胆点，前排或中心区域值得争取。' + mh,
             mood + '，位置选中偏前就好，太靠前不一定体验最好。',
             mood + '，位置不用太执着，后排也不一定差——远观有时能看到更多。')

    # 11. 天气/穿着/装备
    elif any(k in q for k in ['天气','穿什么','穿','带什么','准备什么','需要带']):
        pick(mood + '，按计划好好准备。舒适为主、应援元素点缀。',
             mood + '，常规准备即可，关注天气预报做微调。',
             mood + '，精简装备轻装出行，核心是舒适+应援色，别带太多增加负担。')

    # 通用兜底
    else:
        pick(mood + '。「' + event_name + '」整体磁场不错，按你的计划大胆去。' + mh,
             mood + '。「' + event_name + '」没有大阻碍，心态放轻松，享受过程比纠结结果更重要。',
             mood + '。「' + event_name + '」有阻力，多做准备、留 Plan B，把预期调柔一点。')

    return ''.join(out)


def _gen_event_analysis(cast, event_type, event_name):
    """生成追星场景的解卦文本"""
    star = cast['star']
    ys = cast['yongshen']
    ys_state = cast['yongshen_state']
    ys_state_lbl = STATE_LABELS.get(ys_state, '平淡')
    moving = cast['moving']
    moving_lq = cast['moving_liuqin']
    moving_rel = cast['moving_relation']
    ben = cast['ben_gua']
    bian = cast['bian_gua']
    ben_text = cast['ben_text']
    event_lbl = EVENT_LABELS.get(event_type, '此次活动')
    name_part = f"「{event_name}」" if event_name else ''

    parts = []
    parts.append(f"## {event_lbl}{name_part} · 六爻排盘\n")
    parts.append(f"**本卦**：{ben}（{cast['palace_wx']}宫） — {ben_text}")
    parts.append(f"**变卦**：{bian}")
    parts.append(f"**动爻**：第 {moving} 爻（{moving_lq}发动）")
    parts.append("")
    parts.append(f"**用神**：{ys}（{ys_state_lbl}）")
    parts.append(f"**用神所在爻**：{cast['yongshen_positions'] or '无（伏藏）'}")
    parts.append(f"**动爻与用神**：{moving_rel}（{moving_lq} → {ys}）")
    parts.append("")

    if star >= 4:
        parts.append(f"### ✨ 总评：{star}★ 上吉")
        parts.append(f"用神{ys_state_lbl}，动爻{'生助用神' if moving_rel == '生' else ('与用神同气' if moving_lq == ys else '尚可')}，{event_lbl}成功的磁场很强，宜积极行动。")
    elif star == 3:
        parts.append(f"### ⚖️ 总评：3★ 平"
                     if False else f"### ⚖️ 总评：{star}★ 平")
        parts.append(f"用神{ys_state_lbl}，{event_lbl}的运势平稳，看个人把握，没有特别阻碍也没有大助力。")
    else:
        parts.append(f"### ⚠️ 总评：{star}★ 凶")
        parts.append(f"用神{ys_state_lbl}{'，动爻克伤用神' if moving_rel == '克' else ''}，{event_lbl}阻力较大，建议{'暂缓行动或择吉日再起' if star <= 2 else '谨慎为之'}。")

    parts.append("")
    parts.append(f"> 本卦卦辞：{ben_text}")
    parts.append(f"> 月令：{cast['season']}季 · 用神五行：{cast['yongshen_wx']} · 卦宫五行：{cast['palace_wx']}")
    return '\n'.join(parts)
