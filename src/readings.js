/* 真假CP鉴定器 — 解读文案库（本地固定规则生成，无 LLM、无网络）
 * 输入 engine 的 cast 对象（+ CP状态）→ 输出结构化白话鉴定
 * 0904 八轮（lyvia 定稿结构）：每条解答=卦象一句 → 过去一句 → 现在一句 → 未来一句
 *   → （有转变日期才给日期）→ 金句建议一到两句；一句一行，绝不两句连排
 * 0904 十四轮（lyvia）：第2行=直觉对照句（回应她选的看法：看得准/对一半/看拧了；看法=预判，
 *   档位仍由卦定；跳过表态→无对照句）＋时间轴连接词（眼下的局面是/往后的走向/所以）
 * 0906 四十四轮（lyvia 定调）：裁定词/大字/正文一律只依据卦象测算的关系走向，绝不跟随表态换池；
 *   表态只进对照句一句（回应「他选的看法是否符合卦象」）——BE 专属池（裁定/正文/金句）整体退役
 *   ＋未来↔建议↔金句撞词时确定性换位，杜绝三句连说同一件事
 * 措辞约束：0828 违禁词族一律不用；🔴无北方口语（那几个词的写法本身也进了违禁扫描表，注释里不再复写）；
 * 无难懂句（术语腔全禁）；同位话术池轮换，全套近 200 条，尽量不复读
 * 事实判定权在用户（表态自选），仪器只做趣味参照、绝不与事实对着干
 * 注意：score/moving_relation 沿用线上怪癖（对妻财），展示层动爻关系在此单独对真实用神重算
 */
