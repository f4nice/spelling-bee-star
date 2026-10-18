import test from "node:test";
import assert from "node:assert/strict";
import { applyCommittedWordAudio } from "../src/app/wordAudioState.js";
import { preferredWordAudioAccent, resolveWordAudioSource } from "../src/app/wordAudioSource.js";

test("word detail keeps generated TTS sources playable when local audio is absent", () => {
  const data = {
    word: { american_audio_url: "", british_audio_url: "/media/audio/gb.mp3" },
    audio_sources: { us: "/tts?word=rare&accent=us&v=2", gb: "/media/audio/gb.mp3?v=2" },
  };

  assert.equal(resolveWordAudioSource(data, "us"), "/tts?word=rare&accent=us&v=2");
  assert.equal(resolveWordAudioSource(data, "gb"), "/media/audio/gb.mp3?v=2");
  assert.equal(resolveWordAudioSource({ word: { american_audio_url: "/media/audio/fallback.mp3" } }, "us"), "/media/audio/fallback.mp3");
});

test("auto study prefers an available local accent before generated TTS", () => {
  assert.equal(preferredWordAudioAccent({
    word: { american_audio_url: "", british_audio_url: "/media/audio/gb.mp3" },
    audio_sources: { us: "/tts?word=rare&accent=us", gb: "/media/audio/gb.mp3" },
  }), "gb");
  assert.equal(preferredWordAudioAccent({
    word: { american_audio_url: "", british_audio_url: "" },
    audio_sources: { us: "/tts?word=rare&accent=us", gb: "/tts?word=rare&accent=gb" },
  }), "us");
});

test("committed uploaded audio replaces the active accent and playback URL", () => {
  const data = {
    word: { american_audio_url: "/media/audio/old-us.mp3", british_audio_url: "/media/audio/old-gb.mp3" },
    audio_sources: {
      us: "/media/audio/old-us.mp3?v=20261017",
      gb: "/media/audio/old-gb.mp3?v=20261017",
    },
  };

  applyCommittedWordAudio(data, "us", {
    committed: true,
    audio_url: "/media/audio/record-word-us-new.mp3",
  });

  assert.equal(data.word.american_audio_url, "/media/audio/record-word-us-new.mp3");
  assert.equal(data.audio_sources.us, "/media/audio/record-word-us-new.mp3");
  assert.equal(data.audio_sources.gb, "/media/audio/old-gb.mp3?v=20261017");
});

test("uncommitted or invalid audio responses do not replace playback", () => {
  const data = {
    word: { american_audio_url: "/media/audio/old-us.mp3" },
    audio_sources: { us: "/media/audio/old-us.mp3?v=20261017" },
  };

  applyCommittedWordAudio(data, "us", { committed: false, audio_url: "/media/audio/new.mp3" });
  applyCommittedWordAudio(data, "xx", { committed: true, audio_url: "/media/audio/new.mp3" });
  applyCommittedWordAudio(data, "us", { committed: true });

  assert.equal(data.word.american_audio_url, "/media/audio/old-us.mp3");
  assert.equal(data.audio_sources.us, "/media/audio/old-us.mp3?v=20261017");
});
