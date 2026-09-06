const TIME_PHASES = Object.freeze({
  dawn: Object.freeze({
    key: "dawn",
    label: "清晨",
    englishLabel: "DAWN",
    wallTint: 0xffdf9f,
    wallAlpha: 0.13,
    floorTint: 0xffefc2,
    floorAlpha: 0.05,
    accent: 0xfff07d,
  }),
  day: Object.freeze({
    key: "day",
    label: "白天",
    englishLabel: "DAYLIGHT",
    wallTint: 0xd9f6ff,
    wallAlpha: 0.06,
    floorTint: 0xfff8df,
    floorAlpha: 0.02,
    accent: 0x87d9ff,
  }),
  dusk: Object.freeze({
    key: "dusk",
    label: "黄昏",
    englishLabel: "DUSK",
    wallTint: 0xff8cad,
    wallAlpha: 0.14,
    floorTint: 0x6c5578,
    floorAlpha: 0.09,
    accent: 0xff9b73,
  }),
  night: Object.freeze({
    key: "night",
    label: "夜晚",
    englishLabel: "NIGHT",
    wallTint: 0x26375c,
    wallAlpha: 0.3,
    floorTint: 0x17243a,
    floorAlpha: 0.2,
    accent: 0xd9f6ff,
  }),
});

function normalizedHour(value) {
  const hour = value instanceof Date ? value.getHours() : Number(value);
  if (!Number.isFinite(hour)) return 12;
  return ((Math.floor(hour) % 24) + 24) % 24;
}

export function catWorldTimePhase(value = new Date()) {
  const hour = normalizedHour(value);
  if (hour >= 5 && hour < 9) return TIME_PHASES.dawn;
  if (hour >= 9 && hour < 17) return TIME_PHASES.day;
  if (hour >= 17 && hour < 20) return TIME_PHASES.dusk;
  return TIME_PHASES.night;
}

export function catWorldTimeAmbience(value = new Date()) {
  const date = value instanceof Date && Number.isFinite(value.getTime()) ? value : new Date();
  const phase = catWorldTimePhase(date);
  const clockLabel = `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  return {
    ...phase,
    hour: date.getHours(),
    clockLabel,
  };
}

