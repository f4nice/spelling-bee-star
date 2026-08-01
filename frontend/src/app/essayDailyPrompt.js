const ESSAY_DAILY_PROMPTS = [
  {
    sourceLabel: "高考英语作文",
    typeLabel: "Practical Writing · Advice Letter",
    title: "A Greener School Week",
    prompt: "Your school is planning a Green School Week. Write a letter to the student union suggesting two practical environmental activities and explain why they would be helpful.",
    wordRange: "80-100 words",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 1 · Email",
    title: "A Weekend Plan for My Friend",
    prompt: "Your English-speaking friend is visiting this weekend. Write an email suggesting where to go, what to do and what to bring.",
    wordRange: "About 100 words",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "Practical Writing · Activity Report",
    title: "Our English Reading Day",
    prompt: "Your school English newspaper is collecting activity reports. Describe one activity from English Reading Day, explain how the students took part and share what you learned from it.",
    wordRange: "80-100 words",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 2 · Story",
    title: "The Message on the Desk",
    prompt: "Write a story beginning with this sentence: When I entered the classroom, I saw a surprising message on my desk.",
    wordRange: "About 100 words",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "Practical Writing · Invitation Letter",
    title: "An Invitation to Culture Day",
    prompt: "Your school will hold a Chinese Culture Day. Write an invitation to your foreign teacher, including the time, the place and two main activities.",
    wordRange: "80-100 words",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 2 · Article",
    title: "The Best Way to Learn Something New",
    prompt: "Write an article about something useful you learned recently. Explain how you learned it and why you would recommend it to others.",
    wordRange: "About 100 words",
  },
  {
    sourceLabel: "高考英语作文",
    typeLabel: "Practical Writing · Speech",
    title: "Small Actions, Real Progress",
    prompt: "Give a speech in your English class about how small actions can lead to real progress. Use one personal experience to support your ideas.",
    wordRange: "80-100 words",
  },
  {
    sourceLabel: "PET Writing",
    typeLabel: "Part 1 · Email",
    title: "Joining a New School Club",
    prompt: "Your friend wants to join a school club. Write an email recommending one club, describing its activities and explaining why it is a good choice.",
    wordRange: "About 100 words",
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
