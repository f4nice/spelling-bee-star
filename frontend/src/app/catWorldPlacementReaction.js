const DAILY_MOOD_PLACEMENT_PROFILES = Object.freeze({
  bright: Object.freeze({
    prefix: "我今天很有精神，",
    styleKey: "delighted",
    cueKind: "sparkle",
    badgeLabel: "开心落脚",
  }),
  curious: Object.freeze({
    prefix: "我正想探索，",
    styleKey: "inspect",
    cueKind: "question",
    badgeLabel: "好奇观察",
  }),
  clingy: Object.freeze({
    prefix: "只要你在附近，",
    styleKey: "cuddle",
    cueKind: "heart",
    badgeLabel: "等你陪伴",
  }),
  lazy: Object.freeze({
    prefix: "我今天想慢慢来，",
    styleKey: "settle",
    cueKind: "yawn",
    badgeLabel: "慢慢安顿",
  }),
  quiet: Object.freeze({
    prefix: "我想安静一会儿，",
    styleKey: "settle",
    cueKind: "ellipsis",
    badgeLabel: "安静落脚",
  }),
  grumpy: Object.freeze({
    prefix: "我今天有点闹情绪，不过",
    styleKey: "wiggle",
    cueKind: "huff",
    badgeLabel: "还在适应",
  }),
});

const TEMPERAMENT_PLACEMENT_PROFILES = Object.freeze({
  calm: Object.freeze({ styleKey: "settle", cueKind: "ellipsis", badgeLabel: "安静落脚" }),
  gentle: Object.freeze({ styleKey: "soften", cueKind: "heart", badgeLabel: "轻轻落下" }),
  chatty: Object.freeze({ styleKey: "bounce", cueKind: "chirp", badgeLabel: "落地喵喵" }),
  guardian: Object.freeze({ styleKey: "inspect", cueKind: "lookout", badgeLabel: "巡视落点" }),
  clingy: Object.freeze({ styleKey: "cuddle", cueKind: "heart", badgeLabel: "等你陪伴" }),
  adventurous: Object.freeze({ styleKey: "bounce", cueKind: "sparkle", badgeLabel: "马上探索" }),
  balanced: Object.freeze({ styleKey: "soften", cueKind: "paw", badgeLabel: "稳稳落脚" }),
});

const TEMPERAMENT_DESTINATION_MESSAGES = Object.freeze({
  calm: Object.freeze({
    floor: Object.freeze(["这里挺安静，我先坐下看看。", "这个落点不吵，我先在附近待一会儿。"]),
    decor: Object.freeze(["我先在{item}旁安静待一会儿。", "我会慢慢试试{item}，看看这里够不够安静。"]),
    favorite: Object.freeze(["这是我喜欢的{item}，正好安静待一会儿。", "{item}最合我心意，我想在这里多坐一会儿。"]),
  }),
  gentle: Object.freeze({
    floor: Object.freeze(["放得很稳，我会轻轻看看周围。", "这里很舒服，我先慢慢熟悉一下。"]),
    decor: Object.freeze(["我会轻轻试试{item}，放稳就好。", "谢谢你带我来{item}，我先舒服地靠一会儿。"]),
    favorite: Object.freeze(["是我喜欢的{item}，谢谢你记得。", "{item}让我很安心，我会在这里乖乖待着。"]),
  }),
  chatty: Object.freeze({
    floor: Object.freeze(["落地啦，我要把这里的新发现都讲给你听。", "这里视野不错，等我边走边告诉你。"]),
    decor: Object.freeze(["到{item}啦，我有好多感受想告诉你。", "我先试试{item}，待会儿给你讲讲好不好玩。"]),
    favorite: Object.freeze(["是我最爱聊的{item}！我要马上告诉你有多舒服。", "你把我放到喜欢的{item}啦，听我开心地喵一会儿。"]),
  }),
  guardian: Object.freeze({
    floor: Object.freeze(["从这里看得清，我先去巡一圈。", "这个位置适合观察，我会守好附近。"]),
    decor: Object.freeze(["我先检查一下{item}和周围的动静。", "站在{item}这里，正好把附近看清楚。"]),
    favorite: Object.freeze(["喜欢的{item}视野很好，这里交给我守着。", "{item}是我的好哨位，我会认真看住周围。"]),
  }),
  clingy: Object.freeze({
    floor: Object.freeze(["我就在这里等你，别走得太远。", "落地也要离你近一点，我会跟着你的声音。"]),
    decor: Object.freeze(["你在附近的话，我愿意在{item}多待一会儿。", "把{item}放在你看得见的地方，我就安心了。"]),
    favorite: Object.freeze(["喜欢的{item}和你都在，我想一直待在这里。", "你陪我坐在{item}旁边，我就特别安心。"]),
  }),
  adventurous: Object.freeze({
    floor: Object.freeze(["新落点收到，我马上从这里出发探索。", "这里没来过，我要先跑一小圈看看。"]),
    decor: Object.freeze(["新落点是{item}，我马上探索一下。", "{item}看起来很有意思，我先试个新玩法。"]),
    favorite: Object.freeze(["最喜欢的{item}！我已经想好怎么玩了。", "{item}就是我的探索基地，我要多待一会儿。"]),
  }),
  balanced: Object.freeze({
    floor: Object.freeze(["这里不错，我先看看四周。", "落稳啦，我会从这里慢慢熟悉房间。"]),
    decor: Object.freeze(["我先试试{item}，看看这里舒不舒服。", "到{item}啦，我会按自己的节奏待一会儿。"]),
    favorite: Object.freeze(["这是我喜欢的{item}，我想在这里多待一会儿。", "你选中了我喜欢的{item}，这里正合适。"]),
  }),
});

