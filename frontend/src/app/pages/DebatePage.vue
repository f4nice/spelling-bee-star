<script setup>
import { computed, nextTick, ref, watch } from "vue";
import {
  Award,
  CalendarDays,
  CheckCircle2,
  MessageSquareQuote,
  Send,
  Sparkles,
  Swords,
  Target,
  Trophy,
  Zap,
} from "lucide-vue-next";
import { routeApiPaths } from "../routeApiPaths.js";
import { fetchJson } from "../utils.js";

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
});

const payload = ref(props.data || {});
const selectedLevel = ref("primary");
const selectedStance = ref("pro");
const argument = ref("");
const busyAction = ref("");
const notice = ref("");
const transcriptEnd = ref(null);

watch(
  () => props.data,
  (value) => applyPayload(value),
  { immediate: true },
);

const session = computed(() => payload.value?.session || null);
const rules = computed(() => payload.value?.rules || {});
const levels = computed(() => payload.value?.levels || []);
const currentTopic = computed(() => {
  if (session.value?.topic) return session.value.topic;
  return payload.value?.dailyTopics?.[selectedLevel.value] || {};
});
const active = computed(() => session.value?.status === "active");
const completed = computed(() => Boolean(session.value && session.value.status !== "active"));
const canSubmit = computed(() => active.value && argument.value.trim().length >= 8 && !busyAction.value);
const argumentMaxChars = computed(() => Number(rules.value.argumentMaxChars || 2000));
const targetPoints = computed(() => Number(session.value?.targetPoints || rules.value.targetPoints || 100));
const maxTurns = computed(() => Number(session.value?.maxTurns || rules.value.maxTurns || 6));
const userProgress = computed(() => scoreProgress(session.value?.userPoints));
const aiProgress = computed(() => scoreProgress(session.value?.aiPoints));
const stanceText = computed(() => (session.value?.userStance === "con" ? "反对方" : "支持方"));
const aiStanceText = computed(() => (session.value?.aiStance === "con" ? "反对方" : "支持方"));
const finalReview = computed(() => session.value?.finalFeedback || {});
const resultTone = computed(() => {
  if (session.value?.status === "won") return "won";
  if (session.value?.status === "lost") return "lost";
  return "draw";
});
const resultTitle = computed(() => {
  if (session.value?.status === "won") return "恭喜，你赢下了今天的辩论";
  if (session.value?.status === "lost") return "今天由 AI 对手获胜";
  return "势均力敌，本场平局";
});

function applyPayload(value) {
  payload.value = value || {};
  if (value?.session?.level) selectedLevel.value = value.session.level;
  if (value?.session?.userStance) selectedStance.value = value.session.userStance;
}

function scoreProgress(value) {
  return `${Math.min(Math.max((Number(value || 0) / targetPoints.value) * 100, 0), 100)}%`;
}

function stanceLabel(value) {
  return value === "con" ? "反对" : "支持";
}

function dimensionRows(entry) {
  const dimensions = entry?.dimensions || {};
  return (rules.value.scoreDimensions || []).map((item) => ({
    ...item,
    value: Number(dimensions[item.key] || 0),
  }));
}

