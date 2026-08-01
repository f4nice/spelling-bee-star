const ESSAY_DAILY_PROMPTS = [
  {
    sourceLabel: "高考英语作文",
    typeLabel: "应用文 · 建议信",
    title: "A Greener School Week",
    prompt: "学校准备举办绿色校园周。请用英语给学生会写一封建议信，提出两项可执行的环保活动，并说明理由。",
    wordRange: "80-100 词",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 1 · Email",
    title: "A Weekend Plan for My Friend",
    prompt: "Your English-speaking friend is visiting this weekend. Write an email suggesting where to go, what to do and what to bring.",
    wordRange: "约 100 词",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "应用文 · 活动报道",
    title: "Our English Reading Day",
    prompt: "校英文报正在征集活动报道。请介绍学校英语阅读日的一项活动、同学们的参与情况以及你的收获。",
    wordRange: "80-100 词",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 2 · Story",
    title: "The Message on the Desk",
    prompt: "Write a story beginning with this sentence: When I entered the classroom, I saw a surprising message on my desk.",
    wordRange: "约 100 词",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "应用文 · 邀请信",
    title: "An Invitation to Culture Day",
    prompt: "学校将举办中国文化体验日。请用英语邀请外教参加，介绍时间、地点和两项主要活动。",
    wordRange: "80-100 词",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 2 · Article",
    title: "The Best Way to Learn Something New",
    prompt: "Write an article about something useful you learned recently. Explain how you learned it and why you would recommend it to others.",
    wordRange: "约 100 词",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "应用文 · 演讲稿",
    title: "Small Actions, Real Progress",
    prompt: "英语课将进行主题演讲。请结合一次亲身经历，谈谈小行动如何带来真正的进步。",
    wordRange: "80-100 词",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 1 · Email",
    title: "Joining a New School Club",
    prompt: "Your friend wants to join a school club. Write an email recommending one club, describing its activities and explaining why it is a good choice.",
    wordRange: "约 100 词",
  },
];

function normalizedDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? new Date() : date;
}

export function essayDailyPromptForDate(value = new Date()) {
  const date = normalizedDate(value);
  const dayNumber = Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000);
  const prompt = ESSAY_DAILY_PROMPTS[((dayNumber % ESSAY_DAILY_PROMPTS.length) + ESSAY_DAILY_PROMPTS.length) % ESSAY_DAILY_PROMPTS.length];
  return {
    ...prompt,
    dateKey: [date.getFullYear(), date.getMonth() + 1, date.getDate()].map((part) => String(part).padStart(2, "0")).join("-"),
  };
}
