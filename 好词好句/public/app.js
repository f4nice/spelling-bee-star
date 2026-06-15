const searchTab = document.querySelector("#searchTab");
const textTab = document.querySelector("#textTab");
const searchForm = document.querySelector("#searchForm");
const textForm = document.querySelector("#textForm");
const queryInput = document.querySelector("#query");
const bookFileInput = document.querySelector("#bookFile");
const textTitleInput = document.querySelector("#textTitle");
const sourceTextInput = document.querySelector("#sourceText");
const bookUploadPreview = document.querySelector("#bookUploadPreview");
const bookUploadCover = document.querySelector("#bookUploadCover");
const bookUploadTitle = document.querySelector("#bookUploadTitle");
const bookUploadMeta = document.querySelector("#bookUploadMeta");
const suggestionsPanel = document.querySelector("#suggestionsPanel");
const results = document.querySelector("#results");
const notice = document.querySelector("#notice");
const loadingTemplate = document.querySelector("#loadingTemplate");
const healthStatus = document.querySelector("#healthStatus");
const historyList = document.querySelector("#historyList");
const refreshHistory = document.querySelector("#refreshHistory");
const saveAnalysisButton = document.querySelector("#saveAnalysisButton");
const featuredQuotes = document.querySelector("#featuredQuotes");
const refreshFeatured = document.querySelector("#refreshFeatured");
const FAVORITES_KEY = "booklearner:favorites";
const APP_BASE = "/booklearner";
const DETAIL_ANALYSIS_ID = Number(window.BOOKLEARNER_DETAIL_ID || 0);
const QUOTES_ONLY = Boolean(window.BOOKLEARNER_QUOTES_ONLY);
const FEATURED_LIMIT = Number(window.BOOKLEARNER_FEATURED_LIMIT || (QUOTES_ONLY ? 40 : 12));
const CAN_REFRESH_FEATURED_ON_SCROLL = Boolean(featuredQuotes && !DETAIL_ANALYSIS_ID && !QUOTES_ONLY);
let suggestTimer;
let suggestController;
let currentAnalysis = null;
let featuredLoading = false;

const escapeHtml = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const setMode = (mode) => {
  if (!searchTab || !textTab || !searchForm || !textForm) return;
  const isSearch = mode === "search";
  searchTab.classList.toggle("active", isSearch);
  textTab.classList.toggle("active", !isSearch);
  searchForm.classList.toggle("active", isSearch);
  textForm.classList.toggle("active", !isSearch);
};

const setLoading = () => {
  if (!results || !loadingTemplate) return;
  results.replaceChildren(loadingTemplate.content.cloneNode(true));
};