(function () {
  'use strict';

  var BAND = {
    high: { key: 'high', label: '高走' },
    mid: { key: 'mid', label: '拉扯' },
    low: { key: 'low', label: '降温' }
  };

  var CAT_SUBJECT = {
    career: '他们这对CP',
    wealth: '这场追星行程',
    study: '你和本命的缘分',
    social: '你的粉圈处境',
    mind: '你的追星心情'
  };

  /* ── 档位词（lyvia 十二词；0904 八轮：北方味档位词已换软词）──
   * 星数 5→1 对应 吉→凶；四十四轮（lyvia）：裁定词只按星数取，与表态无关
   */
  var VERDICTS = {
    5: ['修成正果'],
    4: ['临门一脚', '八九不离十'],
    3: ['重在暧昧', '势在拉扯', '五五开'],
    2: ['心怀鬼胎', '耿耿于怀'],
    // 四十四轮：BE 专属池退役，「爱过」「可以看看别家」并入最低档，lyvia 12 词全保留
    1: ['各有新欢', '不必勉强', '爱过', '可以看看别家']
  };
  /* ── 十四轮：直觉对照句——回应她选的看法（对/对一半/看拧了）──
   * 四十轮（lyvia）重写：开头不再是「你选的是」那种机械腔，先接她给的判断、再给卦对这段关系的看法，
   * 最后落到「从结论上看，××」；== == 之间是结论短语=高亮位（结论重要，她选了什么不重要）。
   * 看法=她的预判，档位仍由卦定；四十四轮起此句=表态唯一出场位
   * 跳过表态（cpState 空）→ 不给对照句，卦直说
   */
  var REPLY = {
    hot: {
      high: [
        '「就差结婚了」是你心里的答案，卦面给出的判断也一样，温度确实在往上走：从结论上看，==你看得很准==。',
        '「就差结婚了」这个直觉给对了，卦里读到的是一段实打实在升温的感情：从结论上看，==你看得很准==。'
      ],
      mid: [
        '「就差结婚了」方向没有选错，只是这一步卦面看得比你要保守：从结论上看，==只对了一半==，还差一步没走到。',
        '「就差结婚了」当参考来看，这段关系确实在往上走，只是脚步比预想的慢：从结论上看，==只对了一半==。'
      ],
      low: [
        '「就差结婚了」是你的期待，卦里读到的关系却在降温：从结论上看，==这一题你看反了==。',
        '「就差结婚了」说在前头，卦面给出的走向却相反，温度在往下走：从结论上看，==这一题你看反了==。'
      ]
    },
    rumor: {
      high: [
        '「难以分辨」留了余地，卦面却比你想的乐观，这段不是悬着，是在往上走：从结论上看，==你看保守了==。',
        '「难以分辨」是稳当的说法，卦里读到的走向却已经偏甜，是明确的往上走：从结论上看，==你看保守了==。'
      ],
      mid: [
        '「难以分辨」和卦面的判断是同一个意思，事情就悬在中间：从结论上看，==你看得很准==。',
        '「难以分辨」这个感觉没有偏，卦里这段关系确实还悬着，给不出更干脆的答案：从结论上看，==你看得很准==。'
      ],
      low: [
        '「难以分辨」听着中立，卦面却比你想的冷静，这不是暧昧，是在降温：从结论上看，==你看乐观了==。',
        '「难以分辨」是往稳里猜的，卦里读到的结果却更清楚，不是五五开，是温度在往下走：从结论上看，==你看乐观了==。'
      ]
    },
    be: {
      high: [
        '「已经BE」说的是事实，但卦里这段回忆是甜的，分量比你认的更足：从结论上看，==看对了方向，看轻了成色==。',
        '「已经BE」这一页翻得没错，只是这段回忆的分量，比你现在认的更足：从结论上看，==翻篇没错，分量看轻了==。'
      ],
      mid: [
        '「已经BE」说对的是结局，没算到的是余温，这事名义上翻篇，心里还没散干净：从结论上看，==对了一半==。',
        '「已经BE」认的是结束，卦里认的是两样同时都在，结束是真的，惦记也是真的：从结论上看，==对了一半==。'
      ],
      low: [
        '「已经BE」和卦面的判断对上了，这一页确实翻过去了：从结论上看，==你看得很准==。',
        '「已经BE」是这个故事的收尾，卦里读到的也是同一条干净的线：从结论上看，==你看得很准==。'
      ]
    }
  };
  /* 拆出 ==标记== 的结论短语：text=去标记全文，hot=高亮位；没有成对标记则整句素色 */
  function splitHot(s) {
    var k1 = s.indexOf('=='), k2 = k1 < 0 ? -1 : s.indexOf('==', k1 + 2);
    if (k1 < 0 || k2 < 0) return { text: s.split('==').join(''), hot: '' };
    return { text: s.slice(0, k1) + s.slice(k1 + 2, k2) + s.slice(k2 + 2), hot: s.slice(k1 + 2, k2) };
  }

  /* ── 十七轮（lyvia）：回答句式——解读必须回答她问的那件事（答案/凶吉/趋势），句式轮换不当开头腔 ── */
  var ANSWER = {
    hot: {
      high: [
        '直接回答你问的走向：还在往上走，而且是能一直走下去的那种势头。',
        '你问的走向，卦面给得很干脆：一路向上，甜度还在涨。'
      ],
      mid: [
        '你问的走向，卦面的回答是：大方向是好的，脚步慢，属于慢热的走法。',
        '直接说走向：不会凉，但也不会一夜爆甜，是慢慢升温的路线。'
      ],
      low: [
        '你问的走向，答案很明确：温度在往下走，短期难回头。',
        '直接说走向：势头在转淡，往后大概率是越走越平的一条线。'
      ]
    }
  };

  var STATE_PHRASE = {
    '旺': '气势正盛',
    '相': '势头向上',
    '休': '不急不缓',
    '囚': '一时受困',
    '死': '气数极弱'
  };

  var FOOTNOTE = '本鉴定由本地固定规则生成（六爻卦象 × 世应旺衰 × 动爻关系），无网络、无 AI 参与；结果属传统趣味的参照，不构成对任何真实人物的判断。';

  // 展示层用：动爻五行 相对 真实用神五行 的关系（与打分用的妻财怪癖无关）
  var SHENG = { '木': '火', '火': '土', '土': '金', '金': '水', '水': '木' };
  var KE = { '木': '土', '火': '金', '土': '水', '金': '木', '水': '火' };
  function rel(a, b) {
    if (a === b) return '同';
    if (SHENG[a] === b) return '生';
    if (KE[a] === b) return '克';
    return '无关';
  }
  function relWord(a, b) {
    var r = rel(a, b);
    if (r === '生') return '正生着用神，有助力暗推';
    if (r === '克') return '与用神相克，阻力显形';
    if (r === '同') return '与用神同气，变数就在关系本身';
    return '与用神不直接相干，主线看用神自己';
  }

  function bandOf(star) {
    return star >= 4 ? BAND.high : (star >= 2 ? BAND.mid : BAND.low); // 十七轮（lyvia）：两星=中段强弱，归拉扯；解读比例随卦象分布走
  }

  /* ── 十四轮：时间轴连接词——句首重复的时间词先剥掉，再统一挂连接词 ── */
  var LEADS = ['往后的走向', '再往后', '往后不久', '往后', '未来某天', '未来', '接下来', '此刻', '眼下', '现在', '当下',
    '照这个走向', '照此发展', '照这个势头'];
  function stripLead(line) {
    for (var i = 0; i < LEADS.length; i++) {
      if (line.indexOf(LEADS[i]) === 0) {
        var rest = line.slice(LEADS[i].length);
        if (rest.charAt(0) === '的') rest = rest.slice(1);
        rest = rest.replace(/^[，、]/, '');
        if (rest.indexOf('想起') === 0) rest = '哪天' + rest; // 剥头后「想起」悬空，补回主语

        if (rest.length > 4) return rest;
      }
    }
    return line;
  }

  /* ── 十四轮：未来/建议/金句三句撞词（如三句都说「下一个心动」）→ 确定性换位 ── */
  var CLASH_WORDS = ['心动', '新欢', '翻篇', '下一个'];
  function clashWords(line) {
    var out = [];
    for (var i = 0; i < CLASH_WORDS.length; i++) {
      if ((line || '').indexOf(CLASH_WORDS[i]) >= 0) out.push(CLASH_WORDS[i]);
    }
    return out;
  }
  function distinctPick(pool, cast, salt, seqN, avoid) {
    if (!pool || !pool.length) return '';
    var start = seedOf(cast, salt, seqN) % pool.length;
    for (var i = 0; i < pool.length; i++) {
      var cand = pool[(start + i) % pool.length];
      var clash = false;
      for (var k = 0; k < (avoid || []).length; k++) {
        if (cand.indexOf(avoid[k]) >= 0) { clash = true; break; }
      }
      if (!clash) return cand;
    }
    return pool[start];
  }

  /* ── 档位词：按星数取 ──
   * 二十七轮：BE 高/中档各补一词，取词种子沿用 动爻+星数，双词档两词都能露脸
   * 四十四轮（lyvia）：裁定词与看法脱钩——大字结论只依据卦象测算的关系走向，
   * 看法只在正文对照句里回应一句「是否符合卦象」，不再让裁定与大字跟随表态换池
   */
  function verdictOf(cast, cpState) {
    var pool = VERDICTS[Math.min(5, Math.max(1, cast.star))] || VERDICTS[3];
    var pick = pool.length ? pool[(cast.moving + cast.star) % pool.length] : '五五开';
    return { word: pick, pool: pool };
  }

  /* ── 生年 → 生肖/本命五行（用户自愿填写；只取年份，跳过则不参断）── */
  var ZODIAC = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪'];
  var ZODIAC_WX = { '鼠': '水', '猪': '水', '虎': '木', '兔': '木', '蛇': '火', '马': '火', '猴': '金', '鸡': '金', '牛': '土', '龙': '土', '羊': '土', '狗': '土' };
  function zodiacOf(year) {
    var y = Number(year);
    if (!y || y < 1900 || y > 2100) return null;
    var z = ZODIAC[(y - 4) % 12];
    return { zodiac: z, wx: ZODIAC_WX[z] };
  }
  function birthSentence(cast, birthYear) {
    var zb = zodiacOf(birthYear);
    if (!zb) return '';
    var ywx = (cast.lines_wx && cast.lines_wx[yingPosOf(cast) - 1]) || ''; // 三十一轮：对看应爻
    var r = rel(zb.wx, ywx);
    if (r === '生') return '（TA 本命' + zb.zodiac + '属' + zb.wx + '，正生着应爻，看TA自带滤镜）';
    if (r === '克') return '（TA 本命' + zb.zodiac + '属' + zb.wx + '，与应爻相克，看TA容易挑刺）';
    if (r === '同') return '（TA 本命' + zb.zodiac + '属' + zb.wx + '，与应爻同气，代入感直接拉满）';
    return '（TA 本命' + zb.zodiac + '属' + zb.wx + '，与应爻不直接相干，看TA全凭心情）';
  }

  /* ════ 话术池（0904 八轮全量重写：豆卜式温柔饭圈白话，无北方口语，无术语腔）════
   * 结构六槽：卦象 / 过去 / 现在 / 未来 / 日期 / 金句建议
   * 全套独立文案 ≈200 条，按卦象+日期+动爻+星数+第几对做确定性轮换
   */

  var CN_NUM = ['', '一', '二', '三', '四', '五', '六'];

  // 槽1 卦象句（模板 × 本卦/变卦/动爻 → 64×6×5 种表面形态）
  var GUA_LINE = [
    '这一卦是「{A}」走向「{B}」，第{n}爻在动，卦面把变化的方向已经摆出来了。',
    '起出来的是「{A}」，动爻落在第{n}爻，最后走向「{B}」，说的正是你问的这件事。',
    '「{A}」是现在的局面，「{B}」是接下去的方向，中间第{n}爻在动。',
    '卦面给的是「{A}」变「{B}」，第{n}爻独独在动，这件事的走向就藏在里面。',
    '本卦「{A}」，变卦「{B}」，动爻在第{n}爻，一静一动之间，答案其实已经给了方向。'
  ];

  // 槽2 过去（3×8；四十四轮起正文不跟随表态，BE 专属池退役）
  var PAST = {
    high: [
      '从最初的相遇到现在，他们之间的好感是有来有往的，谁都不是单方面在使劲。',
      '这段关系的起点是甜的，两个人都真心投入过，这一点从相处的痕迹里看得出来。',
      '最初的心动是真实的，不是错觉，也不只是你一个人在想。',
      '回看早期的互动，他们之间一直有一种默契，那种对得上频道的感觉装不出来。',
      '这段缘分从一开始就走得正，早期的每一步都算数。',
      '他们的故事有一个足够好的开头，彼此都是带着诚意进来的。',
      '从过去的相处看，这段感情是有根的，不是风一吹就散的那种。',
      '早期那些一来一往的回应，现在回想起来都是真的，谁都没有敷衍。'
    ],
    mid: [
      '过去的热度忽高忽低，两个人的节奏一直没有真正对齐过。',
      '他们曾经靠近过，也各自退开过，总是差一句话的火候。',
      '起初聊得很好，后来渐渐变得小心，谁都怕先动了心就输了。',
      '过去更多是在试探，谁都没有把那层窗户纸说破。',
      '这段关系的早期，暧昧的成分多过确定，甜和悬各占一半。',
      '他们过去的互动总像隔着一层纱，看得见影子，摸不清心意。',
      '曾经的甜是真的，犹豫也是真的，两样东西一直并存着。',
      '过去的日子里，热情和犹豫轮流做主，谁也没能彻底压过谁。'
    ],
    low: [
      '过去的温度其实一直在慢慢往下退，只是身在其中不容易察觉。',
      '曾经的默契后来慢慢对不上了，回应越来越像在走流程。',
      '各自的心思从某个时候起，就已经开始往不同的方向走了。',
      '早期的热情没有续上，中间断掉的那一截，后来再也没接回来。',
      '现在回头去看，走远的信号其实早就出现过，只是一直被忽略。',
      '回看得越清楚，越发现这段缘分早就开始降温了。',
      '过去的美好是真的，只是它留在了它该在的位置，翻不回来了。',
      '这段关系最好的时候其实已经过完了，后面多半是在延长线里走。'
    ]
  };
  // 槽3 现在（常规 3×8 / BE 3×5）
  var NOW = {
    high: [
      '此刻两个人的心意是对得上的，那种互相靠拢的势头藏不住。',
      '眼下的温度正在往上走，互动都有回应，不是你一个人在唱独角戏。',
      '现在谁都没有松手的意思，这段关系还稳稳地悬在中间。',
      '当下的氛围是松动的，靠近起来很自然，不需要刻意找理由。',
      '此刻他们之间的好感是流动的，不是停在不动的老位置上。',
      '现在的关系正在悄悄升温，明眼人都能看出来那种变化。',
      '眼下的每一次互动都有回音，这种有来有往是最健康的信号。',
      '此刻的亲近是双向的，他们的步调难得地对在了一起。'
    ],
    mid: [
      '现在不冷不热，两个人都在等对方先动，谁也不肯先伸手。',
      '眼下正处在试探期，话到嘴边又咽回去，谁都没把话说透。',
      '此刻的心意各自藏着，表面平静，底下其实都有数。',
      '现在的关系像在拉锯，进一步又退一步，僵持在这一来一回里。',
      '眼下的暧昧还在，但确定性不够，谁也不敢替对方做主。',
      '此刻谁都好奇对方的心思，又都按着不动，比的就是耐心。',
      '现在的问题不是没感觉，是没有人愿意先开口把事挑明。',
      '眼下维持着一种微妙的平衡，动一下就变，不动就一直悬着。'
    ],
    low: [
      '此刻的联系在变少，回应在变慢，热度肉眼可见地凉下来。',
      '眼下的温度已经明显降了，谁都感觉到了，只是没人说破。',
      '现在各自的心思已经不在一处，同框却不同频。',
      '此刻维系着的，更多是习惯，不是心跳。',
      '眼下的互动越来越像例行公事，做是做了，心没有跟上。',
      '现在的沉默比话语多，偶尔开口也只是客套几句。',
      '此刻两个人都在小心翼翼地省力，谁也不想再多付出一点。',
      '眼下的疏远是缓慢的，但它是真实的，装作看不见也还在走。'
    ]
  };
  // 槽4 未来（3×8；四十四轮起正文不跟随表态）
  var FUTURE = {
    high: [
      '往后顺着这个节奏走下去，大概率能走到一个让人满意的结果。',
      '接下来会出现一个明确的答案，而且是让人安心的那种。',
      '往后的每一步都在靠近确定，悬着的事情会一件一件落地。',
      '照这个势头走下去，好事就在不远处等着。',
      '接下来会有一段高甜的窗口期，值得你好好期待。',
      '往后的发展是往上走的，一步一步都比现在更稳。',
      '这个趋势只要保持住，结果大概率不会让人失望。',
      '往后会出现让所有人都安心的转折，之前悬着的心可以放下了。'
    ],
    mid: [
      '接下来就看谁先迈出那一步，先动的那个人会拿到主动权。',
      '他们的走向，多半取决于一次坦诚的对话，早晚要来。',
      '再往后变数还多，这个悬念会再保留一阵子，急不来。',
      '接下来可能在某个契机之后突然明朗，之前的一切铺垫都算数。',
      '往后要么升温要么降温，很难一直停在原地，答案不会太远。',
      '未来的变数还在他们自己手里，谁更认真，答案就偏向谁。',
      '接下来的每一次互动都是一张选票，票会慢慢告诉你结果。',
      '往后不久会有新的信号出现，到时候答案自然清楚。'
    ],
    low: [
      '再往后，大概率是渐行渐远，联系会一点一点变稀。',
      '照这个走向，温度只会继续往下掉，很难再有回温的机会。',
      '往后能维持现状已经不容易，别再指望它自己好起来。',
      '接下来的每一步都在往淡出的方向走，这是趋势不是意外。',
      '往后各自会有各自的新篇章，只是不再写进同一本书里。',
      '再往后的联系会越来越礼节性，逢年过节的一句问候而已。',
      '照此发展，散场只是时间问题，心里有个数就好。',
      '往后主线会换人，他们的戏份到这里就交代完了。'
    ]
  };
  // 槽5 应期（二十六轮lyvia：按增删卜易·各门类应期总注取——空/墓/破/合/旺衰/动静各依其法，
  // 不再只取用神值支；仍只给干支月/年粗粒度，禁具体日期；BE/降温不给，不画饼）
  var YQ_CHONG = { 子: '午', 午: '子', 丑: '未', 未: '丑', 寅: '申', 申: '寅',
    卯: '酉', 酉: '卯', 辰: '戌', 戌: '辰', 巳: '亥', 亥: '巳' };
  var YQ_LIUHE = { 子: '丑', 丑: '子', 寅: '亥', 亥: '寅', 卯: '戌', 戌: '卯',
    辰: '酉', 酉: '辰', 巳: '申', 申: '巳', 午: '未', 未: '午' };
  // 墓库（火土同墓于戌）与长生（火土同宫，长生在寅）
  var YQ_MU = { 木: '未', 火: '戌', 金: '丑', 水: '辰', 土: '戌' };
  var YQ_SHENG = { 木: '亥', 火: '寅', 金: '巳', 水: '申', 土: '寅' };
  var YQ_ZHI = '子丑寅卯辰巳午未申酉戌亥';
  // 引导语按卦轮换（确定性取句，同一对复测换说法）；断言只锁规则主体
  var YQ_LEADS = {
    kong: ['用神落空，先等出空', '卦在空处，出空才算', '这一卦落空，先等出空'],
    mu: ['卦气入库，要等冲开', '入了墓库，冲开才动'],
    po: ['这一卦逢破，出了{ym}月才算数', '月破的卦，出了{ym}月才立得住'],
    he: ['卦被合住，冲开才动', '这卦被合住，要等冲开'],
    wang: ['势头太满，冲一冲才动', '旺过了头，冲一冲才动'],
    ruo: ['眼下气弱，等生旺的时节', '火候未到，等生旺的时节', '卦气还弱，要等生旺的时节'],
    dong: ['用神发动，逢值逢合', '用神已动，等值合的时节'],
    jing: ['卦是静的，等值等冲', '卦走得不急，等它当令', '静卦不急，等值等冲'],
    bkong: ['动爻化出的那支落了空，出空才算', '变爻落空，先等它出空'],
    richong: ['动而逢冲，动荡未定', '这一动被日辰冲着，动荡未定'],
    huike: ['化出的那支回头克它，这一动走得费劲', '变爻回头克，势里带一股反劲']
  };

  /* 二十九轮：变爻装支（与引擎同一配法：阳爻取阳支、阴爻取阴支，只看爻位）
   * 引擎配法下动爻变出的支是固定搭档（初=子/未…上=戌/酉），逐对核过五行：
   * 化进神/化退神/回头生/变爻冲本爻在此体系里结构性不出现，故只落能出现的
   * 三样——变爻旬空 / 变爻月破 / 日辰冲动爻（暗动）/ 回头克，取法照教程：
   * 变爻空破等出空出破填实，动而逢冲应逢值逢合，回头克应变爻或动爻逢值 */
  var YQ_YANG_DZ = ['子', '寅', '辰', '午', '申', '戌'];
  var YQ_YIN_DZ = ['未', '巳', '卯', '丑', '亥', '酉'];
  var YQ_DZ_WX = { 子: '水', 丑: '土', 寅: '木', 卯: '木', 辰: '土', 巳: '火', 午: '火', 未: '土', 申: '金', 酉: '金', 戌: '土', 亥: '水' };
  function bianDzOf(cast) {
    var m = Number(cast.moving) || 0;
    if (m < 1 || m > 6 || !cast.changed_lines) return '';
    return cast.changed_lines[m - 1] === 1 ? YQ_YANG_DZ[m - 1] : YQ_YIN_DZ[m - 1];
  }
  function wxRel(a, b) {
    var SHENG = { 木: '火', 火: '土', 土: '金', 金: '水', 水: '木' };
    var KE = { 木: '土', 土: '水', 水: '火', 火: '金', 金: '木' };
    if (SHENG[a] === b) return '生';
    if (KE[a] === b) return '克';
    return '';
  }

  /* ════ 三十一轮（lyvia 拍板）：用神切应爻，改走世应 ════
   * 世＝测算者，应＝你家CP。世位按京房八宫卦序硬表（引擎锁死不动，表放展示层），
   * 应位由世隔两位取；旺衰打分改锚应爻＋世应生克，星数由 app 层覆写。
   */
  var SHI_TABLE = {
    '乾为天': 6, '天风姤': 1, '天山遁': 2, '天地否': 3, '风地观': 4, '山地剥': 5, '火地晋': 4, '火天大有': 3,
    '坎为水': 6, '水泽节': 1, '水雷屯': 2, '水火既济': 3, '泽火革': 4, '雷火丰': 5, '地火明夷': 4, '地水师': 3,
    '艮为山': 6, '山火贲': 1, '山天大畜': 2, '山泽损': 3, '火泽睽': 4, '天泽履': 5, '风泽中孚': 4, '风山渐': 3,
    '震为雷': 6, '雷地豫': 1, '雷水解': 2, '雷风恒': 3, '地风升': 4, '水风井': 5, '泽风大过': 4, '泽雷随': 3,
    '巽为风': 6, '风天小畜': 1, '风火家人': 2, '风雷益': 3, '天雷无妄': 4, '火雷噬嗑': 5, '山雷颐': 4, '山风蛊': 3,
    '离为火': 6, '火山旅': 1, '火风鼎': 2, '火水未济': 3, '山水蒙': 4, '风水涣': 5, '天水讼': 4, '天火同人': 3,
    '坤为地': 6, '地雷复': 1, '地泽临': 2, '地天泰': 3, '雷天大壮': 4, '泽天夬': 5, '水天需': 4, '水地比': 3,
    '兑为泽': 6, '泽水困': 1, '泽地萃': 2, '泽山咸': 3, '水山蹇': 4, '地山谦': 5, '雷山小过': 4, '雷泽归妹': 3
  };
  function shiPosOf(cast) { return SHI_TABLE[cast.ben_gua] || 6; }
  function yingPosOf(cast) { var s = shiPosOf(cast); return ((s + 2) % 6) + 1; }

  var YQ_MONTH_WX = { '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水', '辰': '土', '戌': '土', '丑': '土', '未': '土' };
  // 应爻旺衰：与引擎 SEASON_WANG 同法（当令旺/令生相/生令休/克令囚/令克死）
  function seasonStateOf(wx, monthZhi) {
    var mw = YQ_MONTH_WX[monthZhi];
    if (!wx || !mw) return '';
    if (wx === mw) return '旺';
    if (SHENG[mw] === wx) return '相';
    if (SHENG[wx] === mw) return '休';
    if (KE[wx] === mw) return '囚';
    if (KE[mw] === wx) return '死';
    return '';
  }

  // 世应打分：应爻旺衰 ＋ 世应生克 ＋ 应爻空破 ＋ 应爻临动；阈值沿用引擎（≥3→5★ ≥1→4★ ≥0→3★ ≥-2→2★ 否则1★）
  var SY_WANG_SCORE = { '旺': 2, '相': 1, '休': 0, '囚': -1, '死': -2 };
  function yingStar(cast) {
    var yp = yingPosOf(cast);
    var yz = (cast.lines_dz && cast.lines_dz[yp - 1]) || '';
    var wx = (cast.lines_wx && cast.lines_wx[yp - 1]) || '';
    var swx = (cast.lines_wx && cast.lines_wx[shiPosOf(cast) - 1]) || '';
    var score = SY_WANG_SCORE[seasonStateOf(wx, cast.yuezhi)] || 0;
    if (wx && swx) {
      if (swx === wx) score += 1;                 // 世应比和
      else if (SHENG[wx] === swx) score += 1;     // 应生世，糖是对方递的
      else if (KE[wx] === swx) score -= 1;        // 应克世，拉扯
      // 世生应 / 世克应：我在付出，不加不减
    }
    var xk = cast.xunkong || '';
    var ym = cast.yuezhi || '';
    if (yz && xk.indexOf(yz) >= 0) score -= 1;        // 应爻落空
    if (yz && ym && ym === YQ_CHONG[yz]) score -= 1;  // 应爻逢破
    if ((Number(cast.moving) || 0) === yp) score += 1; // 应爻临动，对方那边有动静
    return score >= 3 ? 5 : score >= 1 ? 4 : score >= 0 ? 3 : score >= -2 ? 2 : 1;
  }

  // 卦盘/卡图用：世应一句话关系
  function shiYingRel(cast) {
    var wx = (cast.lines_wx && cast.lines_wx[yingPosOf(cast) - 1]) || '';
    var swx = (cast.lines_wx && cast.lines_wx[shiPosOf(cast) - 1]) || '';
    if (!wx || !swx) return '';
    if (swx === wx) return '世应比和，两下里对得上';
    if (SHENG[wx] === swx) return '应爻生世爻，糖是对方递过来的';
    if (SHENG[swx] === wx) return '世爻生应爻，心意是你这边在给';
    if (KE[wx] === swx) return '应爻克世爻，拉扯里带点硬劲';
    return '世爻克应爻，这势要你先松一寸';
  }

  function yingqiLine(cast, seqN) {
    // 三十一轮：取法锚切到应爻（用神=应爻）；yongshen_positions 不再使用
    var pos = [yingPosOf(cast)];
    var idx = (pos[0] || 1) - 1;
    var yz = (cast.lines_dz && cast.lines_dz[idx]) || '';
    if (!yz || YQ_ZHI.indexOf(yz) < 0) return '';
    var wx = (cast.lines_wx && cast.lines_wx[idx]) || '';
    var chong = YQ_CHONG[yz];
    var he = YQ_LIUHE[yz];
    var xk = cast.xunkong || '';
    var ym = cast.yuezhi || '';
    var dzhi = (cast.day_gz && cast.day_gz.length > 1 && YQ_ZHI.indexOf(cast.day_gz[1]) >= 0) ? cast.day_gz[1] : '';
    var isMoving = pos.indexOf(Number(cast.moving) || 0) >= 0;
    var st = seasonStateOf(wx, ym); // 三十一轮：旺衰按应爻自己算，不再借引擎的用神状态
    var mu = wx ? YQ_MU[wx] : '';
    var sh = wx ? YQ_SHENG[wx] : '';
    // 应期总注次序：旬空 → 入墓 → 月破 → 逢合 → 太旺 → 衰绝 → 动静
    if (yz && xk.indexOf(yz) >= 0) {
      return pick(YQ_LEADS.kong, cast, 10, seqN) + '：' + yz + '月填实看第一波，' + chong + '月冲开就有动静。';
    }
    if (mu && ((dzhi && dzhi === mu) || (ym && ym === mu))) {
      var cmu = YQ_CHONG[mu];
      return pick(YQ_LEADS.mu, cast, 10, seqN) + '：' + cmu + '月看第一波，再往后就看' + cmu + '年。';
    }
    if (ym && ym === chong) {
      return pick(YQ_LEADS.po, cast, 10, seqN).replace('{ym}', ym) + '：' + yz + '月填实看第一波，' + he + '月接着看。';
    }
    if ((dzhi && dzhi === he) || (ym && ym === he)) {
      return pick(YQ_LEADS.he, cast, 10, seqN) + '：' + chong + '月看第一波，再往后就看' + chong + '年。';
    }
    if (st === '旺' && ym === yz) {
      return pick(YQ_LEADS.wang, cast, 10, seqN) + '：' + chong + '月看第一波，再往后就看' + chong + '年。';
    }
    if (st === '休' || st === '囚') {
      return pick(YQ_LEADS.ruo, cast, 10, seqN) + '：' + sh + '月看第一波，到' + yz + '月就壮了。';
    }
    if (isMoving) {
      // 二十九轮：动爻先看病在变爻（空/破），再看日辰冲，最后看回头克，都不中才是 plain 动
      var bdz = bianDzOf(cast);
      var bwx = bdz ? YQ_DZ_WX[bdz] : '';
      var bchong = bdz ? YQ_CHONG[bdz] : '';
      if (bdz && bwx && xk.indexOf(bdz) >= 0) {
        return pick(YQ_LEADS.bkong, cast, 10, seqN) + '：' + bdz + '月填实看第一波，' + bchong + '月冲空也有动静。';
      }
      // 变爻月破在世应取法下结构性被逢合接住（动位=应位⟹冲变=合本），分支删除（三十一轮）
      if (dzhi && dzhi === chong) {
        return pick(YQ_LEADS.richong, cast, 10, seqN) + '：' + yz + '月看第一波，' + he + '月也有动静。';
      }
      if (bdz && bwx && wxRel(bwx, wx) === '克') {
        return pick(YQ_LEADS.huike, cast, 10, seqN) + '：' + bdz + '月看第一波，到' + yz + '月稳住。';
      }
      return pick(YQ_LEADS.dong, cast, 10, seqN) + '：' + yz + '月看第一波，' + he + '月也有动静。';
    }
    return pick(YQ_LEADS.jing, cast, 10, seqN) + '：' + yz + '月看第一波，' + chong + '月也有动静。';
  }

  // 槽6a 行动建议（常规 3×6 / BE 3×4；三十五轮lyvia：只下判断不给指令——
  // 测的是CP不是测算者，一句话说清态度，12-22字，禁动手类台词与比喻腔）
  var ADVICE = {
    high: [
      '他们这次的动静值得你认真跟下去。',
      '这段关系正处在好的势头里，值得期待。',
      '他们俩的心意眼下对得上，看着就舒心。',
      '这一对的走向是稳的，可以安心看下去。',
      '眼下的甜是双向的，不是一厢情愿。',
      '他们正往一处走，这段值得多看一阵。'
    ],
    mid: [
      '他们还在中间地带，暂时不会有定论。',
      '这段关系的答案，还没到揭晓的时候。',
      '眼下就是拉锯，谁也没跨出那一步。',
      '他们的事还悬着，但没有往坏里走。',
      '这个阶段变数还在，结论下早了。',
      '他们的火候还差一截，还不到定局。'
    ],
    low: [
      '这段的势在往下走，热度难再续。',
      '他们的联系会越来越淡，这是趋势。',
      '这一对最好的阶段，已经过去了。',
      '他们的心思，已经各自往别处走了。',
      '这段缘分到这里，基本就收尾了。',
      '往后再有互动，多半也只是寒暄。'
    ]
  };
  // 槽6b 金句（常规 3×6 / BE 3×4；也供大字报取用；二十一轮lyvia：加长口语化）
  var GOLD = {
    high: [
      '好的关系就是两个人都不用猜，消息一来一回都坦荡，看着都替他们舒心。',
      '心动这种事是藏不住的，他们眼里的光你早就看见了，剩下的只是时间问题。',
      '双向的靠近从来不需要一个人使劲，他们这一次，是同时朝对方走过去的。',
      '最甜的桥段就是两个人都在悄悄靠近，谁也没有喊停，而你正好全程在场。',
      '真诚是唯一的捷径，他们这一份走得慢，但每一步都算数。',
      '势均力敌的心动才经得起时间，他们这一份，值得你慢慢看下去。'
    ],
    mid: [
      '现在还没到揭晓的时候，你先别急，把这份悬念多留几天，后面自然有答案。',
      '暧昧这门课要修满才有答案，他们还在中间晃，急也急不来。',
      '有些答案时间会比人先知道，你只管把自己的日子过好，到点自然会揭晓。',
      '心动有多少，互动会说话，嘴上说的可以修饰，行动是装不出来的。',
      '这个阶段耐心比猜测管用，他们自己会把关系走明白的。',
      '别用猜测消耗自己，值得的答案不会失约，不值得的猜中了也没有意思。'
    ],
    low: [
      '体面退场也是一种成全，成全那段回忆，也成全下一个马上要心动的你。',
      '留不住的剧情就别再追更了，你的热情很贵，要花在还会更新的故事上。',
      '认真嗑过的人自带光，这段心意没有白费，它让你更清楚自己喜欢什么。',
      '散场不是失败，是各自去对了片场，戏好看就行，不用管座位怎么分。',
      '别把告别拖成连续剧，长痛和短痛之间，选短的那个，对谁都仁慈。',
      '放下不是认输，是给自己让路，路让出来了，新的心动才进得来。'
    ]
  };
  /* ── 确定性轮换：卦名+日期+动爻+星数+分类+第几对 → 种子 ──
   * 同一对同一天复测不变；再摇一卦（第几对+1）或换日子即轮到下一组话术
   */
  function seedOf(cast, salt, seq) {
    var s = (cast.event_date || '') + '|' + (cast.ben_gua || '') + '|' + cast.moving +
      '|' + cast.star + '|' + (cast.category || '') + '|' + (salt || 0) + '|' + (seq || 0);
    var h = 7;
    for (var i = 0; i < s.length; i++) h = (h * 131 + s.charCodeAt(i)) % 999983;
    return h;
  }
  function pick(pool, cast, salt, seq) {
    if (!pool || !pool.length) return '';
    return pool[seedOf(cast, salt, seq) % pool.length];
  }

  function yingMark(cast) {
    var pos = yingPosOf(cast); // 三十一轮：标记句锚应爻
    var mk = (cast.lines_marks && cast.lines_marks[pos - 1]) || '';
    if (mk.indexOf('空') >= 0) return '另：应爻落旬空，答案悬而未决，过些时日会有新信息。';
    if (mk.indexOf('破') >= 0) return '另：应爻逢月破，中途易有反复。';
    return '';
  }

  /* ── 六槽解读：卦象 → 过去 → 现在 → 未来 → （日期）→ 金句建议 ──
   * 一句一行；seq=第几对（轮换用），BE 线走专属池且绝不给事实断言
   */
  /* ── 三十二轮（lyvia）：干支月挂公历注——看的人不知道申月寅月是几月 ──
   * 节气月约口径：寅月=立春到惊蛰≈公历2月到3月初，余者顺推；只作粗粒度对照，不给具体日期
   */
  var YQ_GLOSS = {
    '寅': '公历约2月到3月初', '卯': '公历约3月到4月初', '辰': '公历约4月到5月初',
    '巳': '公历约5月到6月初', '午': '公历约6月到7月初', '未': '公历约7月到8月初',
    '申': '公历约8月到9月初', '酉': '公历约9月到10月初', '戌': '公历约10月到11月初',
    '亥': '公历约11月到12月初', '子': '公历约12月到1月初', '丑': '公历约1月到2月初'
  };
  var YQ_ZHI_ORDER = '子丑寅卯辰巳午未申酉戌亥';
  function glossGz(line, cast) {
    var out = line || '';
    for (var i = 0; i < YQ_ZHI_ORDER.length; i++) {
      var z = YQ_ZHI_ORDER.charAt(i);
      out = out.split(z + '月').join(z + '月（' + YQ_GLOSS[z] + '）');
    }
    var y = parseInt((cast.event_date || '') + '', 10); // '2026-9-5' → 2026
    if (y >= 1900 && y <= 2100) {
      for (var k = 0; k < YQ_ZHI_ORDER.length; k++) {
        var b = YQ_ZHI_ORDER.charAt(k);
        if (out.indexOf(b + '年') < 0) continue;
        var ty = y + 1;
        while ((((ty - 4) % 12) + 12) % 12 !== k) ty++;
        out = out.split(b + '年').join(b + '年（' + ty + '年）');
      }
    }
    return out;
  }

  function build(cast, yq, cpState, birthYear, seq) {
    var band = bandOf(cast.star);
    var vd = verdictOf(cast, cpState);
    /* 四十四轮（lyvia）：正文只依据卦象测算的关系走向；表态只进 REPLY 对照句一句
     * （回应「他选的看法是否符合卦象」），PAST/NOW/FUTURE/ADVICE/GOLD/ANSWER 一律不跟随表态
     */
    var seqN = Number(seq) || 0;

    var guaLine = pick(GUA_LINE, cast, 0, seqN)
      .replace('{A}', cast.ben_gua).replace('{B}', cast.bian_gua)
      .replace('{n}', CN_NUM[cast.moving] || cast.moving);
    var pastLine = pick(PAST[band.key], cast, 1, seqN);
    var futureRaw = pick(FUTURE[band.key], cast, 3, seqN);
    var nowLine = '眼下的局面是：' + stripLead(pick(NOW[band.key], cast, 2, seqN));
    var futureLine = '往后的走向：' + stripLead(futureRaw);
    var reply = (REPLY[cpState] && REPLY[cpState][band.key]) ? pick(REPLY[cpState][band.key], cast, 7, seqN) : '';

    var ansPool = ANSWER.hot;
    var ansLine = ansPool ? pick(ansPool[band.key], cast, 8, seqN) : '';
    /* 三十六轮（lyvia）：高亮从撒词改成标位置——全文只有两处上色：
     * 关系判断句（赞成/反对）＋最后金句；卦象与正文一律素色。
     * 跳过表态没有对照句时，判断位退回直接回答句，位置仍只有两处
     */
    var vdLine = reply || ansLine || '';
    var vdHot = '';
    if (reply) { var sp0 = splitHot(reply); vdLine = sp0.text; vdHot = sp0.hot; } // 四十轮：结论短语=高亮位
    var summary = [guaLine];
    var roles = ['gua'];
    if (vdLine) { summary.push(vdLine); roles.push('vd'); }
    if (vdLine !== ansLine && ansLine) { summary.push(ansLine); roles.push('bd'); } // 十七轮：回答句式在场但不当开头
    summary.push(pastLine, nowLine, futureLine);
    roles.push('bd', 'bd', 'bd');

    if (band.key !== 'low') {
      // 二十四轮禁具体日期；二十六轮取法改按总注（空/墓/破/合/旺衰/动静），不再只看用神值支
      var yqLine = yingqiLine(cast, seqN);
      if (yqLine) { summary.push(glossGz(yqLine, cast)); roles.push('bd'); } // 三十二轮：干支月/年挂公历对照
    }

    var adviceLine = '所以，' + distinctPick(ADVICE[band.key], cast, 5, seqN, clashWords(futureRaw));
    var goldLine = distinctPick(GOLD[band.key], cast, 6, seqN,
      clashWords(futureRaw).concat(clashWords(adviceLine)));
    var birthTail = cast.category === 'career' ? birthSentence(cast, birthYear) : '';
    summary.push(adviceLine);
    roles.push('bd');
    summary.push(goldLine + birthTail);
    roles.push('gold');

    // 三十一轮：meta 行切世应口径
    var ywx2 = (cast.lines_wx && cast.lines_wx[yingPosOf(cast) - 1]) || '';
    var base = '世应：' + shiYingRel(cast) + '；应爻' +
      (STATE_PHRASE[seasonStateOf(ywx2, cast.yuezhi)] || '平稳') + '。' + yingMark(cast);

    return {
      band: band,
      reply: vdLine,
      cpState: cpState === 'rumor' ? 'rumor' : (cpState === 'be' ? 'be' : ''), // 四十四轮：仅作输入回执，裁定/正文已与表态无关
      verdict: vd.word,
      title: cast.category_label + ' · ' + cast.ben_gua + '（' + vd.word + '）',
      summary: summary,
      roles: roles, // 三十六轮（lyvia）：与 summary 一一对应——gua/vd/bd/gold，页面与卡图按此定式样
      vdHot: vdHot, // 四十轮（lyvia）：判断句里的结论短语=高亮位；跳过表态退回答句时为空=整句素色
      base: base,
      timing: '',
      advice: [],
      footnote: FOOTNOTE
    };
  }

  /* ── 大字报：档位词做结论大字 ＋ 金句（金句与解答的槽6b共用池，不与页面重复取词）
   * 四十四轮（lyvia）：金句池不再按表态切换——大字报整张只反映卦象测算
   */
  function posterFor(cast, rd) {
    var sub = pick(GOLD[rd.band.key], cast, 8, 0);
    return { big: rd.verdict, quote: sub };
  }

  /* ── 三十六轮（lyvia）：重点词撒词高亮整体退役——标的词不是读者心里的重点，反而莫名其妙。
   * 改为按槽位标位置：roles 里 vd（赞成/反对判断句）与 gold（金句）两处上色，
   * 卦象与正文素色；式样（颜色/标签/底色）归页面层（app.js + style.css），数据层只给角色
   */

  var Readings = { build: build, bandOf: bandOf, BAND: BAND, posterFor: posterFor, verdictOf: verdictOf, zodiacOf: zodiacOf,
    yingStar: yingStar, shiPosOf: shiPosOf, yingPosOf: yingPosOf, shiYingRel: shiYingRel, seasonStateOf: seasonStateOf, SHI_TABLE: SHI_TABLE };

  if (typeof window !== 'undefined') {
    window.Readings = Readings;
  } else if (typeof global !== 'undefined') {
    global.Readings = Readings;
  }
})();