const PLACEMENT_MOTIONS = Object.freeze({
  delighted: Object.freeze({ hopY: 8, swayX: 1.5, tilt: 1.8, duration: 175, repeats: 2 }),
  inspect: Object.freeze({ hopY: 3, swayX: 2.2, tilt: 2.6, duration: 260, repeats: 2 }),
  cuddle: Object.freeze({ hopY: 4, swayX: 0.8, tilt: 0.8, duration: 310, repeats: 1 }),
  settle: Object.freeze({ hopY: 2, swayX: 0.5, tilt: -1.2, duration: 380, repeats: 1 }),
  wiggle: Object.freeze({ hopY: 2, swayX: 3.4, tilt: 3.8, duration: 145, repeats: 3 }),
  soften: Object.freeze({ hopY: 4, swayX: 0.9, tilt: 1.1, duration: 270, repeats: 1 }),
  bounce: Object.freeze({ hopY: 7, swayX: 1.8, tilt: 2, duration: 185, repeats: 2 }),
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

function fillItemLabel(message = "", label = "这里") {
  return String(message || "").replaceAll("{item}", label || "这里");
}

export function catWorldPlacementReactionPlan(cat = {}, behavior = {}, target = {}) {
  const catId = String(cat.id || cat.profileId || cat.breedId || "cat");
  const dailyMoodKey = String(behavior.dailyMoodKey || "");
  const temperament = String(behavior.temperament || cat.traits?.temperament || "balanced");
  const moodProfile = DAILY_MOOD_PLACEMENT_PROFILES[dailyMoodKey];
  const temperamentProfile = TEMPERAMENT_PLACEMENT_PROFILES[temperament]
    || TEMPERAMENT_PLACEMENT_PROFILES.balanced;
  const destinationMessages = TEMPERAMENT_DESTINATION_MESSAGES[temperament]
    || TEMPERAMENT_DESTINATION_MESSAGES.balanced;
  const targetType = target.targetType === "decor" ? "decor" : "floor";
  const favorite = targetType === "decor" && target.favorite === true;
  const itemId = String(target.itemId || targetType);
  const itemLabel = String(target.itemLabel || "这里");
  const messageKind = targetType === "floor" ? "floor" : favorite ? "favorite" : "decor";
  const baseMessage = fillItemLabel(
    stablePick(destinationMessages[messageKind], `${catId}:${itemId}:${messageKind}:placement`),
    itemLabel,
  );
  const prefix = moodProfile?.prefix || "";
  const styleKey = favorite
    ? ["settle", "cuddle"].includes(moodProfile?.styleKey || temperamentProfile.styleKey)
      ? moodProfile?.styleKey || temperamentProfile.styleKey
      : dailyMoodKey === "grumpy"
        ? "soften"
        : "delighted"
    : moodProfile?.styleKey || temperamentProfile.styleKey;
  const cueKind = favorite
    ? ["gentle", "clingy"].includes(temperament) || dailyMoodKey === "clingy" ? "heart" : "sparkle"
    : moodProfile?.cueKind || temperamentProfile.cueKind;

  return {
    catId,
    targetType,
    itemId,
    itemLabel,
    favorite,
    temperament,
    dailyMoodKey,
    source: moodProfile ? "daily-mood+temperament" : "temperament",
    styleKey,
    cueKind,
    badgeLabel: favorite ? "最喜欢这里" : moodProfile?.badgeLabel || temperamentProfile.badgeLabel,
    message: `${prefix}${baseMessage}`,
    motion: { ...(PLACEMENT_MOTIONS[styleKey] || PLACEMENT_MOTIONS.soften) },
    identityToken: `${catId}:${stableHash(`${catId}:${itemId}:placement`) % 7}`,
  };
}