const renderError = (message) => {
  if (!results) return;
  results.innerHTML = `
    <div class="empty-state error-box">
      <div>
        <h2>分析失败</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
};

const bookAuthors = (book = {}) => {
  const authors = Array.isArray(book.authors) ? book.authors.filter(Boolean) : [];
  return authors.length ? authors.join(" / ") : "作者未知";
};

const metaItem = (label, value) => (value ? `<span>${label}: ${escapeHtml(value)}</span>` : "");

const hideSuggestions = () => {
  if (!suggestionsPanel) return;
  suggestionsPanel.hidden = true;
  suggestionsPanel.innerHTML = "";
};

const suggestionMeta = (item) => {
  const authors = Array.isArray(item.authors) ? item.authors.filter(Boolean).join(" / ") : "";
  const year = item.firstPublishYear ? ` · ${item.firstPublishYear}` : "";
  const source = item.availableText ? "可分析公版全文" : item.sourceName || "书籍提示";
  return [authors, `${source}${year}`].filter(Boolean).join(" · ");
};

const renderSuggestions = (items = []) => {
  if (!suggestionsPanel) return;
  if (!items.length) {
    suggestionsPanel.innerHTML = `<div class="suggestion-empty">没有找到接近的书名</div>`;
    suggestionsPanel.hidden = false;
    return;
  }

  suggestionsPanel.innerHTML = items
    .map(
      (item) => `
        <button class="suggestion-item" type="button" role="option" data-title="${escapeHtml(item.title)}">
          <span class="suggestion-title">${escapeHtml(item.title)}</span>
          <span class="suggestion-meta">${escapeHtml(suggestionMeta(item))}</span>
          <span class="suggestion-hint">${escapeHtml(item.hint || "")}</span>
        </button>
      `,
    )
    .join("");
  suggestionsPanel.hidden = false;
};

const loadSuggestions = async (query) => {
  if (!queryInput || !suggestionsPanel) return;
  const value = query.trim();
  if (value.length < 2) {
    hideSuggestions();
    return;
  }

  if (suggestController) {
    suggestController.abort();
  }
  suggestController = new AbortController();

  try {
    const data = await requestJson(`${APP_BASE}/api/suggest?q=${encodeURIComponent(value)}`, {
      signal: suggestController.signal,
    });
    if (queryInput.value.trim() === value) {
      renderSuggestions(data.items || []);
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      hideSuggestions();
    }
  }
};

const scheduleSuggestions = () => {
  if (!queryInput) return;
  clearTimeout(suggestTimer);
  suggestTimer = setTimeout(() => loadSuggestions(queryInput.value), 260);
};

const quoteKey = (text = "") => {
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 31 + text.charCodeAt(index)) >>> 0;
  }
  return `${hash}-${text.length}`;
};

const readFavorites = () => {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || "{}");
  } catch {
    return {};
  }
};

const writeFavorites = (favorites) => {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
};

const favoriteButton = (quote) => {
  const favorites = readFavorites();
  const key = quoteKey(quote.text);
  const active = Boolean(favorites[key]);
  return `
    <button
      class="favorite-button${active ? " active" : ""}"
      type="button"
      data-favorite-key="${escapeHtml(key)}"
      aria-label="${active ? "取消收藏" : "收藏"}"
      aria-pressed="${active ? "true" : "false"}"
      title="${active ? "取消收藏" : "收藏"}"
    >${active ? "★" : "☆"}</button>
  `;
};

const renderSummary = (data) => {
  const book = data.book || {};
  const storage = data.storage || {};
  const title = book.title || data.query || "分析结果";
  const vocabularyCount = Array.isArray(data.vocabulary) ? data.vocabulary.length : 0;
  const sourceUrl = book.sourceUrl
    ? `<a class="source-link" href="${escapeHtml(book.sourceUrl)}" target="_blank" rel="noreferrer">来源</a>`
    : "";
  const stats = data.stats || {};
  const meta = [
    metaItem("作者", bookAuthors(book)),
    metaItem("语言", book.language),
    stats.words ? metaItem("词数", stats.words.toLocaleString()) : "",
    stats.sentences ? metaItem("句数", stats.sentences.toLocaleString()) : "",
    metaItem("数据", book.sourceName),
  ].join("");

  return `
    <section class="summary-band">
      <div class="book-title">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <div class="meta">${meta}</div>
        </div>
        <div class="book-actions">
          <button class="create-word-list-button" type="button" data-create-word-list>
            创建单词表
          </button>
          <span>${vocabularyCount ? `${vocabularyCount} 个难点单词` : "可先分析出难点单词"}</span>
          ${sourceUrl}
        </div>
      </div>
      ${data.notice ? `<div class="notice-banner">${escapeHtml(data.notice)}</div>` : ""}
    </section>
  `;
};

const renderQuotes = (quotes = [], label = "经典短句") => {
  if (!quotes.length) return "";
  return `
    <section class="result-card">
      <h3>${escapeHtml(label)}</h3>
      <ul class="quote-list">
        ${quotes
          .map(
            (quote) => `
              <li class="quote-item">
                ${favoriteButton(quote)}
                <p class="quote-text">${escapeHtml(quote.text)}</p>
                <p class="quote-note">${escapeHtml(quote.note || "")}</p>
              </li>
            `,
          )
          .join("")}
      </ul>
    </section>
  `;
};

const renderVocabulary = (words = []) => {
  if (!words.length) return "";
  return `
    <section class="result-card">
      <h3>难点单词</h3>
      <ul class="word-list">
        ${words
          .map(
            (item, index) => `
              <li class="word-item" role="button" tabindex="0" data-word-index="${index}">
                <div class="word-head">
                  <div>
                    <span class="word">${escapeHtml(item.word)}</span>
                    ${item.partOfSpeech ? `<span class="part"> ${escapeHtml(item.partOfSpeech)}</span>` : ""}
                  </div>
                  <span class="count">${Number(item.count || 0)} 次</span>
                </div>
                <p class="definition">${escapeHtml(item.definition || "")}</p>
                ${item.example ? `<p class="word-example">${escapeHtml(item.example)}</p>` : ""}
                <p class="word-hint">${escapeHtml(item.memoryHint || "")}</p>
              </li>
            `,
          )
          .join("")}
      </ul>
    </section>
  `;
};

const renderFocus = (items = []) => {
  if (!items.length) return "";
  return `
    <section class="result-card">
      <h3>阅读关注点</h3>
      <ul class="focus-list">
        ${items
          .map(
            (item) => `
              <li class="focus-item">
                <span class="focus-term">${escapeHtml(item.term)}</span>
                <span class="focus-count">${Number(item.count || 0)} 次</span>
              </li>
            `,
          )
          .join("")}
      </ul>
    </section>
  `;
};

const renderSteps = (steps = []) => {
  if (!steps.length) return "";
  return `
    <section class="result-card">
      <h3>下一步</h3>
      <ul class="steps-list">
        ${steps.map((step) => `<li class="step-item">${escapeHtml(step)}</li>`).join("")}
      </ul>
    </section>
  `;
};

const renderResults = (data) => {
  currentAnalysis = data;
  if (data?.book?.coverUrl || data?.book?.title) {
    renderUploadBookPreview({
      title: data.book?.title || currentAnalysis.query,
      coverUrl: data.book?.coverUrl || "",
    });
  }
  if (DETAIL_ANALYSIS_ID && !results) {
    renderAnalysisQuotes(data);
    return;
  }
  const body = `
    ${renderSummary(data)}
    <div class="grid">
      <div>
        ${renderQuotes(data.quotes, data.quotesLabel)}
        ${renderSteps(data.nextSteps)}
      </div>
      <div>
        ${renderVocabulary(data.vocabulary)}
        ${renderFocus(data.readingFocus)}
      </div>
    </div>
  `;
  results.innerHTML = body;
  notice.textContent = data.book?.copyrightNote || data.notice || "";
  if (saveAnalysisButton) saveAnalysisButton.disabled = !currentAnalysis;
  if (DETAIL_ANALYSIS_ID) {
    renderAnalysisQuotes(data);
  } else {
    loadFeaturedQuotes();
  }
};

const coverLetters = (title = "") =>
  title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("") || "B";

const renderUploadBookPreview = ({ title = "", filename = "", coverUrl = "" } = {}) => {
  if (!bookUploadPreview || !bookUploadCover || !bookUploadTitle || !bookUploadMeta) return;
  const displayTitle = title || filename || textTitleInput?.value || "未命名书籍";
  bookUploadPreview.hidden = false;
  bookUploadTitle.textContent = displayTitle;
  bookUploadMeta.textContent = coverUrl ? "已读取书籍封面" : "未读取到封面，先使用书名封面";
  bookUploadCover.className = coverUrl ? "upload-book-cover has-image" : "upload-book-cover";
  bookUploadCover.innerHTML = coverUrl
    ? `<img src="${escapeHtml(coverUrl)}" alt="${escapeHtml(displayTitle)}">`
    : `<span>${escapeHtml(coverLetters(displayTitle))}</span>`;
};

const clearUploadBookPreview = () => {
  if (!bookUploadPreview) return;
  bookUploadPreview.hidden = true;
};

const renderFeaturedQuotes = (items = [], { append = false } = {}) => {
  if (!featuredQuotes) return;
  if (!items.length) {
    if (append && featuredQuotes.children.length) return;
    featuredQuotes.innerHTML = `
      <div class="quote-feed-empty">
        暂时还没有书摘。先在右侧搜索或上传一本书，分析后这里会自动出现好词好句。
      </div>
    `;
    return;
  }

  const html = items
    .map(
      (item) => `
        <button class="featured-quote-card" type="button" data-analysis-id="${Number(item.analysisId || 0)}">
          ${
            item.coverUrl
              ? `<span class="book-cover image-cover"><img src="${escapeHtml(item.coverUrl)}" alt="${escapeHtml(item.title)}"></span>`
              : `<span class="book-cover cover-${Number(item.coverSeed || 0)}"><span>${escapeHtml(coverLetters(item.title))}</span></span>`
          }
          <span class="featured-quote-main">
            <span class="featured-quote-text">“${escapeHtml(item.quote)}”</span>
            <span class="featured-quote-book">${escapeHtml(item.title)} · ${escapeHtml(item.author || "作者未记")}</span>
            ${item.note ? `<span class="featured-quote-note">${escapeHtml(item.note)}</span>` : ""}
            <span class="featured-quote-meta">
              ${Number(item.vocabularyCount || 0)} 个难点单词
              ${item.words ? ` · ${Number(item.words).toLocaleString()} 词` : ""}
            </span>
          </span>
        </button>
      `,
    )
    .join("");
  if (append) {
    featuredQuotes.insertAdjacentHTML("beforeend", html);
  } else {
    featuredQuotes.innerHTML = html;
  }
};

const analysisQuoteItems = (data) => {
  const book = data?.book || {};
  const title = book.title || data?.query || "未命名书籍";
  const author = bookAuthors(book) || "作者未记";
  const vocabularyCount = Array.isArray(data?.vocabulary) ? data.vocabulary.length : 0;
  const words = data?.stats?.words || 0;
  const coverSeed = title.length % 6;
  const coverUrl = book.coverUrl || "";
  return (data?.quotes || []).map((quote) => ({
    analysisId: DETAIL_ANALYSIS_ID || data?.storage?.analysisId || 0,
    title,
    author,
    quote: quote.text || "",
    note: quote.note || "",
    vocabularyCount,
    words,
    coverSeed,
    coverUrl,
  }));
};

const renderAnalysisVocabulary = (words = []) => {
  if (!words.length) {
    return `<div class="quote-feed-empty">这本书暂时还没有整理出难点词汇。</div>`;
  }
  return words
    .map(
      (item, index) => `
        <button class="book-detail-word-card word-item" type="button" data-word-index="${index}">
          <span class="word-head">
            <span>
              <span class="word">${escapeHtml(item.word || "")}</span>
              ${item.partOfSpeech ? `<span class="part"> ${escapeHtml(item.partOfSpeech)}</span>` : ""}
            </span>
            <span class="count">${Number(item.count || 0)} 次</span>
          </span>
          ${item.definition ? `<span class="definition">${escapeHtml(item.definition)}</span>` : ""}
          ${item.example ? `<span class="word-example">${escapeHtml(item.example)}</span>` : ""}
          ${item.memoryHint ? `<span class="word-hint">${escapeHtml(item.memoryHint)}</span>` : ""}
        </button>
      `,
    )
    .join("");
};

const renderAnalysisQuotes = (data) => {
  if (!featuredQuotes) return;
  const quotes = analysisQuoteItems(data);
  const words = Array.isArray(data?.vocabulary) ? data.vocabulary : [];
  const quoteHtml = quotes.length
    ? quotes
        .map(
          (item) => `
            <button class="featured-quote-card" type="button" data-analysis-id="${Number(item.analysisId || 0)}">
              ${
                item.coverUrl
                  ? `<span class="book-cover image-cover"><img src="${escapeHtml(item.coverUrl)}" alt="${escapeHtml(item.title)}"></span>`
                  : `<span class="book-cover cover-${Number(item.coverSeed || 0)}"><span>${escapeHtml(coverLetters(item.title))}</span></span>`
              }
              <span class="featured-quote-main">
                <span class="featured-quote-text">“${escapeHtml(item.quote)}”</span>
                <span class="featured-quote-book">${escapeHtml(item.title)} · ${escapeHtml(item.author || "作者未记")}</span>
                ${item.note ? `<span class="featured-quote-note">${escapeHtml(item.note)}</span>` : ""}
                <span class="featured-quote-meta">
                  ${Number(item.vocabularyCount || 0)} 个难点单词
                  ${item.words ? ` · ${Number(item.words).toLocaleString()} 词` : ""}
                </span>
              </span>
            </button>
          `,
        )
        .join("")
    : `<div class="quote-feed-empty">这本书暂时还没有整理出好句。</div>`;

  featuredQuotes.innerHTML = `
    <div class="book-detail-study-grid">
      <section class="book-detail-column">
        <div class="book-detail-column-head">
          <span>好句</span>
          <strong>${quotes.length}</strong>
        </div>
        <div class="book-detail-quotes">${quoteHtml}</div>
      </section>
      <section class="book-detail-column">
        <div class="book-detail-column-head">
          <span>难点词汇</span>
          <strong>${words.length}</strong>
        </div>
        <div class="book-detail-vocab">${renderAnalysisVocabulary(words)}</div>
      </section>
    </div>
  `;
};

const loadFeaturedQuotes = async ({ append = false } = {}) => {
  if (!featuredQuotes) return;
  if (featuredLoading) return;
  featuredLoading = true;
  if (!append) {
  featuredQuotes.innerHTML = `<div class="quote-feed-empty">正在随机挑选书摘...</div>`;
  }
  try {
    const params = new URLSearchParams({ limit: String(FEATURED_LIMIT) });
    if (DETAIL_ANALYSIS_ID) {
      params.set("analysis_id", String(DETAIL_ANALYSIS_ID));
    }
    const data = await requestJson(`${APP_BASE}/api/featured?${params.toString()}`);
    renderFeaturedQuotes(data.items || [], { append });
  } catch (error) {
    if (!append) {
      featuredQuotes.innerHTML = `<div class="quote-feed-empty">${escapeHtml(error.message)}</div>`;
    }
  } finally {
    featuredLoading = false;
  }
};

const createWordListFromCurrentAnalysis = async (button) => {
  if (!currentAnalysis) return;
  const book = currentAnalysis.book || {};
  const title = book.title || currentAnalysis.query || "BookLearner 单词表";
  const vocabulary = Array.isArray(currentAnalysis.vocabulary) ? currentAnalysis.vocabulary : [];

  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = "创建中...";
  try {
    const data = await requestJson(`${APP_BASE}/api/word-list`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, vocabulary }),
    });
    button.textContent = "已创建";
    window.location.href = `/lists/${data.word_list_id}`;
  } catch (error) {
    button.disabled = false;
    button.textContent = originalText;
    renderError(error.message);
  }
};

const saveCurrentAnalysis = async () => {
  if (!currentAnalysis || !saveAnalysisButton) return;
  saveAnalysisButton.disabled = true;
  const originalText = saveAnalysisButton.textContent;
  saveAnalysisButton.textContent = "保存中...";
  try {
    const data = await requestJson(`${APP_BASE}/api/save-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: currentAnalysis.book?.title || currentAnalysis.query || "",
        result: currentAnalysis,
      }),
    });
    currentAnalysis.storage = data.storage;
    saveAnalysisButton.textContent = "已保存";
    await loadFeaturedQuotes();
  } catch (error) {
    saveAnalysisButton.textContent = originalText;
    renderError(error.message);
  } finally {
    setTimeout(() => {
      if (saveAnalysisButton && currentAnalysis) {
        saveAnalysisButton.textContent = originalText;
        saveAnalysisButton.disabled = false;
      }
    }, 1200);
  }
};

