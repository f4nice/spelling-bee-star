<script setup>
import { computed, nextTick, ref, watch } from "vue";
import {
  ArrowRightLeft,
  Award,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  MessageSquareQuote,
  Send,
  Sparkles,
  Swords,
  Target,
  Trophy,
  X,
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
const argument = ref("");
const busyAction = ref("");
const notice = ref("");
const transcriptEnd = ref(null);
const replaySession = ref(null);
const replayBusy = ref(0);
const selectedStage = ref("pro");
const replayStage = ref("pro");
const showRoleSwitch = ref(false);
const acknowledgedRoleSwitchSession = ref(0);

watch(
  () => props.data,
  (value) => applyPayload(value),
  { immediate: true },
);

const session = computed(() => payload.value?.session || null);
const rules = computed(() => payload.value?.rules || {});
const levels = computed(() => payload.value?.levels || []);
const history = computed(() => payload.value?.history || []);
const currentTopic = computed(() => {
  if (session.value?.topic) return session.value.topic;
  return payload.value?.dailyTopics?.[selectedLevel.value] || {};
});
const active = computed(() => session.value?.status === "active");
const completed = computed(() => Boolean(session.value && session.value.status !== "active"));
const argumentWordCount = computed(() => (argument.value.match(/[A-Za-z]+(?:[-'][A-Za-z]+)*/g) || []).length);
const canSubmit = computed(() => active.value && argumentWordCount.value >= 3 && !busyAction.value);
const argumentMaxChars = computed(() => Number(rules.value.argumentMaxChars || 2000));
const roundsPerSide = computed(() => Number(session.value?.roundsPerSide || rules.value.roundsPerSide || 10));
const sideTargetPoints = computed(() => Number(session.value?.sideTargetPoints || rules.value.sideTargetPoints || 100));
const totalRounds = computed(() => Number(session.value?.maxTurns || rules.value.maxTurns || roundsPerSide.value * 2));
const turnMaxPoints = computed(() => Number(session.value?.turnMaxPoints || rules.value.turnMaxPoints || 10));
const proPoints = computed(() => Number(session.value?.proPoints || 0));
const conPoints = computed(() => Number(session.value?.conPoints || 0));
const totalPoints = computed(() => Number(session.value?.totalPoints || proPoints.value + conPoints.value));
const proProgress = computed(() => scoreProgress(proPoints.value, sideTargetPoints.value));
const conProgress = computed(() => scoreProgress(conPoints.value, sideTargetPoints.value));
const stanceText = computed(() => stanceLabel(session.value?.currentUserStance));
const currentStageRound = computed(() => Number(
  session.value?.currentStageRound
  || ((Math.max(Number(session.value?.turnCount || 0), 0) % roundsPerSide.value) + 1),
));
const finalReview = computed(() => session.value?.finalFeedback || {});
const visibleTranscript = computed(() => (session.value?.transcript || []).filter(
  (entry) => stageForEntry(entry, session.value) === selectedStage.value,
));
const replayTranscript = computed(() => (replaySession.value?.transcript || []).filter(
  (entry) => stageForEntry(entry, replaySession.value) === replayStage.value,
));
const selectedStageIsCurrent = computed(() => selectedStage.value === session.value?.currentUserStance);

function applyPayload(value) {
  payload.value = value || {};
  if (value?.session?.level) selectedLevel.value = value.session.level;
  const nextSession = value?.session;
  if (!nextSession) {
    selectedStage.value = "pro";
    showRoleSwitch.value = false;
    return;
  }
  if (nextSession.status === "active") {
    selectedStage.value = Number(nextSession.turnCount || 0) >= Number(nextSession.roundsPerSide || 10)
      ? "con"
      : "pro";
    showRoleSwitch.value = (
      Number(nextSession.turnCount || 0) === Number(nextSession.roundsPerSide || 10)
      && acknowledgedRoleSwitchSession.value !== Number(nextSession.id || 0)
    );
  } else {
    selectedStage.value = "con";
    showRoleSwitch.value = false;
  }
}

function scoreProgress(value, maximum) {
  return `${Math.min(Math.max((Number(value || 0) / Math.max(Number(maximum || 0), 1)) * 100, 0), 100)}%`;
}

function stanceLabel(value) {
  return value === "con" ? "CON" : "PRO";
}

function sideForEntry(entry, source) {
  if (entry?.stance) return stanceLabel(entry.stance);
  if (source?.userStance === "both") {
    const sideRounds = Number(source?.scoringVersion || 1) >= 2
      ? Number(source?.roundsPerSide || rules.value.roundsPerSide || 10)
      : 1;
    const userStance = Number(entry?.round || 1) <= sideRounds ? "pro" : "con";
    return stanceLabel(entry?.role === "user" ? userStance : userStance === "pro" ? "con" : "pro");
  }
  return stanceLabel(entry?.role === "user" ? source?.userStance : source?.aiStance);
}

function entryMaxPoints(source) {
  return Number(source?.scoringVersion || 1) >= 2
    ? Number(source?.turnMaxPoints || rules.value.turnMaxPoints || 10)
    : 30;
}

function stageForEntry(entry, source) {
  const sideRounds = Number(source?.scoringVersion || 1) >= 2
    ? Number(source?.roundsPerSide || rules.value.roundsPerSide || 10)
    : 1;
  return Number(entry?.round || 1) <= sideRounds ? "pro" : "con";
}

function entryStageRound(entry, source) {
  if (entry?.stageRound) return Number(entry.stageRound);
  if (Number(source?.scoringVersion || 1) < 2) return Number(entry?.round || 1);
  const sideRounds = Number(source?.roundsPerSide || rules.value.roundsPerSide || 10);
  return ((Math.max(Number(entry?.round || 1), 1) - 1) % sideRounds) + 1;
}

function dimensionRows(entry, source) {
  const dimensions = entry?.dimensions || {};
  const legacyDimensions = [
    { key: "claim", label: "观点清楚", max: 8 },
    { key: "reason", label: "理由充分", max: 8 },
    { key: "evidence", label: "例子有效", max: 7 },
    { key: "rebuttal", label: "回应对方", max: 7 },
  ];
  const sourceDimensions = Number(source?.scoringVersion || 1) >= 2
    ? (rules.value.scoreDimensions || [])
    : legacyDimensions;
  return sourceDimensions.map((item) => ({
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
      requestOptions({ level: selectedLevel.value }),
    );
    applyPayload(nextPayload);
    notice.value = "PRO Round 1 of 10: support the motion in English. The AI will argue CON.";
  } catch (error) {
    notice.value = error.message || "The debate could not be started.";
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
    const latestUserTurn = [...(nextPayload?.session?.transcript || [])]
      .reverse()
      .find((entry) => entry?.role === "user");
    if (nextPayload?.energyGain > 0) {
      notice.value = `本场结算完成，猫咪世界获得 +${nextPayload.energyGain} 能量。`;
    } else {
      const nextSession = nextPayload?.session;
      if (nextSession?.status !== "active") {
        notice.value = "All 20 rounds are complete.";
      } else if (Number(nextSession?.turnCount || 0) === roundsPerSide.value) {
        notice.value = `本回合 ${latestUserTurn?.points || 0}/${turnMaxPoints.value} 分。正方 10 回合完成，现在切换为反方。`;
      } else {
        notice.value = `本回合 ${latestUserTurn?.points || 0}/${turnMaxPoints.value} 分。继续 ${stanceLabel(nextSession?.currentUserStance)} 第 ${nextSession?.currentStageRound || 1} 回合。`;
      }
    }
    await nextTick();
    transcriptEnd.value?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    notice.value = error.message || "这一轮暂时没有提交成功。";
  } finally {
    busyAction.value = "";
  }
}

async function openReplay(item) {
  if (!item?.id || replayBusy.value) return;
  replayBusy.value = item.id;
  try {
    const response = await fetchJson(routeApiPaths.debateSession(item.id));
    replaySession.value = response?.session || null;
    replayStage.value = "pro";
  } catch (error) {
    notice.value = error.message || "The debate record could not be opened.";
  } finally {
    replayBusy.value = 0;
  }
}

function closeReplay() {
  replaySession.value = null;
}

function selectStage(stage) {
  if (stage === "con" && Number(session.value?.turnCount || 0) < roundsPerSide.value) return;
  selectedStage.value = stage;
}

function confirmRoleSwitch() {
  acknowledgedRoleSwitchSession.value = Number(session.value?.id || 0);
  selectedStage.value = "con";
  showRoleSwitch.value = false;
  notice.value = "现在你是反方，AI 是正方。请从反方角度提出新的理由或反驳。";
}
</script>

<template>
  <section class="debate-page">
    <header class="debate-page-head">
      <div>
        <span class="eyebrow">SPEAKEASY</span>
        <h1>Daily AI Debate</h1>
        <p><CalendarDays :size="16" /> {{ payload.today }}</p>
      </div>
      <div class="debate-head-rules" aria-label="比赛规则">
        <span><Target :size="18" /><strong>{{ rules.roundsPerSide || 10 }}</strong> Rounds / Side</span>
        <span><Swords :size="18" /><strong>{{ rules.targetPoints || 200 }}</strong> Total Points</span>
      </div>
    </header>

    <p v-if="notice" class="debate-notice" aria-live="polite">{{ notice }}</p>

    <section v-if="!session" class="debate-setup panel">
      <div class="debate-setup-controls">
        <div>
          <span class="debate-field-label">Choose a division</span>
          <div class="debate-segmented" role="group" aria-label="Choose a debate division">
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
        <span>{{ currentTopic.category || "Today's motion" }}</span>
        <h2>{{ currentTopic.title }}</h2>
        <div class="debate-topic-hints">
          <span v-for="hint in currentTopic.hints || []" :key="hint">{{ hint }}</span>
        </div>
      </div>

      <div class="debate-two-round-plan" aria-label="Two ten-round debate stages">
        <span>
          <strong>Stage 1 · PRO · 10 rounds</strong>
          <small>You support the motion. Every round is /10; the PRO stage is /100.</small>
        </span>
        <span>
          <strong>Stage 2 · CON · 10 rounds</strong>
          <small>You switch sides after Round 10. The CON stage is another /100.</small>
        </span>
      </div>

      <button class="primary-action-button debate-start-button" type="button" :disabled="Boolean(busyAction)" @click="startDebate">
        <Swords :size="20" />
        {{ busyAction === "start" ? "Preparing the debate..." : "Start today's debate" }}
      </button>
    </section>

    <template v-else>
      <section class="debate-scoreboard">
        <div :class="['debate-score-side', 'pro', { active: active && stanceText === 'PRO' }]">
          <span>PRO · {{ Math.min(session.turnCount, roundsPerSide) }} / {{ roundsPerSide }} rounds</span>
          <strong>{{ proPoints }}<small>/ {{ sideTargetPoints }}</small></strong>
          <i><b :style="{ width: proProgress }"></b></i>
        </div>
        <div class="debate-score-center">
          <Target :size="26" />
          <strong>{{ active ? `${stanceText} ${currentStageRound} / ${roundsPerSide}` : "Complete" }}</strong>
          <span>Overall {{ Math.min(session.turnCount, totalRounds) }} / {{ totalRounds }} rounds</span>
        </div>
        <div :class="['debate-score-side', 'con', { active: active && stanceText === 'CON' }]">
          <span>CON · {{ Math.max(Math.min(session.turnCount - roundsPerSide, roundsPerSide), 0) }} / {{ roundsPerSide }} rounds</span>
          <strong>{{ conPoints }}<small>/ {{ sideTargetPoints }}</small></strong>
          <i><b :style="{ width: conProgress }"></b></i>
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

        <nav class="debate-stage-tabs" aria-label="Debate stage conversations">
          <button
            type="button"
            :class="{ active: selectedStage === 'pro' }"
            :aria-pressed="selectedStage === 'pro'"
            @click="selectStage('pro')"
          >
            <span>PRO Dialog</span>
            <strong>{{ proPoints }} / 100</strong>
            <small>{{ Math.min(session.turnCount, roundsPerSide) }} / {{ roundsPerSide }} rounds</small>
          </button>
          <button
            type="button"
            :class="{ active: selectedStage === 'con' }"
            :aria-pressed="selectedStage === 'con'"
            :disabled="active && session.turnCount < roundsPerSide"
            @click="selectStage('con')"
          >
            <span>CON Dialog</span>
            <strong>{{ conPoints }} / 100</strong>
            <small v-if="active && session.turnCount < roundsPerSide">Unlocks after PRO Round 10</small>
            <small v-else>{{ Math.max(Math.min(session.turnCount - roundsPerSide, roundsPerSide), 0) }} / {{ roundsPerSide }} rounds</small>
          </button>
        </nav>

        <div v-if="visibleTranscript.length" class="debate-transcript" aria-live="polite">
          <article
            v-for="(entry, index) in visibleTranscript"
            :key="`${entry.round}-${entry.role}-${index}`"
            :class="['debate-message', entry.role]"
          >
            <header>
              <span>
                <MessageSquareQuote v-if="entry.role === 'user'" :size="17" />
                <Sparkles v-else :size="17" />
                {{ sideForEntry(entry, session) }} Round {{ entryStageRound(entry, session) }} argument
              </span>
              <strong v-if="entry.role === 'user'">{{ entry.points }} / {{ entryMaxPoints(session) }}</strong>
            </header>
            <p>{{ entry.text }}</p>
            <div v-if="entry.role === 'user'" class="debate-dimension-row">
              <span v-for="item in dimensionRows(entry, session)" :key="item.key">
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
          <strong>{{ selectedStage === "pro" ? "PRO" : "CON" }} Dialog</strong>
          <span v-if="selectedStage === 'pro'">Support the motion with a clear reason or example.</span>
          <span v-else>This is a fresh conversation. Challenge the motion from the CON side.</span>
        </div>

        <form v-if="active && selectedStageIsCurrent" class="debate-turn-form" @submit.prevent="submitTurn">
          <label for="debate-argument">{{ stanceText }} Round {{ currentStageRound }} / {{ roundsPerSide }} · Your argument</label>
          <textarea
            id="debate-argument"
            v-model="argument"
            :maxlength="argumentMaxChars"
            placeholder="Write your claim, reason, example, or rebuttal in English..."
            :disabled="Boolean(busyAction)"
          ></textarea>
          <div>
            <span>{{ argumentWordCount }} words · {{ argument.length }} / {{ argumentMaxChars }}</span>
            <button class="primary-action-button" type="submit" :disabled="!canSubmit">
              <Sparkles v-if="busyAction === 'turn'" :size="18" />
              <Send v-else :size="18" />
              {{ busyAction === "turn" ? "The other side is responding..." : "Submit my argument" }}
            </button>
          </div>
        </form>
        <div v-else-if="active" class="debate-stage-return">
          <span>You are reviewing the {{ selectedStage === "pro" ? "PRO" : "CON" }} dialog.</span>
          <button type="button" class="secondary-button" @click="selectStage(session.currentUserStance)">
            Continue {{ stanceText }} Round {{ currentStageRound }}
          </button>
        </div>
      </section>

      <section v-if="completed" class="debate-result completed">
        <header>
          <div>
            <span class="eyebrow">GROWTH REVIEW</span>
            <h2>Great work - today's debate is complete!</h2>
          </div>
          <div class="debate-final-score">
            <Trophy :size="22" />
            <strong>{{ totalPoints }}<small>/ 200</small></strong>
            <span>Total debate points</span>
            <small>PRO {{ proPoints }} · CON {{ conPoints }}</small>
          </div>
        </header>
        <p>{{ finalReview.summary || "你完成了今天的辩论，坚持表达本身就是一次进步。" }}</p>
        <div class="debate-reward-band">
          <Zap :size="22" />
          <strong>+{{ session.energyAwarded }} Cat Energy</strong>
          <span>Reward added to Cat World</span>
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
            <blockquote v-if="item.example"><strong>English example</strong>{{ item.example }}</blockquote>
          </article>
        </div>

        <div v-if="finalReview.nextChallenge" class="debate-next-challenge">
          <Target :size="20" />
          <span><strong>下一次重点</strong>{{ finalReview.nextChallenge }}</span>
        </div>
      </section>
    </template>

    <div v-if="showRoleSwitch && session" class="debate-role-switch-backdrop">
      <article class="debate-role-switch-dialog" role="dialog" aria-modal="true" aria-labelledby="debate-role-switch-title">
        <div class="debate-role-switch-icon" aria-hidden="true">
          <ArrowRightLeft :size="30" />
        </div>
        <span class="eyebrow">ROLE SWITCH</span>
        <h2 id="debate-role-switch-title">PRO stage complete</h2>
        <p>正方 10 回合已经完成。接下来请切换立场，从反方角度重新思考同一个辩题。</p>
        <div class="debate-role-switch-sides">
          <span><small>Your completed role</small><strong>PRO · {{ proPoints }} / 100</strong></span>
          <ArrowRightLeft :size="22" aria-hidden="true" />
          <span><small>Your new role</small><strong>CON · Round 1 / 10</strong></span>
        </div>
        <div class="debate-role-switch-note">
          <strong>You argue CON</strong>
          <span>AI now argues PRO. Your CON dialog starts clean, and the PRO dialog remains available for review.</span>
        </div>
        <button class="primary-action-button" type="button" @click="confirmRoleSwitch">
          <Swords :size="19" />
          Start CON Round 1
        </button>
      </article>
    </div>

    <section v-if="history.length" class="debate-history panel">
      <header>
        <div>
          <span class="eyebrow">DEBATE REVIEW</span>
          <h2>Past Debates</h2>
        </div>
        <strong>{{ history.length }} records</strong>
      </header>
      <div class="debate-history-list">
        <button
          v-for="item in history"
          :key="item.id"
          type="button"
          :disabled="Boolean(replayBusy)"
          @click="openReplay(item)"
        >
          <time>{{ item.date }}</time>
          <span>
            <strong>{{ item.topic.title }}</strong>
            <small>{{ item.levelLabel }} · {{ item.formatLabel }} · {{ item.statusLabel }}</small>
          </span>
          <em v-if="item.status === 'completed' && item.scoringVersion >= 2">
            PRO {{ item.proPoints }}/100 · CON {{ item.conPoints }}/100
          </em>
          <em v-else-if="item.status === 'completed'">{{ item.finalScore }} / 100</em>
          <em v-else>In progress</em>
          <ChevronRight :size="19" />
        </button>
      </div>
    </section>

    <div v-if="replaySession" class="debate-replay-backdrop" @click.self="closeReplay">
      <article class="debate-replay-dialog" role="dialog" aria-modal="true" aria-labelledby="debate-replay-title">
        <header>
          <div>
            <span class="eyebrow">DEBATE RECORD · {{ replaySession.date }}</span>
            <h2 id="debate-replay-title">{{ replaySession.topic.title }}</h2>
          </div>
          <button type="button" aria-label="Close debate record" title="Close" @click="closeReplay">
            <X :size="21" />
          </button>
        </header>

        <div class="debate-replay-summary">
          <span><BookOpen :size="17" />{{ replaySession.statusLabel }}</span>
          <span>{{ replaySession.formatLabel }}</span>
          <strong v-if="replaySession.status === 'completed' && replaySession.scoringVersion >= 2">
            PRO {{ replaySession.proPoints }}/100 · CON {{ replaySession.conPoints }}/100
          </strong>
          <strong v-else-if="replaySession.status === 'completed'">{{ replaySession.finalScore }} / 100</strong>
        </div>

        <nav class="debate-stage-tabs compact" aria-label="Replay debate stage conversations">
          <button
            type="button"
            :class="{ active: replayStage === 'pro' }"
            :aria-pressed="replayStage === 'pro'"
            @click="replayStage = 'pro'"
          >
            <span>PRO Dialog</span>
            <strong v-if="replaySession.scoringVersion >= 2">{{ replaySession.proPoints }} / 100</strong>
          </button>
          <button
            type="button"
            :class="{ active: replayStage === 'con' }"
            :aria-pressed="replayStage === 'con'"
            @click="replayStage = 'con'"
          >
            <span>CON Dialog</span>
            <strong v-if="replaySession.scoringVersion >= 2">{{ replaySession.conPoints }} / 100</strong>
          </button>
        </nav>

        <section class="debate-replay-transcript">
          <article
            v-for="(entry, index) in replayTranscript"
            :key="`${entry.round}-${entry.role}-${index}`"
            :class="['debate-message', entry.role]"
          >
            <header>
              <span>
                <MessageSquareQuote v-if="entry.role === 'user'" :size="17" />
                <Sparkles v-else :size="17" />
                {{ sideForEntry(entry, replaySession) }} Round {{ entryStageRound(entry, replaySession) }} argument
              </span>
              <strong v-if="entry.role === 'user'">{{ entry.points }} / {{ entryMaxPoints(replaySession) }}</strong>
            </header>
            <p>{{ entry.text }}</p>
            <div v-if="entry.role === 'user'" class="debate-dimension-row">
              <span v-for="item in dimensionRows(entry, replaySession)" :key="item.key">
                {{ item.label }} <strong>{{ item.value }}/{{ item.max }}</strong>
              </span>
            </div>
            <aside v-if="entry.coachNote" class="debate-coach-note">
              <Award :size="18" />
              <span><strong>{{ entry.highlight }}</strong>{{ entry.coachNote }}</span>
            </aside>
          </article>
          <p v-if="!replayTranscript.length" class="debate-replay-empty">No arguments were submitted in this stage.</p>
        </section>

        <footer v-if="replaySession.finalFeedback?.summary">
          <strong>成长回顾</strong>
          <p>{{ replaySession.finalFeedback.summary }}</p>
          <div v-if="replaySession.finalFeedback.strengths?.length">
            <span v-for="item in replaySession.finalFeedback.strengths" :key="item">
              <CheckCircle2 :size="15" />{{ item }}
            </span>
          </div>
        </footer>
      </article>
    </div>
  </section>
</template>
