import { ref } from "vue";

// Explicit user selection is independent of camera focus and automatic bubbles.
export function useCatWorldInteractionTarget() {
  const interactionCatId = ref("");
  let selectionVersion = 0;

  function selectInteractionCat(cat) {
    interactionCatId.value = String(cat?.profileId || cat?.id || "");
    return ++selectionVersion;
  }

  function clearInteractionCat() {
    interactionCatId.value = "";
    selectionVersion += 1;
  }

  function completeInteractionSelection(version, cat) {
    if (version !== selectionVersion) return false;
    selectInteractionCat(cat);
    return true;
  }

  function buildPlayPayload(item, roomCats = []) {
    const payload = { itemId: item.id };
    if (item.category !== "toy" || !interactionCatId.value) return payload;
    const cat = roomCats.find((entry) => entry.id === interactionCatId.value);
    if (!cat) throw new Error("刚才选中的猫咪已不在当前房间，请重新选择一只猫再玩。");
    return { ...payload, catId: interactionCatId.value };
  }

  return { interactionCatId, selectInteractionCat, clearInteractionCat, completeInteractionSelection, buildPlayPayload };
}
