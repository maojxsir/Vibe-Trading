import type { NavigateFunction } from "react-router-dom";
import { useAgentStore } from "@/stores/agent";
import { api } from "@/lib/api";
import type { AgentMessage } from "@/types/agent";

let _id = 0;
const nextId = () => String(++_id);

/** Prime chat UI before navigating to Agent — shows user msg + ack + streaming state. */
export function primeAgentSession(
  sessionId: string,
  userPrompt: string,
  ackText = "收到，已开始处理您的请求，正在分析…",
): void {
  const now = Date.now();
  const messages: AgentMessage[] = [
    { id: nextId(), type: "user", content: userPrompt, timestamp: now },
    { id: nextId(), type: "status", content: ackText, timestamp: now + 1 },
  ];
  const store = useAgentStore.getState();
  store.cacheSession(sessionId, messages);
  store.setSessionId(sessionId);
  store.setStatus("streaming");
}

export function appendAgentAck(ackText = "收到，已开始处理您的请求，正在分析…"): void {
  useAgentStore.getState().addMessage({
    id: nextId(),
    type: "status",
    content: ackText,
    timestamp: Date.now(),
  });
}

/** Create session, show ack immediately, navigate to Agent, then send in background. */
export async function launchAgentFromPage(
  navigate: NavigateFunction,
  sessionTitle: string,
  userPrompt: string,
  ackText?: string,
): Promise<string> {
  const session = await api.createSession(sessionTitle);
  primeAgentSession(session.session_id, userPrompt, ackText);
  navigate(`/agent?session=${session.session_id}`);
  try {
    await api.sendMessage(session.session_id, userPrompt);
    return session.session_id;
  } catch (error) {
    const store = useAgentStore.getState();
    store.setStatus("error");
    store.clearStatusMessages();
    throw error;
  }
}