const renderHistory = (items = []) => {
  if (!items.length) {
    historyList.innerHTML = "<li>暂无 MySQL 学习记录。</li>";
    return;
  }

  historyList.innerHTML = items
    .map((item) => {
      const title = item.title || item.query_text || "未命名记录";
      const createdAt = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      const meta = [item.status, item.source_name, createdAt].filter(Boolean).join(" · ");
      return `
        <li>
          <button class="history-item-button" type="button" data-history-id="${Number(item.id || 0)}">
            <span class="history-title">${escapeHtml(title)}</span>
            <span class="history-meta">${escapeHtml(meta)}</span>
          </button>
        </li>
      `;
    })
    .join("");
};

const loadAnalysisById = async (historyId) => {
  if (!historyId) return;
  const data = await requestJson(`${APP_BASE}/api/history/${historyId}`);
  data.storage = { ...(data.storage || {}), analysisId: historyId };
  renderResults(data);
  results?.scrollIntoView({ behavior: "smooth", block: "start" });
};

const loadHistoryItem = async (button) => {
  const historyId = Number(button.dataset.historyId || 0);
  const originalText = button.textContent;
  button.disabled = true;
  button.classList.add("loading-history");
  try {
    await loadAnalysisById(historyId);
  } catch (error) {
    renderError(error.message);
  } finally {
    button.disabled = false;
    button.classList.remove("loading-history");
    button.setAttribute("aria-label", originalText.trim());
  }
};