function requestOptions(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function startDebate() {
  if (busyAction.value) return;
  busyAction.value = "start";
  notice.value = "";
  try {
    const nextPayload = await fetchJson(
      routeApiPaths.debateStart(),
      requestOptions({ level: selectedLevel.value, stance: selectedStance.value }),
    );
    applyPayload(nextPayload);
    notice.value = "比赛开始。请先亮出你的第一个观点。";
  } catch (error) {
    notice.value = error.message || "暂时无法开始比赛。";
  } finally {
    busyAction.value = "";
  }
}

async function submitTurn() {
  const text = argument.value.trim();
  if (!canSubmit.value || !text) return;
  busyAction.value = "turn";
  notice.value = "";
  try {
    const nextPayload = await fetchJson(
      routeApiPaths.debateTurn(session.value.id),
      requestOptions({ argument: text }),
    );
    argument.value = "";
    applyPayload(nextPayload);
    if (nextPayload?.energyGain > 0) {
      notice.value = `本场结算完成，猫咪世界获得 +${nextPayload.energyGain} 能量。`;
    } else {
      notice.value = nextPayload?.session?.status === "active" ? "本轮评分完成，轮到你继续回应。" : "本场结算完成。";
    }
    await nextTick();
    transcriptEnd.value?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    notice.value = error.message || "这一轮暂时没有提交成功。";
  } finally {
    busyAction.value = "";
  }
}
</script>

<template>
  <section class="debate-page">
    <header class="debate-page-head">
      <div>
        <span class="eyebrow">DAILY DEBATE</span>
        <h1>每日 AI 辩论赛</h1>
        <p><CalendarDays :size="16" /> {{ payload.today }}</p>
      </div>
      <div class="debate-head-rules" aria-label="比赛规则">
        <span><Target :size="18" /><strong>{{ rules.targetPoints || 100 }}</strong> 赛点</span>
        <span><Swords :size="18" /><strong>{{ rules.maxTurns || 6 }}</strong> 轮上限</span>
      </div>
    </header>

    <p v-if="notice" class="debate-notice" aria-live="polite">{{ notice }}</p>

    <section v-if="!session" class="debate-setup panel">
      <div class="debate-setup-controls">
        <div>
          <span class="debate-field-label">选择组别</span>
          <div class="debate-segmented" role="group" aria-label="选择辩论组别">
            <button
              v-for="level in levels"
              :key="level.key"
              type="button"
              :class="{ active: selectedLevel === level.key }"
              :aria-pressed="selectedLevel === level.key"
              @click="selectedLevel = level.key"
            >
              {{ level.label }}
            </button>
          </div>
        </div>
        <p>{{ levels.find((item) => item.key === selectedLevel)?.description }}</p>
      </div>

      <div class="debate-daily-topic">
        <span>{{ currentTopic.category || "今日辩题" }}</span>
        <h2>{{ currentTopic.title }}</h2>
        <div class="debate-topic-hints">
          <span v-for="hint in currentTopic.hints || []" :key="hint">{{ hint }}</span>
        </div>
      </div>

      <div class="debate-stance-picker">
        <span class="debate-field-label">选择你的立场</span>
        <div>
          <button
            type="button"
            :class="{ active: selectedStance === 'pro' }"
            :aria-pressed="selectedStance === 'pro'"
            @click="selectedStance = 'pro'"
          >
            <CheckCircle2 :size="20" />
            <span><strong>支持方</strong><small>我赞成这个观点</small></span>
          </button>
          <button
            type="button"
            :class="{ active: selectedStance === 'con' }"
            :aria-pressed="selectedStance === 'con'"
            @click="selectedStance = 'con'"
          >
            <Swords :size="20" />
            <span><strong>反对方</strong><small>我不赞成这个观点</small></span>
          </button>
        </div>
      </div>

      <button class="primary-action-button debate-start-button" type="button" :disabled="Boolean(busyAction)" @click="startDebate">
        <Swords :size="20" />
        {{ busyAction === "start" ? "正在准备赛场..." : "开始今天的辩论" }}
      </button>
    </section>

    <template v-else>
      <section class="debate-scoreboard">
        <div class="debate-score-side user">
          <span>YOU · {{ stanceText }}</span>
          <strong>{{ session.userPoints }}</strong>
          <i><b :style="{ width: userProgress }"></b></i>
        </div>
        <div class="debate-score-center">
          <Swords :size="26" />
          <strong>第 {{ Math.min(session.turnCount + (active ? 1 : 0), maxTurns) }} / {{ maxTurns }} 轮</strong>
          <span>先到 {{ targetPoints }} 赛点获胜</span>
        </div>
        <div class="debate-score-side ai">
          <span>AI · {{ aiStanceText }}</span>
          <strong>{{ session.aiPoints }}</strong>
          <i><b :style="{ width: aiProgress }"></b></i>
        </div>
      </section>

      <section class="debate-arena panel">
        <header class="debate-arena-head">
          <div>
            <span>{{ session.topic.category }}</span>
            <h2>{{ session.topic.title }}</h2>
          </div>
          <em :class="['debate-status', session.status]">{{ session.statusLabel }}</em>
        </header>

        <div v-if="session.transcript.length" class="debate-transcript" aria-live="polite">
          <article
            v-for="(entry, index) in session.transcript"
            :key="`${entry.round}-${entry.role}-${index}`"
            :class="['debate-message', entry.role]"
          >
            <header>
              <span>
                <MessageSquareQuote v-if="entry.role === 'user'" :size="17" />
                <Sparkles v-else :size="17" />
                {{ entry.role === "user" ? `我的第 ${entry.round} 轮` : `AI 第 ${entry.round} 轮回应` }}
              </span>
              <strong>+{{ entry.points }} 赛点</strong>
            </header>
            <p>{{ entry.text }}</p>
            <div v-if="entry.role === 'user'" class="debate-dimension-row">
              <span v-for="item in dimensionRows(entry)" :key="item.key">
                {{ item.label }} <strong>{{ item.value }}/{{ item.max }}</strong>
              </span>
            </div>
            <aside v-if="entry.coachNote" class="debate-coach-note">
              <Award :size="18" />
              <span><strong>{{ entry.highlight }}</strong>{{ entry.coachNote }}</span>
            </aside>
          </article>
          <div ref="transcriptEnd"></div>
        </div>
        <div v-else class="debate-opening">
          <MessageSquareQuote :size="30" />
          <strong>{{ stanceLabel(session.userStance) }}方先发言</strong>
          <span>亮出观点，再用一个理由或例子支持它。</span>
        </div>

        <form v-if="active" class="debate-turn-form" @submit.prevent="submitTurn">
          <label for="debate-argument">本轮发言</label>
          <textarea
            id="debate-argument"
            v-model="argument"
            :maxlength="argumentMaxChars"
            placeholder="写下你的观点、理由、例子，或回应 AI 刚才的论点..."
            :disabled="Boolean(busyAction)"
          ></textarea>
          <div>
            <span>{{ argument.length }} / {{ argumentMaxChars }}</span>
            <button class="primary-action-button" type="submit" :disabled="!canSubmit">
              <Sparkles v-if="busyAction === 'turn'" :size="18" />
              <Send v-else :size="18" />
              {{ busyAction === "turn" ? "AI 正在思考和评分..." : "提交本轮" }}
            </button>
          </div>
        </form>
      </section>

      <section v-if="completed" :class="['debate-result', resultTone]">
        <header>
          <div>
            <span class="eyebrow">FINAL REVIEW</span>
            <h2>{{ resultTitle }}</h2>
          </div>
          <div class="debate-final-score">
            <Trophy :size="22" />
            <strong>{{ session.finalScore }}</strong>
            <span>综合分</span>
          </div>
        </header>
        <p>{{ finalReview.summary || "你完成了今天的辩论，坚持表达本身就是一次进步。" }}</p>
        <div class="debate-reward-band">
          <Zap :size="22" />
          <strong>+{{ session.energyAwarded }} 猫能量</strong>
          <span>本场奖励已计入猫咪世界</span>
        </div>

        <div v-if="finalReview.strengths?.length" class="debate-strengths">
          <strong>今天做得好的地方</strong>
          <span v-for="item in finalReview.strengths" :key="item"><CheckCircle2 :size="16" />{{ item }}</span>
        </div>

        <div v-if="finalReview.improvements?.length" class="debate-improvements">
          <h3>AI 教练建议</h3>
          <article v-for="(item, index) in finalReview.improvements" :key="`${item.title}-${index}`">
            <header><span>{{ index + 1 }}</span><strong>{{ item.title }}</strong></header>
            <p>{{ item.advice }}</p>
            <blockquote v-if="item.example"><strong>示例表达</strong>{{ item.example }}</blockquote>
          </article>
        </div>

        <div v-if="finalReview.nextChallenge" class="debate-next-challenge">
          <Target :size="20" />
          <span><strong>下一次重点</strong>{{ finalReview.nextChallenge }}</span>
        </div>
      </section>
    </template>
  </section>
</template>
