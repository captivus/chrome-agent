// chrome.tabs knows each tab's position in its window; chrome.debugger knows
// the CDP target id behind each tab. Joined, they give CDP the tab order it
// has no command for. getTargets does not attach, so no "debugging" banner.
globalThis.tabOrder = async () => {
  const targets = await chrome.debugger.getTargets();
  const byTab = Object.fromEntries(targets.filter(t => t.tabId).map(t => [t.tabId, t.id]));
  const tabs = await chrome.tabs.query({});
  return tabs
    .filter(t => byTab[t.id])
    .map(t => ({targetId: byTab[t.id], windowId: t.windowId, index: t.index}));
};