const trackVocabularyClick = async (itemElement) => {
  if (!currentAnalysis) return;
  const index = Number(itemElement.dataset.wordIndex);
  const vocabulary = Array.isArray(currentAnalysis.vocabulary) ? currentAnalysis.vocabulary : [];
  const item = vocabulary[index];
  if (!item?.word) return;

  itemElement.classList.add("word-item-saving");
  try {
    const book = currentAnalysis.book || {};
    const storage = currentAnalysis.storage || {};
    await requestJson(`${APP_BASE}/api/clicked-word`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysisId: storage.analysisId,
        bookTitle: book.title || currentAnalysis.query || "",
        ...item,
      }),
    });
    itemElement.classList.remove("word-item-saving");
    itemElement.classList.add("word-item-saved");
  } catch {
    itemElement.classList.remove("word-item-saving");
  }
};

const loadStorageStatus = async () => {
  if (!healthStatus) return;
  try {
    const status = await requestJson(`${APP_BASE}/api/storage`);
    healthStatus.textContent = status.connected ? "MySQL 已连接" : status.enabled ? "MySQL 未连接" : "本地运行";
  } catch {
    healthStatus.textContent = "本地运行";
  }
};

const loadHistory = async () => {
  if (!historyList) return;
  try {
    const data = await requestJson(`${APP_BASE}/api/history`);
    renderHistory(data.items || []);
  } catch {
    renderHistory([]);
  }
};

