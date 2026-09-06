const DAILY_MOOD_CARRY_PROFILES = Object.freeze({
  bright: Object.freeze({
    styleKey: "happy",
    badgeLabel: "开心抱抱",
    cueKind: "sparkle",
    messages: Object.freeze([
      "好呀，抱稳我，我们去看看房间里还有什么。",
      "我今天心情很好，可以抱着我去选一个新位置。",
      "被你抱起来啦，我想看看你准备带我去哪。",
    ]),
  }),
  curious: Object.freeze({
    styleKey: "lookout",
    badgeLabel: "好奇张望",
    cueKind: "question",
    messages: Object.freeze([
      "咦，要带我去哪儿？我先看看四周。",
      "这个高度看得更远，我想仔细看看你选的位置。",
      "先别急着放下，我正在观察新的落脚点。",
    ]),
  }),
  clingy: Object.freeze({
    styleKey: "cling",
    badgeLabel: "安心贴贴",
    cueKind: "heart",
    messages: Object.freeze([
      "再抱一会儿也可以，我会乖乖跟着你。",
      "这样离你更近啦，放到哪里我都愿意陪你。",
      "我喜欢被你抱着，慢慢走就好。",
    ]),
  }),
  lazy: Object.freeze({
    styleKey: "sleepy",
    badgeLabel: "软软垂下",
    cueKind: "breathe",
    messages: Object.freeze([
      "我今天有点懒，抱稳一点，我还想继续打盹。",
      "先让我软软地挂一会儿，再放到舒服的地方吧。",
      "移动慢一点，我还没有完全醒过来。",
    ]),
  }),
  quiet: Object.freeze({
    styleKey: "quiet",
    badgeLabel: "安静抱起",
    cueKind: "ellipsis",
    messages: Object.freeze([
      "我会安静待着，你慢慢选位置。",
      "抱稳就好，我想先看看你要把我放在哪里。",
      "不用着急，我会配合你换个地方。",
    ]),
  }),
  grumpy: Object.freeze({
    styleKey: "wiggle",
    badgeLabel: "抱稳一点",
    cueKind: "huff",
    messages: Object.freeze([
      "我今天有点闹脾气，抱稳一点，别突然放手。",
      "先说好，只换个舒服的位置，我就不扭来扭去。",
      "我现在不太高兴，动作轻一点，我会慢慢配合。",
    ]),
  }),
});

const TEMPERAMENT_CARRY_PROFILES = Object.freeze({
  calm: Object.freeze({
    styleKey: "quiet",
    badgeLabel: "安静抱起",
    cueKind: "ellipsis",
    messages: Object.freeze([
      "我会安静待着，放到能看见你学习的地方就好。",
      "抱稳一点，我想先确认新的位置够不够安静。",
      "慢慢走，我会在你选好的地方继续陪读。",
    ]),
  }),
  gentle: Object.freeze({
    styleKey: "relaxed",
    badgeLabel: "轻轻抱起",
    cueKind: "heart",
    messages: Object.freeze([
      "轻轻抱着就好，我会配合你换个舒服的位置。",
      "我准备好了，带我去你觉得合适的地方吧。",
      "不用着急，我会乖乖等你把我放稳。",
    ]),
  }),
  chatty: Object.freeze({
    styleKey: "happy",
    badgeLabel: "一路喵喵",
    cueKind: "chirp",
    messages: Object.freeze([
      "要带我去哪？我一路都可以讲给你听。",
      "抱起来啦，先告诉我新位置有什么好玩的。",
      "我已经准备好换地方了，别忘了听我喵一声。",
    ]),
  }),
  guardian: Object.freeze({
    styleKey: "lookout",
    badgeLabel: "警觉巡视",
    cueKind: "lookout",
    messages: Object.freeze([
      "抱高一点，我正好检查一下房间四周。",
      "先让我看看路线，再把我放到需要守着的地方。",
      "我会盯着前面，带我去新的巡逻位置吧。",
    ]),
  }),
  clingy: Object.freeze({
    styleKey: "cling",
    badgeLabel: "安心贴贴",
    cueKind: "heart",
    messages: Object.freeze([
      "这样离你更近啦，我会好好抱住。",
      "再抱一会儿吧，放在哪里我都愿意陪着你。",
      "我已经贴好了，慢慢带我去新位置吧。",
    ]),
  }),
  adventurous: Object.freeze({
    styleKey: "wiggle",
    badgeLabel: "跃跃欲试",
    cueKind: "sparkle",
    messages: Object.freeze([
      "新位置在哪里？抱稳我，我已经想跳过去看看了。",
      "快带我去探索，不过落地以前要抱稳一点。",
      "我看到好玩的地方了，带我靠近一点吧。",
    ]),
  }),
  balanced: Object.freeze({
    styleKey: "relaxed",
    badgeLabel: "稳稳抱起",
    cueKind: "paw",
    messages: Object.freeze([
      "抱稳我，点地板或发光家具就可以放下。",
      "我准备好了，带我去一个舒服的位置吧。",
      "慢慢移动就好，我会看看新的落脚点。",
    ]),
  }),
});

