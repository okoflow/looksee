import { negotiateSdp } from "./sdp";

export class WhepNoStreamError extends Error {
  constructor() {
    super("No active stream — the camera is not publishing yet");

    this.name = "WhepNoStreamError";
  }
}

function whepResponseError(response: Response): Error {
  if (response.status === 404) {
    return new WhepNoStreamError();
  }

  return new Error(`WHEP ${response.status} ${response.statusText}`);
}

export async function playWhep(
  whepUrl: string,
  authorization: string,
  video: HTMLVideoElement,
  signal: AbortSignal
): Promise<RTCPeerConnection> {
  signal.throwIfAborted();

  const peerConnection = new RTCPeerConnection({ iceServers: [] });
  let closeSession: (() => void) | undefined;

  peerConnection.addTransceiver("video", { direction: "recvonly" });
  peerConnection.addTransceiver("audio", { direction: "recvonly" });

  peerConnection.ontrack = (event) => {
    const [stream] = event.streams;

    if (stream) {
      video.srcObject = stream;
    }
  };

  const close = () => {
    signal.removeEventListener("abort", close);
    peerConnection.removeEventListener("connectionstatechange", release);
    peerConnection.close();
    closeSession?.();

    video.srcObject = null;
  };
  const release = () => {
    if (peerConnection.connectionState === "closed") {
      signal.removeEventListener("abort", close);
      peerConnection.removeEventListener("connectionstatechange", release);
      closeSession?.();
    }
  };

  signal.addEventListener("abort", close, { once: true });
  peerConnection.addEventListener("connectionstatechange", release);

  try {
    closeSession = await negotiateSdp({
      authorization,
      mapErrorResponse: whepResponseError,
      peerConnection,
      signal,
      url: whepUrl,
    });
  } catch (caught) {
    close();

    throw caught;
  }

  return peerConnection;
}