const requestJson = async (url, options) => {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.detail || "请求失败");
  }
  return data;
};

searchTab?.addEventListener("click", () => setMode("search"));
textTab?.addEventListener("click", () => setMode("text"));

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!queryInput || !searchForm) return;
    queryInput.value = button.dataset.query;
    hideSuggestions();
    searchForm.requestSubmit();
  });
});

queryInput?.addEventListener("input", scheduleSuggestions);
queryInput?.addEventListener("focus", scheduleSuggestions);
queryInput?.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    hideSuggestions();
  }
});

suggestionsPanel?.addEventListener("click", (event) => {
  if (!queryInput || !searchForm) return;
  const button = event.target.closest(".suggestion-item");
  if (!button) return;

  queryInput.value = button.dataset.title || "";
  hideSuggestions();
  searchForm.requestSubmit();
});

document.addEventListener("click", (event) => {
  if (event.target.closest(".search-field")) return;
  hideSuggestions();
});

searchForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!queryInput) return;
  const query = queryInput.value.trim();
  if (!query) {
    renderError("请输入书名或作者名。");
    return;
  }

  hideSuggestions();
  setLoading();
  try {
    const data = await requestJson(`${APP_BASE}/api/analyze?q=${encodeURIComponent(query)}`);
    renderResults(data);
  } catch (error) {
    renderError(error.message);
  }
});

