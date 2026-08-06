import { isTerminalConnectionState } from "./connection-state";
import { playWhep, WhepNoStreamError } from "./whep";

export type WhepSessionState =
  | { status: "connecting" }
  | { status: "playing" }
  | { status: "waiting" }
  | { status: "error"; error: string };

const NO_STREAM_RETRY_DELAY_MS = 3000;

interface RunWhepSessionArgs {
  authorization: string;
  onStateChange: (state: WhepSessionState) => void;
  signal: AbortSignal;
  url: string;
  video: HTMLVideoElement;
}

export async function runWhepSession({
  authorization,
  onStateChange,
  signal,
  url,
  video,
}: RunWhepSessionArgs): Promise<void> {
  const emit = (state: WhepSessionState) => {
    if (!signal.aborted) {
      onStateChange(state);
    }
  };

  while (!signal.aborted) {
    emit({ status: "connecting" });

    try {
      // biome-ignore lint/performance/noAwaitInLoops: reconnect attempts are inherently sequential
      const peerConnection = await playWhep(url, authorization, video, signal);

      watchPlayback(peerConnection, emit, signal);

      return;
    } catch (caught) {
      if (signal.aborted) {
        return;
      }

      if (!(caught instanceof WhepNoStreamError)) {
        emit({
          status: "error",
          error: caught instanceof Error ? caught.message : "Stream failed",
        });

        return;
      }

      emit({ status: "waiting" });

      await abortableDelay(NO_STREAM_RETRY_DELAY_MS, signal);
    }
  }
}

function watchPlayback(
  peerConnection: RTCPeerConnection,
  emit: (state: WhepSessionState) => void,
  signal: AbortSignal
) {
  const update = () => {
    const state = peerConnection.connectionState;

    if (state === "connected") {
      emit({ status: "playing" });
    } else if (isTerminalConnectionState(state)) {
      emit({ status: "error", error: `Connection ${state}` });
    }
  };

  peerConnection.addEventListener("connectionstatechange", update);

  signal.addEventListener(
    "abort",
    () => {
      peerConnection.removeEventListener("connectionstatechange", update);
    },
    { once: true }
  );

  update();
}

function abortableDelay(delayMs: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, delayMs);

    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);

        resolve();
      },
      { once: true }
    );
  });
}
