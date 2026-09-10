// Google Apps Script fallback trigger for AI News Bot.
// GitHub's own cron scheduler sometimes never registers a brand-new workflow.
// This script runs every 15 minutes (time-driven trigger) and asks GitHub to
// start the workflow via the workflow_dispatch API. Setup steps: README.md.

const OWNER = "baebyungchan";
const REPO = "ainewsbot";
const WORKFLOW = "newsbot.yml";
const BRANCH = "main";

function triggerNewsbot() {
  const token = PropertiesService.getScriptProperties().getProperty("GH_PAT");
  if (!token) throw new Error("Script property GH_PAT is missing (프로젝트 설정 → 스크립트 속성)");
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const res = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    payload: JSON.stringify({ ref: BRANCH }),
    muteHttpExceptions: true,
  });
  const code = res.getResponseCode();
  if (code !== 204) {
    throw new Error(`GitHub returned ${code}: ${res.getContentText().slice(0, 300)}`);
  }
  console.log("dispatched " + new Date().toISOString());
}

// Run this ONCE by hand: installs (or replaces) the every-15-minutes trigger.
function installTrigger() {
  ScriptApp.getProjectTriggers().forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("triggerNewsbot").timeBased().everyMinutes(15).create();
  console.log("trigger installed: triggerNewsbot every 15 min");
}

// Run this to stop the fallback (e.g. once GitHub's own schedule works).
function removeTrigger() {
  ScriptApp.getProjectTriggers().forEach((t) => ScriptApp.deleteTrigger(t));
  console.log("all triggers removed");
}