const CARRY_MOTIONS = Object.freeze({
  happy: Object.freeze({ swayX: 1.2, bobY: 3.8, tilt: 1.2, duration: 480 }),
  lookout: Object.freeze({ swayX: 1.7, bobY: 1.6, tilt: 2.1, duration: 620 }),
  cling: Object.freeze({ swayX: 0.8, bobY: 2.2, tilt: 0.7, duration: 760 }),
  sleepy: Object.freeze({ swayX: 0.6, bobY: 2.8, tilt: -2.2, duration: 960 }),
  quiet: Object.freeze({ swayX: 0.7, bobY: 1.4, tilt: 0.6, duration: 880 }),
  wiggle: Object.freeze({ swayX: 3.2, bobY: 1.2, tilt: 3.8, duration: 260 }),
  relaxed: Object.freeze({ swayX: 1, bobY: 2, tilt: 1, duration: 720 }),
});

const HABIT_CARRY_CUES = Object.freeze({
  chirp: "chirp",
  heart: "heart",
  hop: "sparkle",
  lookout: "lookout",
  paw: "paw",
  breathe: "breathe",
});

function stableHash(value = "") {
  let hash = 2166136261;
  for (const character of String(value || "")) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

function stablePick(values = [], seed = "") {
  if (!values.length) return "";
  return values[stableHash(seed) % values.length];
}

export function catWorldCarryReactionPlan(cat = {}, behavior = {}) {
  const catId = String(cat.id || cat.profileId || cat.breedId || "cat");
  const dailyMoodKey = String(behavior.dailyMoodKey || "");
  const temperament = String(
    behavior.temperament
    || cat.traits?.temperament
    || "balanced",
  );
  const sleeping = Boolean(behavior.sleeping || behavior.key === "sleeping");
  const waking = behavior.key === "waking";
  const moodProfile = DAILY_MOOD_CARRY_PROFILES[dailyMoodKey];
  const temperamentProfile = TEMPERAMENT_CARRY_PROFILES[temperament]
    || TEMPERAMENT_CARRY_PROFILES.balanced;
  const profile = sleeping
    ? DAILY_MOOD_CARRY_PROFILES.lazy
    : waking
      ? DAILY_MOOD_CARRY_PROFILES.curious
      : moodProfile || temperamentProfile;
  const source = sleeping ? "sleep" : waking ? "wake" : moodProfile ? "daily-mood" : "temperament";
  const habitAnimation = String(cat.individualHabit?.animation || "");
  const message = stablePick(
    profile.messages,
    `${catId}:${dailyMoodKey}:${temperament}:${habitAnimation}:carry`,
  );
  const cueKind = HABIT_CARRY_CUES[habitAnimation] || profile.cueKind;
  const styleKey = profile.styleKey;

  return {
    catId,
    source,
    styleKey,
    badgeLabel: profile.badgeLabel,
    message,
    cueKind,
    motion: { ...(CARRY_MOTIONS[styleKey] || CARRY_MOTIONS.relaxed) },
    identityToken: `${catId}:${stableHash(`${catId}:carry-pose`) % 4}`,
  };
}