bookFileInput?.addEventListener("change", async () => {
  if (!textTitleInput || !sourceTextInput) return;
  const file = bookFileInput.files?.[0];
  if (!file) {
    clearUploadBookPreview();
    return;
  }

  textTitleInput.value = file.name.replace(/\.[^.]+$/, "");
  const lowerName = file.name.toLowerCase();
  renderUploadBookPreview({ title: textTitleInput.value, filename: file.name });

  try {
    const previewData = new FormData();
    previewData.append("file", file);
    const preview = await requestJson(`${APP_BASE}/api/book-preview`, {
      method: "POST",
      body: previewData,
    });
    renderUploadBookPreview({
      title: preview.title || textTitleInput.value,
      filename: preview.filename || file.name,
      coverUrl: preview.coverUrl || "",
    });
  } catch (error) {
    renderUploadBookPreview({ title: textTitleInput.value, filename: file.name });
  }

  if (lowerName.endsWith(".epub")) {
    sourceTextInput.value = "";
    sourceTextInput.placeholder = "已选择 EPUB，点击“分析书籍”后会由服务器读取正文。";
    return;
  }

  if (!lowerName.endsWith(".txt") && file.type !== "text/plain") {
    renderError("当前支持 txt 和 epub；pdf、docx 我们后续再接服务端解析。");
    return;
  }

  try {
    sourceTextInput.value = await file.text();
  } catch {
    renderError("书籍文件读取失败，请换一个 txt 文件或直接粘贴正文。");
  }
});

textForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(textForm);
  const file = bookFileInput?.files?.[0];
  const lowerName = file?.name?.toLowerCase() || "";

  setLoading();
  try {
    const data =
      file && lowerName.endsWith(".epub")
        ? await requestJson(`${APP_BASE}/api/analyze-file`, {
            method: "POST",
            body: formData,
          })
        : await requestJson(`${APP_BASE}/api/analyze-text`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: formData.get("title"),
              author: formData.get("author"),
              text: formData.get("text"),
            }),
          });
    renderResults(data);
  } catch (error) {
    renderError(error.message);
  }
});

refreshHistory?.addEventListener("click", loadHistory);
refreshFeatured?.addEventListener("click", () => {
  if (DETAIL_ANALYSIS_ID && currentAnalysis) {
    renderAnalysisQuotes(currentAnalysis);
    return;
  }
  loadFeaturedQuotes();
});
saveAnalysisButton?.addEventListener("click", saveCurrentAnalysis);

window.addEventListener("scroll", () => {
  if (!CAN_REFRESH_FEATURED_ON_SCROLL || featuredLoading) return;
  const distanceToBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
  if (distanceToBottom > 160) return;
  loadFeaturedQuotes({ append: true });
});

featuredQuotes?.addEventListener("click", async (event) => {
  const wordItem = event.target.closest("[data-word-index]");
  if (wordItem) {
    trackVocabularyClick(wordItem);
    return;
  }

  const button = event.target.closest("[data-analysis-id]");
  if (!button) return;
  const analysisId = Number(button.dataset.analysisId || 0);
  if (!analysisId) return;
  if (DETAIL_ANALYSIS_ID && analysisId === DETAIL_ANALYSIS_ID) return;
  window.location.href = `${APP_BASE}/detail/${analysisId}`;
});

historyList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-history-id]");
  if (!button) return;
  loadHistoryItem(button);
});

results?.addEventListener("click", (event) => {
  const createButton = event.target.closest("[data-create-word-list]");
  if (createButton) {
    createWordListFromCurrentAnalysis(createButton);
    return;
  }

  const wordItem = event.target.closest("[data-word-index]");
  if (wordItem) {
    trackVocabularyClick(wordItem);
    return;
  }

  const button = event.target.closest(".favorite-button");
  if (!button) return;

  const item = button.closest(".quote-item");
  const text = item?.querySelector(".quote-text")?.textContent?.trim();
  const note = item?.querySelector(".quote-note")?.textContent?.trim();
  if (!text) return;

  const key = button.dataset.favoriteKey || quoteKey(text);
  const favorites = readFavorites();
  const nextActive = !favorites[key];
  if (nextActive) {
    favorites[key] = {
      text,
      note,
      createdAt: new Date().toISOString(),
    };
  } else {
    delete favorites[key];
  }
  writeFavorites(favorites);

  button.classList.toggle("active", nextActive);
  button.textContent = nextActive ? "★" : "☆";
  button.setAttribute("aria-pressed", String(nextActive));
  button.setAttribute("aria-label", nextActive ? "取消收藏" : "收藏");
  button.title = nextActive ? "取消收藏" : "收藏";
});

results?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const wordItem = event.target.closest("[data-word-index]");
  if (!wordItem) return;
  event.preventDefault();
  trackVocabularyClick(wordItem);
});

loadStorageStatus();
loadHistory();
if (DETAIL_ANALYSIS_ID) {
  loadAnalysisById(DETAIL_ANALYSIS_ID).catch((error) => {
    if (featuredQuotes) {
      featuredQuotes.innerHTML = `<div class="quote-feed-empty">${escapeHtml(error.message)}</div>`;
    }
  });
} else {
  loadFeaturedQuotes();
}
